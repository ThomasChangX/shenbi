"""Queue-path re-dispatch: corrective feedback wiring + drain success gate.

probe20 (adjudication #008): the queue re-dispatch path retried failed
entries byte-identically (15270/15270 tokens, 3 attempts, deterministic
rejection) because attempt N's stderr never reached attempt N+1's prompt —
#30 only wired the chapter_loop dispatch sites (point fix, not family fix).
Worse, the queue's failures never blocked chapter advancement: surviving
entries were carried along while the orchestrate loop rolled into ch2
planning on empty templates.

#45: attempt-N stderr rides into the entry's feedback for attempt N+1.
#46: a queue that cannot drain (survivors or cap-dropped entries) raises an
ESCALATION checkpoint instead of letting the loop advance.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import patch

from shenbi.pipeline.cli import _execute_pending_re_dispatches
from shenbi.pipeline.dispatch_helper import DispatchResult
from shenbi.pipeline.state import CheckpointType, PipelineState


def _entry() -> dict[str, Any]:
    from shenbi.pipeline.chapter_loop import _audit_routed_settle_redispatch_entry

    return dict(_audit_routed_settle_redispatch_entry(1))


def _state(tmp_path: Path) -> PipelineState:
    state = PipelineState.default(str(tmp_path))
    state.pending_re_dispatches = [_entry()]
    return state


class TestRetryFeedbackWiring:
    def test_failed_attempt_stderr_rides_into_next_attempt_feedback(self, tmp_path):
        """#45: the entry's feedback must accumulate the failed attempt's
        stderr so the retry prompt carries corrective signal.
        """
        state = _state(tmp_path)
        stderr = "输出未落盘——append_dedup（key: chapter）增量包含整档脚手架"
        with patch(
            "shenbi.pipeline.dispatch_helper.dispatch_skill",
            return_value=DispatchResult(False, -1, "", stderr),
        ):
            _execute_pending_re_dispatches(state, tmp_path)
        remaining = state.pending_re_dispatches
        assert len(remaining) == 1, "under cap: entry survives for a retry"
        fb = remaining[0].get("feedback") or ""
        assert "上次派分失败" in fb or "上次派发失败" in fb, (
            f"attempt-2 feedback must name the attempt-1 failure: {fb!r}"
        )
        assert "整档脚手架" in fb, "the guard's corrective text must reach attempt N+1"

    def test_original_feedback_survives_as_prefix(self, tmp_path):
        state = _state(tmp_path)
        state.pending_re_dispatches[0]["feedback"] = "修订：回收灯座划痕的埋设"
        with patch(
            "shenbi.pipeline.dispatch_helper.dispatch_skill",
            return_value=DispatchResult(False, -1, "", "boom"),
        ):
            _execute_pending_re_dispatches(state, tmp_path)
        fb = state.pending_re_dispatches[0]["feedback"]
        assert fb.startswith("修订：回收灯座划痕的埋设"), (
            "human feedback stays the lead instruction"
        )
        assert "boom" in fb


class TestQueueDrainSuccessGate:
    def test_surviving_entries_raise_escalation_checkpoint(self, tmp_path):
        """#46: a queue that cannot drain blocks chapter advancement by
        raising a human checkpoint — the loop must not roll into the next
        chapter while a re-dispatch is still failing.
        """
        state = _state(tmp_path)
        with patch(
            "shenbi.pipeline.dispatch_helper.dispatch_skill",
            return_value=DispatchResult(False, -1, "", "still failing"),
        ):
            _execute_pending_re_dispatches(state, tmp_path)
        cp = state.pending_checkpoint
        assert cp is not None and cp.type == CheckpointType.ESCALATION, (
            "surviving queue entries must surface an escalation checkpoint"
        )
        assert "shenbi-state-settling" in (cp.context or "")

    def test_cap_dropped_entries_also_raise_escalation(self, tmp_path):
        state = _state(tmp_path)
        entry = state.pending_re_dispatches[0]
        entry["attempts"] = 99  # at/over cap: this attempt drops the entry
        with patch(
            "shenbi.pipeline.dispatch_helper.dispatch_skill",
            return_value=DispatchResult(False, -1, "", "deterministic death"),
        ):
            _execute_pending_re_dispatches(state, tmp_path)
        assert state.pending_re_dispatches == [], "cap entry dropped"
        cp = state.pending_checkpoint
        assert cp is not None and cp.type == CheckpointType.ESCALATION, (
            "a cap-dropped entry must surface a human checkpoint, not vanish"
        )

    def test_clean_queue_does_not_raise_checkpoint(self, tmp_path):
        """A fully-drained queue raises no escalation. Uses a chapter-revision
        entry (not settle — settle's success re-raises STATE_SETTLE by
        design, pinned in its own test below).
        """
        state = _state(tmp_path)
        state.pending_re_dispatches[0]["skill"] = "shenbi-chapter-revision"
        with patch(
            "shenbi.pipeline.dispatch_helper.dispatch_skill",
            return_value=DispatchResult(True, 0, "", ""),
        ):
            _execute_pending_re_dispatches(state, tmp_path)
        assert state.pending_re_dispatches == []
        cp = state.pending_checkpoint
        assert cp is None or cp.type == CheckpointType.NONE, (
            "a fully drained queue raises no escalation"
        )

    def test_settle_success_re_raises_state_settle_checkpoint(self, tmp_path):
        """Existing behavior pin (probe4 fix): a successful settle re-dispatch
        re-raises STATE_SETTLE so the human reviews the staged increments.
        """
        state = _state(tmp_path)
        with patch(
            "shenbi.pipeline.dispatch_helper.dispatch_skill",
            return_value=DispatchResult(True, 0, "", ""),
        ):
            _execute_pending_re_dispatches(state, tmp_path)
        cp = state.pending_checkpoint
        assert cp is not None and cp.type == CheckpointType.STATE_SETTLE
