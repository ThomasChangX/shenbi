"""Tests for snapshot coverage and emergency handler."""

import tempfile
from pathlib import Path

from shenbi.pipeline.chapter_loop import (
    _do_emergency_snapshot,
    _register_emergency_snapshot,
    _should_generate_starting_snapshot,
    _update_emergency_checkpoint,
)


def test_starting_snapshot_triggers_at_ch1_step0():
    """Starting snapshot triggers at chapter 1, step index 0."""
    assert _should_generate_starting_snapshot(current_chapter=1, step_index=0) is True


def test_starting_snapshot_does_not_trigger_at_ch2():
    """No starting snapshot at chapter 2."""
    assert _should_generate_starting_snapshot(current_chapter=2, step_index=0) is False


def test_starting_snapshot_does_not_trigger_at_ch1_step1():
    """No starting snapshot mid-chapter."""
    assert _should_generate_starting_snapshot(current_chapter=1, step_index=5) is False


def test_starting_snapshot_triggers_at_ch2_when_ch1_missing():
    """Self-heal: triggers at Ch2 step 0 if Ch1 snapshot is missing."""
    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)
        snapshots_dir = project_dir / "snapshots"
        snapshots_dir.mkdir(parents=True)
        # No chapter-1 snapshot exists

        assert (
            _should_generate_starting_snapshot(
                current_chapter=2, step_index=0, project_dir=project_dir
            )
            is True
        )


def test_starting_snapshot_skips_when_ch1_snapshot_exists():
    """No starting snapshot at Ch2 step 0 if Ch1 snapshot exists."""
    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)
        snapshots_dir = project_dir / "snapshots"
        snapshots_dir.mkdir(parents=True)
        # Create a chapter-1 snapshot marker
        (snapshots_dir / "chapter-1-snapshot.md").write_text("# snapshot")

        assert (
            _should_generate_starting_snapshot(
                current_chapter=2, step_index=0, project_dir=project_dir
            )
            is False
        )


def test_emergency_snapshot_registered():
    """Emergency snapshot handler can be registered without error."""
    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)

        # Should not raise (installs signal handlers + atexit backstop)
        _register_emergency_snapshot(project_dir, chapter=5)


def test_emergency_checkpoint_tracks_latest_chapter():
    """Checkpoint-on-step updates the emergency target to the latest chapter."""
    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)
        _register_emergency_snapshot(project_dir, chapter=1)
        # Simulate the loop advancing through chapters
        _update_emergency_checkpoint(project_dir, chapter=56)

        import shenbi.pipeline.chapter_loop as cl

        assert cl._emergency_snapshot_chapter == 56
        assert cl._emergency_snapshot_project_dir == project_dir


def test_do_emergency_snapshot_uses_latest_checkpoint():
    """The snapshot helper reads the checkpoint-on-step state, not init state."""
    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)
        (project_dir / "chapters").mkdir()
        (project_dir / "chapters" / "chapter-56.md").write_text("# Ch56")
        _register_emergency_snapshot(project_dir, chapter=1)
        _update_emergency_checkpoint(project_dir, chapter=56)

        # Must not raise; best-effort snapshot of chapter 56 (not chapter 1)
        _do_emergency_snapshot()
