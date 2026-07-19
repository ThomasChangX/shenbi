"""Test parallel execution of foreshadowing-lifecycle and state-settling.

Uses the single-writer (actor-model) pattern: workers return dict results,
the main thread merges. No _state_lock.
"""

import inspect
from unittest.mock import MagicMock, patch

from shenbi.pipeline.chapter_loop import run_parallel_post_draft_steps
from shenbi.pipeline.state import PipelineState


class TestParallelPostDraft:
    @patch("shenbi.pipeline.chapter_loop.dispatch_skill")
    def test_both_steps_executed_concurrently(self, mock_dispatch):
        """Verify both foreshadowing-lifecycle and state-settling are dispatched."""
        mock_dispatch.return_value = MagicMock(success=True, result={})
        state = PipelineState.default("/tmp/test-project")
        state.chapter_loop.current_chapter = 3

        run_parallel_post_draft_steps(state)

        assert mock_dispatch.call_count == 2
        skills_called = [c.kwargs.get("skill") or c.args[0] for c in mock_dispatch.call_args_list]
        assert "shenbi-foreshadowing-lifecycle" in skills_called
        assert "shenbi-state-settling" in skills_called

    @patch("shenbi.pipeline.chapter_loop.dispatch_skill")
    def test_lifecycle_failure_isolated_from_settling(self, mock_dispatch):
        """Lifecycle failure is logged but does not block state-settling."""

        def side_effect(skill, project_dir, prompt, **kwargs):
            result = MagicMock()
            if skill == "shenbi-foreshadowing-lifecycle":
                result.success = False
                result.result = {}
                result.stdout = ""
                result.stderr = "mock lifecycle failure"
                result.returncode = 1
            else:
                result.success = True
                result.result = {}
            return result

        mock_dispatch.side_effect = side_effect
        state = PipelineState.default("/tmp/test-project")
        state.chapter_loop.current_chapter = 3

        # Should not raise; lifecycle failure is logged but does not
        # block state-settling from succeeding.
        run_parallel_post_draft_steps(state)

        # Both were dispatched
        assert mock_dispatch.call_count == 2

    @patch("shenbi.pipeline.chapter_loop.dispatch_skill")
    def test_state_settling_failure_handled(self, mock_dispatch):
        """State-settling failure is reported in results (caller handles escalation)."""

        def side_effect(skill, project_dir, prompt, **kwargs):
            result = MagicMock()
            if skill == "shenbi-state-settling":
                result.success = False
                result.result = {}
                result.stdout = ""
                result.stderr = "mock settling failure"
                result.returncode = 1
            else:
                result.success = True
                result.result = {}
            return result

        mock_dispatch.side_effect = side_effect
        state = PipelineState.default("/tmp/test-project")
        state.chapter_loop.current_chapter = 3

        lifecycle_result, settling_result = run_parallel_post_draft_steps(state)
        assert lifecycle_result.success
        assert not settling_result.success

    def test_state_merged_on_main_thread_single_writer(self):
        """Workers return dict results; the main thread merges to PipelineState.

        No _state_lock should exist -- this is the actor-model pattern.
        """
        from shenbi.pipeline import state as state_mod

        src = inspect.getsource(state_mod)
        # The single-writer pattern forbids a module-level _state_lock
        assert "_state_lock" not in src, (
            "Use single-writer (actor-model), NOT _state_lock (Spec 6 §3.4)"
        )
