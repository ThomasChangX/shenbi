"""Trigger-table routing assertions (spec #59 T4; acceptance 1/2)."""

from __future__ import annotations

from pathlib import Path

import pytest

SKILL_MD = Path(__file__).resolve().parents[2] / "skills" / "using-shenbi" / "SKILL.md"
REPO = Path(__file__).resolve().parents[2]


@pytest.mark.unit
def test_no_deprecated_routed() -> None:
    """Full-text scan (table + default column + Phase list) — zero DEPRECATED names."""
    from shenbi.skill_utils.deprecated import deprecated_skill_names

    dead = deprecated_skill_names(REPO / "skills")
    text = SKILL_MD.read_text(encoding="utf-8")
    hits = [d for d in dead if d in text]
    assert not hits, f"DEPRECATED named in using-shenbi: {hits}"


@pytest.mark.unit
def test_successors_have_rows() -> None:
    text = SKILL_MD.read_text(encoding="utf-8")
    rows = "\n".join(ln for ln in text.splitlines() if ln.startswith("| "))
    for succ in (
        "shenbi-review-group-character",
        "shenbi-review-group-craft",
        "shenbi-review-group-factual",
        "shenbi-review-group-plan",
        "shenbi-foreshadowing-lifecycle",
    ):
        assert succ in rows, succ


@pytest.mark.unit
def test_merged_phrases_survive() -> None:
    """Deleting rows must not delete semantics: user trigger phrases from the
    14 removed rows must survive in the successor rows (plan T4 / review I1).
    """
    text = SKILL_MD.read_text(encoding="utf-8")
    rows = "\n".join(ln for ln in text.splitlines() if ln.startswith("| "))
    for phrase in (
        "检查这章",
        "审计",
        "审查",
        "连贯性",
        "前后矛盾",
        "对不上",
        "角色一致性",
        "人设崩了",
        "OOC",
        "节奏不对",
        "太拖",
        "太赶",
        "节奏检查",
        "伏笔检查",
        "埋线检查",
        "世界观矛盾",
        "设定冲突",
        "世界规则",
        "对话问题",
        "台词",
        "说话方式",
        "动机不合理",
        "为什么这么做",
        "角色动机",
        "视角问题",
        "POV",
        "视角混乱",
        "质感",
        "沉浸感",
        "画面感",
        "吸引力",
        "读不下去",
        "读者",
        "备忘合规",
        "章节备忘检查",
        "计划执行",
        "伏笔",
        "埋线",
        "hook",
        "伏笔追踪",
        "hook状态",
    ):
        assert phrase in rows, phrase
