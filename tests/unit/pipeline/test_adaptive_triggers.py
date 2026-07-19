"""Tests for adaptive recall, drift, and snapshot triggers."""

from __future__ import annotations

import json
from pathlib import Path

from shenbi.pipeline.chapter_loop import (
    ChapterStep,
    _should_run_drift,
    _should_run_recall,
    _should_run_step,
    _snapshot_chapter_files,
)
from shenbi.pipeline.state import PipelineState


class TestAdaptiveRecall:
    def test_no_hooks_returns_false(self, tmp_path: Path):
        (tmp_path / "truth").mkdir()
        (tmp_path / "truth" / "pending_hooks.md").write_text(
            "---\nhooks: []\n---\n", encoding="utf-8"
        )
        assert _should_run_recall(tmp_path, chapter=5) is False

    def test_hook_near_max_distance_triggers(self, tmp_path: Path):
        (tmp_path / "truth").mkdir()
        (tmp_path / "truth" / "pending_hooks.md").write_text(
            "---\nhooks:\n  - id: hook-001\n    state: PLANTED\n    last_reinforced: 5\n    max_distance: 20\n---\n",
            encoding="utf-8",
        )
        # Chapter 22: silence = 22-5 = 17, max_distance = 20, 17 >= 20-3 = 17 → triggers
        assert _should_run_recall(tmp_path, chapter=22) is True


class TestAdaptiveDrift:
    def test_insufficient_scores_returns_false(self, tmp_path: Path):
        assert _should_run_drift(tmp_path, chapter=5) is False


class TestFileSnapshot:
    def test_creates_timestamped_copy(self, tmp_path: Path):
        (tmp_path / "chapters").mkdir()
        chapter_file = tmp_path / "chapters" / "chapter-5.md"
        chapter_file.write_text("# Chapter 5 content", encoding="utf-8")

        _snapshot_chapter_files(tmp_path, chapter=5)

        snap_dir = tmp_path / "snapshots"
        assert snap_dir.exists()
        # Differential snapshots create chapter subdirectories with a manifest.
        chapter_snap_dir = snap_dir / "chapter-005"
        assert chapter_snap_dir.exists()
        manifest_file = chapter_snap_dir / "snapshot-manifest.json"
        assert manifest_file.exists()
        data = json.loads(manifest_file.read_text(encoding="utf-8"))
        assert data["chapter"] == 5
        # Verify the chapter file entry exists.
        assert any("chapter-5.md" in f["path"] for f in data.get("files", []))


class TestShouldRunStep:
    """Integration tests for _should_run_step adaptive triggering."""

    def test_snapshot_manage_always_returns_false(self, tmp_path: Path):
        """Snapshot-manage step always returns False — it runs inline, no LLM dispatch."""
        state = PipelineState.default(str(tmp_path))
        state.chapter_loop.current_chapter = 5

        step = ChapterStep(
            step_num=19,
            skill="shenbi-snapshot-manage",
            name="snapshot-manage",
        )

        assert _should_run_step(step, state, tmp_path) is False
