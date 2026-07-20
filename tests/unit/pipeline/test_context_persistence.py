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


def test_curated_context_written_on_curation():
    """Curated context MUST be written to disk (Gap 2 fix)."""
    from shenbi.pipeline.chapter_loop import _run_context_curation

    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)
        (project_dir / "context").mkdir(parents=True)
        (project_dir / "chapters").mkdir(parents=True)

        # curate_context returns a string; ensure it gets persisted
        with patch(
            "shenbi.pipeline.context_curation.curate_context",
            return_value="## Curated\n\nSection body.\n",
        ):
            _run_context_curation(project_dir, 1)

        curated_file = project_dir / "context" / "chapter-1-curated.md"
        assert curated_file.exists(), (
            "Curated context must be written to disk (spec §3.1 Gap 2: "
            "curate_context output was previously computed and discarded)"
        )
        assert "Section body" in curated_file.read_text(encoding="utf-8")


def test_curated_context_uses_safe_write():
    """Curation persistence must go through safe_write (atomic + locked)."""
    from shenbi.pipeline.chapter_loop import _run_context_curation

    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)
        (project_dir / "context").mkdir(parents=True)
        (project_dir / "chapters").mkdir(parents=True)

        with (
            patch(
                "shenbi.pipeline.context_curation.curate_context",
                return_value="curated body",
            ),
            patch("shenbi.safe_write.safe_write") as mock_sw,
        ):
            _run_context_curation(project_dir, 2)
            assert mock_sw.called, "safe_write must be used to persist curated context"
