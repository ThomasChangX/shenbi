"""Chapter loop orchestrator: per-chapter step sequence with staging, context
assembly, and G4 validation (spec section 6.1).

The chapter loop runs 20 steps per chapter (the spec's 13-step loop expanded
with individual audit-circle skills). Steps 2 (chapter-planning) and 7
(state-settling) write to ``staging/`` and are gated by human-review
checkpoints. Step 4 (pipeline-context-assemble) materializes the three-route
context package (section 7) before chapter-drafting consumes it.

Each dispatched step runs G4 (skill-specific structure). Step 17
(review-resonance) additionally runs G3 (scoring independence) because it is a
``requires_independent_agent`` skill.

dispatch/gate failures retry per spec section 11: up to
``max_revision_retries`` attempts, then an escalation checkpoint is raised.
The retry decision is delegated to
``shenbi.pipeline.error_handler.handle_dispatch_failure`` (W3T8).

Steps 8-11 (audit genre circle + revision routing) are stubbed: W3T4
implements the audit layer, W3T5 implements revision routing. Clear TODO
markers indicate the integration points.
Revision routing (W3T5) is integrated: after review-resonance the router
determines the route and step 18 (chapter-revision) is skipped when no
revision is needed.

The orchestrator is stateless itself: it mutates the passed-in
:class:`PipelineState` in memory and the caller persists it.
"""

from __future__ import annotations

import atexit as _atexit
import json
import re
import shutil as _shutil
import signal as _signal
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from shenbi.skill_utils.drift_detection.linguistic_drift import DriftResult

from shenbi.contracts.paths import resolve_chapter_path
from shenbi.contracts.schemas.hooks import HookState, parse_hook_state

import yaml

from shenbi.logging import get_logger
from shenbi.safe_write import safe_write
from shenbi.pipeline.audit_layer import run_audit_layer
from shenbi.pipeline.dispatch_helper import (
    dispatch_skill,
    requires_independent,
    run_gate_g3,
    run_gate_g4,
)
from shenbi.pipeline.snapshot_diff import create_differential_snapshot
from shenbi.pipeline.machine import set_checkpoint
from shenbi.pipeline.revision_router import (
    RevisionRoute,
    check_resonance,
    collect_audit_issues,
    dispatch_escalation,
    route_chapter_revision,
)
from shenbi.pipeline.state import (
    ChapterState,
    CheckpointType,
    PipelineState,
    SoftFailTracker,
)
from shenbi.exceptions import RetryExhaustedError
from shenbi.skill_utils.escalation.check import check_escalation
from shenbi.status import GateStatus
from datetime import UTC

log = get_logger(__name__)


# ---------------------------------------------------------------------------
# Module-level storage for emergency snapshot params (spec §3.6).
# Set at pipeline init, consumed by the atexit + signal handlers.
# This is the "checkpoint-on-step": updated on every chapter-loop step so the
# signal handler always knows the latest chapter to snapshot on SIGTERM/SIGINT.
# ---------------------------------------------------------------------------
_emergency_snapshot_project_dir: Path | None = None
_emergency_snapshot_chapter: int = 0
_emergency_signal_handler_installed: bool = False
_emergency_flag: bool = False


@dataclass
class ChapterStep:
    """One step in the per-chapter sequence (spec section 6.1).

    Attributes:
        step_num: 1-based step number for logging.
        skill: Skill name dispatched (``shenbi-*``) or pipeline-internal
            identifier (``pipeline-*`` -- not dispatched, just advanced).
        name: Human-readable label.
        checkpoint: Checkpoint type raised after this step succeeds, or None.
        uses_staging: If True, the dispatched skill writes to ``staging/``
            and G4 validates the staging copy (spec section 2.7).
        calls_context_assembly: If True, run :func:`assemble_context` before
            dispatching this step (materializes ``context/chapter-N-context.md``).
        is_audit: If True, this step is part of the audit core circle.
        output_path: Expected output file relative to project dir (with N
            placeholders for chapter number). Used for G4 validation. Empty
            string means no single file (G4 validates generically).
    """

    step_num: int
    skill: str
    name: str
    checkpoint: CheckpointType | None = None
    uses_staging: bool = False
    calls_context_assembly: bool = False
    is_audit: bool = False
    output_path: str = ""


# Full 13-step + sub-steps from spec section 6.1.
# The audit layer (spec step 8) is expanded into 7 individual core-circle
# skills for serial execution. Genre-circle skills are dispatched dynamically
# by the audit sub-orchestrator (W3T4).
CHAPTER_STEPS: list[ChapterStep] = [
    ChapterStep(
        1,
        "shenbi-intent-management",
        "intent-management",
        output_path="truth/current_focus.md",
    ),
    ChapterStep(
        2,
        "shenbi-chapter-planning",
        "chapter-planning",
        checkpoint=CheckpointType.CHAPTER_MEMO,
        uses_staging=True,
        output_path="plans/chapter-N-plan.md",
    ),
    ChapterStep(
        3,
        "shenbi-foreshadowing-plant",
        "foreshadowing-plant",
        output_path="truth/pending_hooks.md",
    ),
    ChapterStep(
        4,
        "pipeline-context-assemble",
        "context-assembly",
        calls_context_assembly=True,
        output_path="context/chapter-N-context.md",
    ),
    ChapterStep(
        5,
        "shenbi-context-composing",
        "context-composing",
        output_path="",
    ),
    ChapterStep(
        6,
        "shenbi-chapter-drafting",
        "chapter-drafting",
        output_path="chapters/chapter-N.md",
    ),
    ChapterStep(
        7,
        "shenbi-state-settling",
        "state-settling",
        checkpoint=CheckpointType.STATE_SETTLE,
        uses_staging=True,
        output_path="",
    ),
    ChapterStep(
        8,
        "shenbi-foreshadowing-track",
        "foreshadowing-track",
        output_path="truth/pending_hooks.md",
    ),
    ChapterStep(
        9,
        "shenbi-foreshadowing-recall",
        "foreshadowing-recall",
        output_path="truth/foreshadowing_recall_result.md",
    ),
    # foreshadowing-resolve is conditional -- handled in run_chapter_step
    # after foreshadowing-track succeeds (spec section 6.1 step 7b).
    # Audit core circle: 7 skills, serial, BLOCKING stops (spec section 6.2).
    ChapterStep(
        10,
        "shenbi-review-anti-ai",
        "audit:anti-ai",
        is_audit=True,
        output_path="audits/chapter-N-anti-ai.md",
    ),
    ChapterStep(
        11,
        "shenbi-review-continuity",
        "audit:continuity",
        is_audit=True,
        output_path="audits/chapter-N-continuity.md",
    ),
    ChapterStep(
        12,
        "shenbi-review-character",
        "audit:character",
        is_audit=True,
        output_path="audits/chapter-N-character.md",
    ),
    ChapterStep(
        13,
        "shenbi-review-pacing",
        "audit:pacing",
        is_audit=True,
        output_path="audits/chapter-N-pacing.md",
    ),
    ChapterStep(
        14,
        "shenbi-review-foreshadowing",
        "audit:foreshadowing",
        is_audit=True,
        output_path="audits/chapter-N-foreshadowing.md",
    ),
    ChapterStep(
        15,
        "shenbi-review-memo-compliance",
        "audit:memo-compliance",
        is_audit=True,
        output_path="audits/chapter-N-memo-compliance.md",
    ),
    ChapterStep(
        16,
        "shenbi-review-pov",
        "audit:pov",
        is_audit=True,
        output_path="audits/chapter-N-pov.md",
    ),
    # Genre circle dispatched dynamically by audit sub-orchestrator (W3T4).
    # TODO(W3T4): from shenbi.pipeline.audit_layer import run_audit_layer
    #   Call after step 16 (last core-circle audit) to run genre-circle skills.
    # review-resonance (independent agent, G3 required, spec section 6.1 step 9).
    ChapterStep(
        17,
        "shenbi-review-resonance",
        "review-resonance",
        output_path="audits/chapter-N-resonance.md",
    ),
    # Revision routing + execution (conditional, spec section 6.1 steps 10-11).
    # Revision routing runs after review-resonance (W3T5 integrated, spec §6.3).
    # Step 18 is skipped when route == RevisionRoute.NO_REVISION.
    ChapterStep(
        18,
        "shenbi-chapter-revision",
        "revision",
        output_path="chapters/chapter-N.md",
    ),
    # Snapshot + drift (spec section 6.1 steps 12-13).
    # D20: snapshot-manage is handled inline by _snapshot_chapter_files, which
    # writes a timestamped flatfile snapshots/chapter-NNN-{ts}.md (never a
    # fixed path). The old output_path="snapshots/chapter-NNN/" was a fictional
    # directory that never existed on disk. Empty output_path = no single file.
    ChapterStep(
        19,
        "shenbi-snapshot-manage",
        "snapshot-manage",
        output_path="",
    ),
    ChapterStep(
        20,
        "shenbi-drift-guidance",
        "drift-guidance",
        output_path="truth/drift_guidance.md",
    ),
]

# 0-based index of the first core-circle audit step (for parallel dispatch trigger).
_FIRST_AUDIT_IDX = min(i for i, s in enumerate(CHAPTER_STEPS) if s.is_audit)

# 0-based index of the last core-circle audit step (for genre-circle trigger).
_LAST_AUDIT_IDX = max(i for i, s in enumerate(CHAPTER_STEPS) if s.is_audit)


# ---------------------------------------------------------------------------
# Audit Cascading (Spec 8 Fix 8)
# ---------------------------------------------------------------------------

# Core 4 pass, skip 8 (NOT "skip 9").
# memo-compliance and resonance ALWAYS run (scoring requires them) — they are
# excluded from CASCADABLE_AUDITS and are never cascade-skipped. There is no
# "confidence >90%" signal available; instead we use an N=3 chapter streak with
# zero HARD failures as the cascade trigger.

CORE_AUDITS = ["continuity", "character", "world-rules", "pacing"]

ALWAYS_RUN = {"memo-compliance", "resonance"}

CASCADABLE_AUDITS = [
    "dialogue",
    "motivation",
    "sensitivity",
    "foreshadowing",
    "pov",
    "anti-ai",
    "texture",
    "reader-pull",
]

CASCADE_STREAK_LENGTH = 3  # N=3


def _should_skip_audit(skill: str, audit_history: list[dict[str, Any]]) -> bool:
    """N-chapter-streak cascade heuristic (Spec 8 Fix 8).

    Skip `skill` only when ALL of the following hold:
      1. `skill` is in CASCADABLE_AUDITS (core audits and ALWAYS_RUN audits run).
      2. We have at least N=3 chapters of history for `skill`.
      3. Each of the trailing N=3 entries for `skill` passed with zero HARD
         failures.

    Args:
        skill: audit skill short-name (e.g. "dialogue", "continuity").
        audit_history: list of per-chapter audit result dicts, most-recent-last.
            Each entry maps skill -> {"passed": bool, "hard_failures": int}.

    Returns:
        True if the audit may be cascade-skipped this chapter.
    """
    # Core audits and always-run audits are never cascade-skipped.
    if skill in CORE_AUDITS or skill in ALWAYS_RUN:
        return False
    if skill not in CASCADABLE_AUDITS:
        return False  # Unknown skill → run normally

    # Need at least N=3 chapters of history to establish a streak.
    recent = audit_history[-CASCADE_STREAK_LENGTH:]
    if len(recent) < CASCADE_STREAK_LENGTH:
        return False

    for chapter_results in recent:
        result = chapter_results.get(skill)
        if result is None:
            return False  # No record for this skill in that chapter → no streak
        if not result.get("passed", False):
            return False  # Did not pass → break streak
        if result.get("hard_failures", 0) > 0:
            return False  # Any HARD failure → break streak

    return True  # N=3 streak of zero-HARD-failure passes → cascade-skip


