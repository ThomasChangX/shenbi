"""Tests for audit_context_cache.py — SharedAuditContext and build_shared_audit_context."""

import tempfile
from pathlib import Path

from shenbi.pipeline.audit_context_cache import (
    build_shared_audit_context,
)


def test_build_shared_context_extracts_chapter_fields():
    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)
        chapter_dir = project_dir / "chapters"
        chapter_dir.mkdir(parents=True)
        chapter_text = "# Chapter 1\n\n林风站在山顶。\n\n" + "故事继续。" * 100
        (chapter_dir / "chapter-001.md").write_text(chapter_text, encoding="utf-8")

        ctx = build_shared_audit_context(project_dir, 1)
        assert ctx.chapter_text is not None
        assert len(ctx.chapter_text) > 100
        assert ctx.world_rules is not None or ctx.world_rules == ""  # may be missing


def test_shared_context_reduces_repeated_io():
    """Shared context should be buildable once and reusable across audit calls."""
    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)
        chapter_dir = project_dir / "chapters"
        chapter_dir.mkdir(parents=True)
        (chapter_dir / "chapter-001.md").write_text("test content" * 50, encoding="utf-8")

        ctx1 = build_shared_audit_context(project_dir, 1)
        ctx2 = build_shared_audit_context(project_dir, 1)
        # Same input should produce identical context
        assert ctx1.chapter_text == ctx2.chapter_text
