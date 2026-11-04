"""Spec #95 T1: gate-vocab <-> prompt contract lint (red/green).

Red: slash-grouping / missing per-value lines / missing anchor template.
Green: the rewritten SKILL passes fully.
"""

from __future__ import annotations

import pytest


@pytest.fixture()
def values() -> tuple[str, ...]:
    from shenbi.contracts.enums import CHAPTER_ROLE_VALUES

    return CHAPTER_ROLE_VALUES


def test_current_skill_passes_after_rewrite(values: tuple[str, ...]) -> None:
    from tools.lint_gate_prompt_contract import lint_skill

    findings = lint_skill(
        "cp.chapter_role",
        "CHAPTER_ROLE_VALUES",
        "skills/shenbi-chapter-planning/SKILL.md",
        "chapter_role",
        values,
    )
    assert findings == [], findings


def test_slash_grouping_flagged(tmp_path, monkeypatch, values: tuple[str, ...]) -> None:
    import tools.lint_gate_prompt_contract as mod

    body = (
        "只许单值\n- 高潮\n- 兑现\n- 推进\n- 转折\n- 过渡\n- 铺垫\n"
        "chapter_role: 推进\n至第N卷·KRn\n- → defer 至第2卷·KR3\n"
        "但旧写法仍教 `chapter_role: 高潮/兑现`。\n"
    )
    f = tmp_path / "SKILL.md"
    f.write_text(body, encoding="utf-8")
    monkeypatch.setattr(mod, "REPO_ROOT", tmp_path)
    findings = mod.lint_skill(
        "cp.chapter_role", "CHAPTER_ROLE_VALUES", f.name, "chapter_role", values
    )
    assert any("斜杠分组教学形" in x for x in findings)


def test_missing_value_line_and_exemplar_flagged(
    tmp_path, monkeypatch, values: tuple[str, ...]
) -> None:
    import tools.lint_gate_prompt_contract as mod

    body = "只许单值\n- 高潮\n- 推进\n（缺其余值行、缺正例、缺锚模板）\n"
    f = tmp_path / "SKILL.md"
    f.write_text(body, encoding="utf-8")
    monkeypatch.setattr(mod, "REPO_ROOT", tmp_path)
    findings = mod.lint_skill(
        "cp.chapter_role", "CHAPTER_ROLE_VALUES", f.name, "chapter_role", values
    )
    assert any("逐行清单缺值行" in x for x in findings)
    assert any("最小正例行" in x for x in findings)
    assert any("defer" in x for x in findings)