def _get_audit_history(state: PipelineState, current_chapter: int) -> list[dict[str, Any]]:
    """Extract audit results from previous chapters in pipeline state.

    Returns list of dicts with keys: skill, chapter, passed, issues
    for all audit results from chapters < current_chapter.
    The returned list is most-recent-last (sorted by chapter number).
    """
    results: list[dict[str, Any]] = []
    for ch_num, ch_state in sorted(state.chapter_loop.chapter_states.items()):
        ch_num_int = int(ch_num)
        if ch_num_int >= current_chapter:
            continue
        for audit_key, audit_result in ch_state.audit_results.items():
            if isinstance(audit_result, dict):
                results.append(
                    {
                        "skill": audit_key,
                        "chapter": ch_num_int,
                        "passed": audit_result.get("passed", False),
                        "hard_failures": audit_result.get("hard_failures", 0),
                        "issues": audit_result.get("issues", []),
                    }
                )
    return results


def _audit_short_name(skill_name: str) -> str:
    """Map full skill name to short audit dimension name.

    Examples:
        "shenbi-review-anti-ai" -> "anti-ai"
        "shenbi-review-continuity" -> "continuity"
        "shenbi-review-dialogue" -> "dialogue"
    """
    return skill_name.replace("shenbi-review-", "")


# ---------------------------------------------------------------------------
# G4 Severity Classification (spec §11)
# ---------------------------------------------------------------------------


class G4Severity(StrEnum):
    """Classification of G4 validation failures."""

    HARD = "hard"
    SOFT = "soft"
    WARN = "warn"


G4_CHECK_MAP: dict[str, G4Severity] = {
    "not_found": G4Severity.HARD,
    "pre_check": G4Severity.HARD,
    "post_check": G4Severity.HARD,
    "meta": G4Severity.HARD,
    "word_count": G4Severity.HARD,
    "no_visual_scene": G4Severity.HARD,
    "content_overlap": G4Severity.HARD,
    "no_valid_verdict": G4Severity.HARD,
    "no_file_line_ref": G4Severity.HARD,
    "missing_cols": G4Severity.HARD,
    "missing_sections": G4Severity.HARD,
    "no_result": G4Severity.HARD,
    "no_evidence": G4Severity.HARD,
    "cp.sections": G4Severity.HARD,
    "cp.chapter_role": G4Severity.HARD,
    "cp.s7_hook_ops": G4Severity.HARD,
    "transition": G4Severity.SOFT,
    "fatigue": G4Severity.SOFT,
    "cd.chapter_end_hook": G4Severity.SOFT,
    "cp.golden": G4Severity.WARN,
    "cp.s5_choice": G4Severity.WARN,
}


def _classify_g4_failures(must_fix: list[str]) -> tuple[list[str], list[str], list[str]]:
    """Partition G4 must_fix into (hard, soft, warn) by substring matching against G4_CHECK_MAP."""
    hard: list[str] = []
    soft: list[str] = []
    warn: list[str] = []
    for item in must_fix:
        matched = False
        for key, severity in G4_CHECK_MAP.items():
            if key in item:
                if severity == G4Severity.HARD:
                    hard.append(item)
                elif severity == G4Severity.SOFT:
                    soft.append(item)
                else:
                    warn.append(item)
                matched = True
                break
        if not matched:
            hard.append(item)  # conservative default
    return hard, soft, warn


def _extract_check_id(must_fix_item: str) -> str:
    """Extract the G4 check ID from a must_fix string like 'G4.transition:path:7>6'."""
    m = re.match(r"G4\.([a-z_.]+)", must_fix_item)
    return m.group(1) if m else must_fix_item.split(":", maxsplit=1)[0].replace("G4.", "")


# ---------------------------------------------------------------------------
# G4 format examples for enriched retry feedback (Task 6)
# ---------------------------------------------------------------------------


G4_FORMAT_EXAMPLES: dict[str, str] = {
    "G4.rr.detail_table": (
        "评分明细表格式：\n"
        "| 维度 | 得分 | 满分 | 置信度 | 证据 | 裁判理由 |\n"
        "|------|------|------|--------|------|----------|\n"
        '| 情感落地 | 25 | 30 | 高 | chapter-N.md L45-52 > "..." | ... |\n'
        "注意：六列必须完整，不可缺列。"
    ),
    "G4.rr.verdict": (
        "校准门判定必须包含以下行：\n"
        "判定: 通过    （或：判定: 阻断  / 判定: 待人机复核）\n"
        "注意：'判定: ' 后必须有空格，且必须使用中文冒号"
    ),
    "G4.rr.evidence": (
        "证据列每行必须包含文件和行号引用，格式：\n"
        'chapter-N.md L45-52 > "引用原文"\n'
        "至少一行包含 Lnn 或 line nn 格式的行号引用。"
    ),
}


def _enrich_g4_feedback(failures: list[str]) -> str:
    """Build enriched retry feedback with format examples for each failed check.

    For each failure in ``failures``, extracts the check ID prefix and
    appends the corresponding format example from ``G4_FORMAT_EXAMPLES``.
    Failures without a known check ID receive generic retry guidance.

    Args:
        failures: List of G4 failure strings (e.g., "G4.rr.verdict:file.md:reason").

    Returns:
        A formatted feedback string suitable for inclusion in retry prompts.
    """
    lines = ["以下 G4 检查失败，请按指定格式修正：", ""]
    for f in failures:
        # Extract check ID prefix (e.g., "G4.rr.verdict" from "G4.rr.verdict:file:reason")
        check_prefix = f.split(":")[0] if ":" in f else f
        lines.append(f"- **{f}**")
        if check_prefix in G4_FORMAT_EXAMPLES:
            lines.append("  期望格式：")
            for fmt_line in G4_FORMAT_EXAMPLES[check_prefix].split("\n"):
                lines.append(f"  {fmt_line}")
        else:
            lines.append("  (请重新生成此检查的输出以达到标准格式)")
        lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Drift escalation exception
# ---------------------------------------------------------------------------


class DriftEscalationError(Exception):
    """Raised when linguistic drift reaches ESCALATE severity."""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _gate_passed(result: dict[str, Any]) -> bool:
    """True iff a gate result dict reports PASS (handles str and GateStatus)."""
    return str(result.get("status", "")) == GateStatus.PASS


def _retry_key(chapter: int, skill: str) -> str:
    """Chapter-scoped retry key so retries from different chapters don't collide."""
    return f"ch{chapter}-{skill}"


def _resolve_g4_path(project_dir: Path, step: ChapterStep, chapter: int) -> str:
    """Resolve the output file path for G4 validation.

    For staging steps, returns the staging-relative path so G4 validates the
    staging copy (not the final committed path). Empty string if the step has
    no single output file.
    """
    if not step.output_path:
        return ""
    resolved = resolve_chapter_path(step.output_path, chapter)
    if step.uses_staging:
        from shenbi.pipeline.checkpoint import STAGING_DIR

        return f"{STAGING_DIR}/{resolved}"
    return resolved


def _resolve_g4_files(project_dir: Path, step: ChapterStep, chapter: int) -> list[str]:
    """Return list of file paths for G4 validation.

    Single-file steps return one path. State-settling returns all
    staging/truth/*.md files because it writes multiple truth outputs.
    Steps with no output return [].
    """
    single = _resolve_g4_path(project_dir, step, chapter)
    if single:
        return [single]

    # State-settling writes multiple truth files to staging/
    if step.uses_staging and "state-settling" in step.skill:
        from shenbi.pipeline.checkpoint import STAGING_DIR

        staging_truth = project_dir / STAGING_DIR / "truth"
        if staging_truth.exists():
            return sorted(f"{STAGING_DIR}/truth/{p.name}" for p in staging_truth.glob("*.md"))

    return []


def _handle_failure(
    state: PipelineState,
    step: ChapterStep,
    chapter: int,
    failure: str,
    project_dir: Path | str,
    *,
    budget_pre_consumed: bool = False,
) -> bool:
    """Record a dispatch/gate failure for a chapter step.

    Retries per spec section 11 up to ``max_revision_retries`` (default 3),
    then raises an escalation checkpoint. Returns False when the step should
    be retried on the next call (step_index unchanged) or True once an
    escalation checkpoint has been raised.

    When *budget_pre_consumed* is True, the caller has already incremented
    ``retry_budget_consumed`` (e.g. G4 hard-fail path), so this function
    skips its own increment to avoid double-counting.
    """
    key = _retry_key(chapter, step.skill)
    count = state.chapter_loop.retry_counts.get(key, 0) + 1
    state.chapter_loop.retry_counts[key] = count

    # Durable budget (spec §3.1): NOT cleared by _reset_retries, so crash-resume
    # can enforce max_audit_retries even after a successful retry.
    if not budget_pre_consumed:
        consumed = state.chapter_loop.retry_budget_consumed.get(key, 0) + 1
        state.chapter_loop.retry_budget_consumed[key] = consumed
    else:
        consumed = state.chapter_loop.retry_budget_consumed.get(key, 0)
    if consumed > state.config.max_audit_retries:
        log.error(
            "retry_budget_exhausted",
            chapter=chapter,
            skill=step.skill,
            consumed=consumed,
            max=state.config.max_audit_retries,
        )
        raise RetryExhaustedError(
            f"Retry budget ({state.config.max_audit_retries}) exhausted for {key} "
            f"(consumed {consumed})"
        )

    from shenbi.pipeline.error_handler import handle_dispatch_failure

    if handle_dispatch_failure(state, step.skill, count):
        log.warning(
            "chapter_step_failed_retrying",
            chapter=chapter,
            step=step.step_num,
            skill=step.skill,
            failure=failure,
            attempt=count,
            limit=state.config.max_revision_retries,
        )
        return False
    # Retries exhausted: dispatch escalation-review first, then set checkpoint.
    from shenbi.pipeline.revision_router import dispatch_escalation

    dispatch_escalation(
        project_dir,
        chapter,
        context=f"Chapter {chapter} step {step.step_num} ({step.skill}) failed after {count} {failure} attempts",
    )
    log.error(
        "chapter_step_escalation",
        chapter=chapter,
        step=step.step_num,
        skill=step.skill,
        failure=failure,
        attempts=count,
    )
    set_checkpoint(
        state,
        CheckpointType.ESCALATION,
        chapter=chapter,
        artifact=f"audits/escalation-{chapter}-report.md",
        context=(
            f"Chapter {chapter} step {step.step_num} ({step.skill}) "
            f"failed after {count} {failure} attempts. "
            f"See audits/escalation-{chapter}-report.md for analysis."
        ),
    )
    return True


def _record_step_done(state: PipelineState, step: ChapterStep, chapter: int) -> None:
    """Append the skill to the chapter's steps_done list."""
    key = str(chapter)
    cs = state.chapter_loop.chapter_states.get(key)
    if cs is None:
        cs = ChapterState()
        state.chapter_loop.chapter_states[key] = cs
    if step.skill not in cs.steps_done:
        cs.steps_done.append(step.skill)


def _reset_retries(state: PipelineState, step: ChapterStep, chapter: int) -> None:
    """Clear retry count after a successful step."""
    state.chapter_loop.retry_counts.pop(_retry_key(chapter, step.skill), None)


