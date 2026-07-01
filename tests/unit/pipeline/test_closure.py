"""Tests for the Phase 3 book closure runner (spec section 8).

Wave 3 Task 6. The closure runner executes a 10-step sequence after all
chapters are complete, ending with a book-closure checkpoint and a final
full snapshot.
"""

from __future__ import annotations

from unittest.mock import patch

from shenbi.pipeline.closure import (
    CLOSURE_STEPS,
    ClosureStep,
    run_closure_step,
)
from shenbi.pipeline.dispatch_helper import DispatchResult
from shenbi.pipeline.state import (
    CheckpointType,
    ClosureState,
    PipelineState,
)

# ---------------------------------------------------------------------------
# CLOSURE_STEPS table structure
# ---------------------------------------------------------------------------


class TestClosureSteps:
    def test_step_count(self):
        assert len(CLOSURE_STEPS) == 10

    def test_step_nums_sequential(self):
        assert [s.step_num for s in CLOSURE_STEPS] == list(range(1, 11))

    def test_foreshadowing_resolve_first(self):
        assert "foreshadowing-resolve" in CLOSURE_STEPS[0].skill

    def test_snapshot_manage_last(self):
        assert "snapshot-manage" in CLOSURE_STEPS[-1].skill

    def test_foundation_review_present(self):
        skills = [s.skill for s in CLOSURE_STEPS]
        assert "shenbi-foundation-review" in skills

    def test_memory_distill_present(self):
        skills = [s.skill for s in CLOSURE_STEPS]
        assert "shenbi-memory-distill" in skills

    def test_score_volume_present(self):
        skills = [s.skill for s in CLOSURE_STEPS]
        assert "shenbi-score-volume" in skills

    def test_style_learning_present(self):
        skills = [s.skill for s in CLOSURE_STEPS]
        assert "shenbi-style-learning" in skills

    def test_review_arc_payoff_present(self):
        skills = [s.skill for s in CLOSURE_STEPS]
        assert "shenbi-review-arc-payoff" in skills

    def test_review_long_span_present(self):
        skills = [s.skill for s in CLOSURE_STEPS]
        assert "shenbi-review-long-span" in skills

    def test_chapter_pattern_present(self):
        skills = [s.skill for s in CLOSURE_STEPS]
        assert "shenbi-chapter-pattern" in skills

    def test_volume_consolidation_present(self):
        skills = [s.skill for s in CLOSURE_STEPS]
        assert "shenbi-volume-consolidation" in skills


class TestClosureStepDataclass:
    def test_defaults(self):
        s = ClosureStep(1, "shenbi-test")
        assert s.step_num == 1
        assert s.skill == "shenbi-test"
        assert s.output_path == ""
        assert s.requires_g3 is False


# ---------------------------------------------------------------------------
# run_closure_step: execution with mock dispatch + gates
# ---------------------------------------------------------------------------


