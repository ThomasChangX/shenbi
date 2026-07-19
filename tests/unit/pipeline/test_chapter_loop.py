"""Tests for the chapter loop orchestrator (Wave 3 Task 3).

The chapter loop runs 20 steps per chapter (spec section 6.1's 13-step loop
expanded with individual audit-circle skills). Steps 2 (chapter-planning)
and 7 (state-settling) write to staging/ and are gated by human-review
checkpoints. Step 4 (pipeline-context-assemble) materializes the
three-route context package before chapter-drafting consumes it.

dispatch/gate failures retry per spec section 11 up to max_revision_retries,
then escalate.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from shenbi.pipeline.chapter_loop import (
    _LAST_AUDIT_IDX,
    CHAPTER_STEPS,
    run_chapter_step,
)
from shenbi.pipeline.dispatch_helper import DispatchResult
from shenbi.pipeline.state import (
    CheckpointType,
    PipelineState,
)


# ---------------------------------------------------------------------------
# Step table structure (brief verbatim + structural invariants)
# ---------------------------------------------------------------------------
class TestChapterSteps:
    def test_foreshadowing_plant_after_planning(self):
        cp = next(i for i, s in enumerate(CHAPTER_STEPS) if "chapter-planning" in s.skill)
        fp = next(i for i, s in enumerate(CHAPTER_STEPS) if "foreshadowing-plant" in s.skill)
        assert cp < fp

    def test_state_settling_before_track(self):
        ss = next(i for i, s in enumerate(CHAPTER_STEPS) if "state-settling" in s.skill)
        ft = next(i for i, s in enumerate(CHAPTER_STEPS) if "foreshadowing-track" in s.skill)
        assert ss < ft

    def test_context_assembly_before_drafting(self):
        ca = next(i for i, s in enumerate(CHAPTER_STEPS) if "context-assemble" in s.skill)
        cd = next(i for i, s in enumerate(CHAPTER_STEPS) if "chapter-drafting" in s.skill)
        assert ca < cd

    def test_audit_skills_present(self):
        audit_skills = [s.skill for s in CHAPTER_STEPS if "review-" in s.skill]
        assert len(audit_skills) >= 7  # at least core circle

    def test_step_count(self):
        assert len(CHAPTER_STEPS) == 20

    def test_step_nums_are_sequential(self):
        assert [s.step_num for s in CHAPTER_STEPS] == list(range(1, 21))

    def test_chapter_planning_has_staging(self):
        cp = next(s for s in CHAPTER_STEPS if "chapter-planning" in s.skill)
        assert cp.uses_staging is True

    def test_chapter_planning_checkpoint(self):
        cp = next(s for s in CHAPTER_STEPS if "chapter-planning" in s.skill)
        assert cp.checkpoint == CheckpointType.CHAPTER_MEMO

    def test_state_settling_has_staging(self):
        ss = next(s for s in CHAPTER_STEPS if "state-settling" in s.skill)
        assert ss.uses_staging is True

    def test_state_settling_checkpoint(self):
        ss = next(s for s in CHAPTER_STEPS if "state-settling" in s.skill)
        assert ss.checkpoint == CheckpointType.STATE_SETTLE

    def test_context_assemble_calls_assembly(self):
        ca = next(s for s in CHAPTER_STEPS if "context-assemble" in s.skill)
        assert ca.calls_context_assembly is True

    def test_audit_steps_marked(self):
        audit_steps = [s for s in CHAPTER_STEPS if s.is_audit]
        assert len(audit_steps) == 7

    def test_review_resonance_present(self):
        rr = [s for s in CHAPTER_STEPS if "review-resonance" in s.skill]
        assert len(rr) == 1


# ---------------------------------------------------------------------------
# run_chapter_step: happy path + gate failures
# ---------------------------------------------------------------------------
class TestRunChapterStep:
    @patch("shenbi.pipeline.chapter_loop.dispatch_skill")
    @patch("shenbi.pipeline.chapter_loop.run_gate_g4")
    def test_runs_step_and_advances(self, mock_g4, mock_disp, tmp_path):
        mock_disp.return_value = DispatchResult(True, 0, "{}", "")
        mock_g4.return_value = {"status": "PASS"}
        state = PipelineState.default(str(tmp_path))
        state.chapter_loop.current_chapter = 1
        run_chapter_step(state, tmp_path)
        assert state.chapter_loop.step_index == 1

    @patch("shenbi.pipeline.chapter_loop.dispatch_skill")
    @patch("shenbi.pipeline.chapter_loop.run_gate_g4")
    def test_records_step_done(self, mock_g4, mock_disp, tmp_path):
        mock_disp.return_value = DispatchResult(True, 0, "{}", "")
        mock_g4.return_value = {"status": "PASS"}
        state = PipelineState.default(str(tmp_path))
        state.chapter_loop.current_chapter = 1
        run_chapter_step(state, tmp_path)
        cs = state.chapter_loop.chapter_states["1"]
        assert "shenbi-intent-management" in cs.steps_done

    @patch("shenbi.pipeline.chapter_loop.dispatch_skill")
    @patch("shenbi.pipeline.chapter_loop.run_gate_g4")
    def test_g4_pass_is_str_enum(self, mock_g4, mock_disp, tmp_path):
        from shenbi.status import GateStatus

        mock_disp.return_value = DispatchResult(True, 0, "{}", "")
        mock_g4.return_value = {"status": GateStatus.PASS}
        state = PipelineState.default(str(tmp_path))
        state.chapter_loop.current_chapter = 1
        run_chapter_step(state, tmp_path)
        assert state.chapter_loop.step_index == 1

    @patch("shenbi.pipeline.chapter_loop.dispatch_skill")
    @patch("shenbi.pipeline.chapter_loop.run_gate_g4")
    def test_g4_fail_does_not_advance(self, mock_g4, mock_disp, tmp_path):
        mock_disp.return_value = DispatchResult(True, 0, "{}", "")
        mock_g4.return_value = {"status": "FAIL"}
        state = PipelineState.default(str(tmp_path))
        state.chapter_loop.current_chapter = 1
        run_chapter_step(state, tmp_path)
        assert state.chapter_loop.step_index == 0

    @patch("shenbi.pipeline.chapter_loop.dispatch_skill")
    def test_dispatch_fail_does_not_advance(self, mock_disp, tmp_path):
        mock_disp.return_value = DispatchResult(False, 1, "", "error")
        state = PipelineState.default(str(tmp_path))
        state.chapter_loop.current_chapter = 1
        run_chapter_step(state, tmp_path)
        assert state.chapter_loop.step_index == 0

    @patch("shenbi.pipeline.chapter_loop.run_gate_g3")
    @patch("shenbi.pipeline.chapter_loop.requires_independent", return_value=True)
    @patch("shenbi.pipeline.chapter_loop.run_gate_g4")
    @patch("shenbi.pipeline.chapter_loop.dispatch_skill")
    def test_g3_checked_for_independent_skill(self, mock_disp, mock_g4, mock_ri, mock_g3, tmp_path):
        mock_disp.return_value = DispatchResult(True, 0, "{}", "")
        mock_g4.return_value = {"status": "PASS"}
        mock_g3.return_value = {"status": "PASS"}
        state = PipelineState.default(str(tmp_path))
        state.chapter_loop.current_chapter = 1
        state.chapter_loop.step_index = 16  # review-resonance (step 17)
        run_chapter_step(state, tmp_path)
        mock_g3.assert_called_once()
        assert state.chapter_loop.step_index == 17


# ---------------------------------------------------------------------------
# Staging integration: G4 validates staging copy, checkpoint raised
# ---------------------------------------------------------------------------
class TestStagingIntegration:
    @patch("shenbi.pipeline.chapter_loop.dispatch_skill")
    @patch("shenbi.pipeline.chapter_loop.run_gate_g4")
    def test_staging_g4_validates_staging_path(self, mock_g4, mock_disp, tmp_path):
        mock_disp.return_value = DispatchResult(True, 0, "{}", "")
        mock_g4.return_value = {"status": "PASS"}
        state = PipelineState.default(str(tmp_path))
        state.chapter_loop.current_chapter = 1
        state.chapter_loop.step_index = 1  # chapter-planning
        run_chapter_step(state, tmp_path)
        files = mock_g4.call_args[0][1]
        assert any("staging/" in f for f in files)

    @patch("shenbi.pipeline.chapter_loop.dispatch_skill")
    @patch("shenbi.pipeline.chapter_loop.run_gate_g4")
    def test_staging_prompt_includes_staging_dir(self, mock_g4, mock_disp, tmp_path):
        mock_disp.return_value = DispatchResult(True, 0, "{}", "")
        mock_g4.return_value = {"status": "PASS"}
        state = PipelineState.default(str(tmp_path))
        state.chapter_loop.current_chapter = 1
        state.chapter_loop.step_index = 1
        run_chapter_step(state, tmp_path)
        prompt = mock_disp.call_args[0][2]
        assert "staging/" in prompt

    @patch("shenbi.pipeline.chapter_loop.dispatch_skill")
    @patch("shenbi.pipeline.chapter_loop.run_gate_g4")
    def test_chapter_planning_sets_checkpoint(self, mock_g4, mock_disp, tmp_path):
        mock_disp.return_value = DispatchResult(True, 0, "{}", "")
        mock_g4.return_value = {"status": "PASS"}
        state = PipelineState.default(str(tmp_path))
        state.chapter_loop.current_chapter = 1
        state.chapter_loop.step_index = 1
        result = run_chapter_step(state, tmp_path)
        assert result is True
        assert state.pending_checkpoint.type == CheckpointType.CHAPTER_MEMO
        assert state.chapter_loop.step_index == 2


# ---------------------------------------------------------------------------
# Context assembly integration
# ---------------------------------------------------------------------------
class TestContextAssembly:
    @patch("shenbi.pipeline.context_assemble.write_context_file")
    @patch("shenbi.pipeline.context_assemble.assemble_context")
    def test_context_assembly_called(self, mock_assemble, mock_write, tmp_path):
        """Step 4 (pipeline-context-assemble) calls assemble_context + write."""
        state = PipelineState.default(str(tmp_path))
        state.chapter_loop.current_chapter = 1
        state.chapter_loop.step_index = 3  # pipeline-context-assemble
        run_chapter_step(state, tmp_path)
        mock_assemble.assert_called_once_with(tmp_path, "plans/chapter-1-plan.md")
        mock_write.assert_called_once()
        assert state.chapter_loop.step_index == 4

    @patch(
        "shenbi.pipeline.context_assemble.assemble_context",
        side_effect=FileNotFoundError("no plan"),
    )
    def test_context_assembly_failure_does_not_crash(self, mock_assemble, tmp_path):
        """Missing plan file is tolerated -- step still advances."""
        state = PipelineState.default(str(tmp_path))
        state.chapter_loop.current_chapter = 1
        state.chapter_loop.step_index = 3
        run_chapter_step(state, tmp_path)
        assert state.chapter_loop.step_index == 4


# ---------------------------------------------------------------------------
# Chapter completion
# ---------------------------------------------------------------------------
class TestChapterCompletion:
    @patch("shenbi.pipeline.chapter_loop.dispatch_skill")
    @patch("shenbi.pipeline.chapter_loop.run_gate_g4")
    def test_last_step_completes_chapter(self, mock_g4, mock_disp, tmp_path):
        mock_disp.return_value = DispatchResult(True, 0, "{}", "")
        mock_g4.return_value = {"status": "PASS"}
        state = PipelineState.default(str(tmp_path))
        state.chapter_loop.current_chapter = 1
        state.chapter_loop.step_index = 19  # last step (drift-guidance)
        run_chapter_step(state, tmp_path)
        assert state.chapter_loop.current_chapter == 2
        assert state.chapter_loop.step_index == 0

    @patch("shenbi.pipeline.chapter_loop.dispatch_skill")
    @patch("shenbi.pipeline.chapter_loop.run_gate_g4")
    def test_completion_sets_per_chapter_checkpoint_when_enabled(
        self, mock_g4, mock_disp, tmp_path
    ):
        mock_disp.return_value = DispatchResult(True, 0, "{}", "")
        mock_g4.return_value = {"status": "PASS"}
        state = PipelineState.default(str(tmp_path))
        state.chapter_loop.current_chapter = 1
        state.chapter_loop.step_index = 19
        state.chapter_loop.per_chapter_review_enabled = True
        result = run_chapter_step(state, tmp_path)
        assert result is True
        assert state.pending_checkpoint.type == CheckpointType.PER_CHAPTER

    @patch("shenbi.pipeline.chapter_loop.dispatch_skill")
    @patch("shenbi.pipeline.chapter_loop.run_gate_g4")
    def test_completion_no_checkpoint_when_disabled(self, mock_g4, mock_disp, tmp_path):
        mock_disp.return_value = DispatchResult(True, 0, "{}", "")
        mock_g4.return_value = {"status": "PASS"}
        state = PipelineState.default(str(tmp_path))
        state.chapter_loop.current_chapter = 1
        state.chapter_loop.step_index = 19
        state.chapter_loop.per_chapter_review_enabled = False
        result = run_chapter_step(state, tmp_path)
        assert result is False
        assert state.pending_checkpoint.type == CheckpointType.NONE


# ---------------------------------------------------------------------------
# Conditional foreshadowing-resolve
# ---------------------------------------------------------------------------
class TestConditionalResolve:
    @patch("shenbi.pipeline.chapter_loop.dispatch_skill")
    def test_triggered_hooks_dispatch_resolve(self, mock_disp, tmp_path):
        from shenbi.pipeline.chapter_loop import _check_conditional_resolve

        hooks_file = tmp_path / "truth" / "pending_hooks.md"
        hooks_file.parent.mkdir(parents=True)
        hooks_file.write_text(
            "---\nhooks:\n  - id: H01\n    state: TRIGGERED\n---\nbody",
            encoding="utf-8",
        )
        state = PipelineState.default(str(tmp_path))
        _check_conditional_resolve(state, tmp_path, 1)
        assert mock_disp.called
        assert "foreshadowing-resolve" in mock_disp.call_args[0][0]

    @patch("shenbi.pipeline.chapter_loop.dispatch_skill")
    def test_no_triggered_hooks_no_resolve(self, mock_disp, tmp_path):
        from shenbi.pipeline.chapter_loop import _check_conditional_resolve

        hooks_file = tmp_path / "truth" / "pending_hooks.md"
        hooks_file.parent.mkdir(parents=True)
        hooks_file.write_text(
            "---\nhooks:\n  - id: H01\n    state: PLANTED\n---\nbody",
            encoding="utf-8",
        )
        state = PipelineState.default(str(tmp_path))
        _check_conditional_resolve(state, tmp_path, 1)
        assert not mock_disp.called

    @patch("shenbi.pipeline.chapter_loop.dispatch_skill")
    def test_missing_hooks_file_no_crash(self, mock_disp, tmp_path):
        from shenbi.pipeline.chapter_loop import _check_conditional_resolve

        state = PipelineState.default(str(tmp_path))
        _check_conditional_resolve(state, tmp_path, 1)
        assert not mock_disp.called


# ---------------------------------------------------------------------------
# Retry + escalation (spec section 11)
# ---------------------------------------------------------------------------
class TestRetryEscalation:
    @patch("shenbi.pipeline.chapter_loop.dispatch_skill")
    @patch("shenbi.pipeline.revision_router.dispatch_skill")
    def test_dispatch_fail_retries_then_escalates(self, mock_esc_disp, mock_disp, tmp_path):
        mock_disp.return_value = DispatchResult(False, 1, "", "error")
        mock_esc_disp.return_value = DispatchResult(True, 0, "{}", "")
        state = PipelineState.default(str(tmp_path))
        state.chapter_loop.current_chapter = 1
        state.config.max_revision_retries = 3

        result1 = run_chapter_step(state, tmp_path)
        assert result1 is False
        assert state.chapter_loop.step_index == 0

        result2 = run_chapter_step(state, tmp_path)
        assert result2 is False
        assert state.chapter_loop.step_index == 0

        result3 = run_chapter_step(state, tmp_path)
        assert result3 is True
        assert state.pending_checkpoint.type == CheckpointType.ESCALATION

    @patch("shenbi.pipeline.chapter_loop.dispatch_skill")
    @patch("shenbi.pipeline.revision_router.dispatch_skill")
    @patch("shenbi.pipeline.chapter_loop.run_gate_g4")
    def test_g4_fail_retries_then_escalates(self, mock_g4, mock_esc_disp, mock_disp, tmp_path):
        mock_disp.return_value = DispatchResult(True, 0, "{}", "")
        mock_esc_disp.return_value = DispatchResult(True, 0, "{}", "")
        mock_g4.return_value = {"status": "FAIL"}
        state = PipelineState.default(str(tmp_path))
        state.chapter_loop.current_chapter = 1
        state.config.max_revision_retries = 2

        run_chapter_step(state, tmp_path)
        assert state.chapter_loop.step_index == 0

        result = run_chapter_step(state, tmp_path)
        assert result is True
        assert state.pending_checkpoint.type == CheckpointType.ESCALATION

    @patch("shenbi.pipeline.chapter_loop.dispatch_skill")
    @patch("shenbi.pipeline.chapter_loop.run_gate_g4")
    def test_retry_count_reset_on_success(self, mock_g4, mock_disp, tmp_path):
        mock_disp.return_value = DispatchResult(True, 0, "{}", "")
        mock_g4.return_value = {"status": "PASS"}
        state = PipelineState.default(str(tmp_path))
        state.chapter_loop.current_chapter = 1
        state.chapter_loop.retry_counts["ch1-shenbi-intent-management"] = 2
        run_chapter_step(state, tmp_path)
        assert "ch1-shenbi-intent-management" not in state.chapter_loop.retry_counts


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------
class TestEdgeCases:
    def test_all_steps_consumed_returns_true(self, tmp_path):
        state = PipelineState.default(str(tmp_path))
        state.chapter_loop.current_chapter = 1
        state.chapter_loop.step_index = len(CHAPTER_STEPS)
        result = run_chapter_step(state, tmp_path)
        assert result is True

    @patch("shenbi.pipeline.chapter_loop.dispatch_skill")
    @patch("shenbi.pipeline.chapter_loop.run_gate_g4")
    def test_pipeline_step_skips_dispatch(self, mock_g4, mock_disp, tmp_path):
        """pipeline-context-assemble is pipeline-internal -- no dispatch."""
        state = PipelineState.default(str(tmp_path))
        state.chapter_loop.current_chapter = 1
        state.chapter_loop.step_index = 3
        run_chapter_step(state, tmp_path)
        mock_disp.assert_not_called()
        mock_g4.assert_not_called()


# ---------------------------------------------------------------------------
# G3 failure path + audit circle + conditional resolve integration
# ---------------------------------------------------------------------------
class TestGateFailurePaths:
    @patch("shenbi.pipeline.chapter_loop.run_gate_g3")
    @patch("shenbi.pipeline.chapter_loop.requires_independent", return_value=True)
    @patch("shenbi.pipeline.chapter_loop.run_gate_g4")
    @patch("shenbi.pipeline.chapter_loop.dispatch_skill")
    def test_g3_fail_does_not_advance(self, mock_disp, mock_g4, mock_ri, mock_g3, tmp_path):
        """G3 failure triggers retry (step_index unchanged)."""
        mock_disp.return_value = DispatchResult(True, 0, "{}", "")
        mock_g4.return_value = {"status": "PASS"}
        mock_g3.return_value = {"status": "FAIL"}
        state = PipelineState.default(str(tmp_path))
        state.chapter_loop.current_chapter = 1
        state.chapter_loop.step_index = 16  # review-resonance
        run_chapter_step(state, tmp_path)
        assert state.chapter_loop.step_index == 16


class TestAuditCircleIntegration:
    @patch("shenbi.pipeline.chapter_loop.dispatch_skill")
    @patch("shenbi.pipeline.chapter_loop.run_gate_g4")
    def test_last_audit_step_logs_core_circle_complete(self, mock_g4, mock_disp, tmp_path):
        """Step 16 (last core-circle audit) triggers the genre-circle hook."""
        mock_disp.return_value = DispatchResult(True, 0, "{}", "")
        mock_g4.return_value = {"status": "PASS"}
        state = PipelineState.default(str(tmp_path))
        state.chapter_loop.current_chapter = 1
        state.chapter_loop.step_index = 15  # shenbi-review-pov (step 16, index 15)
        run_chapter_step(state, tmp_path)
        assert state.chapter_loop.step_index == 16


class TestConditionalResolveIntegration:
    @patch("shenbi.pipeline.chapter_loop.dispatch_skill")
    @patch("shenbi.pipeline.chapter_loop.run_gate_g4")
    def test_track_step_triggers_resolve_check(self, mock_g4, mock_disp, tmp_path):
        """foreshadowing-track step calls _check_conditional_resolve."""
        mock_disp.return_value = DispatchResult(True, 0, "{}", "")
        mock_g4.return_value = {"status": "PASS"}
        # No hooks file -> no resolve dispatch, but the check is exercised.
        state = PipelineState.default(str(tmp_path))
        state.chapter_loop.current_chapter = 1
        state.chapter_loop.step_index = 7  # foreshadowing-track (step 8, index 7)
        run_chapter_step(state, tmp_path)
        assert state.chapter_loop.step_index == 8

    @patch("shenbi.pipeline.chapter_loop.dispatch_skill")
    @patch("shenbi.pipeline.chapter_loop.run_gate_g4")
    def test_track_step_with_triggered_hooks_dispatches_resolve(self, mock_g4, mock_disp, tmp_path):
        """foreshadowing-track with TRIGGERED hooks dispatches resolve too."""
        mock_disp.return_value = DispatchResult(True, 0, "{}", "")
        mock_g4.return_value = {"status": "PASS"}
        hooks_file = tmp_path / "truth" / "pending_hooks.md"
        hooks_file.parent.mkdir(parents=True)
        hooks_file.write_text(
            "---\nhooks:\n  - id: H01\n    state: TRIGGERED\n---\nbody",
            encoding="utf-8",
        )
        state = PipelineState.default(str(tmp_path))
        state.chapter_loop.current_chapter = 1
        state.chapter_loop.step_index = 7
        run_chapter_step(state, tmp_path)
        # dispatch_skill called twice: once for track, once for resolve
        assert mock_disp.call_count == 2
        second_skill = mock_disp.call_args_list[1][0][0]
        assert "foreshadowing-resolve" in second_skill


class TestCountTriggeredHooks:
    def test_yaml_frontmatter(self):
        from shenbi.pipeline.chapter_loop import _count_triggered_hooks

        text = "---\nhooks:\n  - id: H01\n    state: TRIGGERED\n  - id: H02\n    state: PLANTED\n---\nbody"
        assert _count_triggered_hooks(text) == 1

    def test_no_frontmatter_text_scan(self):
        from shenbi.pipeline.chapter_loop import _count_triggered_hooks

        text = "some hooks: state: TRIGGERED and state: TRIGGERED"
        assert _count_triggered_hooks(text) == 2

    def test_malformed_yaml_falls_back(self):
        from shenbi.pipeline.chapter_loop import _count_triggered_hooks

        text = "---\nnot: valid: yaml: [\n---\nstate: TRIGGERED"
        assert _count_triggered_hooks(text) == 1

    def test_no_hooks(self):
        from shenbi.pipeline.chapter_loop import _count_triggered_hooks

        text = "---\nhooks: []\n---\nnothing"
        assert _count_triggered_hooks(text) == 0

    # --- D22 canary: HookState enum (case-insensitive + non-canonical) ---

    def test_lowercase_triggered_counted(self):
        # D22 canary: lowercase 'triggered' must be recognized as TRIGGERED.
        from shenbi.pipeline.chapter_loop import _count_triggered_hooks

        text = "---\nhooks:\n  - id: H01\n    state: triggered\n---\nbody"
        assert _count_triggered_hooks(text) == 1

    def test_noncanonical_trigger_spelling_counted(self):
        # SKILL.md:87 uses bare 'TRIGGER' — must fold to TRIGGERED.
        from shenbi.pipeline.chapter_loop import _count_triggered_hooks

        text = "---\nhooks:\n  - id: H01\n    state: TRIGGER\n---\nbody"
        assert _count_triggered_hooks(text) == 1

    def test_expired_not_counted_as_triggered(self):
        # D22 canary: state: EXPIRED loads and is NOT counted as TRIGGERED.
        from shenbi.pipeline.chapter_loop import _count_triggered_hooks

        text = (
            "---\nhooks:\n"
            "  - id: H01\n    state: EXPIRED\n"
            "  - id: H02\n    state: triggered\n"
            "---\nbody"
        )
        assert _count_triggered_hooks(text) == 1

    def test_all_six_states_only_triggered_counted(self):
        from shenbi.pipeline.chapter_loop import _count_triggered_hooks

        states = ["PLANTED", "RELEVANT", "TRIGGERED", "RESOLVED", "ARCHIVED", "EXPIRED"]
        lines = "\n".join(f"  - id: H{i}\n    state: {s}" for i, s in enumerate(states))
        text = f"---\nhooks:\n{lines}\n---\nbody"
        assert _count_triggered_hooks(text) == 1


# ---------------------------------------------------------------------------
# Revision routing integration (W3T5, spec §6.3)
# ---------------------------------------------------------------------------
class TestRevisionRoutingIntegration:
    """After review-resonance (step 17), the router determines whether step 18
    (chapter-revision) runs or is skipped.
    """

    @patch("shenbi.pipeline.chapter_loop.run_gate_g3")
    @patch("shenbi.pipeline.chapter_loop.requires_independent", return_value=True)
    @patch("shenbi.pipeline.chapter_loop.run_gate_g4")
    @patch("shenbi.pipeline.chapter_loop.dispatch_skill")
    def test_clean_audits_skip_revision(self, mock_disp, mock_g4, mock_ri, mock_g3, tmp_path):
        """No blocking issues -> step 18 (chapter-revision) is skipped."""
        mock_disp.return_value = DispatchResult(True, 0, "{}", "")
        mock_g4.return_value = {"status": "PASS"}
        mock_g3.return_value = {"status": "PASS"}
        state = PipelineState.default(str(tmp_path))
        state.chapter_loop.current_chapter = 1

        # Run step 17 (review-resonance) with no audit files -> NO_REVISION.
        state.chapter_loop.step_index = 16
        run_chapter_step(state, tmp_path)
        assert state.chapter_loop.step_index == 17
        cs = state.chapter_loop.chapter_states["1"]
        assert cs.audit_results["revision_route"] == "no-revision"

        # Step 18 (chapter-revision) should be skipped.
        run_chapter_step(state, tmp_path)
        assert state.chapter_loop.step_index == 18
        # dispatch_skill called only once (for step 17), not for step 18.
        step18_skill = "shenbi-chapter-revision"
        called_skills = [c[0][0] for c in mock_disp.call_args_list]
        assert step18_skill not in called_skills

    @patch("shenbi.pipeline.chapter_loop.run_gate_g3")
    @patch("shenbi.pipeline.chapter_loop.requires_independent", return_value=True)
    @patch("shenbi.pipeline.chapter_loop.run_gate_g4")
    @patch("shenbi.pipeline.chapter_loop.dispatch_skill")
    def test_blocking_audits_route_revision(self, mock_disp, mock_g4, mock_ri, mock_g3, tmp_path):
        """Blocking audit issues -> step 18 (chapter-revision) runs normally."""
        mock_disp.return_value = DispatchResult(True, 0, "{}", "")
        mock_g4.return_value = {"status": "PASS"}
        mock_g3.return_value = {"status": "PASS"}
        state = PipelineState.default(str(tmp_path))
        state.chapter_loop.current_chapter = 1

        # Create a blocking audit report.
        audit_dir = tmp_path / "audits"
        audit_dir.mkdir()
        (audit_dir / "chapter-1-anti-ai.md").write_text("**BLOCKING**")

        # Run step 17 (review-resonance) -> blocking -> REGENERATE.
        state.chapter_loop.step_index = 16
        run_chapter_step(state, tmp_path)
        cs = state.chapter_loop.chapter_states["1"]
        assert cs.audit_results["revision_route"] == "regenerate"

        # Step 18 (chapter-revision) should NOT be skipped.
        run_chapter_step(state, tmp_path)
        assert state.chapter_loop.step_index == 18
        step18_skill = "shenbi-chapter-revision"
        called_skills = [c[0][0] for c in mock_disp.call_args_list]
        assert step18_skill in called_skills

    @patch("shenbi.pipeline.chapter_loop.run_gate_g3")
    @patch("shenbi.pipeline.chapter_loop.requires_independent", return_value=True)
    @patch("shenbi.pipeline.chapter_loop.run_gate_g4")
    @patch("shenbi.pipeline.chapter_loop.dispatch_skill")
    def test_revision_route_stored_in_chapter_state(
        self, mock_disp, mock_g4, mock_ri, mock_g3, tmp_path
    ):
        """The revision route is persisted on the chapter's audit_results."""
        mock_disp.return_value = DispatchResult(True, 0, "{}", "")
        mock_g4.return_value = {"status": "PASS"}
        mock_g3.return_value = {"status": "PASS"}
        state = PipelineState.default(str(tmp_path))
        state.chapter_loop.current_chapter = 1
        state.chapter_loop.step_index = 16

        # Critical (not blocking) audit -> SPOT_FIX.
        audit_dir = tmp_path / "audits"
        audit_dir.mkdir()
        (audit_dir / "chapter-1-pacing.md").write_text("**CRITICAL**")
        run_chapter_step(state, tmp_path)
        cs = state.chapter_loop.chapter_states["1"]
        assert cs.audit_results["revision_route"] == "spot-fix"

    @patch("shenbi.pipeline.chapter_loop.check_resonance", return_value=True)
    @patch("shenbi.pipeline.chapter_loop.run_gate_g3")
    @patch("shenbi.pipeline.chapter_loop.requires_independent", return_value=True)
    @patch("shenbi.pipeline.chapter_loop.run_gate_g4")
    @patch("shenbi.pipeline.chapter_loop.dispatch_skill")
    def test_check_resonance_wired_after_review(
        self, mock_disp, mock_g4, mock_ri, mock_g3, mock_cr, tmp_path
    ):
        """check_resonance is called during revision routing (no longer dead code)."""
        mock_disp.return_value = DispatchResult(True, 0, "{}", "")
        mock_g4.return_value = {"status": "PASS"}
        mock_g3.return_value = {"status": "PASS"}
        state = PipelineState.default(str(tmp_path))
        state.chapter_loop.current_chapter = 1
        state.chapter_loop.step_index = 16  # review-resonance
        run_chapter_step(state, tmp_path)
        mock_cr.assert_called_once()
        # Called with the chapter's resonance score and the config floor.
        args = mock_cr.call_args[0]
        assert args[1] == state.config.resonance_global_floor

    @patch("shenbi.pipeline.chapter_loop.run_gate_g3")
    @patch("shenbi.pipeline.chapter_loop.requires_independent", return_value=True)
    @patch("shenbi.pipeline.chapter_loop.run_gate_g4")
    @patch("shenbi.pipeline.chapter_loop.dispatch_skill")
    def test_clean_audits_dont_skip_snapshot_or_drift(
        self, mock_disp, mock_g4, mock_ri, mock_g3, tmp_path
    ):
        """Steps 19 (snapshot) & 20 (drift) run even when audits are clean.

        Regression: _is_revision_skipped must only affect step 18
        (chapter-revision), not the snapshot/drift steps that follow.

        With adaptive triggering (Task 8), snapshot is file-based (no dispatch)
        and drift only dispatches when resonance data indicates need. The steps
        still advance, they just don't always dispatch.
        """
        mock_disp.return_value = DispatchResult(True, 0, "{}", "")
        mock_g4.return_value = {"status": "PASS"}
        mock_g3.return_value = {"status": "PASS"}
        state = PipelineState.default(str(tmp_path))
        state.chapter_loop.current_chapter = 1
        state.config.max_revision_retries = 3

        # Step 17 (review-resonance) with no audit files -> NO_REVISION.
        state.chapter_loop.step_index = 16
        run_chapter_step(state, tmp_path)
        cs = state.chapter_loop.chapter_states["1"]
        assert cs.audit_results["revision_route"] == "no-revision"

        # Step 18 (chapter-revision) skipped.
        run_chapter_step(state, tmp_path)
        assert state.chapter_loop.step_index == 18

        # Step 19 (snapshot-manage): file-based snapshot runs inline.
        # Advancing through it should not dispatch.
        run_chapter_step(state, tmp_path)
        assert state.chapter_loop.step_index == 19
        # Verify file-based snapshot was created (differential format).
        snap_dir = tmp_path / "snapshots"
        assert snap_dir.exists()
        chapter_snap_dir = snap_dir / "chapter-001"
        assert chapter_snap_dir.exists()
        manifest_file = chapter_snap_dir / "snapshot-manifest.json"
        assert manifest_file.exists()

        # Step 20 (drift-guidance): skipped when no resonance data.
        # Still advances and completes chapter.
        run_chapter_step(state, tmp_path)
        assert state.chapter_loop.current_chapter == 2
        assert state.chapter_loop.step_index == 0

        called_skills = [c[0][0] for c in mock_disp.call_args_list]
        assert "shenbi-chapter-revision" not in called_skills
        # Snapshot is now file-based (no dispatch); drift skipped without data.


