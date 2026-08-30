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
    _FIRST_AUDIT_IDX,
    CHAPTER_STEPS,
    run_chapter_step,
)
from shenbi.pipeline.crash_recovery import reset_emergency_state
from shenbi.pipeline.dispatch_helper import DispatchResult
from shenbi.pipeline.state import (
    CheckpointType,
    PipelineState,
)


@pytest.fixture(autouse=True)
def _reset_crash_state():
    """Prevent cross-test contamination of module-level emergency globals under xdist."""
    reset_emergency_state()


# ---------------------------------------------------------------------------
# Step table structure (brief verbatim + structural invariants)
# ---------------------------------------------------------------------------
class TestChapterSteps:
    def test_foreshadowing_lifecycle_after_planning(self):
        cp = next(i for i, s in enumerate(CHAPTER_STEPS) if "chapter-planning" in s.skill)
        fl = next(i for i, s in enumerate(CHAPTER_STEPS) if "foreshadowing-lifecycle" in s.skill)
        assert cp < fl

    def test_state_settling_after_lifecycle(self):
        ss = next(i for i, s in enumerate(CHAPTER_STEPS) if "state-settling" in s.skill)
        fl = next(i for i, s in enumerate(CHAPTER_STEPS) if "foreshadowing-lifecycle" in s.skill)
        assert fl < ss

    def test_context_assembly_before_drafting(self):
        ca = next(i for i, s in enumerate(CHAPTER_STEPS) if "context-prepare" in s.skill)
        cd = next(i for i, s in enumerate(CHAPTER_STEPS) if "chapter-drafting" in s.skill)
        assert ca < cd

    def test_audit_skills_present(self):
        audit_skills = [s.skill for s in CHAPTER_STEPS if "review-" in s.skill]
        assert len(audit_skills) >= 6  # 6 domain-grouped audits (MERGE-2)

    def test_step_count(self):
        assert len(CHAPTER_STEPS) == 15

    def test_step_nums_are_sequential(self):
        assert [s.step_num for s in CHAPTER_STEPS] == list(range(1, 16))

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
        # State-settling checkpoint is raised at runtime after parallel
        # post-draft dispatch (not stored in the step definition itself).
        assert ss.checkpoint is None

    def test_context_assemble_calls_assembly(self):
        ca = next(s for s in CHAPTER_STEPS if "context-prepare" in s.skill)
        assert ca.calls_context_assembly is True

    def test_audit_steps_marked(self):
        audit_steps = [s for s in CHAPTER_STEPS if s.is_audit]
        assert len(audit_steps) == 6

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
        assert "pipeline-volume-align" in cs.steps_done

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
        """Step 2 (chapter-planning, index 1) is dispatched; G4 fail blocks advance."""
        mock_disp.return_value = DispatchResult(True, 0, "{}", "")
        mock_g4.return_value = {"status": "FAIL"}
        state = PipelineState.default(str(tmp_path))
        state.chapter_loop.current_chapter = 1
        state.chapter_loop.step_index = 1  # chapter-planning (step 2)
        run_chapter_step(state, tmp_path)
        assert state.chapter_loop.step_index == 1

    @patch("shenbi.pipeline.chapter_loop.dispatch_skill")
    def test_dispatch_fail_does_not_advance(self, mock_disp, tmp_path):
        """Step 2 (chapter-planning, index 1) is dispatched; dispatch fail blocks advance."""
        mock_disp.return_value = DispatchResult(False, 1, "", "error")
        state = PipelineState.default(str(tmp_path))
        state.chapter_loop.current_chapter = 1
        state.chapter_loop.step_index = 1  # chapter-planning (step 2)
        run_chapter_step(state, tmp_path)
        assert state.chapter_loop.step_index == 1

    @patch("shenbi.pipeline.chapter_loop.run_gate_g3")
    @patch("shenbi.pipeline.chapter_loop.requires_independent", return_value=True)
    @patch("shenbi.pipeline.chapter_loop.run_gate_g4")
    @patch("shenbi.pipeline.chapter_loop.dispatch_skill")
    def test_g3_checked_for_independent_skill(self, mock_disp, mock_g4, mock_ri, mock_g3, tmp_path):
        """G3 independence check runs for skills where requires_independent returns True.
        Uses chapter-drafting (step 4, index 3) which dispatches and hits the G3 path.
        """
        mock_disp.return_value = DispatchResult(True, 0, "{}", "")
        mock_g4.return_value = {"status": "PASS"}
        mock_g3.return_value = {"status": "PASS"}
        state = PipelineState.default(str(tmp_path))
        state.chapter_loop.current_chapter = 1
        state.chapter_loop.step_index = 3  # chapter-drafting (step 4)
        run_chapter_step(state, tmp_path)
        mock_g3.assert_called_once()
        assert state.chapter_loop.step_index == 4


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
        """Step 2 (chapter-planning) calls context assembly (calls_context_assembly=True)."""
        from unittest.mock import patch as _patch

        with (
            _patch(
                "shenbi.pipeline.chapter_loop.dispatch_skill",
                return_value=DispatchResult(True, 0, "{}", ""),
            ),
            _patch("shenbi.pipeline.chapter_loop.run_gate_g4", return_value={"status": "PASS"}),
        ):
            state = PipelineState.default(str(tmp_path))
            state.chapter_loop.current_chapter = 1
            state.chapter_loop.step_index = 1  # chapter-planning (step 2)
            run_chapter_step(state, tmp_path)
            mock_assemble.assert_called_once_with(tmp_path, "plans/chapter-1-plan.md")
            mock_write.assert_called_once()
            assert state.chapter_loop.step_index == 2

    @patch(
        "shenbi.pipeline.context_assemble.assemble_context",
        side_effect=FileNotFoundError("no plan"),
    )
    def test_context_assembly_failure_does_not_crash(self, mock_assemble, tmp_path):
        """Missing plan file is tolerated -- step still advances.
        Step 2 (chapter-planning) dispatches, so we also mock dispatch/G4.
        """
        from unittest.mock import patch as _patch

        with (
            _patch(
                "shenbi.pipeline.chapter_loop.dispatch_skill",
                return_value=DispatchResult(True, 0, "{}", ""),
            ),
            _patch("shenbi.pipeline.chapter_loop.run_gate_g4", return_value={"status": "PASS"}),
        ):
            state = PipelineState.default(str(tmp_path))
            state.chapter_loop.current_chapter = 1
            state.chapter_loop.step_index = 1  # chapter-planning (step 2)
            run_chapter_step(state, tmp_path)
            assert state.chapter_loop.step_index == 2


