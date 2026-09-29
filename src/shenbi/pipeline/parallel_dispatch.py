"""Parallel review dispatch with rate limiting and retry.

Dispatches multiple reviews in parallel via ThreadPoolExecutor, limited by
a threading.Semaphore to MAX_CONCURRENT_REVIEWS (4). Each review has
exponential backoff retry (up to MAX_RETRIES) with random jitter.
"""

from __future__ import annotations

import random
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from threading import Semaphore
from typing import Any
from collections.abc import Callable

from shenbi.logging import get_logger
from shenbi.pipeline.dispatch_helper import DispatchResult, dispatch_skill
from shenbi.pipeline.write_safety import WriteSafety, classify_skill_write_safety

log = get_logger(__name__)

#: Maximum concurrent review dispatches (API rate limit).
MAX_CONCURRENT_REVIEWS = 4

#: Maximum retry attempts for a failed dispatch.
MAX_RETRIES = 2

#: Base for exponential backoff calculation (seconds).
RETRY_BACKOFF_BASE = 2.0

#: Random jitter range for backoff (seconds, uniform [0, jitter]).
#: Spec §5.3/§2.8: jitter must be same-magnitude as RETRY_BACKOFF_BASE
#: to decorrelate parallel workers (old 1.0 was half the base → near-lockstep).
RETRY_JITTER = 2.0


@dataclass
class ReviewTask:
    """A single review dispatch task.

    Attributes:
        skill: The review skill name (e.g. 'shenbi-review-anti-ai').
        project_dir: Project root directory.
        prompt: The review prompt to dispatch.
        output_path: Expected output file path (for tracking).
        shared_context: Optional SharedAuditContext with pre-extracted fields
            (world_rules, character_list, style_profile, pending_hooks) shared
            across all audit calls for a single chapter.
    """

    skill: str
    project_dir: Path
    prompt: str
    output_path: str
    shared_context: Any = None
    #: C33 R4 (F363, spec #47): attempts used (1 = first try). Set by
    #: _dispatch_with_retry; aggregated into retry_budget_consumed at wave
    #: completion by the main thread (_charge_wave_retries in chapter_loop).
    attempts: int = 0


def _dispatch_with_retry(
    task: ReviewTask,
    semaphore: Semaphore,
) -> DispatchResult:
    """Dispatch a single review with retry on failure.

    Uses exponential backoff with random jitter between retry attempts.
    Catches all exceptions and returns a failed DispatchResult rather than
    crashing the batch.

    Args:
        task: The review task to dispatch.
        semaphore: Semaphore for rate limiting concurrent dispatches.

    Returns:
        DispatchResult indicating success or failure.
    """
    for attempt in range(MAX_RETRIES + 1):
        task.attempts = attempt + 1
        try:
            with semaphore:
                log.info(
                    "parallel_dispatch_attempt",
                    skill=task.skill,
                    attempt=attempt + 1,
                    max_retries=MAX_RETRIES,
                )
                result = dispatch_skill(
                    skill=task.skill,
                    project_dir=task.project_dir,
                    prompt=task.prompt,
                    shared_context=task.shared_context,
                )
                if result.success:
                    log.info(
                        "parallel_dispatch_success",
                        skill=task.skill,
                        attempt=attempt + 1,
                    )
                    return result
                log.warning(
                    "parallel_dispatch_failed_attempt",
                    skill=task.skill,
                    attempt=attempt + 1,
                    returncode=result.returncode,
                    stderr=result.stderr[:200],
                )
                # C33 R1 classification point ④ (F533, spec #47): deterministic
                # failures (rc=2 write-audit GATE_FAIL etc.) are not retried —
                # retrying a deterministic outcome burns full-price dispatches.
                from shenbi.contracts.enums import FailureClass
                from shenbi.pipeline.dispatch_helper import classify_dispatch_failure

                if (
                    classify_dispatch_failure(returncode=result.returncode, stderr=result.stderr)
                    is not FailureClass.TRANSIENT
                ):
                    log.warning(
                        "parallel_dispatch_deterministic_no_retry",
                        skill=task.skill,
                        returncode=result.returncode,
                    )
                    return result
        except Exception as exc:
            log.error(
                "parallel_dispatch_exception",
                skill=task.skill,
                attempt=attempt + 1,
                error=str(exc),
            )
            if attempt >= MAX_RETRIES:
                return DispatchResult(False, -1, "", f"All retries exhausted: {exc}")

        # Backoff before retry (skip after last attempt)
        if attempt < MAX_RETRIES:
            delay = RETRY_BACKOFF_BASE**attempt + random.uniform(0, RETRY_JITTER)
            log.debug(
                "parallel_dispatch_backoff",
                skill=task.skill,
                delay=delay,
                attempt=attempt + 1,
            )
            time.sleep(delay)

    # All retries exhausted with failures (non-exception path)
    return DispatchResult(False, -1, "", f"All {MAX_RETRIES} retries exhausted")