# ---------------------------------------------------------------------------
# Audit layer wiring (A8, Task 2.2)
# ---------------------------------------------------------------------------
class TestAuditLayerWiring:
    """Tests that run_audit_layer is called after core circle and handles BLOCKING."""

    def test_run_audit_layer_called_after_last_core_audit(self, tmp_path, monkeypatch):
        """After step 16 (last is_audit step), run_audit_layer is called."""
        from shenbi.pipeline.state import PipelinePhase, PipelineState

        state = PipelineState.default(str(tmp_path))
        state.phase = PipelinePhase.CHAPTER_LOOP
        state.chapter_loop.current_chapter = 1
        state.chapter_loop.step_index = _LAST_AUDIT_IDX  # position at step 16

        # Mock audit_layer to avoid actual dispatch
        called = []

        def fake_run_audit(project_dir, chapter, gc):
            called.append((chapter, gc))
            from shenbi.pipeline.audit_layer import AuditResult

            return AuditResult(blocking_found=False)

        monkeypatch.setattr("shenbi.pipeline.chapter_loop.run_audit_layer", fake_run_audit)
        # Mock dispatch_skill for step 16
        monkeypatch.setattr(
            "shenbi.pipeline.chapter_loop.dispatch_skill",
            lambda *a, **kw: type("R", (), {"success": True})(),
        )
        # Mock G4
        monkeypatch.setattr(
            "shenbi.pipeline.chapter_loop.run_gate_g4",
            lambda *a, **kw: {"status": "PASS"},
        )

        run_chapter_step(state, tmp_path)
        assert len(called) == 1, f"run_audit_layer should be called once, was {len(called)}"

    def test_audit_blocking_triggers_revision_dispatch(self, tmp_path, monkeypatch):
        """BLOCKING finding dispatches chapter-revision."""
        from shenbi.pipeline.state import PipelinePhase, PipelineState

        state = PipelineState.default(str(tmp_path))
        state.phase = PipelinePhase.CHAPTER_LOOP
        state.chapter_loop.current_chapter = 1
        state.chapter_loop.step_index = _LAST_AUDIT_IDX

        # Mock audit_layer returning BLOCKING
        def fake_run_audit(project_dir, chapter, gc):
            from shenbi.pipeline.audit_layer import AuditResult

            r = AuditResult(blocking_found=True)
            r.issues = [{"skill": "test", "severity": "BLOCKING"}]
            return r

        monkeypatch.setattr("shenbi.pipeline.chapter_loop.run_audit_layer", fake_run_audit)

        revisions = []

        def fake_dispatch(skill, project_dir, prompt, **kwargs):
            if "chapter-revision" in skill:
                revisions.append(prompt)
            return type("R", (), {"success": True})()

        monkeypatch.setattr("shenbi.pipeline.chapter_loop.dispatch_skill", fake_dispatch)
        monkeypatch.setattr(
            "shenbi.pipeline.chapter_loop.run_gate_g4",
            lambda *a, **kw: {"status": "PASS"},
        )

        run_chapter_step(state, tmp_path)
        assert len(revisions) >= 1, f"Expected revision dispatch, got {len(revisions)}"

    def test_audit_max_retries_triggers_escalation(self, tmp_path, monkeypatch):
        """After max_audit_retries BLOCKING rounds, ESCALATION checkpoint is set."""
        from shenbi.pipeline.state import PipelinePhase, PipelineState

        state = PipelineState.default(str(tmp_path))
        state.phase = PipelinePhase.CHAPTER_LOOP
        state.chapter_loop.current_chapter = 1
        state.chapter_loop.step_index = _LAST_AUDIT_IDX
        state.config.max_audit_retries = 3

        def fake_run_audit(project_dir, chapter, gc):
            from shenbi.pipeline.audit_layer import AuditResult

            r = AuditResult(blocking_found=True)
            r.issues = [{"skill": "test", "severity": "BLOCKING"}]
            return r

        monkeypatch.setattr("shenbi.pipeline.chapter_loop.run_audit_layer", fake_run_audit)
        monkeypatch.setattr(
            "shenbi.pipeline.chapter_loop.dispatch_skill",
            lambda *a, **kw: type("R", (), {"success": True})(),
        )
        monkeypatch.setattr(
            "shenbi.pipeline.chapter_loop.run_gate_g4",
            lambda *a, **kw: {"status": "PASS"},
        )

        run_chapter_step(state, tmp_path)
        cs = state.chapter_loop.chapter_states.get("1")
        assert cs is not None
        assert cs.audit_retry_count > 0, (
            f"audit_retry_count should be > 0, got {cs.audit_retry_count}"
        )
        assert state.pending_checkpoint.type == CheckpointType.ESCALATION, (
            f"Expected ESCALATION checkpoint, got {state.pending_checkpoint.type}"
        )


