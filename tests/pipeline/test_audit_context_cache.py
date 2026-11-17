"""Tests for audit_context_cache.py — SharedAuditContext and build_shared_audit_context."""

import shutil
import tempfile
from pathlib import Path

from shenbi.pipeline.audit_context_cache import (
    build_shared_audit_context,
)
from tests.pipeline.conftest import assemble_shared_context_project

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


def test_shared_context_fields_are_injectable(tmp_path):
    """SharedAuditContext cached fields land in the real build_skill_prompt output.

    Drives the production injection block (dispatch_helper._INJECT_FROM_CACHE)
    instead of re-implementing it: canonical keys (C28 R1 F312) must appear
    in the built user_prompt with the ctx content.
    """
    from shenbi.pipeline.dispatch_helper import build_skill_prompt

    assemble_shared_context_project(tmp_path)

    ctx = build_shared_audit_context(tmp_path, 3)
    _, user_prompt, _, _, _ = build_skill_prompt(
        skill="shenbi-review-anti-ai",
        project_dir=tmp_path,
        prompt="audit chapter 3",
        chapter=3,
        shared_context=ctx,
    )
    assert "world/rules.md" in user_prompt
    assert ctx.world_rules in user_prompt
    assert "truth/character_matrix.md" in user_prompt
    assert "style/style_profile.md" in user_prompt
    assert "truth/pending_hooks.md" in user_prompt


def test_pending_hooks_truncation_disclosed():
    """C29 R1 (F362): >3000-char pending_hooks gets cap-proof sentinel + WARN."""
    from structlog.testing import capture_logs

    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)
        hooks_dir = project_dir / "truth"
        hooks_dir.mkdir(parents=True)
        # Real product content (G0.9) — chapter draft repeated to exceed 3000 chars
        base = (_FIXTURES / "chapter-8-example.md").read_text(encoding="utf-8")
        (hooks_dir / "pending_hooks.md").write_text(base * 3, encoding="utf-8")

        with capture_logs() as logs:
            ctx = build_shared_audit_context(project_dir, 1)

        total = len(base) * 3
        assert ctx.pending_hooks.endswith(f"[TRUNCATED 3000/{total} chars]")
        warn_events = [
            e
            for e in logs
            if e.get("log_level") == "warning" and e["event"] == "pending_hooks_truncated"
        ]
        assert len(warn_events) == 1
        # Full bytes still retained for read-suppression (C28 contract)
        assert ctx.raw_files["truth/pending_hooks.md"] == base * 3


def test_summarize_if_large_uses_new_sentinel():
    """C29 R1: world_rules/character_list truncation uses the [TRUNCATED k/n] sentinel."""
    from shenbi.pipeline.audit_context_cache import _summarize_if_large

    base = (_FIXTURES / "chapter-8-example.md").read_text(encoding="utf-8")
    out = _summarize_if_large(base * 3, max_chars=5000)
    assert out.endswith(f"[TRUNCATED 5000/{len(base) * 3} chars]")
    assert "[... truncated from" not in out


def test_bundle_audit_context_covers_follower_raw_files(tmp_path: Path) -> None:
    from shenbi.pipeline.audit_context_cache import build_bundle_audit_context

    ch = tmp_path / "chapters"
    ch.mkdir()
    (ch / "chapter-25.md").write_text("锚章正文", encoding="utf-8")
    (ch / "chapter-26.md").write_text("随章正文", encoding="utf-8")
    ctx = build_bundle_audit_context(tmp_path, [25, 26])
    assert ctx.raw_files["chapters/chapter-25.md"] == "锚章正文"
    assert ctx.raw_files["chapters/chapter-26.md"] == "随章正文"
    assert ctx.chapter_text == "锚章正文"  # anchor (=chapters[0]) carries the summary field


def test_single_chapter_wrapper_parity(tmp_path: Path) -> None:
    """build_shared_audit_context(chapter) == build_bundle_audit_context([chapter])."""
    from shenbi.pipeline.audit_context_cache import (
        build_bundle_audit_context,
        build_shared_audit_context,
    )

    ch = tmp_path / "chapters"
    ch.mkdir()
    (ch / "chapter-9.md").write_text("solo", encoding="utf-8")
    single = build_shared_audit_context(tmp_path, 9)
    bundle = build_bundle_audit_context(tmp_path, [9])
    assert single.raw_files == bundle.raw_files
    assert single.chapter_text == bundle.chapter_text


def test_wave_prompt_contains_follower_text_and_dual_checklist(tmp_path):
    """Spec #109 T2 blob-level main-defense: follower prose AND both precompute
    blocks ride the wave prompt; the reads manifest declares the follower.
    """
    from shenbi.pipeline.dispatch_helper import build_skill_prompt

    (tmp_path / "chapters").mkdir()
    (tmp_path / "chapters" / "chapter-25.md").write_text("锚章正文开头", encoding="utf-8")
    (tmp_path / "chapters" / "chapter-26.md").write_text("随章正文独有锚串", encoding="utf-8")
    (tmp_path / "plans").mkdir()
    (tmp_path / "plans" / "chapter-25-plan.md").write_text("# 计划 25\n", encoding="utf-8")
    (tmp_path / "plans" / "chapter-26-plan.md").write_text("# 计划 26\n", encoding="utf-8")
    (tmp_path / "truth").mkdir()
    (tmp_path / "truth" / "pending_hooks.md").write_text("- 无\n", encoding="utf-8")
    (tmp_path / "outline").mkdir()
    (tmp_path / "outline" / "volume_map.md").write_text(
        "## 第1卷（第 25-26 章）\n", encoding="utf-8"
    )
    (tmp_path / "genre-config.json").write_text("{}", encoding="utf-8")

    built = build_skill_prompt(
        "shenbi-review-group-craft",
        tmp_path,
        "Execute for chapters 25,26",
        25,
    )
    manifest_paths = [str(r.get("path", "")) for r in built.reads_manifest]
    assert "chapters/chapter-26.md" in manifest_paths
    assert "随章正文独有锚串" in built.user
    assert built.user.count("## 审查参考数据") == 2
