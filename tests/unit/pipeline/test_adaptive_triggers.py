"""Tests for adaptive conditional-step dispatch."""

from __future__ import annotations

from pathlib import Path

from shenbi.pipeline.chapter_loop import (
    ChapterStep,
    _should_run_step,
)


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