# ---------------------------------------------------------------------------
# A7: State-settling G4 validation — _resolve_g4_files
# ---------------------------------------------------------------------------
class TestResolveG4Files:
    """Tests _resolve_g4_files for multi-file steps like state-settling."""

    def test_state_settling_returns_staging_truth_files(self, tmp_path):
        """State-settling step globs staging/truth/*.md."""
        from shenbi.pipeline.chapter_loop import (
            CHAPTER_STEPS,
            _resolve_g4_files,
        )

        # Find state-settling step (step 7, index 6)
        ss_step = next(s for s in CHAPTER_STEPS if "state-settling" in s.skill)

        # Create staging/truth/ with some .md files
        staging_truth = tmp_path / "staging" / "truth"
        staging_truth.mkdir(parents=True)
        (staging_truth / "current_state.md").write_text("# state")
        (staging_truth / "character_matrix.md").write_text("# chars")
        (staging_truth / "not_markdown.txt").write_text("nope")

        files = _resolve_g4_files(tmp_path, ss_step, chapter=5)
        assert len(files) >= 2
        assert any("current_state.md" in f for f in files)
        assert any("character_matrix.md" in f for f in files)
        # .txt file should NOT be in the list
        assert not any("not_markdown.txt" in f for f in files)

    def test_state_settling_empty_staging_returns_empty(self, tmp_path):
        """No staging/truth/ dir → returns empty list, no crash."""
        from shenbi.pipeline.chapter_loop import (
            CHAPTER_STEPS,
            _resolve_g4_files,
        )

        ss_step = next(s for s in CHAPTER_STEPS if "state-settling" in s.skill)
        files = _resolve_g4_files(tmp_path, ss_step, chapter=5)
        assert files == []

    def test_non_state_settling_returns_single_file(self, tmp_path):
        """Non-state-settling steps return single path unchanged."""
        from shenbi.pipeline.chapter_loop import (
            CHAPTER_STEPS,
            _resolve_g4_files,
        )

        drafting_step = CHAPTER_STEPS[5]  # step 6: chapter-drafting
        files = _resolve_g4_files(tmp_path, drafting_step, chapter=3)
        assert len(files) == 1
        assert "chapter-3.md" in files[0]