def _complete_chapter(state: PipelineState, chapter: int) -> bool:
    """Advance to the next chapter, optionally setting a per-chapter checkpoint.

    Returns True when a per-chapter checkpoint is set (review needed), False
    when automatic advancement is configured.
    """
    key = str(chapter)
    cs = state.chapter_loop.chapter_states.get(key)
    if cs is None:
        cs = ChapterState()
        state.chapter_loop.chapter_states[key] = cs
    cs.status = "complete"

    state.chapter_loop.current_chapter = chapter + 1
    state.chapter_loop.step_index = 0
    state.chapter_loop.current_step = ""

    if state.chapter_loop.per_chapter_review_enabled:
        set_checkpoint(
            state,
            CheckpointType.PER_CHAPTER,
            chapter=chapter,
            context=(
                f"Chapter {chapter} complete. Review before proceeding to chapter {chapter + 1}."
            ),
        )
        return True
    return False


def _find_current_volume(chapter: int, volume_boundaries: set[int]) -> int | None:
    """Return the volume index (0-based) that *chapter* belongs to.

    *volume_boundaries* is a set of last-chapter numbers per volume (from
    ``read_volume_boundaries``). Returns ``None`` when boundaries are empty or
    *chapter* lies beyond the last boundary.
    """
    if not volume_boundaries:
        return None
    sorted_boundaries = sorted(volume_boundaries)
    for idx, boundary in enumerate(sorted_boundaries):
        if chapter <= boundary:
            return idx
    return None  # chapter beyond last boundary


def _check_volume_completion(project_dir: Path, current_volume: int | None, chapter: int) -> bool:
    """Check whether the current volume's objective has been met.

    Stub: returns True (volume objective met) when *current_volume* is None;
    otherwise checks for a ``context/volume-{n}-complete.json`` marker file.
    """
    if current_volume is None:
        return True
    marker = project_dir / "context" / f"volume-{current_volume}-complete.json"
    return marker.exists()


def _check_soft_fail_escalation(state: PipelineState, project_dir: Path, chapter: int) -> None:
    """Consume soft-fail-tracker escalation and route to check_escalation.

    Spec 22 E32: the trackers detected transition/fatigue drift but the signal
    was orphaned. This wires it to the existing ``check_escalation`` consumer
    using its real signature. When any tracker has crossed its threshold AND
    ``check_escalation`` fires >=1 signal, dispatch escalation-review via the
    existing ``dispatch_escalation`` path.
    """
    from shenbi.pipeline.triggers import read_volume_boundaries

    any_escalated = any(
        len(t.occurrences) >= t.escalation_threshold
        for t in state.chapter_loop.soft_fail_trackers.values()
    )
    if not any_escalated:
        return

    # Gather check_escalation inputs (real signature).
    resonance_scores: list[float] = [
        float(s) for s in _get_recent_resonance_scores(project_dir, chapter, window=5)
    ]
    sensitivity_blocking = any(
        "sensitivity" in (cid or "").lower()
        for cid, t in state.chapter_loop.soft_fail_trackers.items()
        if len(t.occurrences) >= t.escalation_threshold
    )
    # Check if volume boundary is met by reading volume_map.md
    volume_boundaries = read_volume_boundaries(project_dir)
    current_volume = _find_current_volume(chapter, volume_boundaries)
    volume_objective_met = _check_volume_completion(project_dir, current_volume, chapter)
    # regeneration_attempts: max per-step retry count currently in flight.
    regeneration_attempts = max(state.chapter_loop.retry_counts.values(), default=0)

    signals = check_escalation(
        resonance_scores=resonance_scores,
        sensitivity_blocking=sensitivity_blocking,
        volume_objective_met=volume_objective_met,
        regeneration_attempts=regeneration_attempts,
    )
    if not signals:
        log.info(
            "soft_fail_escalation_no_signals",
            chapter=chapter,
            scores=resonance_scores,
        )
        return

    log.warning(
        "soft_fail_escalation_triggered",
        chapter=chapter,
        signals=[{"trigger": s.trigger, "detail": s.detail} for s in signals],
    )
    # dispatch_escalation's real signature is (project_dir, chapter, context="").
    # It has no `reason=` / `signals=` kwargs. Write the signals to a sidecar
    # file the escalation skill can read, then dispatch with context pointing
    # to that file.
    from dataclasses import asdict

    signals_path = project_dir / "context" / f"chapter-{chapter}-escalation-signals.json"
    safe_write(
        signals_path,
        json.dumps([asdict(s) for s in signals], ensure_ascii=False, indent=2),
    )
    dispatch_escalation(
        project_dir,
        chapter,
        context=f"Soft-fail escalation triggered. Signals at: {signals_path}",
    )


def _advance(
    state: PipelineState,
    step_idx: int,
    step: ChapterStep,
    chapter: int,
    project_dir: Path | None = None,
) -> bool:
    """Bump the step cursor and set checkpoint if the step has one.

    Returns True if a checkpoint was raised or the chapter completed;
    False if the step simply advanced with no human action needed.

    Checkpoint suppression (--auto mode): when the corresponding config
    flag is False the checkpoint is silently skipped, staging files are
    auto-committed to their final paths, and the cursor advances as if
    it were a non-checkpoint step.
    """
    if project_dir is None:
        project_dir = Path(state.project_dir)

    state.chapter_loop.step_index = step_idx + 1
    state.chapter_loop.current_step = ""

    if step.checkpoint is not None:
        # Honour --auto suppression flags so automated runs aren't
        # blocked on every chapter-memo / state-settle.
        cfg = state.config
        if step.checkpoint == CheckpointType.CHAPTER_MEMO and not cfg.chapter_memo_review_required:
            # Auto mode: commit staging immediately since no human review
            from shenbi.pipeline.checkpoint import commit_staging, clear_staging

            target = resolve_chapter_path(step.output_path, chapter)
            try:
                commit_staging(project_dir, [target])
                log.info("staging_auto_committed", chapter=chapter, target=target)
            except FileNotFoundError:
                log.warning("staging_auto_commit_skipped_no_file", chapter=chapter, target=target)
            clear_staging(project_dir)  # Fix: clean staging after auto-commit
            # Fall through to chapter-completion check (no checkpoint raised)
        elif (
            step.checkpoint == CheckpointType.STATE_SETTLE and not cfg.state_settle_review_required
        ):
            from shenbi.pipeline.checkpoint import STAGING_DIR, clear_staging

            staging_truth = project_dir / STAGING_DIR / "truth"
            if staging_truth.exists():
                for src in staging_truth.glob("*.md"):
                    dst = project_dir / "truth" / src.name
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    safe_write(dst, src.read_bytes())
                log.info(
                    "staging_auto_committed_state_settle",
                    chapter=chapter,
                    files=len(list(staging_truth.glob("*.md"))),
                )
            else:
                log.warning("staging_auto_commit_skipped_no_truth", chapter=chapter)
            clear_staging(project_dir)  # Fix: clean staging after auto-commit
            # Fall through to chapter-completion check (no checkpoint raised)
        else:
            artifact = (
                resolve_chapter_path(step.output_path, chapter)
                if step.output_path
                else f"chapter-{chapter}/{step.name}"
            )
            set_checkpoint(
                state,
                step.checkpoint,
                chapter=chapter,
                artifact=artifact,
                context=f"Review {step.name} for chapter {chapter}",
            )
            return True

    if state.chapter_loop.step_index >= len(CHAPTER_STEPS):
        return _complete_chapter(state, chapter)
    return False


def _run_context_assembly(project_dir: Path, chapter: int) -> None:
    """Materialize the three-route context package for the chapter.

    Calls :func:`assemble_context` + :func:`write_context_file` from
    ``context_assemble``. Closing spec §3.1 Gap 1: the previous body wrapped
    everything in a try/except that only logged a warning, so a throw from
    ``write_context_file`` left NO context file on disk and the pipeline
    silently continued. This version adds a mandatory post-check that verifies
    the file exists and writes a minimal Route-C fallback if it does not.
    """
    plan_path = f"plans/chapter-{chapter}-plan.md"
    context_path = project_dir / "context" / f"chapter-{chapter}-context.md"
    try:
        from shenbi.pipeline.context_assemble import (
            assemble_context,
            write_context_file,
        )

        pkg = assemble_context(project_dir, plan_path)
        out = write_context_file(project_dir, chapter, pkg)
        log.info(
            "context_assembled_for_chapter",
            chapter=chapter,
            sections=len(pkg.sections),
            total_tokens=pkg.total_tokens,
            output=str(out),
        )
    except Exception as e:
        log.warning("context_assembly_failed", chapter=chapter, error=str(e), exc_info=True)

    # HARD VERIFY (Gap 1 fix): output file must exist regardless of the try/except.
    if not context_path.exists() or context_path.stat().st_size == 0:
        log.error("context_assembly_no_output", chapter=chapter)
        _write_minimal_context_fallback(project_dir, chapter)


def _write_minimal_context_fallback(project_dir: Path, chapter: int) -> None:
    """Write a minimal Route-C-only context when full assembly failed.

    Uses :func:`safe_write` (atomic + locked) so the fallback itself cannot be
    half-written. Inlines the Route C fixed-rule retrieval to avoid importing
    the private ``_route_c`` from ``context_assemble``.
    """
    from shenbi.safe_write import safe_write

    project_dir = Path(project_dir)
    # Route C: inline fixed-rule retrieval (same as _route_c in context_assemble)
    _ROUTE_C_FILES: list[tuple[str, str]] = [
        ("truth/book_spine.md", "book_spine"),
        ("truth/audit_drift.md", "audit_drift"),
        ("style/style_profile.md", "style_profile"),
    ]
    _ROUTE_C_MAX_CHARS = 2000
    entries: list[dict[str, object]] = []
    for fname, label in _ROUTE_C_FILES:
        p = project_dir / fname
        if p.exists():
            entries.append(
                {
                    "source": f"route-c:{label}",
                    "weight": 0.6,
                    "text": p.read_text(encoding="utf-8")[:_ROUTE_C_MAX_CHARS],
                    "id": label,
                }
            )
    body = "\n\n".join(str(e.get("text", "")) for e in entries) or (
        "## Context (Minimal Fallback)\n\n"
        "Full context assembly failed; only Route C fixed rules available.\n"
    )
    out = project_dir / "context" / f"chapter-{chapter}-context.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    safe_write(out, body)


def _run_context_curation(project_dir: Path, chapter: int) -> None:
    """Run deterministic context curation and PERSIST it (Gap 2 fix).

    Replaces the ``shenbi-context-composing`` LLM call (step 5) with
    deterministic Python operations: 9-section structuring, ending diversity
    check, and hook debt briefing generation.

    Closing spec §3.1 Gap 2: the previous body called ``curate_context`` and
    only logged the result length — the curated string was computed and then
    DISCARDED, never written to disk. This version persists the curated
    9-section document via :func:`safe_write` and post-checks the file.
    """
    from shenbi.pipeline.context_curation import curate_context
    from shenbi.safe_write import safe_write

    curated_path = project_dir / "context" / f"chapter-{chapter}-curated.md"
    try:
        curated = curate_context(project_dir, chapter)
        curated_path.parent.mkdir(parents=True, exist_ok=True)
        safe_write(curated_path, curated)  # FIX: actually persist (was discarded)
        log.info("context_curated", chapter=chapter, length=len(curated), output=str(curated_path))
    except Exception as e:
        log.warning("context_curation_failed", chapter=chapter, error=str(e), exc_info=True)

    # Post-check: curation failures are non-fatal, but surface a hard error if
    # the output is unexpectedly absent after a non-throwing run.
    if not curated_path.exists():
        log.error("context_curation_no_output", chapter=chapter)


