"""Phase 3 book closure orchestrator: 10-step sequence ending with
book-closure checkpoint (spec section 8).

Steps run serially; each dispatches a skill, validates the output with G4
(and G3 for scoring skills), and on success advances the closure cursor.
After step 9 (style-learning) the runner pauses at the book-closure
checkpoint. Step 10 (snapshot-manage) executes after the checkpoint is
approved.

The runner is stateless itself: it mutates the passed-in
:class:`PipelineState` in place and the caller persists it.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from shenbi.contracts.paths import resolve_volume_path
from shenbi.logging import get_logger
from shenbi.pipeline.dispatch_helper import (
    dispatch_skill,
    requires_independent,
    run_gate_g3,
    run_gate_g4,
)
from shenbi.pipeline.machine import is_at_checkpoint, set_checkpoint
from shenbi.pipeline.error_handler import handle_dispatch_failure
from shenbi.pipeline.triggers import read_volume_boundaries
from shenbi.pipeline.state import CheckpointType, ClosureState, PipelineState
from shenbi.status import GateStatus

log = get_logger(__name__)


@dataclass
class ClosureStep:
    """One step in the closure sequence (spec section 8).

    Attributes:
        step_num: 1-based step number.
        skill: Full ``shenbi-*`` skill name.
        output_path: Expected output relative to project_dir (for G4).
        requires_g3: Whether to run G3 (scoring independence). Auto-set
            for ``requires_independent_agent`` skills in :func:`run_closure_step`.
    """

    step_num: int
    skill: str
    output_path: str = ""
    requires_g3: bool = False


# ---------------------------------------------------------------------------
# Closure step table (spec section 8)
#
# 10 steps. Steps 1-9 produce closure artifacts; step 10 (snapshot-manage)
# runs after the book-closure checkpoint is approved. The checkpoint is set
# when closure_step reaches 9 (after step 9 / style-learning), BEFORE
# step 10 executes (spec section 8).
# ---------------------------------------------------------------------------

CLOSURE_STEPS: list[ClosureStep] = [
    ClosureStep(
        1,
        "shenbi-foreshadowing-resolve",
        "truth/pending_hooks.md",
    ),
    ClosureStep(
        2,
        "shenbi-memory-distill",
        "truth/book_strata.md",
    ),
    ClosureStep(
        3,
        "shenbi-volume-consolidation",
        "truth/volume_summaries.md",
    ),
    ClosureStep(
        4,
        "shenbi-score-volume",
        "audits/volume-N-score.md",
        requires_g3=True,
    ),
    ClosureStep(
        5,
        "shenbi-review-arc-payoff",
        "audits/volume-N-payoff.md",
    ),
    ClosureStep(
        6,
        "shenbi-review-long-span",
        "audits/chapter-N-long-span.md",
    ),
    ClosureStep(
        7,
        "shenbi-chapter-pattern",
        "outline/chapter_patterns.md",
    ),
    ClosureStep(
        8,
        "shenbi-foundation-review",
        "foundation/review_report.md",
        requires_g3=True,
    ),
    ClosureStep(
        9,
        "shenbi-style-learning",
        "style/style_profile.md",
    ),
    ClosureStep(
        10,
        "shenbi-snapshot-manage",
        "final-snapshot/",
    ),
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _gate_passed(result: dict[str, Any]) -> bool:
    """True iff a gate result dict reports PASS or SKIP."""
    status = str(result.get("status", ""))
    return status in (GateStatus.PASS, GateStatus.SKIP)


def _record_done(state: PipelineState, skill: str) -> None:
    """Append *skill* to the closure skills-done list."""
    if skill not in state.closure_skills_done:
        state.closure_skills_done.append(skill)
    _reset_closure_retries(state, skill)


def _current_volume(project_dir: Path) -> int:
    """Determine the current (last) volume number from volume_map.md (I5).

    Returns the volume count (the last volume index) when boundaries are
    found, falling back to 1 when the volume map is absent or empty.
    """
    boundaries = read_volume_boundaries(project_dir)
    return len(boundaries) if boundaries else 1


def _resolve_closure_g4_path(step: ClosureStep, project_dir: Path) -> str:
    """Resolve the output path for G4 validation, substituting N (I5).

    Returns the path with volume number substituted, or empty string when
    the step has no single output file.
    """
    if not step.output_path:
        return ""
    if "N" in step.output_path:
        vol = _current_volume(project_dir)
        return resolve_volume_path(step.output_path, vol)
    return step.output_path


def _handle_closure_failure(
    state: PipelineState,
    step: ClosureStep,
    failure: str,
) -> bool:
    """Record a closure step failure and decide retry vs escalate (I2).

    Returns True when the step should be retried (attempt < limit), False
    when retries are exhausted. Mirrors the genesis/chapter_loop pattern
    via :func:`handle_dispatch_failure`.
    """
    skill = step.skill
    count = state.closure_retry_counts.get(skill, 0) + 1
    state.closure_retry_counts[skill] = count
    if handle_dispatch_failure(state, skill, count):
        log.warning(
            "closure_step_failed_retrying",
            step=step.step_num,
            skill=skill,
            failure=failure,
            attempt=count,
            limit=state.config.max_revision_retries,
        )
        return True
    log.error(
        "closure_step_escalation",
        step=step.step_num,
        skill=skill,
        failure=failure,
        attempts=count,
    )
    return False


def _reset_closure_retries(state: PipelineState, skill: str) -> None:
    """Clear closure retry count after a successful step."""
    state.closure_retry_counts.pop(skill, None)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def run_closure_step(state: PipelineState, project_dir: Path | str) -> bool:
    """Execute the next closure step.

    Steps 1-9 run immediately. After step 9 (style-learning) completes, the
    runner sets the ``BOOK_CLOSURE`` checkpoint and returns True: the pipeline
    pauses for human review BEFORE the final snapshot (spec section 8).

    Step 10 (snapshot-manage) only runs once the checkpoint is cleared.
    While the checkpoint is still pending, calling this function returns True
    without dispatching -- the step is blocked pending review.

    After step 10 completes, ``state.closure`` is set to ``COMPLETED`` and the
    function returns True. Calling again after completion is a no-op that keeps
    ``closure == COMPLETED``.

    Returns True if a checkpoint was reached, the step is blocked at a pending
    checkpoint, or closure completed; False if the step failed (dispatch or
    gate). Mutates ``state`` in place; the caller persists it.
    """
    if not project_dir:
        raise ValueError("run_closure_step: project_dir is required")
    project_dir = Path(project_dir)
    idx = state.closure_step
    n = len(CLOSURE_STEPS)

    # Past the last step: closure is already complete.
    if idx >= n:
        state.closure = ClosureState.COMPLETED
        return True

    # Step 10 (snapshot-manage): gated on the book-closure checkpoint being
    # cleared. While pending, do not dispatch -- the human must review first.
    if idx == n - 1 and is_at_checkpoint(state):
        log.info("closure_blocked_at_checkpoint", step=n)
        return True

    step = CLOSURE_STEPS[idx]
    log.info("closure_step", step=step.step_num, skill=step.skill)

    prompt = (
        f"Execute {step.skill} for book closure (step {step.step_num}). Project dir: {project_dir}"
    )

    # Dispatch.
    # Dispatch + gate with retry loop (I2): retries on dispatch/gate failure
    # up to max_revision_retries, then returns False for escalation.
    while True:
        disp = dispatch_skill(step.skill, project_dir, prompt)
        if not disp.success:
            if _handle_closure_failure(state, step, "dispatch"):
                continue
            return False

        # G4: skill-specific structural validation (with volume substitution I5).
        g4_file = _resolve_closure_g4_path(step, project_dir)
        g4 = run_gate_g4(step.skill, [g4_file] if g4_file else [], project_dir)
        if not _gate_passed(g4):
            if _handle_closure_failure(state, step, "gate"):
                continue
            return False

        # G3: scoring independence for requires_independent_agent skills.
        if step.requires_g3 or requires_independent(step.skill):
            g3 = run_gate_g3(step.skill, project_dir)
            if not _gate_passed(g3):
                if _handle_closure_failure(state, step, "gate"):
                    continue
                return False

        break  # all dispatch + gate checks passed

    # Success: record and advance.
    _record_done(state, step.skill)
    state.closure_step = idx + 1
    log.info(
        "closure_step_done",
        step=step.step_num,
        skill=step.skill,
        next_step=state.closure_step,
    )

    # After step 9: raise the book-closure checkpoint BEFORE step 10.
    if state.closure_step == n - 1:
        state.closure = ClosureState.CHECKPOINT_PENDING
        set_checkpoint(
            state,
            CheckpointType.BOOK_CLOSURE,
            artifact="final-snapshot/",
            context=(
                "Review final book before completion. Check: all hooks "
                "RESOLVED, protagonist arc complete, three-layer conflicts "
                "converged, theme fully explored."
            ),
        )
        log.info("closure_checkpoint_set", steps_done=state.closure_step)
        return True

    # After step 10: closure is complete.
    if state.closure_step >= n:
        state.closure = ClosureState.COMPLETED
        log.info("closure_completed", steps_done=state.closure_step)
        return True

    return True