class TestRunClosureStep:
    @patch("shenbi.pipeline.closure.dispatch_skill")
    @patch("shenbi.pipeline.closure.run_gate_g4")
    def test_runs_step_and_advances(self, mock_g4, mock_disp, tmp_path):
        mock_disp.return_value = DispatchResult(True, 0, "{}", "")
        mock_g4.return_value = {"status": "PASS"}
        state = PipelineState.default(str(tmp_path))
        state.closure = ClosureState.IN_PROGRESS
        state.closure_step = 0
        run_closure_step(state, tmp_path)
        assert state.closure_step == 1

    @patch("shenbi.pipeline.closure.dispatch_skill")
    @patch("shenbi.pipeline.closure.run_gate_g4")
    def test_records_step_completion(self, mock_g4, mock_disp, tmp_path):
        mock_disp.return_value = DispatchResult(True, 0, "{}", "")
        mock_g4.return_value = {"status": "PASS"}
        state = PipelineState.default(str(tmp_path))
        state.closure = ClosureState.IN_PROGRESS
        state.closure_step = 0
        run_closure_step(state, tmp_path)
        assert "shenbi-foreshadowing-resolve" in state.closure_skills_done

    @patch("shenbi.pipeline.closure.dispatch_skill")
    @patch("shenbi.pipeline.closure.run_gate_g4")
    def test_dispatch_failure_returns_false(self, mock_g4, mock_disp, tmp_path):
        mock_disp.return_value = DispatchResult(False, 1, "", "error")
        mock_g4.return_value = {"status": "PASS"}
        state = PipelineState.default(str(tmp_path))
        state.closure = ClosureState.IN_PROGRESS
        state.closure_step = 0
        result = run_closure_step(state, tmp_path)
        assert result is False
        assert state.closure_step == 0  # not advanced

    @patch("shenbi.pipeline.closure.dispatch_skill")
    @patch("shenbi.pipeline.closure.run_gate_g4")
    def test_g4_failure_returns_false(self, mock_g4, mock_disp, tmp_path):
        mock_disp.return_value = DispatchResult(True, 0, "{}", "")
        mock_g4.return_value = {"status": "FAIL"}
        state = PipelineState.default(str(tmp_path))
        state.closure = ClosureState.IN_PROGRESS
        state.closure_step = 0
        result = run_closure_step(state, tmp_path)
        assert result is False
        assert state.closure_step == 0

    @patch("shenbi.pipeline.closure.dispatch_skill")
    @patch("shenbi.pipeline.closure.run_gate_g4")
    def test_g4_pass_is_str_enum(self, mock_g4, mock_disp, tmp_path):
        from shenbi.status import GateStatus

        mock_disp.return_value = DispatchResult(True, 0, "{}", "")
        mock_g4.return_value = {"status": GateStatus.PASS}
        state = PipelineState.default(str(tmp_path))
        state.closure = ClosureState.IN_PROGRESS
        state.closure_step = 0
        run_closure_step(state, tmp_path)
        assert state.closure_step == 1

    @patch("shenbi.pipeline.closure.dispatch_skill")
    @patch("shenbi.pipeline.closure.run_gate_g4")
    def test_g4_skip_passes(self, mock_g4, mock_disp, tmp_path):
        mock_disp.return_value = DispatchResult(True, 0, "{}", "")
        mock_g4.return_value = {"status": "SKIP"}
        state = PipelineState.default(str(tmp_path))
        state.closure = ClosureState.IN_PROGRESS
        state.closure_step = 0
        run_closure_step(state, tmp_path)
        assert state.closure_step == 1

    @patch("shenbi.pipeline.closure.dispatch_skill")
    @patch("shenbi.pipeline.closure.run_gate_g4")
    def test_all_steps_consumed_sets_checkpoint(self, mock_g4, mock_disp, tmp_path):
        mock_disp.return_value = DispatchResult(True, 0, "{}", "")
        mock_g4.return_value = {"status": "PASS"}
        state = PipelineState.default(str(tmp_path))
        state.closure = ClosureState.IN_PROGRESS
        state.closure_step = len(CLOSURE_STEPS)  # past all steps
        result = run_closure_step(state, tmp_path)
        assert result is True
        assert state.closure == ClosureState.CHECKPOINT_PENDING
        assert state.pending_checkpoint.type == CheckpointType.BOOK_CLOSURE

    @patch("shenbi.pipeline.closure.dispatch_skill")
    @patch("shenbi.pipeline.closure.run_gate_g4")
    def test_dispatches_correct_skill_for_step_0(self, mock_g4, mock_disp, tmp_path):
        mock_disp.return_value = DispatchResult(True, 0, "{}", "")
        mock_g4.return_value = {"status": "PASS"}
        state = PipelineState.default(str(tmp_path))
        state.closure = ClosureState.IN_PROGRESS
        state.closure_step = 0
        run_closure_step(state, tmp_path)
        called_skill = mock_disp.call_args[0][0]
        assert called_skill == CLOSURE_STEPS[0].skill

    @patch("shenbi.pipeline.closure.dispatch_skill")
    @patch("shenbi.pipeline.closure.run_gate_g4")
    def test_full_run_to_checkpoint(self, mock_g4, mock_disp, tmp_path):
        """Run all 10 steps sequentially, verify checkpoint at end."""
        mock_disp.return_value = DispatchResult(True, 0, "{}", "")
        mock_g4.return_value = {"status": "PASS"}
        state = PipelineState.default(str(tmp_path))
        state.closure = ClosureState.IN_PROGRESS
        state.closure_step = 0

        for _ in range(len(CLOSURE_STEPS)):
            run_closure_step(state, tmp_path)

        assert state.closure_step == len(CLOSURE_STEPS)
        assert len(state.closure_skills_done) == len(CLOSURE_STEPS)

        # Next call should set the checkpoint
        result = run_closure_step(state, tmp_path)
        assert result is True
        assert state.closure == ClosureState.CHECKPOINT_PENDING
        assert state.pending_checkpoint.type == CheckpointType.BOOK_CLOSURE
