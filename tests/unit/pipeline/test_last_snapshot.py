"""Tests that last_snapshot is set after snapshot creation (spec §3.3)."""

from __future__ import annotations

from pathlib import Path

from shenbi.pipeline.chapter_loop import _snapshot_chapter_files
from shenbi.pipeline.state import PipelineState


def test_last_snapshot_set_with_chapter_path_timestamp(tmp_path: Path):
    s = PipelineState.default(project_dir=str(tmp_path))
    # Seed a chapter file so the snapshot has content.
    (tmp_path / "chapters").mkdir()
    (tmp_path / "chapters" / "chapter-5.md").write_text("# Ch5\nbody", encoding="utf-8")

    _snapshot_chapter_files(tmp_path, chapter=5, state=s)

    assert s.last_snapshot, "last_snapshot must be populated"
    assert s.last_snapshot["chapter"] == 5
    assert s.last_snapshot["path"] == "snapshots/chapter-005"
    assert "timestamp" in s.last_snapshot


def test_state_none_keeps_old_behavior(tmp_path: Path):
    """Caller may omit state; snapshot still created, no pointer to set."""
    (tmp_path / "chapters").mkdir()
    (tmp_path / "chapters" / "chapter-1.md").write_text("# Ch1\n", encoding="utf-8")
    # Must not raise.
    _snapshot_chapter_files(tmp_path, chapter=1, state=None)
    snaps = list((tmp_path / "snapshots" / "chapter-001").glob("snapshot-manifest.json"))
    assert len(snaps) == 1


def test_path_is_relative_to_project_dir(tmp_path: Path, monkeypatch):
    s = PipelineState.default(project_dir=str(tmp_path))
    (tmp_path / "chapters").mkdir()
    (tmp_path / "chapters" / "chapter-3.md").write_text("x", encoding="utf-8")
    _snapshot_chapter_files(tmp_path, chapter=3, state=s)
    # path should be relative, not absolute.
    assert not s.last_snapshot["path"].startswith("/")
    assert (tmp_path / s.last_snapshot["path"]).exists()
