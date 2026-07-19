"""Tests for staging cleanup in auto-commit paths."""

import tempfile
from pathlib import Path

from shenbi.pipeline.checkpoint import clear_staging, commit_staging, staging_path


def test_clear_staging_removes_directory():
    """clear_staging removes the entire staging directory."""
    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)
        staging_dir = project_dir / "staging"
        staging_dir.mkdir()
        (staging_dir / "test.txt").write_text("data")

        clear_staging(project_dir)

        assert not staging_dir.exists()


def test_clear_staging_handles_missing_directory():
    """clear_staging does not crash when staging doesn't exist."""
    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)

        # Should not raise
        clear_staging(project_dir)


def test_commit_then_clear_leaves_no_staging():
    """commit_staging + clear_staging = clean state."""
    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)

        # Simulate: skill writes to staging
        staging_plan = staging_path(project_dir, "plans/chapter-5-plan.md")
        staging_plan.parent.mkdir(parents=True)
        staging_plan.write_text("# Chapter 5 Plan")

        # Commit
        commit_staging(project_dir, ["plans/chapter-5-plan.md"])
        final_path = project_dir / "plans" / "chapter-5-plan.md"
        assert final_path.exists()

        # Clear
        clear_staging(project_dir)

        staging_dir = project_dir / "staging"
        assert not staging_dir.exists()


def test_clear_staging_handles_nested_directories():
    """clear_staging removes nested staging directories."""
    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)
        staging_dir = project_dir / "staging"
        staging_dir.mkdir()
        nested = staging_dir / "plans" / "nested"
        nested.mkdir(parents=True)
        (nested / "file.md").write_text("content")

        clear_staging(project_dir)

        assert not staging_dir.exists()
