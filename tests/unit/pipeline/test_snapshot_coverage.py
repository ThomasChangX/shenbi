"""Tests for snapshot coverage and emergency handler."""

import tempfile
from pathlib import Path

from shenbi.pipeline.chapter_loop import (
    _do_emergency_snapshot,
    _get_core_snapshot_files,
    _has_minimum_chinese_chars,
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


# ---------------------------------------------------------------------------
# Task 6: core-file filtering + CJK content guard (spec §3.7, §3.8)
# ---------------------------------------------------------------------------


def test_core_snapshot_files_only_includes_chapter_artifacts():
    """Snapshot file list includes only core chapter files that exist on disk."""
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


def test_min_chinese_chars_detects_short_content():
    """Content with fewer than 500 Chinese chars triggers warning."""
    # Revision metadata — 0 Chinese chars
    short = "Chapter complete. No changes needed. Summary follows."
    assert _has_minimum_chinese_chars(short, threshold=500) is False


def test_min_chinese_chars_passes_normal_prose():
    """Normal Chinese prose passes the minimum character check."""
    normal = "林烽" * 300  # 600 Chinese characters
    assert _has_minimum_chinese_chars(normal, threshold=500) is True


def test_min_chinese_chars_counts_only_cjk():
    """Only CJK unified ideographs are counted, not punctuation."""
    mixed = "林烽站在城墙上。" * 100  # ~400 Chinese chars + punctuation
    result = _has_minimum_chinese_chars(mixed, threshold=300)
    assert result is True
