"""Tests for phase transition logic.

Spec: docs/superpowers/specs/2026-07-01-novel-pipeline-design.md Section 3.1
(state transition table).
"""

from __future__ import annotations

from shenbi.pipeline.state import ClosureState, GenesisState, PipelinePhase, PipelineState
from shenbi.pipeline.transitions import (
    transition_chapter_to_closure,
    transition_closure_to_completed,
    transition_genesis_to_chapter_loop,
    transition_to_failed,
)


def test_genesis_to_chapter_loop():
    state = PipelineState.default("/x")
    state.genesis.state = GenesisState.CHECKPOINT_PENDING
    transition_genesis_to_chapter_loop(state)
    assert state.phase == PipelinePhase.CHAPTER_LOOP
    assert state.chapter_loop.current_chapter == 1


def test_chapter_to_closure():
    state = PipelineState.default("/x")
    state.phase = PipelinePhase.CHAPTER_LOOP
    transition_chapter_to_closure(state)
    assert state.phase == PipelinePhase.CLOSURE


def test_closure_to_completed():
    state = PipelineState.default("/x")
    state.phase = PipelinePhase.CLOSURE
    transition_closure_to_completed(state)
    assert state.phase == PipelinePhase.COMPLETED


def test_to_failed():
    state = PipelineState.default("/x")
    transition_to_failed(state, "unrecoverable error")
    assert state.phase == PipelinePhase.FAILED


def test_genesis_to_chapter_loop_marks_genesis_completed():
    """Spec §3.1: genesis review approve marks genesis complete and starts ch1."""
    state = PipelineState.default("/x")
    state.genesis.state = GenesisState.CHECKPOINT_PENDING
    state.genesis.skills_done.append("shenbi-worldbuilding")
    transition_genesis_to_chapter_loop(state)
    assert state.genesis.state == GenesisState.COMPLETED
    assert state.chapter_loop.step_index == 0
    assert state.chapter_loop.current_step == ""


def test_chapter_to_closure_sets_closure_in_progress():
    """Spec §3.1: N==total_chapters -> closure:in-progress."""
    state = PipelineState.default("/x")
    state.phase = PipelinePhase.CHAPTER_LOOP
    transition_chapter_to_closure(state)
    assert state.closure == ClosureState.IN_PROGRESS


def test_closure_to_completed_sets_closure_completed():
    """Spec §3.1: book-closure review approve -> closure:completed."""
    state = PipelineState.default("/x")
    state.phase = PipelinePhase.CLOSURE
    state.closure = ClosureState.CHECKPOINT_PENDING
    transition_closure_to_completed(state)
    assert state.closure == ClosureState.COMPLETED


def test_genesis_to_chapter_loop_preserves_skills_done():
    """Transition should not wipe the genesis skill history."""
    state = PipelineState.default("/x")
    state.genesis.state = GenesisState.CHECKPOINT_PENDING
    state.genesis.skills_done = ["shenbi-worldbuilding", "shenbi-genre-config"]
    transition_genesis_to_chapter_loop(state)
    assert state.genesis.skills_done == ["shenbi-worldbuilding", "shenbi-genre-config"]