# ---------------------------------------------------------------------------
# A5a: State-settling failure wiring — handle_state_settle_failure
# ---------------------------------------------------------------------------
class TestStateSettleFailureWiring:
    """Tests that state-settling failure calls handle_state_settle_failure."""

    def test_state_settle_failure_triggers_escalation(self, tmp_path, monkeypatch):
        """State-settling dispatch failure → ESCALATION checkpoint."""
        from shenbi.pipeline.chapter_loop import run_chapter_step
        from shenbi.pipeline.state import CheckpointType, PipelinePhase, PipelineState

        state = PipelineState.default(str(tmp_path))
        state.phase = PipelinePhase.CHAPTER_LOOP
        state.chapter_loop.current_chapter = 3
        state.chapter_loop.step_index = 6  # state-settling is index 6

        # Mock dispatch to fail for state-settling
        monkeypatch.setattr(
            "shenbi.pipeline.chapter_loop.dispatch_skill",
            lambda *a, **kw: type("R", (), {"success": False})(),
        )
        monkeypatch.setattr(
            "shenbi.pipeline.chapter_loop.run_gate_g4",
            lambda *a, **kw: {"status": "PASS"},
        )

        result = run_chapter_step(state, tmp_path)
        # Should return True (checkpoint raised)
        assert result is True
        # Check chapter status is settling_failed
        cs = state.chapter_loop.chapter_states.get("3")
        assert cs is not None
        assert cs.status == "settling_failed"
        assert state.pending_checkpoint.type == CheckpointType.ESCALATION


