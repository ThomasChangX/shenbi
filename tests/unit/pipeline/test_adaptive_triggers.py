"""Tests for adaptive recall, drift, and snapshot triggers."""

from __future__ import annotations

import json
from pathlib import Path

from shenbi.pipeline.chapter_loop import (
    _should_run_drift,
    _should_run_recall,
    _snapshot_chapter_files,
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
        snapshots = list(snap_dir.glob("chapter-005-*.md"))
        assert len(snapshots) == 1
        assert "Chapter 5 content" in snapshots[0].read_text(encoding="utf-8")

        manifest = snap_dir / "manifest.json"
        assert manifest.exists()
        data = json.loads(manifest.read_text(encoding="utf-8"))
        assert "5" in data["chapters"]
