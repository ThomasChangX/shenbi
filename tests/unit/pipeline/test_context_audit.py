"""Tests for context coverage audit and backfill (Task 6)."""

import tempfile
from pathlib import Path


def test_audit_context_coverage_finds_gaps():
    from shenbi.pipeline.chapter_loop import _audit_context_coverage

    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)
        context_dir = project_dir / "context"
        context_dir.mkdir(parents=True)
        # Create context for chapters 1, 2, 5 only — gaps at 3, 4
        # (real naming: chapter-{ch}-context.md, no zero-padding)
        for ch in [1, 2, 5]:
            (context_dir / f"chapter-{ch}-context.md").write_text("test", encoding="utf-8")

        missing = _audit_context_coverage(project_dir, current_chapter=5)
        assert 3 in missing, f"Chapter 3 should be missing, got {missing}"
        assert 4 in missing, f"Chapter 4 should be missing, got {missing}"
        assert 1 not in missing, "Chapter 1 should not be missing"


def test_audit_context_coverage_all_present():
    """When all chapters have context files, the list should be empty."""
    from shenbi.pipeline.chapter_loop import _audit_context_coverage

    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)
        context_dir = project_dir / "context"
        context_dir.mkdir(parents=True)
        for ch in [1, 2, 3]:
            (context_dir / f"chapter-{ch}-context.md").write_text("test", encoding="utf-8")

        missing = _audit_context_coverage(project_dir, current_chapter=3)
        assert missing == [], f"Expected no gaps, got {missing}"


def test_audit_context_coverage_empty_context_dir():
    """When the context directory is empty, every chapter should be missing."""
    from shenbi.pipeline.chapter_loop import _audit_context_coverage

    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)
        context_dir = project_dir / "context"
        context_dir.mkdir(parents=True)

        missing = _audit_context_coverage(project_dir, current_chapter=3)
        assert missing == [1, 2, 3], f"Expected all chapters missing, got {missing}"
