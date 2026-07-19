"""Tests for pre-revision backup safety."""

import tempfile
from pathlib import Path

from shenbi.pipeline.chapter_loop import _create_pre_revision_backup


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
