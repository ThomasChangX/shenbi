"""Spec #100 Task 3: drafting SKILL net-new teaching lock.

Only asserts the NET-NEW phrases (the pre-existing 逐段计数/禁止整段估数
wording is untouched); also asserts no hardcoded project value leaks into the
generic SKILL (chapter_word.default must stay a symbol reference).
"""

from __future__ import annotations

from pathlib import Path

import pytest

SKILL = Path(__file__).resolve().parents[3] / "skills" / "shenbi-chapter-drafting" / "SKILL.md"


@pytest.mark.unit
def test_net_new_teaching_phrases_present() -> None:
    text = SKILL.read_text(encoding="utf-8")
    assert "不得以 PRE 自检行或计划场景预算的总计充作 POST 总计" in text
    assert "POST 必须重新点数" in text
    assert "chapter_word.default" in text  # symbol reference, not a literal
    assert "带下限只是硬底线" in text


@pytest.mark.unit
def test_no_hardcoded_project_value() -> None:
    """Generic SKILL must not freeze the vol1-specific value (3200)."""
    text = SKILL.read_text(encoding="utf-8")
    assert "3200" not in text, "SKILL 硬编码了项目值 3200——应只用 chapter_word.default 符号"
