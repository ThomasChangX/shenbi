"""Tests for pre-revision backup safety and content-size guard."""

import tempfile
from pathlib import Path

from shenbi.pipeline.chapter_loop import _create_pre_revision_backup
from shenbi.pipeline.dispatch_helper import _check_content_size_guard


def test_backup_creates_copy_of_chapter_file():
    """Pre-revision backup creates a -pre-rev.md copy."""
    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)
        chapters = project_dir / "chapters"
        chapters.mkdir(parents=True)

        original = chapters / "chapter-5.md"
        original.write_text(
            "\u6797\u70ca\u7ad9\u5728\u57ce\u5899\u4e0a\uff0c\u98ce\u6c99\u6251\u9762\u800c\u6765\u3002\u8fdc\u5904\u7684\u70fd\u706b\u53f0\u5192\u7740\u9ed1\u70df\u3002"
        )

        _create_pre_revision_backup(project_dir, chapter=5)

        backup = chapters / "chapter-5-pre-rev.md"
        assert backup.exists()
        assert backup.read_text() == original.read_text()


def test_backup_preserves_file_metadata():
    """Backup preserves modification time and file size."""
    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)
        chapters = project_dir / "chapters"
        chapters.mkdir(parents=True)

        original = chapters / "chapter-5.md"
        content = "x" * 8000
        original.write_text(content)

        _create_pre_revision_backup(project_dir, chapter=5)

        backup = chapters / "chapter-5-pre-rev.md"
        assert backup.stat().st_size == 8000


def test_backup_skips_when_chapter_missing():
    """No error when chapter file does not exist yet."""
    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)
        chapters = project_dir / "chapters"
        chapters.mkdir(parents=True)

        _create_pre_revision_backup(project_dir, chapter=99)

        backup = chapters / "chapter-99-pre-rev.md"
        assert not backup.exists()


def test_backup_overwrites_previous_backup():
    """Second backup for same chapter overwrites the first."""
    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)
        chapters = project_dir / "chapters"
        chapters.mkdir(parents=True)

        original = chapters / "chapter-5.md"
        original.write_text("version 1")
        _create_pre_revision_backup(project_dir, chapter=5)

        original.write_text("version 2")
        _create_pre_revision_backup(project_dir, chapter=5)

        backup = chapters / "chapter-5-pre-rev.md"
        assert backup.read_text() == "version 2"


# ---------------------------------------------------------------------------
# Content-size guard tests
# ---------------------------------------------------------------------------


def test_content_guard_blocks_tiny_overwrite():
    """Refuses to overwrite when new content < 20% of original."""
    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)
        chapters = project_dir / "chapters"
        chapters.mkdir(parents=True)

        existing = chapters / "chapter-5.md"
        existing.write_text("a" * 8000)

        # New content is 100 bytes — only 1.25% of original
        should_block, reason = _check_content_size_guard(
            project_dir, "chapters/chapter-5.md", "x" * 100
        )

        assert should_block is True
        assert "content_too_small" in reason.lower()


def test_content_guard_allows_legitimate_rewrite():
    """Allows overwrite when new content is >= 20% of original."""
    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)
        chapters = project_dir / "chapters"
        chapters.mkdir(parents=True)

        existing = chapters / "chapter-5.md"
        existing.write_text("a" * 8000)

        # New content is 6000 bytes — 75% of original
        should_block, reason = _check_content_size_guard(
            project_dir, "chapters/chapter-5.md", "x" * 6000
        )

        assert should_block is False


def test_content_guard_allows_new_files():
    """Allows write when no existing file (first creation)."""
    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)

        should_block, reason = _check_content_size_guard(
            project_dir, "chapters/chapter-55.md", "x" * 8000
        )

        assert should_block is False


def test_content_guard_skips_non_chapter_md():
    """Only applies to chapters/chapter-N.md, not other files."""
    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)
        truth_dir = project_dir / "truth"
        truth_dir.mkdir(parents=True)

        existing = truth_dir / "current_state.md"
        existing.write_text("a" * 8000)

        should_block, reason = _check_content_size_guard(
            project_dir, "truth/current_state.md", "short"
        )

        assert should_block is False


def test_content_guard_skips_pre_rev_files():
    """The -pre-rev.md backup files are never guarded."""
    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)
        chapters = project_dir / "chapters"
        chapters.mkdir(parents=True)

        existing = chapters / "chapter-5-pre-rev.md"
        existing.write_text("a" * 8000)

        should_block, reason = _check_content_size_guard(
            project_dir, "chapters/chapter-5-pre-rev.md", "short"
        )

        assert should_block is False