# ---------------------------------------------------------------------------
# A5b: Scoring failure wiring — handle_scoring_failure for review-resonance
# ---------------------------------------------------------------------------
class TestScoringFailureWiring:
    """Tests review-resonance exit code handling."""

    def test_exit_code_2_triggers_redispatch(self, tmp_path, monkeypatch):
        """review-resonance returncode=2 → handle_scoring_failure returns True → retry."""
        from shenbi.pipeline.chapter_loop import run_chapter_step
        from shenbi.pipeline.state import PipelinePhase, PipelineState

        state = PipelineState.default(str(tmp_path))
        state.phase = PipelinePhase.CHAPTER_LOOP
        state.chapter_loop.current_chapter = 1
        state.chapter_loop.step_index = 16  # review-resonance is index 16

        called = []

        def fake_scoring_failure(s, exit_code):
            called.append(exit_code)
            return True  # should retry

        monkeypatch.setattr(
            "shenbi.pipeline.error_handler.handle_scoring_failure", fake_scoring_failure
        )
        monkeypatch.setattr(
            "shenbi.pipeline.chapter_loop.dispatch_skill",
            lambda *a, **kw: type("R", (), {"success": False, "returncode": 2})(),
        )
        monkeypatch.setattr(
            "shenbi.pipeline.chapter_loop.run_gate_g4",
            lambda *a, **kw: {"status": "PASS"},
        )

        result = run_chapter_step(state, tmp_path)
        assert len(called) == 1
        assert called[0] == 2
        # Should return False (retry, step_index unchanged)
        assert result is False
        assert state.chapter_loop.step_index == 16  # not advanced

    def test_exit_code_3_also_retries(self, tmp_path, monkeypatch):
        """review-resonance returncode=3 → handle_scoring_failure returns True → retry."""
        from shenbi.pipeline.chapter_loop import run_chapter_step
        from shenbi.pipeline.state import PipelinePhase, PipelineState

        state = PipelineState.default(str(tmp_path))
        state.phase = PipelinePhase.CHAPTER_LOOP
        state.chapter_loop.current_chapter = 1
        state.chapter_loop.step_index = 16

        def fake_scoring_failure(s, exit_code):
            return True

        monkeypatch.setattr(
            "shenbi.pipeline.error_handler.handle_scoring_failure", fake_scoring_failure
        )
        monkeypatch.setattr(
            "shenbi.pipeline.chapter_loop.dispatch_skill",
            lambda *a, **kw: type("R", (), {"success": False, "returncode": 3})(),
        )
        monkeypatch.setattr(
            "shenbi.pipeline.chapter_loop.run_gate_g4",
            lambda *a, **kw: {"status": "PASS"},
        )

        result = run_chapter_step(state, tmp_path)
        assert result is False
        assert state.chapter_loop.step_index == 16  # not advanced


