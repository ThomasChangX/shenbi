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

from shenbi.logging import get_logger
from shenbi.pipeline.dispatch_helper import DispatchResult, dispatch_skill

log = get_logger(__name__)

#: Maximum concurrent review dispatches (API rate limit).
MAX_CONCURRENT_REVIEWS = 4

#: Maximum retry attempts for a failed dispatch.
MAX_RETRIES = 2

#: Base for exponential backoff calculation (seconds).
RETRY_BACKOFF_BASE = 2.0

#: Random jitter range for backoff (seconds, uniform [0, jitter]).
RETRY_JITTER = 1.0


@dataclass
class ReviewTask:
    """A single review dispatch task.

    Attributes:
        skill: The review skill name (e.g. 'shenbi-review-anti-ai').
        project_dir: Project root directory.
        prompt: The review prompt to dispatch.
        output_path: Expected output file path (for tracking).
    """

    skill: str
    project_dir: Path
    prompt: str
    output_path: str


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


def dispatch_reviews_parallel(
    tasks: list[ReviewTask],
) -> list[DispatchResult]:
    """Dispatch multiple reviews in parallel with rate limiting.

    Uses ThreadPoolExecutor for parallelism and a Semaphore to limit
    concurrent API calls to MAX_CONCURRENT_REVIEWS.

    Args:
        tasks: List of ReviewTask objects to dispatch.

    Returns:
        List of DispatchResult objects, one per task (order preserved).
    """
    if not tasks:
        return []

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

    return [results[i] for i in range(len(tasks))]


def consolidate_review_results(
    results: list[DispatchResult],
    chapter: int,
) -> str:
    """Aggregate review results into a consolidated summary.

    Scans all review outputs for BLOCKING and CRITICAL markers and produces
    a markdown summary with issue counts and details.

    Args:
        results: List of DispatchResult from dispatched reviews.
        chapter: Chapter number being reviewed.

    Returns:
        Markdown-formatted consolidation summary.
    """
    blocking_lines: list[str] = []
    critical_lines: list[str] = []

    for i, result in enumerate(results):
        if not result.success:
            continue
        for line in result.stdout.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            upper = stripped.upper()
            if upper.startswith("BLOCKING"):
                blocking_lines.append(f"- Review #{i + 1}: {stripped}")
            elif upper.startswith("CRITICAL"):
                critical_lines.append(f"- Review #{i + 1}: {stripped}")

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