def _check_conditional_resolve(state: PipelineState, project_dir: Path, chapter: int) -> None:
    """Dispatch foreshadowing-resolve if TRIGGERED hooks are detected.

    Reads the foreshadowing-track output (``truth/pending_hooks.md``). If any
    hooks have ``state: TRIGGERED``, dispatches ``shenbi-foreshadowing-resolve``
    to handle them (spec section 6.1 step 7b). Missing file or no triggered
    hooks are no-ops.
    """
    hooks_file = project_dir / "truth" / "pending_hooks.md"
    if not hooks_file.exists():
        return

    text = hooks_file.read_text(encoding="utf-8")
    triggered_count = _count_triggered_hooks(text)
    if triggered_count > 0:
        log.info("conditional_resolve_triggered", chapter=chapter, count=triggered_count)
        dispatch_skill(
            "shenbi-foreshadowing-resolve",
            project_dir,
            f"Resolve {triggered_count} TRIGGERED hooks for chapter {chapter}.",
        )
    else:
        log.debug("no_triggered_hooks", chapter=chapter)


def _count_triggered_hooks(text: str) -> int:
    r"""Count hooks with state TRIGGERED in the pending_hooks.md content.

    Parses YAML frontmatter (``---\\n...\\n---``) for a ``hooks`` list where
    entries have a ``state`` field. State comparison goes through
    :func:`parse_hook_state` (fix D22): case-insensitive, and the
    non-canonical ``TRIGGER`` spelling folds to ``TRIGGERED``. Falls back to a
    text scan for ``state: TRIGGERED`` when frontmatter is absent or malformed.
    """
    # Try YAML frontmatter first.
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            try:
                fm = yaml.safe_load(parts[1]) or {}
                hooks = fm.get("hooks", [])
                if isinstance(hooks, list):
                    return sum(
                        1
                        for h in hooks
                        if isinstance(h, dict)
                        and parse_hook_state(str(h.get("state", ""))) == HookState.TRIGGERED
                    )
            except Exception:
                pass  # fall through to text scan
    # Fallback: count literal occurrences.
    return text.count("state: TRIGGERED")


def _parse_resonance_score(report_path: Path) -> int | None:
    """Extract resonance score from a review-resonance audit report.

    Attempts three patterns in order:
    1. YAML frontmatter ``resonance_score: 87``
    2. Markdown bold ``**Resonance Score**: 92``
    3. Plain ``Score: 75`` or ``resonance_score: 75``
    """
    if not report_path.exists():
        return None
    text = report_path.read_text(encoding="utf-8")

    # Pattern 1: YAML frontmatter
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            try:
                fm = yaml.safe_load(parts[1]) or {}
                score = fm.get("resonance_score")
                if isinstance(score, int):
                    return score
            except Exception:
                # YAML frontmatter parse error — score not retrievable from
                # this format, fall through to markdown-bold and plain-text patterns.
                pass

    # Pattern 2: Markdown bold label (case-insensitive)
    m = re.search(r"\*\*Resonance\s*Score\*\*:\s*(\d+)", text, re.IGNORECASE)
    if m:
        return int(m.group(1))

    # Pattern 3: Plain "Score: N" or "resonance_score: N"
    m = re.search(r"(?:Score|resonance_score)\s*:\s*(\d+)", text, re.IGNORECASE)
    if m:
        return int(m.group(1))

    return None


def _build_resonance_trend_row(chapter: int, overall: int) -> str:
    """Build a 7-column markdown table row for resonance_trend.md.

    Format MUST match what parse_resonance_scores
    (src/shenbi/orchestration/escalation_bridge.py:15-17) reads:
    lines starting with "|", split on "|", requires >=7 cells, reads
    cells[6] (7th column) as the overall score.

    Only the overall score (cs.resonance_score, an int) is available here;
    the upstream parser _parse_resonance_score (chapter_loop.py:667) returns
    int|None with no per-dimension breakdown. Columns without data use "-"
    placeholders so the column count stays at 7. Key column (cells[0]) is
    Ch{N} for key-based dedup.

    Column layout (split("|")[1:-1] yields exactly these cells):
        cells[0] = Ch{N}     (key)
        cells[1..5] = "-"    (placeholder dimensions)
        cells[6] = {overall} (7th column — what parse_resonance_scores reads)
    """
    return f"| Ch{chapter} | - | - | - | - | - | {overall} |"


# ---------------------------------------------------------------------------
# Adaptive triggering (spec §6.1 steps 9, 19-20 / Phase 4.2)
# ---------------------------------------------------------------------------


def _load_manifest(project_dir: Path) -> dict[str, Any]:
    """Load the snapshot manifest from ``snapshots/manifest.json``.

    Returns a dict with ``chapters`` (dict of chapter→filenames),
    ``last_recall_chapter``, and ``last_drift_chapter``. Returns an empty
    skeleton when the manifest file does not exist.
    """
    manifest_path = project_dir / "snapshots" / "manifest.json"
    if manifest_path.exists():
        return cast(dict[str, Any], json.loads(manifest_path.read_text(encoding="utf-8")))
    return {"chapters": {}}


def _save_manifest(project_dir: Path, manifest: dict[str, Any]) -> None:
    """Persist the snapshot manifest to ``snapshots/manifest.json``."""
    manifest_path = project_dir / "snapshots" / "manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    safe_write(manifest_path, json.dumps(manifest, indent=2, ensure_ascii=False))


def _get_snapshot_retention(project_dir: Path) -> int:
    """Return the number of chapters of snapshots to retain.

    Defaults to 50 (matching ``PipelineConfig.snapshot_retention_chapters``).
    """
    return 50


def _get_last_recall_chapter(project_dir: Path) -> int | None:
    """Return the chapter number where recall last ran, or None."""
    manifest = _load_manifest(project_dir)
    return manifest.get("last_recall_chapter")


def _get_last_drift_chapter(project_dir: Path) -> int | None:
    """Return the chapter number where drift guidance last ran, or None."""
    manifest = _load_manifest(project_dir)
    return manifest.get("last_drift_chapter")


def _should_run_recall(project_dir: Path, chapter: int) -> bool:
    """Determine whether foreshadowing recall should run for *chapter*.

    Triggers when any of these conditions are met:

    1. Any hook's silence (``chapter - last_reinforced``) is within 3 chapters
       of its ``max_distance``.
    2. More than 5 hooks are in ``TRIGGERED`` state.
    3. More than 8 chapters have elapsed since the last recall run.
    """
    hooks_file = project_dir / "truth" / "pending_hooks.md"
    if not hooks_file.exists():
        return False

    # Lazy import to avoid circular dependency at module level.
    from shenbi.pipeline.context_curation import _read_pending_hooks

    hooks = _read_pending_hooks(project_dir)

    # Condition 2: >5 TRIGGERED hooks
    triggered_count = sum(
        1 for h in hooks if parse_hook_state(str(h.get("state", ""))) == HookState.TRIGGERED
    )
    if triggered_count > 5:
        log.info(
            "recall_triggered_by_triggered_count",
            chapter=chapter,
            triggered_count=triggered_count,
        )
        return True

    # Condition 1: any hook near max_distance
    for h in hooks:
        last_reinforced = h.get("last_reinforced", 0)
        max_dist = h.get("max_distance", 0)
        if max_dist <= 0:
            continue
        silence = chapter - last_reinforced
        if silence >= max_dist - 3:
            log.info(
                "recall_triggered_by_max_distance",
                chapter=chapter,
                hook_id=h.get("id", "?"),
                silence=silence,
                max_distance=max_dist,
            )
            return True

    # Condition 3: >8 chapters since last recall
    last = _get_last_recall_chapter(project_dir)
    if last is not None and chapter - last > 8:
        log.info(
            "recall_triggered_by_chapter_gap",
            chapter=chapter,
            last_recall=last,
            gap=chapter - last,
        )
        return True

    return False


def _get_recent_resonance_scores(project_dir: Path, chapter: int, window: int = 3) -> list[int]:
    """Collect resonance scores from the most recent *window* audit reports.

    Reads ``audits/chapter-N-resonance.md`` for chapters
    ``[chapter - window + 1, chapter]``. Missing or unparseable reports are
    skipped (returns whatever could be collected).
    """
    scores: list[int] = []
    for ch in range(max(1, chapter - window + 1), chapter + 1):
        report_path = project_dir / "audits" / f"chapter-{ch}-resonance.md"
        score = _parse_resonance_score(report_path)
        if score is not None:
            scores.append(score)
    return scores


def _should_run_drift(project_dir: Path, chapter: int) -> bool:
    """Determine whether drift guidance should run for *chapter*.

    Triggers when either:

    1. The 3-chapter resonance moving average drops more than 10 points
       compared to the previous window (0-100 scale).
    2. More than 12 chapters have elapsed since the last drift run.
    """
    # Condition 1: 3-chapter MA drop >10 points
    current_scores = _get_recent_resonance_scores(project_dir, chapter, window=3)
    prev_scores = _get_recent_resonance_scores(project_dir, chapter - 1, window=3)

    if len(current_scores) >= 3 and len(prev_scores) >= 3:
        current_ma = sum(current_scores) / len(current_scores)
        prev_ma = sum(prev_scores) / len(prev_scores)
        drop = prev_ma - current_ma
        if drop > 10:
            log.info(
                "drift_triggered_by_resonance_drop",
                chapter=chapter,
                current_ma=round(current_ma, 1),
                prev_ma=round(prev_ma, 1),
                drop=round(drop, 1),
            )
            return True

    # Condition 2: >12 chapters since last drift
    last = _get_last_drift_chapter(project_dir)
    if last is not None and chapter - last > 12:
        log.info(
            "drift_triggered_by_chapter_gap",
            chapter=chapter,
            last_drift=last,
            gap=chapter - last,
        )
        return True

    return False


def _prune_old_snapshots(project_dir: Path) -> None:
    """Remove snapshot files older than the retention window.

    Keeps only the most recent ``snapshot_retention_chapters`` worth of
    snapshots (counting CHAPTERS, not the numeric range — robust to gaps).
    Removes files from disk and updates the manifest. Spec 22 E40: fixes the
    off-by-one in the previous ``ch < keep_from`` comparator (which kept
    ``retention + 1``) and adds a post-prune guard.
    """
    retention = _get_snapshot_retention(project_dir)
    manifest = _load_manifest(project_dir)
    chapters_dict = manifest.get("chapters", {})

    all_chapters = sorted(int(k) for k in chapters_dict)
    if len(all_chapters) <= retention:
        return

    # Keep the newest ``retention`` chapters; prune the rest. Slice-based so
    # gaps in chapter numbering do not distort the count.
    keep_set = set(all_chapters[-retention:])
    to_prune = [ch for ch in all_chapters if ch not in keep_set]

    if not to_prune:
        return

    snap_dir = project_dir / "snapshots"
    for ch in to_prune:
        ch_key = str(ch)
        for filename in chapters_dict.get(ch_key, []):
            file_path = snap_dir / filename
            if file_path.exists():
                file_path.unlink()
        chapters_dict.pop(ch_key, None)

    _save_manifest(project_dir, manifest)
    log.info("snapshots_pruned", pruned=len(to_prune), retention=retention)

    # GUARD: assert the cap is now respected (fail loudly if a concurrent
    # writer re-added snapshots between the prune and this check).
    remaining = len(chapters_dict)
    if remaining > retention:
        log.error(
            "snapshot_prune_failed",
            count=remaining,
            cap=retention,
            msg="snapshot count still exceeds cap after pruning — "
            "concurrent writer or manifest corruption suspected",
        )


# ---------------------------------------------------------------------------
# Core snapshot file list + CJK content guard (spec §3.7, §3.8)
# ---------------------------------------------------------------------------

# Files included in snapshots (core chapter-state only).
# Excludes audits, truth files, and staging to prevent ~15x bloat (spec §3.7).
_CORE_SNAPSHOT_PATTERNS = [
    "chapters/chapter-{chapter}.md",
    "chapters/chapter-{chapter}-meta.md",
    "chapters/chapter-{chapter}-decisions.json",
    "chapters/chapter-{chapter}-revision-decisions.json",
]


