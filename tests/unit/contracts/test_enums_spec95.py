"""spec #95 T1: 枚举常量单源——gate/lint/context_assemble 共读 (R1 斜杠病根).

单值铁律: 斜杠分组形是 SKILL 教错模型的形态 (R1), 常量域只收单值;
斜杠/多值在场由 gate 锚尾判定拒 (G4.cp.invalid_chapter_role).
"""

from __future__ import annotations

from shenbi.contracts.enums import (
    CHAPTER_ROLE_VALUES,
    CHECK_ENUM_REGISTRY,
    GOLDEN_LINE_VALUES,
)


def test_chapter_role_values_single_only() -> None:
    assert CHAPTER_ROLE_VALUES == ("高潮", "兑现", "推进", "转折", "过渡", "铺垫")
    assert all("/" not in v for v in CHAPTER_ROLE_VALUES)  # 单值铁律（禁斜杠分组形）


def test_golden_line_values_cover_current_regex_domain() -> None:
    # 现 chapter_planning.py:125 只编码 燃；GOLDEN_LINE_VALUES 至少含 燃/静（R3 冷三连用 静）
    assert {"燃", "静"}.issubset(set(GOLDEN_LINE_VALUES))


def test_check_enum_registry_covers_chapter_role() -> None:
    assert "cp.chapter_role" in CHECK_ENUM_REGISTRY
    const_name, skill_rel = CHECK_ENUM_REGISTRY["cp.chapter_role"]
    assert const_name == "CHAPTER_ROLE_VALUES"
    assert skill_rel == "skills/shenbi-chapter-planning/SKILL.md"
