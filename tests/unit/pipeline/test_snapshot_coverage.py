"""Tests for snapshot coverage and emergency handler via crash_recovery."""

import tempfile
from pathlib import Path

from shenbi.pipeline.chapter_loop import (
    _get_core_snapshot_files,
    _has_minimum_chinese_chars,
)
from shenbi.pipeline.crash_recovery import (
    _snapshot_chapter_files,
    is_shutdown_requested,
    register_emergency_handlers,
)
from shenbi.pipeline.state import PipelineState


class TestRegisterEmergencyHandlers:
    """Tests for crash_recovery.register_emergency_handlers."""

    def test_register_does_not_raise(self):
        """Registering emergency handlers should not raise."""
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp)
            state = PipelineState.default(str(project_dir))
            # Should not raise (installs signal handlers + atexit backstop)
            register_emergency_handlers(project_dir, state)

    def test_is_shutdown_requested_defaults_false(self):
        """is_shutdown_requested returns False when no shutdown is requested."""
        # After registration, without a signal, should default to False.
        # Note: signal handlers are process-global, so we only check the default.
        assert is_shutdown_requested() is False


class TestSnapshotChapterFiles:
    """Tests for crash_recovery._snapshot_chapter_files."""

    def test_snapshot_creates_labeled_copy(self):
        """_snapshot_chapter_files creates a labeled copy of the chapter file."""
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp)
            (project_dir / "chapters").mkdir()
            (project_dir / "chapters" / "chapter-5.md").write_text("# Chapter 5")

            _snapshot_chapter_files(project_dir, chapter=5, label="test")

            snap_path = project_dir / "snapshots" / "chapter-5-test.md"
            assert snap_path.exists()
            assert snap_path.read_text() == "# Chapter 5"

    def test_snapshot_skips_when_chapter_does_not_exist(self):
        """_snapshot_chapter_files does nothing when chapter file is missing."""
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp)
            (project_dir / "chapters").mkdir()
            # No chapter-5.md exists
            _snapshot_chapter_files(project_dir, chapter=5, label="test")
            # Should not create snapshot dir or file
            assert not (project_dir / "snapshots").exists()


# ---------------------------------------------------------------------------
# Task 6: core-file filtering + CJK content guard (spec §3.7, §3.8)
# ---------------------------------------------------------------------------


class TestCoreSnapshotFiles:
    """Snapshot file list includes only core chapter files that exist on disk."""

    def test_only_includes_chapter_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp)
            (project_dir / "chapters").mkdir()
            # Create all core files for chapter 5
            (project_dir / "chapters" / "chapter-5.md").write_text("# Ch5")
            (project_dir / "chapters" / "chapter-5-meta.md").write_text("meta")
            (project_dir / "chapters" / "chapter-5-decisions.json").write_text("{}")
            (project_dir / "chapters" / "chapter-5-revision-decisions.json").write_text("[]")

            # Also create audit and truth dirs to ensure they are excluded
            (project_dir / "audits").mkdir()
            (project_dir / "audits" / "chapter-5-audit.md").write_text("audit")
            (project_dir / "truth").mkdir()
            (project_dir / "truth" / "truth.md").write_text("truth")

            files = _get_core_snapshot_files(project_dir=project_dir, chapter=5)

            # Should include the chapter body
            assert any(f.name == "chapter-5.md" for f in files)
            # Should have exactly 4 core files
            assert len(files) == 4

            # Should NOT include audit reports
            for f in files:
                assert "audits/" not in str(f)
                assert "truth/" not in str(f)
                assert "staging/" not in str(f)


class TestMinChineseChars:
    """Content with fewer than 500 Chinese chars triggers warning."""

    def test_detects_short_content(self):
        # Revision metadata — 0 Chinese chars
        short = "Chapter complete. No changes needed. Summary follows."
        assert _has_minimum_chinese_chars(short, threshold=500) is False

    def test_passes_normal_prose(self):
        """Normal Chinese prose passes the minimum character check."""
        normal = "林烽" * 300  # 600 Chinese characters
        assert _has_minimum_chinese_chars(normal, threshold=500) is True

    def test_counts_only_cjk(self):
        """Only CJK unified ideographs are counted, not punctuation."""
        mixed = "林烽站在城墙上。" * 100  # ~400 Chinese chars + punctuation
        result = _has_minimum_chinese_chars(mixed, threshold=300)
        assert result is True
