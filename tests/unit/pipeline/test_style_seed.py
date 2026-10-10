"""Universal default seeding + mechanical injection proof for style_directives.

Session31 Q1: the user asked whether the directives channel is (a) settled in
structure, (b) tested, (c) shipped with a workable universal default. This
file pins all three mechanically: the seed writes-if-absent, never clobbers,
and — the load-bearing assertion — the REAL dispatch prompt-assembly loop
includes the file's content when present and excludes it when absent.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from shenbi.pipeline.style_seed import DEFAULT_STYLE_DIRECTIVES, seed_style_directives

pytestmark = pytest.mark.unit


def test_seed_writes_default_when_absent(tmp_path: Path) -> None:
    assert seed_style_directives(tmp_path) is True
    seeded = tmp_path / "style" / "style_directives.md"
    assert seeded.read_text(encoding="utf-8") == DEFAULT_STYLE_DIRECTIVES
    # the four standard sections ride along
    for section in ("节奏与句法", "意象与修辞", "对白/叙述配比"):
        assert f"## {section}" in DEFAULT_STYLE_DIRECTIVES


def test_seed_never_clobbers_user_edits(tmp_path: Path) -> None:
    target = tmp_path / "style" / "style_directives.md"
    target.parent.mkdir(parents=True)
    target.write_text("# 我的手写目标\n\n- 叙述句 15-25 字\n", encoding="utf-8")

    assert seed_style_directives(tmp_path) is False
    assert "我的手写目标" in target.read_text(encoding="utf-8")


def _drafting_read_tree(project: Path) -> None:
    """Minimal on-disk read set for shenbi-chapter-drafting (chapter=1)."""
    (project / "plans").mkdir(exist_ok=True)
    (project / "plans" / "chapter-1-plan.md").write_text(
        "## 1. 当前任务\n\n开场。\n", encoding="utf-8"
    )
    (project / "context").mkdir(exist_ok=True)
    (project / "context" / "chapter-1-context.md").write_text("ctx", encoding="utf-8")
    (project / "context" / "chapter-1-context-decisions.json").write_text("{}", encoding="utf-8")
    (project / "style").mkdir(exist_ok=True)
    (project / "style" / "style_profile.md").write_text(
        "## 11. 综合画像\n\n短句样本。\n", encoding="utf-8"
    )
    (project / "genre-config.json").write_text("{}", encoding="utf-8")
    (project / "truth").mkdir(exist_ok=True)
    (project / "truth" / "audit_drift.md").write_text("## 共鸣短板\n\n无\n", encoding="utf-8")


def test_dispatch_prompt_includes_directives_when_present(tmp_path: Path) -> None:
    """The wiring proof: a present directives file reaches the LLM prompt."""
    from shenbi.pipeline.dispatch_helper import _build_skill_prompt

    _drafting_read_tree(tmp_path)
    seed_style_directives(tmp_path)

    _, user_prompt, _, _ = _build_skill_prompt(
        "shenbi-chapter-drafting", tmp_path, "write chapter 1", chapter=1
    )
    assert "叙述句目标带：10-20 字/句" in user_prompt, "directives content rides into the prompt"
    assert "文风目标（通用默认模板）" in user_prompt


def test_dispatch_prompt_without_directives_is_unchanged_shape(tmp_path: Path) -> None:
    """Absent file = channel inert (no marker, no error — opt-in by existence)."""
    from shenbi.pipeline.dispatch_helper import _build_skill_prompt

    _drafting_read_tree(tmp_path)

    _, user_prompt, _, _ = _build_skill_prompt(
        "shenbi-chapter-drafting", tmp_path, "write chapter 1", chapter=1
    )
    assert "文风目标" not in user_prompt
    assert "style_directives" not in user_prompt
