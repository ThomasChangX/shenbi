"""State machine: load, save, and checkpoint management for pipeline-state.json.

Spec: docs/superpowers/specs/archive/2026-07-01-novel-pipeline-design.md Section 3.
"""

from __future__ import annotations

from datetime import UTC, datetime
from collections.abc import Callable
from pathlib import Path

from shenbi.logging import get_logger
from shenbi.pipeline.state import (
    CheckpointData,
    CheckpointType,
    PipelineState,
    ReviewDecision,
)
from shenbi.safe_write import safe_write

log = get_logger(__name__)

STATE_FILENAME = "pipeline-state.json"


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def load_state(project_dir: Path | str) -> PipelineState:
    """Load pipeline state from project_dir/pipeline-state.json."""
    project_dir = Path(project_dir)
    state_file = project_dir / STATE_FILENAME
    if not state_file.exists():
        raise FileNotFoundError(f"pipeline-state.json not found in {project_dir}")
    state = PipelineState.from_json(state_file.read_text(encoding="utf-8"))
    log.debug("state_loaded", project_dir=str(project_dir), phase=state.phase.value)
    return state


def transact_state(
    project_dir: Path | str, mutator: Callable[[PipelineState], None]
) -> PipelineState:
    """Lock a whole read-modify-write cycle on pipeline-state.json (spec #37 T605).

    WriteLock (L1) critical section around load -> mutator -> save. Replaces
    the unlockable load/increment/save pattern that lost cross-writer updates.
    """
    from shenbi.pipeline.filelock_utils import WriteLock

    with WriteLock(project_dir):
        try:
            state = load_state(project_dir)
        except FileNotFoundError:
            state = PipelineState(project_dir=str(project_dir))
        mutator(state)
        save_state(project_dir, state)
        return state


def save_state(project_dir: Path | str, state: PipelineState) -> None:
    """Atomically save pipeline state to project_dir/pipeline-state.json."""
    project_dir = Path(project_dir)
    state_file = project_dir / STATE_FILENAME
    safe_write(state_file, state.to_json())
    log.debug("state_saved", project_dir=str(project_dir), phase=state.phase.value)


def set_checkpoint(
    state: PipelineState,
    checkpoint_type: CheckpointType,
    chapter: int | None = None,
    artifact: str | None = None,
    context: str | None = None,
    options: list[str] | None = None,
) -> None:
    """Set the pending checkpoint on the state."""
    if options is None:
        options = ["approve", "modify", "reject"]
    state.pending_checkpoint = CheckpointData(
        type=checkpoint_type,
        chapter=chapter,
        artifact=artifact,
        context=context,
        options=options,
        created_at=_now_iso(),
    )


def clear_checkpoint(state: PipelineState, decision: ReviewDecision) -> None:
    """Clear the pending checkpoint and record it in history.

    C33 (spec #47 R3): resolving an ESCALATION checkpoint (approve/reject/
    modify) resets ALL per-phase retry counters — the three retry_counts
    maps AND per-chapter audit_retry_count/revision_count.


    C30 F338: a NONE checkpoint (no real checkpoint pending) is a no-op —
    it must not enter the history that ``cmd_resume`` keys phase
    transitions off.

    C30 F371: history entries carry ``consumed=False``; the resume command
    that ACTS on an approve event flips it to True, so transitions no
    longer guess from ``history[-1]``.
    """
    cp = state.pending_checkpoint
    if cp.type == CheckpointType.NONE:
        state.pending_checkpoint = CheckpointData(type=CheckpointType.NONE)
        return
    state.checkpoint_history.append(
        {
            "type": cp.type.value,
            "chapter": cp.chapter,
            "decision": decision.value,
            "resolved_at": _now_iso(),
            "consumed": False,
        }
    )
    if cp.type == CheckpointType.ESCALATION and decision in (
        ReviewDecision.APPROVE,
        ReviewDecision.REJECT,
        ReviewDecision.MODIFY,
    ):
        state.genesis.retry_counts.clear()
        state.chapter_loop.retry_counts.clear()
        state.closure_retry_counts.clear()
        # C33 R3 (T508, spec #47): per-chapter audit counters share the reset
        # contract. Scope rule: chapter set → clear that chapter only; None →
        # all (mirrors _reset_retry_budget prefix semantics, NOT dict clear-all).
        _keys = (
            [str(cp.chapter)] if cp.chapter is not None else list(state.chapter_loop.chapter_states)
        )
        for k in _keys:
            cs = state.chapter_loop.chapter_states.get(k)
            if cs is not None:
                cs.audit_retry_count = 0
                cs.revision_count = 0
        log.info("retry_counters_reset", reason="escalation_resolved", decision=decision.value)
    state.pending_checkpoint = CheckpointData(type=CheckpointType.NONE)


def is_at_checkpoint(state: PipelineState) -> bool:
    """Check if the pipeline is currently waiting at a checkpoint."""
    return state.pending_checkpoint.type != CheckpointType.NONE
