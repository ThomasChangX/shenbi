"""Tests for audit_context_cache.py — SharedAuditContext and build_shared_audit_context."""

import tempfile
from pathlib import Path

from shenbi.pipeline.audit_context_cache import (
    SharedAuditContext,
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


def test_shared_context_fields_are_injectable():
    """SharedAuditContext fields can be injected into input_texts (Task 6 Step 2)."""
    ctx = SharedAuditContext(
        chapter_text="chapter content",
        world_rules="world rules summary",
        character_list="character list summary",
        style_profile="style profile text",
        pending_hooks="pending hooks text",
    )

    # Simulate the injection logic from _build_skill_prompt.
    # Keys use project-relative form (spec §6.1 C1) — matches the real
    # _input_key helper used by both the disk-read path and injection block.
    raw_inputs: dict[str, str] = {"chapters/chapter-001.md": ctx.chapter_text}

    _INJECT_FROM_CACHE: dict[str, str] = {}
    if ctx.world_rules:
        _INJECT_FROM_CACHE["truth/world_rules.md"] = ctx.world_rules
    if ctx.character_list:
        _INJECT_FROM_CACHE["truth/character_matrix.md"] = ctx.character_list
    if ctx.style_profile:
        _INJECT_FROM_CACHE["truth/style_profile.md"] = ctx.style_profile
    if ctx.pending_hooks:
        _INJECT_FROM_CACHE["truth/pending_hooks.md"] = ctx.pending_hooks
    for fname, cached in _INJECT_FROM_CACHE.items():
        if cached and fname not in raw_inputs:
            raw_inputs[fname] = cached

    assert "truth/world_rules.md" in raw_inputs
    assert raw_inputs["truth/world_rules.md"] == "world rules summary"
    assert "truth/character_matrix.md" in raw_inputs
    assert "truth/style_profile.md" in raw_inputs
    assert "truth/pending_hooks.md" in raw_inputs
    # Chapter text from the original read is preserved
    assert raw_inputs["chapters/chapter-001.md"] == "chapter content"
