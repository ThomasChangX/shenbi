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

from shenbi.logging import get_logger
from shenbi.pipeline.dispatch_helper import (
    dispatch_skill,
    requires_independent,
    run_gate_g3,
    run_gate_g4,
)
from shenbi.pipeline.machine import set_checkpoint
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
# when all 10 steps have been consumed (closure_step >= len(CLOSURE_STEPS)).
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


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def run_closure_step(state: PipelineState, project_dir: Path | str) -> bool:
    """Execute the next closure step.

    Returns True if a checkpoint was reached (book-closure) or all steps
    are already consumed; False if the step failed (dispatch or gate).
    Mutates ``state`` in place; the caller persists it.

    When all 10 steps have been consumed, the runner sets the
    ``BOOK_CLOSURE`` checkpoint and returns True.
    """
    project_dir = Path(project_dir)
    idx = state.closure_step

    if idx >= len(CLOSURE_STEPS):
        # All steps consumed: set book-closure checkpoint.
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
        log.info("closure_checkpoint_set", steps_done=idx)
        return True

    step = CLOSURE_STEPS[idx]
    log.info("closure_step", step=step.step_num, skill=step.skill)

    prompt = (
        f"Execute {step.skill} for book closure (step {step.step_num}). Project dir: {project_dir}"
    )

    # Dispatch.
    disp = dispatch_skill(step.skill, project_dir, prompt)
    if not disp.success:
        log.error(
            "closure_dispatch_failed",
            step=step.step_num,
            skill=step.skill,
            returncode=disp.returncode,
        )
        return False

    # G4: skill-specific structural validation.
    g4_file = step.output_path if step.output_path else ""
    g4 = run_gate_g4(step.skill, [g4_file] if g4_file else [], project_dir)
    if not _gate_passed(g4):
        log.error(
            "closure_g4_failed",
            step=step.step_num,
            skill=step.skill,
            g4=g4,
        )
        return False

    # G3: scoring independence for requires_independent_agent skills.
    if step.requires_g3 or requires_independent(step.skill):
        g3 = run_gate_g3(step.skill, project_dir)
        if not _gate_passed(g3):
            log.error(
                "closure_g3_failed",
                step=step.step_num,
                skill=step.skill,
            )
            return False

    # Success: record and advance.
    _record_done(state, step.skill)
    state.closure_step = idx + 1
    log.info(
        "closure_step_done",
        step=step.step_num,
        skill=step.skill,
        next_step=idx + 1,
    )

    return True