def _get_core_snapshot_files(project_dir: Path, chapter: int) -> list[Path]:
    """Get list of core chapter files to include in a snapshot.

    Only includes chapter body, metadata, decisions, and revision decisions.
    Excludes audit reports, truth files, and staging to reduce snapshot bloat.

    Args:
        project_dir: Root directory of the novel project.
        chapter: Chapter number.

    Returns:
        List of existing file paths to include in the snapshot.
    """
    files: list[Path] = []
    for pattern in _CORE_SNAPSHOT_PATTERNS:
        path = project_dir / pattern.format(chapter=chapter)
        if path.exists():
            files.append(path)
    return files


def _has_minimum_chinese_chars(text: str, threshold: int = 500) -> bool:
    """Check if text has at least ``threshold`` Chinese characters.

    Chinese characters are defined as CJK Unified Ideographs (U+4E00 to
    U+9FFF). This is used to flag snapshots that may contain revision
    metadata instead of actual prose.

    Args:
        text: The text content to check.
        threshold: Minimum number of Chinese characters required.

    Returns:
        True if the text has >= ``threshold`` Chinese characters.
    """
    count = sum(1 for c in text if "\u4e00" <= c <= "\u9fff")
    return count >= threshold


def _snapshot_chapter_files(
    project_dir: Path,
    chapter: int,
    label: str = "",
    use_legacy_snapshot: bool = False,
    *,
    state: PipelineState | None = None,
) -> None:
    """Create a snapshot of chapter outputs.

    By default, uses a differential SHA-256 hash-based snapshot that stores
    full content only for the most recent RING_BUFFER_N chapters (enabling
    revision-rollback to restore previous chapter content after a revision
    overwrite). Truth files are always stored in full. Older chapter/plan
    files are tracked by hash only.

    Set ``use_legacy_snapshot=True`` to use the old monolithic markdown
    snapshot format (timestamped flat file in ``snapshots/``). The legacy
    path is maintained for rollback safety during migration.

    When *state* is provided, updates ``state.last_snapshot`` to point at the
    newly written snapshot (spec §3.3) so resume/rollback can find the recovery
    point from state without scanning the snapshots directory.

    Args:
        project_dir: Root directory of the novel project.
        chapter: Chapter number to snapshot.
        label: Optional label for legacy snapshots (e.g. "emergency").
        use_legacy_snapshot: If True, use the old monolithic markdown format.
        state: Optional pipeline state to record last_snapshot pointer into.
    """
    if use_legacy_snapshot:
        from datetime import datetime

        snap_dir = project_dir / "snapshots"
        snap_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S")
        if label:
            snap_filename = f"chapter-{chapter:03d}-{label}-{timestamp}.md"
        else:
            snap_filename = f"chapter-{chapter:03d}-{timestamp}.md"
        snap_path = snap_dir / snap_filename

        parts: list[str] = []

        # Core chapter files only (excludes audits, truth, staging — spec §3.7)
        core_files = _get_core_snapshot_files(project_dir, chapter)
        for fpath in core_files:
            fname = fpath.name
            parts.append(f"## {fname}\n\n{fpath.read_text(encoding='utf-8')}")

        # Content guard: warn if chapter body has too few Chinese chars (§3.8)
        chapter_path = project_dir / "chapters" / f"chapter-{chapter}.md"
        if chapter_path.exists():
            text = chapter_path.read_text(encoding="utf-8")
            if not _has_minimum_chinese_chars(text):
                log.warning(
                    "snapshot_suspect_content",
                    chapter=chapter,
                    chinese_chars=sum(1 for c in text if "\u4e00" <= c <= "\u9fff"),
                )

        content = (
            "\n\n---\n\n".join(parts) if parts else f"# Snapshot Chapter {chapter}\n\n(no files)"
        )
        safe_write(snap_path, content.encode("utf-8"))

        # Wire last_snapshot (spec §3.3): point state at the newest snapshot so
        # resume/rollback can find the recovery point without a directory scan.
        if state is not None:
            state.last_snapshot = {
                "chapter": chapter,
                "path": str(snap_path.relative_to(project_dir)),
                "timestamp": timestamp,
            }
            log.info(
                "last_snapshot_updated",
                chapter=chapter,
                path=state.last_snapshot["path"],
            )

        # Update manifest
        manifest = _load_manifest(project_dir)
        chapter_key = str(chapter)
        manifest.setdefault("chapters", {})
        manifest["chapters"].setdefault(chapter_key, [])
        manifest["chapters"][chapter_key].append(snap_filename)
        _save_manifest(project_dir, manifest)

        log.info(
            "snapshot_created",
            chapter=chapter,
            file=snap_filename,
            size=len(content),
        )

        # Prune old snapshots
        _prune_old_snapshots(project_dir)
    else:
        # Differential SHA-256 hash-based snapshot (default).
        # Stores full content for recent chapters (ring buffer) so
        # revision-rollback can restore previous chapter after an overwrite.
        # Truth files always stored in full; older chapters hash-only.
        from datetime import datetime

        snapshot_dir = project_dir / "snapshots" / f"chapter-{chapter:03d}"
        create_differential_snapshot(project_dir, chapter, snapshot_dir)

        # Wire last_snapshot (spec §3.3): point state at the newest snapshot so
        # resume/rollback can find the recovery point without a directory scan.
        if state is not None:
            state.last_snapshot = {
                "chapter": chapter,
                "path": str(snapshot_dir.relative_to(project_dir)),
                "timestamp": datetime.now(UTC).strftime("%Y%m%dT%H%M%S"),
            }
            log.info(
                "last_snapshot_updated",
                chapter=chapter,
                path=state.last_snapshot["path"],
            )

        # Prune old snapshots
        _prune_old_snapshots(project_dir)


# ---------------------------------------------------------------------------
# Emergency snapshot system (spec §3.6)
# ---------------------------------------------------------------------------


def _check_emergency_flag(project_dir: Path, chapter: int) -> None:
    """Called at step boundaries in the main loop. If flag is set,
    perform emergency snapshot safely from the main thread.
    """
    global _emergency_flag  # noqa: PLW0603
    if _emergency_flag:
        _emergency_flag = False
        _do_emergency_snapshot()


def _should_generate_starting_snapshot(
    current_chapter: int,
    step_index: int,
    project_dir: Path | None = None,
) -> bool:
    """Determine if a starting snapshot should be generated.

    Generates snapshot at:
        - Chapter 1, step 0 (initialization)
        - Any chapter step 0 if Ch1 snapshot is missing (self-heal)

    Args:
        current_chapter: Current chapter number.
        step_index: Current step index (0 = start).
        project_dir: Optional project dir to check for existing snapshots.

    Returns:
        True if a starting snapshot is warranted.
    """
    if current_chapter == 1 and step_index == 0:
        return True

    # Self-heal: if we're at step 0 of any chapter and no Ch1 snapshot exists
    if step_index == 0 and project_dir is not None:
        snapshots_dir = project_dir / "snapshots"
        if not snapshots_dir.exists():
            return True
        ch1_snapshots = list(snapshots_dir.glob("chapter-1-*.md"))
        if not ch1_snapshots:
            return True

    return False


def _do_emergency_snapshot() -> None:
    """Best-effort emergency snapshot. Never raises.

    Reads the module-level checkpoint state (set by checkpoint-on-step) and
    writes an ``emergency`` snapshot of the current chapter. Safe to call from
    a signal handler or atexit: any exception is swallowed so the crash handler
    never crashes the crash.
    """
    try:
        pd = _emergency_snapshot_project_dir
        ch = _emergency_snapshot_chapter
        if pd is not None and ch > 0:
            _snapshot_chapter_files(pd, ch, label="emergency")
            log.warning("emergency_snapshot_saved", chapter=ch)
    except Exception:
        pass


def _register_emergency_snapshot(project_dir: Path, chapter: int) -> None:
    """Register handlers that generate an emergency snapshot on termination.

    Three layers of defense (per spec §3.6, atexit alone is insufficient):

    1. ``signal.signal(SIGTERM/SIGINT)`` — catches abnormal termination that
       ``atexit`` misses (SIGTERM does not run atexit handlers).
    2. ``atexit.register`` — backstop for clean-ish interpreter shutdown.
    3. Checkpoint-on-step — ``_update_emergency_checkpoint`` is called on every
       chapter-loop step so handlers always snapshot the LATEST chapter, not a
       stale one from init.

    The signal handler is installed exactly once (guarded by
    ``_emergency_signal_handler_installed``) to avoid stacking duplicate
    handlers across pipeline re-entries.

    Args:
        project_dir: Root directory of the novel project.
        chapter: Current chapter number at registration time.
    """
    global _emergency_snapshot_project_dir, _emergency_snapshot_chapter  # noqa: PLW0603
    global _emergency_signal_handler_installed  # noqa: PLW0603
    _emergency_snapshot_project_dir = project_dir
    _emergency_snapshot_chapter = chapter

    # Layer 2: atexit backstop
    _atexit.register(_do_emergency_snapshot)

    # Layer 1: signal handlers for SIGTERM/SIGINT (installed once)
    if not _emergency_signal_handler_installed:
        _signal.signal(_signal.SIGTERM, _emergency_snapshot_signal_handler)
        _signal.signal(_signal.SIGINT, _emergency_snapshot_signal_handler)
        _emergency_signal_handler_installed = True


def _emergency_snapshot_signal_handler(signum: int, frame: object) -> None:
    """Signal handler: ONLY sets atomic flag. No I/O, no locks.

    The actual snapshot work is done in _check_emergency_flag(), called at
    step boundaries in the main loop. This keeps I/O out of signal context
    (which is unsafe and can deadlock).
    """
    global _emergency_flag  # noqa: PLW0603
    _emergency_flag = True
    # Restore default disposition so a second signal terminates immediately
    _signal.signal(signum, _signal.SIG_DFL)


def _update_emergency_checkpoint(project_dir: Path, chapter: int) -> None:
    """Checkpoint-on-step: refresh the emergency-snapshot state every step.

    Called on each chapter-loop iteration so signal/atexit handlers always
    snapshot the LATEST chapter rather than the chapter active at init. This
    is what closes the gap that lost Ch56's snapshot (spec §3.6).

    Args:
        project_dir: Root directory of the novel project.
        chapter: The chapter just entered (or currently being processed).
    """
    global _emergency_snapshot_project_dir, _emergency_snapshot_chapter  # noqa: PLW0603
    _emergency_snapshot_project_dir = project_dir
    _emergency_snapshot_chapter = chapter


def _update_last_recall_manifest(project_dir: Path, chapter: int) -> None:
    """Record that recall ran at *chapter* in the manifest."""
    manifest = _load_manifest(project_dir)
    manifest["last_recall_chapter"] = chapter
    _save_manifest(project_dir, manifest)


def _update_last_drift_manifest(project_dir: Path, chapter: int) -> None:
    """Record that drift guidance ran at *chapter* in the manifest."""
    manifest = _load_manifest(project_dir)
    manifest["last_drift_chapter"] = chapter
    _save_manifest(project_dir, manifest)


def _should_run_step(step: ChapterStep, state: PipelineState, project_dir: Path) -> bool:
    """Determine whether *step* should execute based on adaptive triggering rules.

    Returns True if the step should execute normally (dispatch + gates).
    Returns False if the step should be skipped for this chapter.

    For ``shenbi-snapshot-manage``, the file-based snapshot is taken inline
    and the LLM dispatch is always skipped (returns False).
    """
    skill = step.skill
    chapter = state.chapter_loop.current_chapter

    if skill == "shenbi-foreshadowing-recall":
        return _should_run_recall(project_dir, chapter)

    if skill == "shenbi-drift-guidance":
        return _should_run_drift(project_dir, chapter)

    if skill == "shenbi-snapshot-manage":
        # Replace LLM dispatch with deterministic file-based snapshot.
        _snapshot_chapter_files(project_dir, chapter, state=state)
        return False

    # All other steps run unconditionally.
    return True


