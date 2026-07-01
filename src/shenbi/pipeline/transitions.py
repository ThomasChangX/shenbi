"""Phase transition logic for the novel pipeline state machine.

Spec: docs/superpowers/specs/2026-07-01-novel-pipeline-design.md Section 3.1
(state transition table).

Each transition mutates the passed-in :class:`PipelineState` in place and is a
pure state operation. The caller is responsible for persisting the state and
for any side effects named in the spec table (e.g. committing staging,
recording snapshots) -- mirroring how the genesis/chapter-loop/closure
orchestrators keep state mutation separate from disk writes.
"""

from __future__ import annotations

from shenbi.logging import get_logger
from shenbi.pipeline.state import (
    ClosureState,
    GenesisState,
    PipelinePhase,
    PipelineState,
)

log = get_logger(__name__)


def transition_genesis_to_chapter_loop(state: PipelineState) -> None:
    """Genesis checkpoint approved -> enter the chapter loop.

    Spec §3.1: genesis:checkpoint-pending + review approve ->
    chapter-loop:in-progress. Marks genesis complete and starts chapter 1.
    """
    state.phase = PipelinePhase.CHAPTER_LOOP
    state.genesis.state = GenesisState.COMPLETED
    state.chapter_loop.current_chapter = 1
    state.chapter_loop.step_index = 0
    log.info(
        "phase_transition",
        from_phase=PipelinePhase.GENESIS.value,
        to_phase=PipelinePhase.CHAPTER_LOOP.value,
        project_dir=state.project_dir,
    )


def transition_chapter_to_closure(state: PipelineState) -> None:
    """All chapters written -> enter book closure.

    Spec §3.1: chapter-loop:in-progress + N==total_chapters ->
    closure:in-progress.
    """
    state.phase = PipelinePhase.CLOSURE
    state.closure = ClosureState.IN_PROGRESS
    log.info(
        "phase_transition",
        from_phase=PipelinePhase.CHAPTER_LOOP.value,
        to_phase=PipelinePhase.CLOSURE.value,
        project_dir=state.project_dir,
    )


def transition_closure_to_completed(state: PipelineState) -> None:
    """Book-closure checkpoint approved -> pipeline complete.

    Spec §3.1: closure:checkpoint-pending + review approve ->
    closure:completed.
    """
    state.phase = PipelinePhase.COMPLETED
    state.closure = ClosureState.COMPLETED
    log.info(
        "phase_transition",
        from_phase=PipelinePhase.CLOSURE.value,
        to_phase=PipelinePhase.COMPLETED.value,
        project_dir=state.project_dir,
    )


def transition_to_failed(state: PipelineState, reason: str) -> None:
    """Unrecoverable error -> move the pipeline to the failed phase.

    Spec §3.1: chapter-loop:in-progress + unrecoverable error -> failed.
    The reason is recorded in the log for human follow-up.
    """
    state.phase = PipelinePhase.FAILED
    log.error("phase_transition_failed", reason=reason, project_dir=state.project_dir)