# ---------------------------------------------------------------------------
# A4: Escalation-review dispatch wiring
# ---------------------------------------------------------------------------
class TestEscalationWiring:
    """Tests that escalation-review is dispatched before ESCALATION checkpoint."""

    def test_dispatch_escalation_called_before_checkpoint(self, tmp_path, monkeypatch):
        """When retries exhausted, dispatch_escalation is called before set_checkpoint."""
        from shenbi.pipeline.chapter_loop import run_chapter_step
        from shenbi.pipeline.state import CheckpointType, PipelinePhase, PipelineState

        state = PipelineState.default(str(tmp_path))
        state.phase = PipelinePhase.CHAPTER_LOOP
        state.chapter_loop.current_chapter = 1
        # Step 6 (index 5): shenbi-chapter-drafting (non-audit, non-scoring)
        state.chapter_loop.step_index = 5
        state.chapter_loop.retry_counts = {"ch1-shenbi-chapter-drafting": 3}
        state.config.max_revision_retries = 3

        call_order = []

        def fake_dispatch_skill(skill, project_dir, prompt, **kwargs):
            call_order.append(("dispatch", skill))
            return type("R", (), {"success": False})()

        def fake_dispatch_escalation(project_dir, chapter, context=""):
            call_order.append(("escalation", chapter))
            return True

        monkeypatch.setattr("shenbi.pipeline.chapter_loop.dispatch_skill", fake_dispatch_skill)
        monkeypatch.setattr(
            "shenbi.pipeline.revision_router.dispatch_escalation",
            fake_dispatch_escalation,
        )
        monkeypatch.setattr(
            "shenbi.pipeline.chapter_loop.run_gate_g4",
            lambda *a, **kw: {"status": "PASS"},
        )

        run_chapter_step(state, tmp_path)
        assert ("escalation", 1) in call_order
        assert state.pending_checkpoint.type == CheckpointType.ESCALATION