# ---------------------------------------------------------------------------
# Revision routing helpers (spec §6.3, W3T5)
# ---------------------------------------------------------------------------

_REVISION_ROUTE_KEY = "revision_route"


def _get_chapter_state(state: PipelineState, chapter: int) -> ChapterState:
    """Return the ChapterState for *chapter*, creating it if absent."""
    key = str(chapter)
    cs = state.chapter_loop.chapter_states.get(key)
    if cs is None:
        cs = ChapterState()
        state.chapter_loop.chapter_states[key] = cs
    return cs


def _create_pre_revision_backup(project_dir: Path, chapter: int) -> None:
    """Create a backup of the chapter file before revision dispatch.

    Copies ``chapters/chapter-N.md`` to ``chapters/chapter-N-pre-rev.md``
    using ``shutil.copy2`` which preserves metadata. If the chapter file
    does not exist, this is a no-op.

    This ensures the original prose is recoverable even if the revision
    skill incorrectly overwrites the chapter body.

    Args:
        project_dir: Root directory of the novel project.
        chapter: Chapter number.
    """
    chapter_path = project_dir / "chapters" / f"chapter-{chapter}.md"
    if not chapter_path.exists():
        log.debug("pre_rev_backup_skip", chapter=chapter, reason="chapter file does not exist")
        return

    backup_path = project_dir / "chapters" / f"chapter-{chapter}-pre-rev.md"
    _shutil.copy2(chapter_path, backup_path)
    log.info("pre_revision_backup_created", chapter=chapter, size=chapter_path.stat().st_size)


def _route_revision_after_resonance(state: PipelineState, project_dir: Path, chapter: int) -> None:
    """Collect audit issues and determine the revision route (spec §6.3).

    Called after the review-resonance step succeeds. Stores the route in the
    chapter's ``audit_results`` so that step 18 (chapter-revision) can decide
    whether to run or skip.
    """
    _create_pre_revision_backup(project_dir, chapter)

    issues, blocking = collect_audit_issues(project_dir, chapter)
    route = route_chapter_revision(issues, blocking)
    cs = _get_chapter_state(state, chapter)
    cs.audit_results[_REVISION_ROUTE_KEY] = route.value

    # Wire revision_count (spec §3.2): increment only on an actual revision
    # route, not on NO_REVISION. Previously this was missing entirely, leaving
    # revision_count at 0 for all chapters.
    if route != RevisionRoute.NO_REVISION:
        cs.revision_count += 1
        log.info(
            "revision_count_incremented",
            chapter=chapter,
            route=route.value,
            revision_count=cs.revision_count,
        )

    # Resonance floor check (spec §6.3). Full borderline/escalation handling
    # is deferred pending chapter_role calibration (Wave 4+); for now a
    # below-floor score with no audit issues is logged so it is visible.
    resonance_ok = check_resonance(cs.resonance_score, state.config.resonance_global_floor)
    if not resonance_ok and not issues:
        log.warning(
            "resonance_below_floor",
            chapter=chapter,
            score=cs.resonance_score,
            floor=state.config.resonance_global_floor,
        )

    log.info(
        "revision_routed",
        chapter=chapter,
        route=route.value,
        issue_count=len(issues),
        blocking=blocking,
    )


def _is_revision_skipped(state: PipelineState, chapter: int) -> bool:
    """True if step 18 (chapter-revision) should be skipped for *chapter*.

    This only applies when the revision router has already run (after
    review-resonance) and determined ``RevisionRoute.NO_REVISION``. Steps
    before review-resonance always proceed normally.
    """
    cs = state.chapter_loop.chapter_states.get(str(chapter))
    if cs is None:
        return False
    return cs.audit_results.get(_REVISION_ROUTE_KEY) == RevisionRoute.NO_REVISION.value


def _is_revision_routed(route: str | None) -> bool:
    """Check if a revision route was actually assigned.

    Returns True for any non-None route, including 'no_revision'.
    """
    return route is not None


def _ensure_revision_decisions_exists(
    project_dir: Path,
    chapter: int,
    state: PipelineState | None = None,
    log: Any = None,
) -> None:
    """Write a minimal revision decisions file if one does not exist.

    The file conforms to DecisionsDoc (extra="forbid"): $schema, skill,
    chapter, selections, adjustments, produced_at. The skip decision is
    documented in ``selections`` (not a ``route`` key). This ensures every
    chapter routed through revision (including no-revision) produces an
    audit-trail artifact.

    Args:
        project_dir: Root directory of the novel project.
        chapter: Chapter number.
        state: Optional pipeline state for checking revision routing.
        log: Optional logger for recording fallback writes.
    """
    rev_path = project_dir / "chapters" / f"chapter-{chapter}-revision-decisions.json"
    if rev_path.exists():
        return

    if state is not None:
        ch_state = state.chapter_loop.chapter_states.get(str(chapter))
        route = ch_state.audit_results.get(_REVISION_ROUTE_KEY) if ch_state else None
        if not _is_revision_routed(route):
            return  # Chapter was never routed through revision

    from datetime import datetime

    min_decisions = {
        "$schema": "shenbi-decisions-v1",
        "skill": "shenbi-chapter-revision",
        "chapter": chapter,
        "selections": [
            {
                "target": "no_revision_needed",
                "selected": [],
                "basis": "arc_relevance",
                "severity": "low",
                "omitted": [],
            }
        ],
        "adjustments": [],  # empty = no changes made
        "produced_at": datetime.now(UTC).isoformat(),
    }
    safe_write(rev_path, json.dumps(min_decisions, ensure_ascii=False, indent=2))
    if log is not None:
        log.info("revision_decisions_fallback_written", chapter=chapter)


# ---------------------------------------------------------------------------
# Linguistic drift detection (3-tier intervention — spec §3.4, Task 5)
# ---------------------------------------------------------------------------


def _check_linguistic_drift(project_dir: Path, chapter: int) -> DriftResult | None:
    """Check chapter text for linguistic drift and apply tiered intervention.

    Reads the just-written ``chapters/chapter-{chapter}.md`` (no zero-padding),
    compares its pragmatic alarm metrics (Task 3) against the established
    baseline, and applies WARN/HARD/ESCALATE intervention per spec §3.4.
    """
    from shenbi.skill_utils.drift_detection.linguistic_drift import (
        check_opening_similarity,
        compute_linguistic_metrics,
        detect_drift,
    )

    chapter_file = project_dir / "chapters" / f"chapter-{chapter}.md"
    if not chapter_file.exists():
        return None

    chapter_text = chapter_file.read_text(encoding="utf-8")

    # Load baseline (established from first 3 chapters — see Task 6 / spec §3.5)
    baseline_file = project_dir / "style" / "linguistic_baseline.json"
    if baseline_file.exists():
        baseline = json.loads(baseline_file.read_text(encoding="utf-8"))
    else:
        log.warning("no_linguistic_baseline", chapter=chapter)
        return None

    current = compute_linguistic_metrics(chapter_text, project_dir=project_dir)
    result = detect_drift(current, baseline)

    if result.is_drift:
        log.warning(
            "linguistic_drift_detected",
            chapter=chapter,
            severity=result.severity,
            metrics=result.metrics,
        )

        if result.severity == "ESCALATE":
            log.error("drift_escalate_pause_for_review", chapter=chapter)
            raise DriftEscalationError(
                f"Chapter {chapter}: system term density "
                f"{result.metrics.get('system_term_density', 0):.1f} per mille. "
                "Pipeline paused for human review."
            )
        if result.severity == "HARD":
            _inject_drift_correction(project_dir, chapter, result)
        elif result.severity == "WARN":
            _inject_drift_warning(project_dir, chapter, result)

    # Check opening similarity against the previous chapter
    if chapter > 1:
        prev_file = project_dir / "chapters" / f"chapter-{chapter - 1}.md"
        if prev_file.exists():
            prev_text = prev_file.read_text(encoding="utf-8")
            opening_sim = check_opening_similarity(chapter_text, prev_text)
            if opening_sim > 0.6:
                log.warning(
                    "opening_similarity_high",
                    chapter=chapter,
                    similarity=round(opening_sim, 2),
                )
                _inject_opening_variation_directive(project_dir, chapter, opening_sim)

    return result


def _inject_drift_correction(project_dir: Path, chapter: int, result: DriftResult) -> None:
    """Write a PRE_WRITE_CHECK directive for the next chapter to correct drift."""
    directive = f"""## PRE_WRITE_CHECK (AUTO-GENERATED - DRIFT DETECTED)

CRITICAL: Chapter {chapter} has system term density of {result.metrics.get("system_term_density", 0):.1f} per mille (baseline: <5).
The next chapter MUST:
1. Use natural Chinese narrative prose — NO system parameter language (冷在场, 冷值, 在场度)
2. Include at least 3 dialogue exchanges with human characters
3. Include at least 2 physical actions or sensory descriptions
4. Use varied sentence structures — no repeated sentence templates
"""
    directive_file = project_dir / "context" / f"drift-correction-{chapter + 1}.md"
    safe_write(directive_file, directive)


def _inject_drift_warning(project_dir: Path, chapter: int, result: DriftResult) -> None:
    """Write a gentle warning for the next chapter."""
    warning = f"""## PRE_WRITE_CHECK (AUTO-GENERATED - STYLE WARNING)

Note: Chapter {chapter} shows early signs of parametric language.
Please prioritize natural prose and human character dialogue in the next chapter.
"""
    warning_file = project_dir / "context" / f"drift-warning-{chapter + 1}.md"
    safe_write(warning_file, warning)


def _inject_opening_variation_directive(project_dir: Path, chapter: int, similarity: float) -> None:
    """Warn about high opening similarity."""
    directive = f"""## PRE_WRITE_CHECK (OPENING VARIATION)

The opening of Chapter {chapter} is {similarity * 100:.0f}% similar to Chapter {chapter - 1}.
Next chapter MUST use a different opening approach.
Forbidden openings: "冷知道/冷在/冷在场于" sentence patterns.
"""
    directive_file = project_dir / "context" / f"opening-variation-{chapter + 1}.md"
    safe_write(directive_file, directive)


# ---------------------------------------------------------------------------
# Context Coverage Audit (Task 6)
# ---------------------------------------------------------------------------


def _audit_context_coverage(project_dir: Path, current_chapter: int) -> list[int]:  # pyright: ignore[reportUnusedFunction]
    """Scan all chapters up to current_chapter and return list of missing context files.

    Uses the real (non-padded) ``chapter-{ch}-context.md`` naming. Called at
    pipeline resume initialization to surface the 77% coverage gap (spec §3.1).
    """
    import structlog

    log = structlog.get_logger()
    context_dir = project_dir / "context"
    missing = []
    for ch in range(1, current_chapter + 1):
        context_file = context_dir / f"chapter-{ch}-context.md"
        if not context_file.exists():
            missing.append(ch)
    if missing:
        log.warning(
            "context_coverage_gap",
            missing_chapters=missing,
            gap_ratio=f"{len(missing)}/{current_chapter}",
        )
    return missing


# ---------------------------------------------------------------------------
# Volume map alignment check (WARN-level, non-blocking)
# ---------------------------------------------------------------------------


