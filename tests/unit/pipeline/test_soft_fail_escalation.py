"""Tests for the soft-fail-tracker -> check_escalation wiring (Spec 22 E32)."""

from __future__ import annotations

from unittest.mock import patch

from shenbi.pipeline.chapter_loop import _check_soft_fail_escalation
from shenbi.pipeline.state import PipelineState, SoftFailTracker


def _state_with_soft_fail_window(chapters: list[int]) -> PipelineState:
    """Build a state whose ``transition`` tracker has recorded *chapters*."""
    state = PipelineState.default(project_dir="/tmp/novel")
    tracker = SoftFailTracker(check_id="G4.lt.transition")
    for ch in chapters:
        tracker.record(ch)
    state.chapter_loop.soft_fail_trackers["G4.lt.transition"] = tracker
    return state


class TestCheckSoftFailEscalation:
    def test_below_threshold_does_not_dispatch(self, tmp_path):
        state = _state_with_soft_fail_window([10, 11])  # 2 occurrences < threshold 3
        with (
            patch("shenbi.pipeline.chapter_loop.check_escalation") as mock_check,
            patch("shenbi.pipeline.chapter_loop.dispatch_escalation") as mock_disp,
        ):
            _check_soft_fail_escalation(state, tmp_path, chapter=12)
        mock_check.assert_not_called()
        mock_disp.assert_not_called()

    def test_over_threshold_dispatches_when_signals_fire(self, tmp_path):
        # 4 occurrences within the window -> should_escalate True.
        state = _state_with_soft_fail_window([9, 10, 11, 12])
        # check_escalation returns a non-empty signal list.
        from shenbi.skill_utils.escalation.check import EscalationSignal

        with (
            patch(
                "shenbi.pipeline.chapter_loop.check_escalation",
                return_value=[EscalationSignal(trigger="score_decline", detail="x")],
            ) as mock_check,
            patch("shenbi.pipeline.chapter_loop.dispatch_escalation") as mock_disp,
        ):
            _check_soft_fail_escalation(state, tmp_path, chapter=12)
        mock_check.assert_called_once()
        # Verify the real signature was used.
        kwargs = mock_check.call_args.kwargs
        assert "resonance_scores" in kwargs
        assert "sensitivity_blocking" in kwargs
        assert "volume_objective_met" in kwargs
        assert "regeneration_attempts" in kwargs
        mock_disp.assert_called_once()

    def test_over_threshold_no_dispatch_when_no_signals(self, tmp_path):
        state = _state_with_soft_fail_window([9, 10, 11, 12])
        with (
            patch("shenbi.pipeline.chapter_loop.check_escalation", return_value=[]) as mock_check,
            patch("shenbi.pipeline.chapter_loop.dispatch_escalation") as mock_disp,
        ):
            _check_soft_fail_escalation(state, tmp_path, chapter=12)
        mock_check.assert_called_once()
        mock_disp.assert_not_called()

    def test_passes_recent_resonance_scores(self, tmp_path):
        """The scores fed to check_escalation come from the existing
        _get_recent_resonance_scores helper (window 5 to match the escalation
        default).
        """
        state = _state_with_soft_fail_window([9, 10, 11, 12])
        with (
            patch(
                "shenbi.pipeline.chapter_loop._get_recent_resonance_scores",
                return_value=[90, 85, 80, 75, 70],
            ) as mock_scores,
            patch("shenbi.pipeline.chapter_loop.check_escalation", return_value=[]),
        ):
            _check_soft_fail_escalation(state, tmp_path, chapter=12)
        mock_scores.assert_called_once_with(tmp_path, 12, window=5)