# ---------------------------------------------------------------------------
# Resonance Score Parser (A2)
# ---------------------------------------------------------------------------
class TestResonanceScoreParser:
    """Tests _parse_resonance_score from audit reports."""

    def test_parses_yaml_frontmatter(self, tmp_path):
        from shenbi.pipeline.chapter_loop import _parse_resonance_score

        report = tmp_path / "resonance.md"
        report.write_text("---\nresonance_score: 87\n---\n# Report\n...")
        assert _parse_resonance_score(report) == 87

    def test_parses_bold_label(self, tmp_path):
        from shenbi.pipeline.chapter_loop import _parse_resonance_score

        report = tmp_path / "resonance.md"
        report.write_text("# Review\n\n**Resonance Score**: 92\n\nDetails...")
        assert _parse_resonance_score(report) == 92

    def test_parses_plain_label(self, tmp_path):
        from shenbi.pipeline.chapter_loop import _parse_resonance_score

        report = tmp_path / "resonance.md"
        report.write_text("Score: 75")
        assert _parse_resonance_score(report) == 75

    def test_missing_file_returns_none(self, tmp_path):
        from shenbi.pipeline.chapter_loop import _parse_resonance_score

        assert _parse_resonance_score(tmp_path / "nonexistent.md") is None

    def test_no_score_found_returns_none(self, tmp_path):
        from shenbi.pipeline.chapter_loop import _parse_resonance_score

        report = tmp_path / "resonance.md"
        report.write_text("# No score here\n\nJust text.")
        assert _parse_resonance_score(report) is None


