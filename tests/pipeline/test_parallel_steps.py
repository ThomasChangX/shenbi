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
        """Both steps truly overlap: neither returns until BOTH have started.

        F745 (spec #52): a threading.Barrier(2) inside the faked dispatches
        proves real concurrency — a serial implementation deadlocks against
        the barrier timeout and this test goes red. The old call_count==2
        assertion passed even for fully sequential execution.
        """
        import threading

        barrier = threading.Barrier(2, timeout=5.0)
        started = threading.Event()

        def barrier_dispatch(skill, *args, **kwargs):
            try:
                barrier.wait()  # both workers must arrive for either to proceed
                started.set()
                return MagicMock(success=True, result={})
            except threading.BrokenBarrierError:
                return MagicMock(success=False, result={})

        mock_dispatch.side_effect = barrier_dispatch
        state = PipelineState.default("/tmp/test-project")
        state.chapter_loop.current_chapter = 3

        lifecycle_result, settling_result = run_parallel_post_draft_steps(state)

        assert started.is_set(), "both dispatches ran"
        assert lifecycle_result.success and settling_result.success
        skills_called = [c.args[0] for c in mock_dispatch.call_args_list]
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
        # F745 behavioral complement: state mutations happen only on the
        # calling (main) thread — the workers' results are merged after
        # future.result() returns (chapter_loop.py "merge on the main thread
        # ONLY"). The textual grep above cannot see call-site discipline;
        # this pins the observable contract: after run_parallel_post_draft_steps
        # returns, both steps' results are merged into the state.
        import threading as _threading

        from shenbi.pipeline.state import _merge_step_result

        merge_thread_ids: list[int] = []
        real_merge = _merge_step_result

        def tracking_merge(*a, **k):
            merge_thread_ids.append(_threading.get_ident())
            return real_merge(*a, **k)

        with patch("shenbi.pipeline.state._merge_step_result", tracking_merge):
            state = PipelineState.default("/tmp/test-project")
            state.chapter_loop.current_chapter = 4
            run_parallel_post_draft_steps(state)
        main_id = _threading.get_ident()
        assert merge_thread_ids and all(tid == main_id for tid in merge_thread_ids), (
            "state merges must happen on the calling thread only (single-writer)"
        )