# ---------------------------------------------------------------------------
# Chapter completion
# ---------------------------------------------------------------------------
class TestChapterCompletion:
    @patch("shenbi.pipeline.chapter_loop.dispatch_skill")
    @patch("shenbi.pipeline.chapter_loop.run_gate_g4")
    def test_last_step_completes_chapter(self, mock_g4, mock_disp, tmp_path):
        """Last step (chapter-revision, index 14) completes the chapter."""
        mock_disp.return_value = DispatchResult(True, 0, "{}", "")
        mock_g4.return_value = {"status": "PASS"}
        state = PipelineState.default(str(tmp_path))
        state.chapter_loop.current_chapter = 1
        state.chapter_loop.step_index = 14  # last step (chapter-revision)
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
        state.chapter_loop.step_index = 14  # last step (chapter-revision)
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
        state.chapter_loop.step_index = 14  # last step (chapter-revision)
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
        # Real ch56 product (G0.9): P0-4 is TRIGGERED in the lifecycle table
        import shutil

        from shenbi.pipeline.chapter_loop import _check_conditional_resolve

        src = Path("tests/fixtures/pipeline/truth-pending_hooks-ch56.md")
        if not src.exists():
            src = next(Path("tests/fixtures").rglob("truth-pending_hooks-ch56.md"))
        hooks_file = tmp_path / "truth" / "pending_hooks.md"
        hooks_file.parent.mkdir(parents=True)
        shutil.copyfile(src, hooks_file)
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
        """Step 2 (chapter-planning, index 1) dispatch fail retries then escalates."""
        mock_disp.return_value = DispatchResult(False, 1, "", "error")
        mock_esc_disp.return_value = DispatchResult(True, 0, "{}", "")
        state = PipelineState.default(str(tmp_path))
        state.chapter_loop.current_chapter = 1
        state.chapter_loop.step_index = 1  # chapter-planning (step 2)
        state.config.max_revision_retries = 3

        result1 = run_chapter_step(state, tmp_path)
        assert result1 is False
        assert state.chapter_loop.step_index == 1

        result2 = run_chapter_step(state, tmp_path)
        assert result2 is False
        assert state.chapter_loop.step_index == 1

        result3 = run_chapter_step(state, tmp_path)
        assert result3 is True
        assert state.pending_checkpoint.type == CheckpointType.ESCALATION

    @patch("shenbi.pipeline.chapter_loop.dispatch_skill")
    @patch("shenbi.pipeline.revision_router.dispatch_skill")
    @patch("shenbi.pipeline.chapter_loop.run_gate_g4")
    def test_g4_fail_retries_then_escalates(self, mock_g4, mock_esc_disp, mock_disp, tmp_path):
        """Step 2 (chapter-planning, index 1) G4 fail retries then escalates."""
        mock_disp.return_value = DispatchResult(True, 0, "{}", "")
        mock_esc_disp.return_value = DispatchResult(True, 0, "{}", "")
        mock_g4.return_value = {"status": "FAIL"}
        state = PipelineState.default(str(tmp_path))
        state.chapter_loop.current_chapter = 1
        state.chapter_loop.step_index = 1  # chapter-planning (step 2)
        state.config.max_revision_retries = 2

        run_chapter_step(state, tmp_path)
        assert state.chapter_loop.step_index == 1

        result = run_chapter_step(state, tmp_path)
        assert result is True
        assert state.pending_checkpoint.type == CheckpointType.ESCALATION

    @patch("shenbi.pipeline.chapter_loop.dispatch_skill")
    @patch("shenbi.pipeline.chapter_loop.run_gate_g4")
    def test_retry_count_reset_on_success(self, mock_g4, mock_disp, tmp_path):
        """Retry count for a dispatched step is reset after successful run."""
        mock_disp.return_value = DispatchResult(True, 0, "{}", "")
        mock_g4.return_value = {"status": "PASS"}
        state = PipelineState.default(str(tmp_path))
        state.chapter_loop.current_chapter = 1
        state.chapter_loop.step_index = 1  # chapter-planning (step 2)
        state.chapter_loop.retry_counts["ch1-shenbi-chapter-planning"] = 2
        run_chapter_step(state, tmp_path)
        assert "ch1-shenbi-chapter-planning" not in state.chapter_loop.retry_counts


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
        """pipeline-volume-align is pipeline-internal -- no dispatch."""
        state = PipelineState.default(str(tmp_path))
        state.chapter_loop.current_chapter = 1
        state.chapter_loop.step_index = 0  # pipeline-volume-align (step 1)
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
        ridx = next(i for i, s_ in enumerate(CHAPTER_STEPS) if "review-resonance" in s_.skill)
        state.chapter_loop.step_index = ridx  # review-resonance
        run_chapter_step(state, tmp_path)
        assert state.chapter_loop.step_index == ridx