def assert_parallelizable(tasks: list[ReviewTask]) -> None:
    """Verify every task's skill is safe to run concurrently (spec §3.4).

    Raises ValueError listing any task whose skill is not READ_ONLY_AUDIT.
    Called before threads are spawned so a write-shared skill can never
    reach the concurrent path.
    """
    unsafe = [
        f"{t.skill}={classify_skill_write_safety(t.skill).value}"
        for t in tasks
        if classify_skill_write_safety(t.skill) != WriteSafety.READ_ONLY_AUDIT
    ]
    if unsafe:
        raise ValueError(
            "refusing to parallelize non-read-only skills (WRITE_SHARED/"
            f"WRITE_ISOLATED must run serially per spec §3.4): {unsafe}"
        )


def dispatch_reviews_parallel(
    tasks: list[ReviewTask],
    on_task_complete: Callable[[int, DispatchResult], None] | None = None,
) -> list[DispatchResult]:
    """Dispatch multiple reviews in parallel with rate limiting.

    Uses ThreadPoolExecutor for parallelism and a Semaphore to limit
    concurrent API calls to MAX_CONCURRENT_REVIEWS.

    Args:
        tasks: List of ReviewTask objects to dispatch.
        on_task_complete: C30 F377 midpoint save point — invoked from the
            collecting loop as each task finishes, with ``(task_index,
            result)``. Contract: called ONLY for successful results (failed
            tasks are not called back); called from the single collecting
            thread; a raising callback is logged and does not abort the wave.

    Returns:
        List of DispatchResult objects, one per task (order preserved).
    """
    if not tasks:
        return []
    assert_parallelizable(tasks)  # spec §3.4 — never parallelize write-capable skills

    semaphore = Semaphore(MAX_CONCURRENT_REVIEWS)
    results: dict[int, DispatchResult] = {}

    with ThreadPoolExecutor(max_workers=len(tasks)) as executor:
        future_to_idx = {
            executor.submit(_dispatch_with_retry, task, semaphore): idx
            for idx, task in enumerate(tasks)
        }
        for future in as_completed(future_to_idx):
            idx = future_to_idx[future]
            try:
                results[idx] = future.result()
            except Exception as exc:
                log.error(
                    "parallel_dispatch_future_error",
                    index=idx,
                    error=str(exc),
                )
                results[idx] = DispatchResult(False, -1, "", str(exc))
            if on_task_complete is not None and results[idx].success:
                try:
                    on_task_complete(idx, results[idx])
                except Exception as cb_exc:
                    log.error(
                        "parallel_wave_callback_failed",
                        index=idx,
                        error=str(cb_exc),
                    )

    return [results[i] for i in range(len(tasks))]