def _check_volume_map_alignment(project_dir: Path, chapter: int) -> None:
    """WARN-level check: compare volume_map chapter node terms against chapter text.

    Non-blocking: blueprint is guidance, creative deviation is allowed.
    Warns when >70% of key terms from volume_map are missing from chapter.
    """
    vm_path = project_dir / "outline" / "volume_map.md"
    chapter_path = project_dir / "chapters" / f"chapter-{chapter}.md"

    if not vm_path.exists() or not chapter_path.exists():
        return

    volume_map_text = vm_path.read_text(encoding="utf-8")

    # Extract chapter node description
    node = _extract_chapter_node_from_map(volume_map_text, chapter)
    if node is None:
        return

    # Extract key terms (nouns and proper nouns, Chinese/English)
    key_terms = _extract_key_terms(node["content"])
    if not key_terms:
        return

    chapter_text = chapter_path.read_text(encoding="utf-8")

    # Check term presence
    found_terms: list[str] = []
    missing_terms: list[str] = []
    for term in key_terms:
        if term.lower() in chapter_text.lower():
            found_terms.append(term)
        else:
            missing_terms.append(term)

    total = len(key_terms)
    match_rate = len(found_terms) / total if total > 0 else 1.0

    if match_rate < 0.3:  # >70% missing
        log.warning(
            "volume_map_alignment",
            chapter=chapter,
            match_rate=f"{match_rate:.1%}",
            found_terms=found_terms,
            missing_terms=missing_terms,
            expected=node["content"][:120],
        )


def _extract_chapter_node_from_map(volume_map_text: str, chapter: int) -> dict[str, str] | None:
    """Extract {role, content} from volume_map table row for a chapter."""
    pattern = re.compile(rf"\|\s*{chapter}\s*\|([^|]+)\|([^|]+)\|")
    m = pattern.search(volume_map_text)
    if m:
        return {"role": m.group(1).strip(), "content": m.group(2).strip()}
    return None


def _extract_key_terms(text: str) -> list[str]:
    """Extract significant key terms from a description.

    Returns Chinese words (2+ chars) and English words (3+ chars),
    skipping common stop words.
    """
    stop_words = {
        "the",
        "and",
        "in",
        "of",
        "to",
        "a",
        "is",
        "for",
        "with",
        "this",
        "that",
        "from",
        "be",
    }
    terms: list[str] = []

    # English words 3+ chars
    eng_words = re.findall(r"[a-zA-Z]{3,}", text)
    for w in eng_words:
        if w.lower() not in stop_words:
            terms.append(w)

    # Chinese character sequences 2+ chars
    cn_seqs = re.findall(r"[\u4e00-\u9fff]{2,}", text)
    terms.extend(cn_seqs)

    # Filter generic terms
    filtered: list[str] = []
    for t in terms:
        if t.lower() not in {"chapter", "volume", "node", "role", "content", "character"}:
            filtered.append(t)

    return filtered


# ---------------------------------------------------------------------------
# Resume cleanup
# ---------------------------------------------------------------------------


def _cleanup_residual_staging(  # pyright: ignore[reportUnusedFunction]
    project_dir: Path,
    has_pending_staging: bool,
) -> None:
    """Clean residual staging directory at pipeline resume.

    If the staging directory exists and no pipeline steps are pending
    that write to staging, the directory is safe to remove. This
    prevents accumulation of stale staging files across pipeline runs.

    Args:
        project_dir: Root directory of the novel project.
        has_pending_staging: True if any pending step uses staging.
    """
    from shenbi.pipeline.checkpoint import clear_staging

    staging_dir = project_dir / "staging"
    if not staging_dir.exists():
        return

    if has_pending_staging:
        log.debug("staging_cleanup_skipped", reason="pending staging steps")
        return

    clear_staging(project_dir)
    log.info("residual_staging_cleaned_at_resume", project_dir=str(project_dir))


