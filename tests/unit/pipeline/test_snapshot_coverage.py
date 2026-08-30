"""Tests for snapshot coverage and emergency handler via crash_recovery."""

import tempfile
from pathlib import Path

import pytest

from shenbi.pipeline.crash_recovery import (
    _snapshot_chapter_files,
    is_shutdown_requested,
    register_emergency_handlers,
    reset_emergency_state,
)
from shenbi.pipeline.state import PipelineState


@pytest.fixture(autouse=True)
def _reset_crash_state():
    """Prevent cross-test contamination of module-level emergency globals under xdist."""
    reset_emergency_state()


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
