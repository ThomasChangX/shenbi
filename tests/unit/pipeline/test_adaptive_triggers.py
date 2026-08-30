"""Tests for adaptive recall, drift, and snapshot triggers."""

from __future__ import annotations

from pathlib import Path

from shenbi.pipeline.chapter_loop import (
    ChapterStep,
    _should_run_drift,
    _should_run_recall,
    _should_run_step,
)


class TestAdaptiveRecall:
    def test_no_hooks_returns_false(self, tmp_path: Path):
        (tmp_path / "truth").mkdir()
        (tmp_path / "truth" / "pending_hooks.md").write_text(
            "---\nhooks: []\n---\n", encoding="utf-8"
        )
        assert _should_run_recall(tmp_path, chapter=5) is False

    def test_hook_near_max_distance_triggers(self, tmp_path: Path):
        (tmp_path / "truth").mkdir()
        # Production table format (SDD #21 R2): last_reinforced from the
        # interval table, max_distance from the distance table.
        (tmp_path / "truth" / "pending_hooks.md").write_text(
            "---\nlast_chapter: 22\n---\n\n"
            "### 培育间隔检查\n\n"
            "| Hook ID | last_reinforced推定 | 本章 | 间隔(章) | 状态 |\n"
            "|---------|-------------------|------|---------|------|\n"
            "| P0-1 | ch5 | 22 | 17 | ⚠️ OVERDUE |\n\n"
            "### 距离上限逼近\n\n"
            "| Hook ID | 种植章 | 本章 | elapsed | max_distance(20) | 距上限 | 状态 |\n"
            "|---------|--------|------|---------|-----------------|--------|------|\n"
            "| P0-1 | 5 | 22 | 17 | 20 | 3 | WARNING |\n",
            encoding="utf-8",
        )
        # Chapter 22: silence = 22-5 = 17, max_distance = 20, 17 >= 20-3 = 17 → triggers
        assert _should_run_recall(tmp_path, chapter=22) is True

    def test_hook_with_missing_fields_skips_not_fabricates(self, tmp_path: Path):
        """truth_readers returns None for unavailable fields (SDD #21 R2) —
        _should_run_recall must skip them, not substitute defaults.
        """
        (tmp_path / "truth").mkdir()
        (tmp_path / "truth" / "pending_hooks.md").write_text(
            "---\nlast_chapter: 22\n---\n\n"
            "### 本章操作\n\n"
            "| Hook ID | 操作 | 前状态 | 后状态 | 文本位置 |\n"
            "|---------|------|--------|--------|---------|\n"
            "| P0-1 | (无操作) | RELEVANT | RELEVANT | 未出现 |\n",
            encoding="utf-8",
        )
        # No max_distance/last_reinforced → no fabricated trigger.
        assert _should_run_recall(tmp_path, chapter=99) is False


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