@pytest.mark.last
class TestAuditCircleIntegration:
    def test_last_audit_step_advances_past_audits(self, tmp_path):
        """At _FIRST_AUDIT_IDX (index 8), all audits are parallel-dispatched
        and step_index jumps past _LAST_AUDIT_IDX (index 13) to 14.
        """
        state = PipelineState.default(str(tmp_path))
        state.chapter_loop.current_chapter = 1
        state.chapter_loop.step_index = _FIRST_AUDIT_IDX  # index 8 (first audit)

        with (
            patch(
                "shenbi.pipeline.chapter_loop.dispatch_skill",
                return_value=DispatchResult(True, 0, "{}", ""),
            ),
            # Serial WRITE_SHARED members dispatch through the same seam as
            # the concurrent wave (inside _dispatch_with_retry, C32 R4 follow-up).
            patch(
                "shenbi.pipeline.parallel_dispatch.dispatch_skill",
                return_value=DispatchResult(True, 0, "{}", ""),
            ),
            patch(
                "shenbi.pipeline.parallel_dispatch.dispatch_reviews_parallel",
                side_effect=lambda tasks: [DispatchResult(True, 0, "{}", "") for _ in tasks],
            ),
            patch(
                "shenbi.pipeline.parallel_dispatch.consolidate_review_results",
                return_value="# Chapter 1 — Consolidated\n\nNo issues found.",
            ),
            patch("shenbi.pipeline.chapter_loop.run_gate_g4", return_value={"status": "PASS"}),
        ):
            run_chapter_step(state, tmp_path)
        # Advances past all audits to _LAST_AUDIT_IDX + 1 = 14
        assert state.chapter_loop.step_index == 14


