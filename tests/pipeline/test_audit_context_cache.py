"""Tests for audit_context_cache.py — SharedAuditContext and build_shared_audit_context."""

import shutil
import tempfile
from pathlib import Path

from shenbi.pipeline.audit_context_cache import (
    SharedAuditContext,
    build_shared_audit_context,
)

_FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def test_build_shared_context_extracts_chapter_fields():
    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)
        chapter_dir = project_dir / "chapters"
        chapter_dir.mkdir(parents=True)
        # Real product (G0.9); production writers use unpadded chapter-N.md
        # (C28 R1 fixed the zero-padded dead key).
        shutil.copy(_FIXTURES / "chapter-8-example.md", chapter_dir / "chapter-1.md")

        ctx = build_shared_audit_context(project_dir, 1)
        assert ctx.chapter_text is not None
        assert len(ctx.chapter_text) > 100
        assert ctx.raw_files["chapters/chapter-1.md"] == ctx.chapter_text
        assert ctx.world_rules is not None or ctx.world_rules == ""  # may be missing


def test_shared_context_reduces_repeated_io():
    """Shared context should be buildable once and reusable across audit calls."""
    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)
        chapter_dir = project_dir / "chapters"
        chapter_dir.mkdir(parents=True)
        shutil.copy(_FIXTURES / "chapter-8-example.md", chapter_dir / "chapter-1.md")

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

    # Simulate the injection logic from _build_skill_prompt with the
    # CANONICAL keys (C28 R1 F312 fix: world/rules.md + style/style_profile.md
    # — the old truth/* keys were phantoms that never matched a real read).
    raw_inputs: dict[str, str] = {"chapters/chapter-1.md": ctx.chapter_text}

    _INJECT_FROM_CACHE: dict[str, str] = {}
    if ctx.world_rules:
        _INJECT_FROM_CACHE["world/rules.md"] = ctx.world_rules
    if ctx.character_list:
        _INJECT_FROM_CACHE["truth/character_matrix.md"] = ctx.character_list
    if ctx.style_profile:
        _INJECT_FROM_CACHE["style/style_profile.md"] = ctx.style_profile
    if ctx.pending_hooks:
        _INJECT_FROM_CACHE["truth/pending_hooks.md"] = ctx.pending_hooks
    for fname, cached in _INJECT_FROM_CACHE.items():
        if cached and fname not in raw_inputs:
            raw_inputs[fname] = cached

    assert "world/rules.md" in raw_inputs
    assert raw_inputs["world/rules.md"] == "world rules summary"
    assert "truth/character_matrix.md" in raw_inputs
    assert "style/style_profile.md" in raw_inputs
    assert "truth/pending_hooks.md" in raw_inputs
    # Chapter text from the original read is preserved
    assert raw_inputs["chapters/chapter-1.md"] == "chapter content"
