"""State machine: load, save, and checkpoint management for pipeline-state.json.

Spec: docs/superpowers/specs/2026-07-01-novel-pipeline-design.md Section 3.
"""

from __future__ import annotations

from datetime import UTC, datetime
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

    When an ESCALATION checkpoint is resolved (approved or rejected), all
    per-phase retry counters are reset so the pipeline gets a fresh set of
    retry attempts rather than immediately re-escalating.
    """
    cp = state.pending_checkpoint
    state.checkpoint_history.append(
        {
            "type": cp.type.value,
            "chapter": cp.chapter,
            "decision": decision.value,
            "resolved_at": _now_iso(),
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
        log.info("retry_counters_reset", reason="escalation_resolved", decision=decision.value)
    state.pending_checkpoint = CheckpointData(type=CheckpointType.NONE)


def is_at_checkpoint(state: PipelineState) -> bool:
    """Check if the pipeline is currently waiting at a checkpoint."""
    return state.pending_checkpoint.type != CheckpointType.NONE
