import json
import tempfile
from pathlib import Path

from shenbi.pipeline.snapshot_diff import (
    create_differential_snapshot,
    hash_file,
    restore_from_snapshot,
)


def test_differential_snapshot_stores_hashes_not_content():
    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)
        chapter_dir = project_dir / "chapters"
        chapter_dir.mkdir(parents=True)
        chapter_file = chapter_dir / "chapter-001.md"
        chapter_text = "林风站在山顶。" * 100
        chapter_file.write_text(chapter_text, encoding="utf-8")

        snapshot_dir = project_dir / "snapshots" / "chapter-001"
        snapshot_dir.mkdir(parents=True)

        create_differential_snapshot(project_dir, 1, snapshot_dir)

        manifest_file = snapshot_dir / "snapshot-manifest.json"
        assert manifest_file.exists()
        manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
        assert "files" in manifest
        # Chapter file should be stored as hash, not full content
        chapter_entry = next((f for f in manifest["files"] if "chapter-001" in f["path"]), None)
        assert chapter_entry is not None
        assert "sha256" in chapter_entry
        assert len(chapter_entry["sha256"]) == 64  # SHA-256 hex digest


def test_recent_chapter_snapshot_stores_full_content_ring_buffer():
    """Ring buffer: store FULL content for the last N=3 chapter snapshots
    alongside hash references, so revision-rollback can restore the PREVIOUS
    chapter content after a revision overwrite. Only recent chapters keep
    full content; older snapshots are hash-only.
    """
    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)
        chapter_dir = project_dir / "chapters"
        chapter_dir.mkdir(parents=True)
        chapters_text = {
            1: "第一章内容" * 50,
            2: "第二章内容" * 50,
            3: "第三章内容" * 50,
            4: "第四章内容" * 50,
        }
        for ch, text in chapters_text.items():
            (chapter_dir / f"chapter-{ch:03d}.md").write_text(text, encoding="utf-8")

        snapshot_base = project_dir / "snapshots"
        snapshot_base.mkdir(parents=True)

        # Snapshot chapters in order; latest = 4, so ring buffer (N=3) covers 2,3,4
        for ch in [1, 2, 3, 4]:
            create_differential_snapshot(project_dir, ch, snapshot_base / f"chapter-{ch:03d}")

        # Chapter 2,3,4 are recent (within N=3 of latest=4) -> full content stored
        snap_2 = json.loads(
            (snapshot_base / "chapter-002" / "snapshot-manifest.json").read_text(encoding="utf-8")
        )
        ch2_entry = next(f for f in snap_2["files"] if "chapter-002" in f["path"])
        assert "content" in ch2_entry, (
            "Recent chapter (within ring buffer N=3) must store full content"
        )
        assert ch2_entry["content"] == chapters_text[2]

        # Chapter 1 is outside the ring buffer (1 < 4-2=2) -> hash-only, no content
        snap_1 = json.loads(
            (snapshot_base / "chapter-001" / "snapshot-manifest.json").read_text(encoding="utf-8")
        )
        ch1_entry = next(f for f in snap_1["files"] if "chapter-001" in f["path"])
        assert "content" not in ch1_entry, "Older snapshot (outside ring buffer) must be hash-only"
        assert "sha256" in ch1_entry


def test_snapshot_restores_truth_files():
    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)
        for sub in ["chapters", "truth"]:
            (project_dir / sub).mkdir(parents=True)
        (project_dir / "chapters" / "chapter-001.md").write_text(
            "chapter content", encoding="utf-8"
        )
        truth_file = project_dir / "truth" / "current_state.md"
        original_truth = "主角状态：活跃"
        truth_file.write_text(original_truth, encoding="utf-8")

        snapshot_dir = project_dir / "snapshots" / "chapter-001"
        snapshot_dir.mkdir(parents=True)
        create_differential_snapshot(project_dir, 1, snapshot_dir)

        # Modify truth file
        truth_file.write_text("主角状态：已修改", encoding="utf-8")

        # Restore
        restore_from_snapshot(project_dir, 1, snapshot_dir)
        restored = truth_file.read_text(encoding="utf-8")
        assert restored == original_truth, f"Expected '{original_truth}', got '{restored}'"


def test_restore_restores_full_content_chapter_from_ring_buffer():
    """restore_from_snapshot must restore files whose full content was stored
    (ring-buffer recent chapters), not just verify hashes.
    """
    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)
        chapter_dir = project_dir / "chapters"
        chapter_dir.mkdir(parents=True)
        original_text = "第一章原始内容" * 50
        (chapter_dir / "chapter-001.md").write_text(original_text, encoding="utf-8")

        snapshot_dir = project_dir / "snapshots" / "chapter-001"
        snapshot_dir.mkdir(parents=True)
        # Only chapter 1 exists, so it is "recent" and gets full content
        create_differential_snapshot(project_dir, 1, snapshot_dir)

        # Simulate a revision overwrite of the chapter
        (chapter_dir / "chapter-001.md").write_text("修订后的内容" * 50, encoding="utf-8")

        # Restore should recover the original chapter content (ring buffer)
        restore_from_snapshot(project_dir, 1, snapshot_dir)
        restored = (chapter_dir / "chapter-001.md").read_text(encoding="utf-8")
        assert restored == original_text, "Ring-buffer chapter content must be fully restored"


def test_hash_verification_detects_modification():
    with tempfile.TemporaryDirectory() as tmp:
        f = Path(tmp) / "test.txt"
        f.write_text("original", encoding="utf-8")
        h1 = hash_file(f)
        f.write_text("modified", encoding="utf-8")
        h2 = hash_file(f)
        assert h1 != h2
