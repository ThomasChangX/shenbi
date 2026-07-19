"""Tests for pipeline state types."""

from __future__ import annotations

from shenbi.pipeline.state import (
    CheckpointData,
    CheckpointType,
    GenesisState,
    PipelinePhase,
    PipelineState,
    ReviewDecision,
)


class TestPipelineEnums:
    def test_pipeline_phase_values(self):
        assert PipelinePhase.GENESIS == "genesis"
        assert PipelinePhase.CHAPTER_LOOP == "chapter-loop"
        assert PipelinePhase.CLOSURE == "closure"
        assert PipelinePhase.COMPLETED == "completed"
        assert PipelinePhase.FAILED == "failed"

    def test_checkpoint_type_values(self):
        assert CheckpointType.NONE == "none"
        assert CheckpointType.GENESIS_COMPLETE == "genesis-complete"
        assert CheckpointType.CHAPTER_MEMO == "chapter-memo"
        assert CheckpointType.STATE_SETTLE == "state-settle"
        assert CheckpointType.ESCALATION == "escalation"
        assert CheckpointType.PER_CHAPTER == "per-chapter"
        assert CheckpointType.VOLUME_BOUNDARY == "volume-boundary"
        assert CheckpointType.BOOK_CLOSURE == "book-closure"

    def test_review_decision_values(self):
        assert ReviewDecision.APPROVE == "approve"
        assert ReviewDecision.MODIFY == "modify"
        assert ReviewDecision.REJECT == "reject"


class TestPipelineStateSerialization:
    def test_default_state(self):
        state = PipelineState.default(project_dir="/tmp/novel")
        assert state.phase == PipelinePhase.GENESIS
        assert state.genesis.state == GenesisState.PENDING
        assert state.pending_checkpoint.type == CheckpointType.NONE
        assert state.config.max_revision_retries == 3
        assert state.config.resonance_global_floor == 65

    def test_to_json_round_trip(self):
        state = PipelineState.default(project_dir="/tmp/novel")
        state.genesis.state = GenesisState.IN_PROGRESS
        state.genesis.skills_done = ["shenbi-worldbuilding"]
        state.chapter_loop.current_chapter = 5
        state.chapter_loop.current_step = "chapter-planning"

        json_str = state.to_json()
        restored = PipelineState.from_json(json_str)

        assert restored.phase == PipelinePhase.GENESIS
        assert restored.genesis.skills_done == ["shenbi-worldbuilding"]
        assert restored.chapter_loop.current_chapter == 5
        assert restored.chapter_loop.current_step == "chapter-planning"

    def test_checkpoint_round_trip(self):
        state = PipelineState.default(project_dir="/tmp/novel")
        state.pending_checkpoint = CheckpointData(
            type=CheckpointType.CHAPTER_MEMO,
            chapter=5,
            artifact="plans/chapter-5-plan.md",
            context="Review chapter memo",
            options=["approve", "modify", "reject"],
        )
        restored = PipelineState.from_json(state.to_json())
        assert restored.pending_checkpoint.type == CheckpointType.CHAPTER_MEMO
        assert restored.pending_checkpoint.chapter == 5
        assert restored.pending_checkpoint.artifact == "plans/chapter-5-plan.md"

    def test_audit_retry_count_round_trip(self):
        """audit_retry_count is persisted and restored correctly (A8)."""
        from shenbi.pipeline.state import ChapterState

        state = PipelineState.default(project_dir="/tmp/novel")
        cs = ChapterState(audit_retry_count=3)
        state.chapter_loop.chapter_states["1"] = cs

        restored = PipelineState.from_json(state.to_json())
        restored_cs = restored.chapter_loop.chapter_states["1"]
        assert restored_cs.audit_retry_count == 3

    def test_audit_retry_count_default_is_zero(self):
        """New ChapterState instances default audit_retry_count to 0."""
        from shenbi.pipeline.state import ChapterState

        cs = ChapterState()
        assert cs.audit_retry_count == 0

        state = PipelineState.default(project_dir="/tmp/novel")
        cs2 = state.chapter_loop.chapter_states.get("1")
        assert cs2 is None  # no chapter states by default

        # When deserializing from old data without audit_retry_count,
        # it should default to 0.
        old_json = state.to_json()
        restored = PipelineState.from_json(old_json)
        # Force-create a chapter state entry to verify default
        from shenbi.pipeline.state import ChapterLoopStateData

        restored.chapter_loop = ChapterLoopStateData(chapter_states={"1": ChapterState()})
        assert restored.chapter_loop.chapter_states["1"].audit_retry_count == 0

    def test_default_floor_matches_single_source_of_truth(self):
        from shenbi.config.thresholds import DEFAULT_THRESHOLDS

        state = PipelineState.default(project_dir="/tmp/novel")
        assert state.config.resonance_global_floor == DEFAULT_THRESHOLDS.resonance_global_floor