# ---------------------------------------------------------------------------
# Volume Map Alignment Check (Task 3)
# ---------------------------------------------------------------------------
class TestVolumeMapAlignment:
    """Tests _check_volume_map_alignment for blueprint deviation warnings."""

    @pytest.fixture
    def project_with_volume_map_and_chapter(self, tmp_path: Path) -> Path:
        outline_dir = tmp_path / "outline"
        outline_dir.mkdir()
        (outline_dir / "volume_map.md").write_text("""# Volume Map
## Volume 1: Awakening (Ch 1-15)
### Chapter Nodes
| Ch | Role | Content |
|----|------|---------|
| 1 | opening | Lin Feng awakens, cultivates, meets elder |
""")
        chapters_dir = tmp_path / "chapters"
        chapters_dir.mkdir()
        return tmp_path

    def test_alignment_check_passes_when_key_terms_present(
        self, project_with_volume_map_and_chapter: Path
    ):
        from shenbi.pipeline.chapter_loop import _check_volume_map_alignment

        chapter_text = "Lin Feng slowly awoke in the dark cave. He began to cultivate, sensing the elder's presence."
        (project_with_volume_map_and_chapter / "chapters" / "chapter-1.md").write_text(chapter_text)

        with patch("shenbi.pipeline.chapter_loop.log") as mock_log:
            _check_volume_map_alignment(project_with_volume_map_and_chapter, chapter=1)
            # Should not warn when terms match
            warn_calls = [
                c for c in mock_log.warning.call_args_list if "volume_map_alignment" in str(c)
            ]
            assert len(warn_calls) == 0

    def test_alignment_check_warns_when_key_terms_missing(
        self, project_with_volume_map_and_chapter: Path
    ):
        from shenbi.pipeline.chapter_loop import _check_volume_map_alignment

        chapter_text = (
            "The sun rose over the mountains. Birds sang in the trees. A gentle breeze blew."
        )
        (project_with_volume_map_and_chapter / "chapters" / "chapter-1.md").write_text(chapter_text)

        with patch("shenbi.pipeline.chapter_loop.log") as mock_log:
            _check_volume_map_alignment(project_with_volume_map_and_chapter, chapter=1)
            mock_log.warning.assert_any_call(
                "volume_map_alignment",
                chapter=1,
                match_rate="0.0%",
                found_terms=[],
                missing_terms=["Lin", "Feng", "awakens", "cultivates", "meets", "elder"],
                expected="Lin Feng awakens, cultivates, meets elder",
            )

    def test_alignment_check_skips_when_no_volume_map(
        self, project_with_volume_map_and_chapter: Path
    ):
        from shenbi.pipeline.chapter_loop import _check_volume_map_alignment

        (project_with_volume_map_and_chapter / "outline" / "volume_map.md").unlink()
        chapter_text = "Anything."
        (project_with_volume_map_and_chapter / "chapters" / "chapter-1.md").write_text(chapter_text)

        with patch("shenbi.pipeline.chapter_loop.log") as mock_log:
            _check_volume_map_alignment(project_with_volume_map_and_chapter, chapter=1)
            warn_calls = [
                c for c in mock_log.warning.call_args_list if "volume_map_alignment" in str(c)
            ]
            assert len(warn_calls) == 0