class TestConditionalResolveIntegration:
    @patch("shenbi.pipeline.chapter_loop.dispatch_skill")
    def test_lifecycle_step_dispatches_via_parallel(self, mock_disp, tmp_path):
        """foreshadowing-lifecycle (index 6) triggers parallel post-draft
        dispatch which runs both lifecycle and settling together.
        """
        mock_disp.return_value = DispatchResult(True, 0, "{}", "")
        state = PipelineState.default(str(tmp_path))
        state.chapter_loop.current_chapter = 1
        state.chapter_loop.step_index = 6  # foreshadowing-lifecycle (step 7)
        # Mock run_parallel_post_draft_steps to return success for both
        with (
            patch(
                "shenbi.pipeline.chapter_loop.run_parallel_post_draft_steps",
                return_value=(DispatchResult(True, 0, "{}", ""), DispatchResult(True, 0, "{}", "")),
            ),
            patch("shenbi.pipeline.chapter_loop.run_gate_g4", return_value={"status": "PASS"}),
        ):
            run_chapter_step(state, tmp_path)
        # Advances past both lifecycle (6) and settling (7) to index 8
        assert state.chapter_loop.step_index == 8

    def test_track_step_with_triggered_hooks_dispatches_resolve(self, tmp_path):
        """_check_conditional_resolve dispatches resolve when TRIGGERED hooks exist."""
        # Real ch56 product (G0.9): P0-4 is TRIGGERED in the lifecycle table
        import shutil

        from shenbi.pipeline.chapter_loop import _check_conditional_resolve

        src = Path("tests/fixtures/pipeline/truth-pending_hooks-ch56.md")
        if not src.exists():
            src = next(Path("tests/fixtures").rglob("truth-pending_hooks-ch56.md"))
        hooks_file = tmp_path / "truth" / "pending_hooks.md"
        hooks_file.parent.mkdir(parents=True)
        shutil.copyfile(src, hooks_file)
        state = PipelineState.default(str(tmp_path))
        with patch("shenbi.pipeline.chapter_loop.dispatch_skill") as mock_disp:
            mock_disp.return_value = DispatchResult(True, 0, "{}", "")
            _check_conditional_resolve(state, tmp_path, 1)
        # dispatch_skill called for resolve
        assert mock_disp.call_count >= 1
        resolve_skills = [
            c[0][0] for c in mock_disp.call_args_list if "foreshadowing-resolve" in c[0][0]
        ]
        assert len(resolve_skills) >= 1


class TestAnyAuditHasFindings:
    """F340/F369/F370 (spec #27 T5): scan list single-sourced from the step
    table + activation matrix; precise BLOCKING/FAIL marker matching.
    """

    def _state_with_audit(self, tmp_path, filename, content):
        from shenbi.pipeline.state import PipelineState

        proj = tmp_path / "proj"
        (proj / "audits").mkdir(parents=True, exist_ok=True)
        if filename is not None:
            (proj / "audits" / filename).write_text(content, encoding="utf-8")
        state = PipelineState(project_dir=str(proj))
        state.chapter_loop.current_chapter = 3
        return state

    def test_group_factual_blocking_triggers(self, tmp_path):
        """F340 P0: a group-* audit with a BLOCKING section must trigger
        revision gating (old 13-type list missed the group family).
        """
        from shenbi.pipeline.chapter_loop import _any_audit_has_findings

        state = self._state_with_audit(
            tmp_path,
            "chapter-3-group-factual.md",
            "# 审计\n\n## BLOCKING Issues\n\n- 事实错误\n",
        )
        assert _any_audit_has_findings(state) is True

    def test_genre_dimension_era_triggers(self, tmp_path):
        """F369: genre-activated audit families (era/…) must be scanned."""
        from shenbi.pipeline.chapter_loop import _any_audit_has_findings

        state = self._state_with_audit(tmp_path, "chapter-3-era.md", "## BLOCKING\n时代错位\n")
        assert _any_audit_has_findings(state) is True

    def test_real_production_blocking_audit_triggers(self, tmp_path):
        """F370: real BLOCKING product (xinghuo chapter audits) triggers;
        prose mentions of FAIL must not (precise marker, not substring).
        """
        import shutil

        from shenbi.pipeline.chapter_loop import _any_audit_has_findings

        src = Path("novel-output/xinghuo-ranqiong/audits/chapter-2-memo-compliance.md")
        if not src.exists():  # production tree not present in this checkout
            pytest.skip("xinghuo-ranqiong production tree unavailable")
        proj = tmp_path / "proj"
        (proj / "audits").mkdir(parents=True)
        shutil.copy(src, proj / "audits" / "chapter-3-pacing.md")
        state = self._state_with_audit(tmp_path, None, "")
        state.project_dir = str(proj)
        # chapter-2-memo-compliance.md contains "## BLOCKING" (verified real product)
        assert _any_audit_has_findings(state) is True

    def test_prose_fail_mention_does_not_trigger(self, tmp_path):
        """F370: bare 'FAIL' inside prose is not a marker."""
        from shenbi.pipeline.chapter_loop import _any_audit_has_findings

        state = self._state_with_audit(
            tmp_path, "chapter-3-pacing.md", "本次审计未出现 FAIL 情况，一切正常。\n"
        )
        assert _any_audit_has_findings(state) is False