def _has_pending_staging_step(state: PipelineState) -> bool:  # pyright: ignore[reportUnusedFunction]
    """Check if any pending step in the current chapter uses staging."""
    step_idx = state.chapter_loop.step_index
    if step_idx >= len(CHAPTER_STEPS):
        return False
    return any(step.uses_staging for step in CHAPTER_STEPS[step_idx:])


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def run_chapter_step(state: PipelineState, project_dir: Path | str) -> bool:
    """Execute the next chapter step.

    Returns True if a checkpoint was reached (chapter-memo, state-settle,
    per-chapter, or escalation) or all steps are already consumed; False if
    the step simply advanced (or will be retried) and no human action is
    needed yet. Mutates ``state`` in place; the caller persists it.
    """
    project_dir = Path(project_dir)
    step_idx = state.chapter_loop.step_index
    if step_idx >= len(CHAPTER_STEPS):
        return True  # all steps consumed

    step = CHAPTER_STEPS[step_idx]
    chapter = state.chapter_loop.current_chapter
    state.chapter_loop.current_step = step.skill
    log.info("chapter_step", chapter=chapter, step=step.step_num, skill=step.skill)

    # ── Emergency snapshot checkpoint-on-step (spec §3.6) ────────────────
    # Update the emergency checkpoint on every step so signal/atexit handlers
    # always snapshot the LATEST chapter, not the chapter active at init.
    _update_emergency_checkpoint(project_dir, chapter)
    # Check for emergency snapshot flag at each step boundary (safe I/O from
    # the main thread — the signal handler only sets the atomic flag).
    _check_emergency_flag(project_dir, chapter)

    # ── Starting snapshot + emergency registration (first step only) ─────
    if step_idx == 0:
        if _should_generate_starting_snapshot(
            state.chapter_loop.current_chapter,
            state.chapter_loop.step_index,
            project_dir=project_dir,
        ):
            _snapshot_chapter_files(project_dir, state.chapter_loop.current_chapter, state=state)

        # Register emergency handler ONCE (installs signal handlers + atexit backstop)
        _register_emergency_snapshot(project_dir, state.chapter_loop.current_chapter)

    # ── Parallel review dispatch (Task 7) ──────────────────────────────
    # When the first audit step is reached, dispatch all core-circle and
    # genre-circle reviews in two parallel waves instead of serial steps.
    if step_idx == _FIRST_AUDIT_IDX and step.is_audit:
        from shenbi.pipeline.parallel_dispatch import (
            ReviewTask,
            consolidate_review_results,
            dispatch_reviews_parallel,
        )
        from shenbi.pipeline.audit_layer import (
            audit_relative_path,
            audit_suffix,
            get_active_genre_audits,
        )
        from shenbi.pipeline.dispatch_helper import DispatchResult
        from shenbi.safe_write import safe_write

        # Build shared audit context ONCE per chapter so auditors skip
        # re-reading the same files from disk (Task 6 Step 2 wiring).
        from shenbi.pipeline.audit_context_cache import build_shared_audit_context

        shared_ctx = build_shared_audit_context(project_dir, chapter)
        log.info(
            "shared_audit_context_built_for_wave",
            chapter=chapter,
            estimated_tokens=shared_ctx.estimated_tokens,
        )

        # Load per-skill audit history for cascade filtering (Task 6 Step 3).
        audit_history = _get_audit_history(state, chapter)

        def _keep_task(task: ReviewTask) -> bool:
            skill_short = _audit_short_name(task.skill)
            if _should_skip_audit(skill_short, audit_history):
                log.info("audit_cascade_skipped", chapter=chapter, skill=task.skill)
                return False
            return True

        # Wave 1: Core-circle reviews (7 skills in parallel)
        core_skills = [s.skill for s in CHAPTER_STEPS if s.is_audit and "review" in s.skill]
        core_tasks = [
            ReviewTask(
                skill=skill,
                project_dir=project_dir,
                prompt=f"Execute {skill} for chapter {chapter}. Project dir: {project_dir}",
                output_path=f"audits/chapter-{chapter}-{audit_suffix(skill)}.md",
                shared_context=shared_ctx,
            )
            for skill in core_skills
        ]
        # Filter cascaded audits (core audits + always-run are never skipped)
        core_tasks = [t for t in core_tasks if _keep_task(t)]

        core_results: list[DispatchResult] = []
        if core_tasks:
            log.info("parallel_review_wave1_start", chapter=chapter, count=len(core_tasks))
            core_results = dispatch_reviews_parallel(core_tasks)
        else:
            log.info("parallel_review_wave1_empty", chapter=chapter)

        # Wave 2: Genre-circle reviews (conditionally active, in parallel)
        gc_path = project_dir / "genre-config.json"
        genre_gc = json.loads(gc_path.read_text(encoding="utf-8")) if gc_path.exists() else {}
        genre_skills = get_active_genre_audits(genre_gc)
        genre_tasks = [
            ReviewTask(
                skill=skill,
                project_dir=project_dir,
                prompt=f"Execute {skill} audit for chapter {chapter}.",
                output_path=audit_relative_path(chapter, skill),
                shared_context=shared_ctx,
            )
            for skill in genre_skills
        ]
        # Filter cascaded audits for genre wave too
        genre_tasks = [t for t in genre_tasks if _keep_task(t)]

        genre_results: list[DispatchResult] = []
        if genre_tasks:
            log.info("parallel_review_wave2_start", chapter=chapter, count=len(genre_tasks))
            genre_results = dispatch_reviews_parallel(genre_tasks)
        else:
            log.info("parallel_review_wave2_empty", chapter=chapter)

        # Consolidate all results
        all_results = core_results + genre_results
        consolidated = consolidate_review_results(all_results, chapter)
        summary_path = project_dir / "audits" / f"chapter-{chapter}-review-summary.md"
        safe_write(summary_path, consolidated)

        # Record all review steps as done and advance past them
        for i in range(_FIRST_AUDIT_IDX, _LAST_AUDIT_IDX + 1):
            if i < len(CHAPTER_STEPS):
                _record_step_done(state, CHAPTER_STEPS[i], chapter)

        state.chapter_loop.step_index = _LAST_AUDIT_IDX + 1
        state.chapter_loop.current_step = ""

        # Check for blocking issues
        cs = _get_chapter_state(state, chapter)
        # The consolidated summary always contains "- **BLOCKING Issues**: N".
        # Only the "## BLOCKING Issues" H2 section is present when actual
        # blocking issues exist (see consolidate_review_results in parallel_dispatch.py).
        cs.audit_results["blocking_found"] = "## BLOCKING Issues" in consolidated
        cs.audit_results["audit_reports"] = [t.output_path for t in core_tasks + genre_tasks]

        _reset_retries(state, step, chapter)
        return _advance(
            state,
            _LAST_AUDIT_IDX,
            CHAPTER_STEPS[_LAST_AUDIT_IDX],
            chapter,
            project_dir=project_dir,
        )

    # Context assembly (step 4): materialize package before chapter-drafting.
    if step.calls_context_assembly:
        _run_context_assembly(project_dir, chapter)
        # Also run deterministic curation — replaces context-composing LLM call
        _run_context_curation(project_dir, chapter)

    # Pipeline-internal steps (not dispatched): advance without dispatch/G4.
    if step.skill.startswith("pipeline-"):
        _record_step_done(state, step, chapter)
        _reset_retries(state, step, chapter)
        return _advance(state, step_idx, step, chapter, project_dir=project_dir)

    # context-composing replaced by deterministic curation in step 4
    if step.skill == "shenbi-context-composing":
        log.info("context_composing_replaced_by_curation", chapter=chapter)
        _record_step_done(state, step, chapter)
        _reset_retries(state, step, chapter)
        return _advance(state, step_idx, step, chapter, project_dir=project_dir)

    # foreshadowing-plant replaced by deterministic YAML generation
    if step.skill == "shenbi-foreshadowing-plant":
        from shenbi.pipeline.hook_planting import plant_hooks_from_plan

        count = plant_hooks_from_plan(project_dir, chapter)
        log.info("foreshadowing_plant_replaced_by_deterministic", chapter=chapter, count=count)
        _record_step_done(state, step, chapter)
        _reset_retries(state, step, chapter)
        return _advance(state, step_idx, step, chapter, project_dir=project_dir)

    # Step 18 (chapter-revision) is conditional -- skip when routing decided
    # no revision is needed (spec §6.3, set during step 17 review-resonance).
    # Scoped to the revision skill ONLY: snapshot (step 19) and drift (step
    # 20) must always run regardless of the revision route.
    if step.skill == "shenbi-chapter-revision" and _is_revision_skipped(state, chapter):
        log.info("revision_step_skipped", chapter=chapter)
        _record_step_done(state, step, chapter)
        _reset_retries(state, step, chapter)
        _ensure_revision_decisions_exists(project_dir, chapter, state, log)
        return _advance(state, step_idx, step, chapter, project_dir=project_dir)

    # Adaptive triggering: recall, drift, snapshot run only when data indicates need.
    if not _should_run_step(step, state, project_dir):
        _record_step_done(state, step, chapter)
        _reset_retries(state, step, chapter)
        # Update manifest tracking for steps that were handled inline.
        if step.skill == "shenbi-snapshot-manage":
            # snapshot already taken + manifest updated in _snapshot_chapter_files
            # Run linguistic drift check after snapshot (spec §3.4, Task 5)
            try:
                _check_linguistic_drift(project_dir, chapter)
            except DriftEscalationError as e:
                log.error("drift_escalation_checkpoint", chapter=chapter, error=str(e))
                set_checkpoint(
                    state,
                    CheckpointType.ESCALATION,
                    chapter=chapter,
                    artifact=f"audits/escalation-{chapter}-drift.md",
                    context=str(e),
                )
                return True
        return _advance(state, step_idx, step, chapter, project_dir=project_dir)

    # Build dispatch prompt (staging steps write to staging/).
    prompt = f"Execute {step.skill} for chapter {chapter}. Project dir: {project_dir}"
    if step.uses_staging:
        prompt += " Write output to staging/ directory."

    # Inject MODIFY feedback if present (one-shot consumption)
    if state.chapter_loop.modify_feedback:
        prompt += (
            f"\n\nHuman review feedback (incorporate these changes): "
            f"{state.chapter_loop.modify_feedback}"
        )
        state.chapter_loop.modify_feedback = None

    # Inject prior G4 failure details as corrective feedback on retry
    retry_key = _retry_key(chapter, step.skill)
    prev_g4_feedback = state.chapter_loop.retry_feedback.get(retry_key)
    if prev_g4_feedback:
        prompt += (
            f"\n\n## CORRECTIVE FEEDBACK (prior attempt failed G4 validation)\n"
            f"Your previous output failed the structural check:\n"
            f"```\n{prev_g4_feedback}\n```\n"
            f"Fix these issues in your new output."
        )

    # Dispatch the skill.
    result = dispatch_skill(
        step.skill,
        project_dir,
        prompt,
        uses_staging=step.uses_staging,
    )

    # State-settling failure: mark settling_failed and pause (spec §11).
    if not result.success and "state-settling" in step.skill:
        from shenbi.pipeline.error_handler import handle_state_settle_failure

        handle_state_settle_failure(state, chapter)
        log.error(
            "chapter_state_settle_failed",
            chapter=chapter,
            step=step.step_num,
        )
        return True  # checkpoint raised, pause for human

    # Scoring failure (review-resonance): exit code 2/3 need special handling.
    if not result.success and "review-resonance" in step.skill:
        from shenbi.pipeline.error_handler import handle_scoring_failure

        if handle_scoring_failure(state, result.returncode):
            log.warning(
                "scoring_failure_retry",
                chapter=chapter,
                exit_code=result.returncode,
            )
            return False  # retry this step, don't advance step_index
        return _handle_failure(state, step, chapter, "scoring", project_dir)

    if not result.success:
        log.error(
            "chapter_dispatch_failed",
            chapter=chapter,
            step=step.step_num,
            skill=step.skill,
        )
        return _handle_failure(state, step, chapter, "dispatch", project_dir)

    # G4: skill-specific structural validation (every dispatched step).
    g4_files = _resolve_g4_files(project_dir, step, chapter)
    g4 = run_gate_g4(step.skill, g4_files, project_dir, chapter=chapter, phase="chapter_loop")
    if not _gate_passed(g4):
        must_fix = g4.get("must_fix", [])
        hard_fails, soft_fails, warn_fails = _classify_g4_failures(must_fix)

        # Edge case: G4 failed but must_fix was empty or all items unmatched.
        # Treat as a single generic HARD failure (conservative default).
        if not hard_fails and not soft_fails and not warn_fails:
            hard_fails = ["G4.generic_failure: (no must_fix details)"]

        for w in warn_fails:
            log.info("chapter_g4_warn", chapter=chapter, step=step.step_num, item=w)

        for s in soft_fails:
            tracker_key = _extract_check_id(s)
            tracker = state.chapter_loop.soft_fail_trackers.get(tracker_key)
            if tracker is None:
                tracker = SoftFailTracker(check_id=tracker_key)
                state.chapter_loop.soft_fail_trackers[tracker_key] = tracker
            should_escalate = tracker.record(chapter)
            log.warning(
                "chapter_g4_soft_fail",
                chapter=chapter,
                step=step.step_num,
                item=s,
                occurrences=len(tracker.occurrences),
            )
            if should_escalate:
                log.error(
                    "chapter_g4_soft_escalated",
                    chapter=chapter,
                    check_id=tracker_key,
                    occurrences=tracker.occurrences,
                )
                # Spec 22 E32: route the orphaned escalation signal to the
                # check_escalation consumer + dispatch escalation-review.
                _check_soft_fail_escalation(state, Path(project_dir), chapter)

        if hard_fails:
            state.chapter_loop.retry_feedback[retry_key] = _enrich_g4_feedback(hard_fails)
            # Durable budget trail for both paths (spec §3.1).
            consumed = state.chapter_loop.retry_budget_consumed.get(retry_key, 0) + 1
            state.chapter_loop.retry_budget_consumed[retry_key] = consumed
            if consumed > state.config.max_audit_retries:
                raise RetryExhaustedError(
                    f"Retry budget ({state.config.max_audit_retries}) exhausted for {retry_key} "
                    f"(consumed {consumed})"
                )
            if state.config.per_chapter_review_enabled:
                # Budget already consumed above; prevent _handle_failure from
                # double-incrementing the durable counter.
                return _handle_failure(
                    state, step, chapter, "gate", project_dir, budget_pre_consumed=True
                )
            count = state.chapter_loop.retry_counts.get(retry_key, 0) + 1
            state.chapter_loop.retry_counts[retry_key] = count
            if count <= 1:
                log.info(
                    "chapter_g4_retry_auto_hard",
                    chapter=chapter,
                    step=step.step_num,
                    attempt=count,
                    hard_fails=hard_fails,
                )
                return False
            log.info("chapter_g4_continue_auto", chapter=chapter, step=step.step_num)
            state.chapter_loop.retry_counts.pop(retry_key, None)
        # No hard fails → fall through to advance

    # G3: scoring independence for requires_independent_agent skills (step 17).
    if requires_independent(step.skill):
        g3 = run_gate_g3(step.skill, project_dir, chapter=chapter, phase="chapter_loop")
        if not _gate_passed(g3):
            log.error(
                "chapter_g3_failed",
                chapter=chapter,
                step=step.step_num,
                skill=step.skill,
            )
            return _handle_failure(state, step, chapter, "gate", project_dir)

    # Conditional: foreshadowing-resolve after foreshadowing-track (step 7b).
    if "foreshadowing-track" in step.skill:
        _check_conditional_resolve(state, project_dir, chapter)

    # After last core-circle audit: genre circle + boundary circle via audit_layer.
    if step.is_audit and step_idx == _LAST_AUDIT_IDX:
        gc_path = project_dir / "genre-config.json"
        gc: dict[str, object] = {}
        if gc_path.exists():
            gc = json.loads(gc_path.read_text(encoding="utf-8"))

        cs = _get_chapter_state(state, chapter)
        while cs.audit_retry_count < 100:
            audit_result = run_audit_layer(project_dir, chapter, gc)
            cs.audit_results["blocking_found"] = audit_result.blocking_found
            cs.audit_results["issues"] = audit_result.issues
            cs.audit_results["audit_reports"] = audit_result.audit_reports

            if not audit_result.blocking_found:
                log.info("audit_layer_passed", chapter=chapter)
                break

            cs.audit_retry_count += 1
            from shenbi.pipeline.error_handler import handle_audit_blocking

            if not handle_audit_blocking(state, chapter, cs.audit_retry_count):
                log.error(
                    "audit_blocking_escalation",
                    chapter=chapter,
                    retries=cs.audit_retry_count,
                )
                set_checkpoint(
                    state,
                    CheckpointType.ESCALATION,
                    chapter=chapter,
                    context=(
                        f"Audit BLOCKING persists after {cs.audit_retry_count} "
                        f"revision attempts for chapter {chapter}"
                    ),
                )
                return True  # checkpoint raised, pause for human

            log.info(
                "audit_blocking_revision",
                chapter=chapter,
                retry=cs.audit_retry_count,
            )
            rev = dispatch_skill(
                "shenbi-chapter-revision",
                project_dir,
                f"Revise chapter {chapter} to fix audit BLOCKING issues.",
            )
            if not rev.success:
                return _handle_failure(state, step, chapter, "audit-revision", project_dir)

        if cs.audit_retry_count >= 100:
            log.error(
                "audit_hard_cap_reached",
                chapter=chapter,
                retries=cs.audit_retry_count,
            )
            set_checkpoint(
                state,
                CheckpointType.ESCALATION,
                chapter=chapter,
                context=(
                    f"Audit revision hard cap (100) reached for chapter {chapter}. "
                    f"Manual review required."
                ),
            )
            return True

    # After review-resonance: parse score and run revision routing.
    if "review-resonance" in step.skill:
        # Parse resonance score from the audit report
        cs = _get_chapter_state(state, chapter)
        report_path = project_dir / resolve_chapter_path("audits/chapter-N-resonance.md", chapter)
        cs.resonance_score = _parse_resonance_score(report_path)
        log.info(
            "resonance_score_parsed",
            chapter=chapter,
            score=cs.resonance_score,
        )

        _route_revision_after_resonance(state, project_dir, chapter)

        # Persist to resonance_trend.md as a MARKDOWN TABLE ROW (not YAML).
        # _parse_resonance_score (chapter_loop.py:667) already ran and stored the
        # overall int in cs.resonance_score. Reuse it — do NOT re-parse.
        overall = cs.resonance_score  # int | None
        if overall is not None:
            from shenbi.pipeline.truth_io import write_truth_file

            trend_row = _build_resonance_trend_row(chapter, overall)
            write_truth_file(
                project_dir,
                "resonance_trend.md",
                trend_row,
                mode="upsert_markdown_row",
                key_field="chapter",  # dedup on first column (Ch{N})
            )
            log.info("resonance_score_persisted", chapter=chapter, overall=overall)

    # Success: record, reset retries, advance.
    _record_step_done(state, step, chapter)
    _reset_retries(state, step, chapter)

    # After chapter-revision step succeeds, ensure decisions file exists
    if "chapter-revision" in step.skill:
        _ensure_revision_decisions_exists(project_dir, chapter, state, log)

    # Blueprint alignment check after chapter drafting (WARN-level, non-blocking)
    if "chapter-drafting" in step.skill:
        _check_volume_map_alignment(project_dir, chapter)

    # Update manifest tracking for adaptive steps that just ran.
    if step.skill == "shenbi-foreshadowing-recall":
        _update_last_recall_manifest(project_dir, chapter)
    elif step.skill == "shenbi-drift-guidance":
        _update_last_drift_manifest(project_dir, chapter)

    return _advance(state, step_idx, step, chapter, project_dir=project_dir)
