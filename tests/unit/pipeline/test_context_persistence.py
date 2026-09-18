"""Tests for context file persistence (Plan 07, Task 1 — Gap 1 fix).

Verifies that ``_run_context_assembly`` always leaves a non-empty context
file on disk, even when the upstream ``assemble_context`` function throws.
"""

import tempfile
from pathlib import Path
from unittest.mock import patch

from shenbi.pipeline.chapter_loop import _run_context_assembly


def test_context_file_written_on_assembly():
    """Context file must exist and be non-empty after assembly."""
    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)
        (project_dir / "plans").mkdir(parents=True)
        (project_dir / "context").mkdir(parents=True)
        (project_dir / "truth").mkdir(parents=True)

        # Write a minimal plan so assemble_context can read it
        (project_dir / "plans" / "chapter-1-plan.md").write_text(
            "# Plan\nchapter_role: opening\n", encoding="utf-8"
        )
        # Provide Route C files so the package is non-empty
        (project_dir / "truth" / "book_spine.md").write_text(
            "# Book Spine\nThis is the book spine.\n", encoding="utf-8"
        )

        _run_context_assembly(project_dir, 1)

        context_file = project_dir / "context" / "chapter-1-context.md"
        assert context_file.exists(), f"Context file not created at {context_file}"
        content = context_file.read_text(encoding="utf-8")
        assert len(content) > 0, "Context file empty"


def test_context_file_fallback_written_when_assembly_throws():
    """When assemble_context raises, a minimal fallback context MUST still be written."""
    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)
        (project_dir / "plans").mkdir(parents=True)
        (project_dir / "context").mkdir(parents=True)
        (project_dir / "plans" / "chapter-1-plan.md").write_text("# Plan\n")

        # Force assemble_context to raise
        with patch(
            "shenbi.pipeline.context_assemble.assemble_context",
            side_effect=RuntimeError("boom"),
        ):
            _run_context_assembly(project_dir, 1)

        context_file = project_dir / "context" / "chapter-1-context.md"
        assert context_file.exists(), (
            "Fallback context must be written when assembly throws "
            "(spec §3.1 Gap 1: error-swallowing try/except must add post-check + fallback)"
        )