def consolidate_review_results(
    results: list[DispatchResult],
    chapter: int,
    skills: list[str] | None = None,
    project_dir: Any = None,
    cascade_skipped: list[str] | None = None,
) -> str:
    """Aggregate review results into a consolidated summary.

    Scans all review outputs for BLOCKING and CRITICAL markers and produces
    a markdown summary with issue counts and details.

    Args:
        results: List of DispatchResult from dispatched reviews.
        chapter: Chapter number being reviewed.
        skills: Skill names aligned with *results* (attribution replaces the
            anonymous "Review #N" labels).
        project_dir: Project root — when given, the audits/chapter-N-*.md
            FILES are scanned for severity markers (the actual artifacts;
            stdout is routinely empty).
        cascade_skipped: Skills skipped by the N-streak cascade this chapter
            (disclosed in the summary).

    Returns:
        Markdown-formatted consolidation summary.
    """
    skills = skills if skills is not None else []
    blocking_lines: list[str] = []
    critical_lines: list[str] = []

    def _label(i: int) -> str:
        return skills[i] if i < len(skills) else f"Review #{i + 1}"

    for i, result in enumerate(results):
        if not result.success:
            continue
        for line in result.stdout.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            upper = stripped.upper()
            if upper.startswith("BLOCKING"):
                blocking_lines.append(f"- {_label(i)}: {stripped}")
            elif upper.startswith("CRITICAL"):
                critical_lines.append(f"- {_label(i)}: {stripped}")

    # The review artifacts are the audits/chapter-N-*.md FILES — result
    # stdout is routinely empty, and canary's 漏并 7/13 + the probe's
    # vacuous zero-findings both traced to scanning stdout only. Scan the
    # files with the severity regexes (same semantics as the router).
    if project_dir is not None:
        import re as _re

        from pathlib import Path as _Path

        audit_dir = _Path(project_dir) / "audits"
        blocking_re = _re.compile(
            r"\*\*BLOCKING\*\*|(?:severity|严重度)\*{0,2}\W{0,6}BLOCKING\b", _re.IGNORECASE
        )
        critical_re = _re.compile(
            r"\*\*CRITICAL\*\*|(?:severity|严重度)\*{0,2}\W{0,6}CRITICAL\b", _re.IGNORECASE
        )
        for audit_file in sorted(audit_dir.glob(f"chapter-{chapter}-*.md")):
            content = audit_file.read_text(encoding="utf-8")
            hit = None
            if blocking_re.search(content):
                hit = "BLOCKING"
            elif critical_re.search(content):
                hit = "CRITICAL"
            if hit:
                lines_ = content.splitlines()
                idx = next(
                    (j for j, l in enumerate(lines_) if l.strip() and hit in l.upper()),
                    None,
                )
                line = lines_[idx].strip() if idx is not None else audit_file.name
                # finding prose: first non-empty line after the marker that is
                # not itself a severity marker or a heading
                for l in lines_[(idx + 1) if idx is not None else 0 :]:
                    t = l.strip()
                    if t and not t.startswith(("#", "```")) and hit not in t.upper():
                        line = f"{line} — {t}"
                        break
                owner = audit_file.name
                for sk in skills:
                    short = sk.replace("shenbi-review-", "")
                    if short and short in audit_file.name:
                        owner = sk
                        break
                entry = f"- {owner} ({audit_file.name}): {line}"
                (blocking_lines if hit == "BLOCKING" else critical_lines).append(entry)

    failed_count = sum(1 for r in results if not r.success)
    success_count = sum(1 for r in results if r.success)

    parts = [
        f"# Chapter {chapter} — Consolidated Review Results",
        "",
        f"- **Reviews executed**: {len(results)}",
        f"- **Successful**: {success_count}",
        f"- **Failed**: {failed_count}",
        f"- **BLOCKING Issues**: {len(blocking_lines)}",
        f"- **CRITICAL Issues**: {len(critical_lines)}",
    ]
    if cascade_skipped:
        parts.append(
            f"- **cascade-skipped** (N-streak heuristic, re-verified every few chapters): "
            f"{', '.join(cascade_skipped)}"
        )
    parts += [
        "",
    ]

    if blocking_lines:
        parts.append("## BLOCKING Issues")
        parts.extend(blocking_lines)
        parts.append("")

    if critical_lines:
        parts.append("## CRITICAL Issues")
        parts.extend(critical_lines)
        parts.append("")

    if not blocking_lines and not critical_lines:
        parts.append("No BLOCKING or CRITICAL issues found across all reviews.")
        parts.append("")

    return "\n".join(parts)
