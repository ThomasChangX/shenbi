"""Tests for adaptive recall, drift, and snapshot triggers."""

from __future__ import annotations

from pathlib import Path

from shenbi.pipeline.chapter_loop import (
    ChapterStep,
    _should_run_drift,
    _should_run_step,
)


class TestAdaptiveDrift:
    def test_insufficient_scores_returns_false(self, tmp_path: Path):
        assert _should_run_drift(tmp_path, chapter=5) is False


class TestShouldRunStep:
    """Integration tests for _should_run_step conditional dispatch.

    Updated for Plan 18 Task 5: _should_run_step now uses (state, step) signature
    with step.conditional flag gating instead of skill-specific inline handling.
    """

    def test_non_conditional_step_always_runs(self, tmp_path: Path):
        """Steps with conditional=False always return True."""
        from unittest.mock import MagicMock

        state = MagicMock()
        step = ChapterStep(
            step_num=2,
            skill="shenbi-chapter-planning",
            name="chapter-planning",
            step_type="core",
            conditional=False,
        )
        assert _should_run_step(state, step) is True

    def test_intent_management_gated_by_volume_boundary(self, tmp_path: Path):
        """intent-management only runs at volume boundaries."""
        from unittest.mock import MagicMock, patch

        state = MagicMock()
        step = ChapterStep(
            step_num=1,
            skill="shenbi-intent-management",
            name="intent-management",
            step_type="core",
            conditional=True,
        )
        with patch(
            "shenbi.pipeline.chapter_loop._is_volume_boundary",
            return_value=False,
        ):
            assert _should_run_step(state, step) is False
        with patch(
            "shenbi.pipeline.chapter_loop._is_volume_boundary",
            return_value=True,
        ):
            assert _should_run_step(state, step) is True
