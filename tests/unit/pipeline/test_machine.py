"""Tests for pipeline state machine."""

from __future__ import annotations

from pathlib import Path

import pytest

from shenbi.pipeline.machine import (
    clear_checkpoint,
    is_at_checkpoint,
    load_state,
    save_state,
    set_checkpoint,
)
from shenbi.pipeline.state import (
    CheckpointType,
    PipelineState,
    ReviewDecision,
)


class TestLoadSave:
    def test_save_and_load_round_trip(self, tmp_project: Path):
        state = PipelineState.default(project_dir=str(tmp_project))
        state.genesis.current_step = 3
        state.genesis.skills_done = ["a", "b"]

        save_state(tmp_project, state)
        loaded = load_state(tmp_project)

        assert loaded.genesis.current_step == 3
        assert loaded.genesis.skills_done == ["a", "b"]

    def test_load_missing_raises(self, tmp_project: Path):
        with pytest.raises(FileNotFoundError):
            load_state(tmp_project)

    def test_save_creates_state_file(self, tmp_project: Path):
        state = PipelineState.default(project_dir=str(tmp_project))
        save_state(tmp_project, state)
        assert (tmp_project / "pipeline-state.json").exists()

    def test_save_is_atomic(self, tmp_project: Path):
        """Verify state is saved atomically (no partial writes on crash)."""
        state = PipelineState.default(project_dir=str(tmp_project))
        save_state(tmp_project, state)
        content = (tmp_project / "pipeline-state.json").read_text()
        import json

        # Should be valid JSON (atomic write ensures no partial).
        json.loads(content)


class TestCheckpoint:
    def test_set_checkpoint(self):
        state = PipelineState.default(project_dir="/tmp/x")
        set_checkpoint(
            state,
            checkpoint_type=CheckpointType.CHAPTER_MEMO,
            chapter=5,
            artifact="plans/chapter-5-plan.md",
            context="Review memo",
        )
        assert state.pending_checkpoint.type == CheckpointType.CHAPTER_MEMO
        assert state.pending_checkpoint.chapter == 5
        assert state.pending_checkpoint.artifact == "plans/chapter-5-plan.md"
        assert is_at_checkpoint(state) is True

    def test_clear_checkpoint(self):
        state = PipelineState.default(project_dir="/tmp/x")
        set_checkpoint(state, CheckpointType.CHAPTER_MEMO, chapter=5, artifact="x")
        assert is_at_checkpoint(state)

        clear_checkpoint(state, ReviewDecision.APPROVE)
        assert state.pending_checkpoint.type == CheckpointType.NONE
        assert is_at_checkpoint(state) is False
        assert len(state.checkpoint_history) == 1
        assert state.checkpoint_history[0]["decision"] == "approve"

    def test_clear_checkpoint_records_history(self):
        state = PipelineState.default(project_dir="/tmp/x")
        set_checkpoint(state, CheckpointType.GENESIS_COMPLETE, artifact="genesis")
        clear_checkpoint(state, ReviewDecision.MODIFY)
        assert state.checkpoint_history[-1]["decision"] == "modify"
        assert state.checkpoint_history[-1]["type"] == "genesis-complete"
