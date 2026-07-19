"""Tests for the snapshot-retention pruner boundary condition (Spec 22 E40)."""

from __future__ import annotations

import json
from pathlib import Path

from shenbi.pipeline.chapter_loop import _prune_old_snapshots


def _write_manifest(project_dir: Path, chapters: dict[str, list[str]]) -> None:
    snap_dir = project_dir / "snapshots"
    snap_dir.mkdir(parents=True, exist_ok=True)
    # Create the snapshot files on disk so the pruner can unlink them.
    for ch_key, files in chapters.items():
        for fname in files:
            (snap_dir / fname).write_text("snap", encoding="utf-8")
    manifest_path = snap_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps({"chapters": chapters}, ensure_ascii=False), encoding="utf-8"
    )


def _chapter_count(project_dir: Path) -> int:
    manifest = json.loads((project_dir / "snapshots" / "manifest.json").read_text(encoding="utf-8"))
    return len(manifest.get("chapters", {}))


class TestPruneBoundary:
    def test_keeps_exactly_retention_chapters(self, tmp_path, monkeypatch):
        # 56 chapters, retention 50 -> keep 50, prune 6.
        chapters = {str(n): [f"chapter-{n:03d}-t.md"] for n in range(1, 57)}
        _write_manifest(tmp_path, chapters)
        monkeypatch.setattr(
            "shenbi.pipeline.chapter_loop._get_snapshot_retention",
            lambda _pd: 50,
        )

        _prune_old_snapshots(tmp_path)

        assert _chapter_count(tmp_path) == 50
        # The newest 50 (chapters 7..56) survive; 1..6 are pruned.
        manifest = json.loads(
            (tmp_path / "snapshots" / "manifest.json").read_text(encoding="utf-8")
        )
        surviving = sorted(int(k) for k in manifest["chapters"])
        assert surviving == list(range(7, 57))
        # Pruned files are gone from disk.
        assert not (tmp_path / "snapshots" / "chapter-001-t.md").exists()
        assert (tmp_path / "snapshots" / "chapter-056-t.md").exists()

    def test_no_overshoot_at_boundary(self, tmp_path, monkeypatch):
        """The exact E40 scenario: retention 50, 52 chapters on disk -> 50 after."""
        chapters = {str(n): [f"chapter-{n:03d}-t.md"] for n in range(1, 53)}
        _write_manifest(tmp_path, chapters)
        monkeypatch.setattr(
            "shenbi.pipeline.chapter_loop._get_snapshot_retention",
            lambda _pd: 50,
        )

        _prune_old_snapshots(tmp_path)

        assert _chapter_count(tmp_path) == 50

    def test_under_cap_no_prune(self, tmp_path, monkeypatch):
        chapters = {str(n): [f"chapter-{n:03d}-t.md"] for n in range(1, 11)}
        _write_manifest(tmp_path, chapters)
        monkeypatch.setattr(
            "shenbi.pipeline.chapter_loop._get_snapshot_retention",
            lambda _pd: 50,
        )

        _prune_old_snapshots(tmp_path)

        assert _chapter_count(tmp_path) == 10

    def test_empty_manifest_no_op(self, tmp_path, monkeypatch):
        _write_manifest(tmp_path, {})
        monkeypatch.setattr(
            "shenbi.pipeline.chapter_loop._get_snapshot_retention",
            lambda _pd: 50,
        )

        _prune_old_snapshots(tmp_path)  # must not raise

        assert _chapter_count(tmp_path) == 0

    def test_handles_gaps_in_chapter_numbers(self, tmp_path, monkeypatch):
        """Retention counts CHAPTERS, not the numeric range — gaps must not
        cause over-pruning.
        """
        chapters = {
            str(n): [f"chapter-{n:03d}-t.md"] for n in [1, 2, 3, 10, 20, 30, 40, 50, 60, 70]
        }
        _write_manifest(tmp_path, chapters)
        monkeypatch.setattr(
            "shenbi.pipeline.chapter_loop._get_snapshot_retention",
            lambda _pd: 5,
        )

        _prune_old_snapshots(tmp_path)

        # 10 chapters, keep newest 5.
        assert _chapter_count(tmp_path) == 5
        manifest = json.loads(
            (tmp_path / "snapshots" / "manifest.json").read_text(encoding="utf-8")
        )
        surviving = sorted(int(k) for k in manifest["chapters"])
        assert surviving == [30, 40, 50, 60, 70]
