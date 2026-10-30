"""spec #82 T1 (Task 5): quote anchoring + proxy sliding window."""

from __future__ import annotations

from pathlib import Path

import pytest

from shenbi.gates.g4.quote_verbatim import (
    extract_anchor_quotes,
    quote_in_chapter,
    strip_to_prose,
)

FIX = Path(__file__).resolve().parents[3] / "fixtures" / "spec82"

CH1 = (FIX / "chapters" / "chapter-1.md").read_text(encoding="utf-8")
CH6 = (FIX / "chapters" / "chapter-6.md").read_text(encoding="utf-8")


@pytest.mark.unit
def test_strip_to_prose_removes_meta() -> None:
    prose = strip_to_prose(
        "<!--SCENE-->\n正文一句。\n<!--META-BEGIN-->\nPOST 引句\n<!--META-END-->\n<!--SCENE-->\n尾段。\n"
    )
    assert "POST" not in prose
    assert "正文一句。" in prose and "尾段。" in prose


@pytest.mark.unit
def test_ch6_quote_present_in_prose() -> None:
    # #83 evidence: ch6 POST claims「册子认得人」— the prose has it
    assert quote_in_chapter("册子认得人", CH6)


@pytest.mark.unit
def test_ch1_meta_only_quote_absent_from_prose() -> None:
    # #83 evidence: ch1 POST 引句 exists only inside the META block
    assert quote_in_chapter("却不知道明天城就破了", CH1) is False


@pytest.mark.unit
def test_extract_anchor_quotes_v4_form() -> None:
    memo = "章尾张力拍: 大｜『他数到第三遍，门被推开一半。』\n"
    assert extract_anchor_quotes(memo) == [("大", "他数到第三遍，门被推开一半。")]
    assert extract_anchor_quotes("plan_format: v3\n章尾张力拍: 章＋形态\n") == []


@pytest.mark.unit
def test_anchor_quote_verdict_e2e(tmp_path: Path) -> None:
    """v4 memo's anchored quote replayed against the real ch6 prose."""
    from shenbi.gates.g4.chapter_drafting import g4_chapter_drafting

    d = tmp_path
    (d / "plans").mkdir()
    (d / "chapters").mkdir()
    (d / "plans" / "chapter-6-plan.md").write_text(
        "plan_format: v4\n章尾张力拍: 章｜『册子认得人』\n", encoding="utf-8"
    )
    (d / "chapters" / "chapter-6.md").write_text(CH6, encoding="utf-8")
    import json

    result = json.loads(
        g4_chapter_drafting([str(d / "chapters" / "chapter-6.md")], rd=str(d), project_dir=str(d))
    )
    assert not any("quote_verbatim" in m for m in result["must_fix"])

    # flipped: anchored quote that the prose does not carry
    (d / "plans" / "chapter-6-plan.md").write_text(
        "plan_format: v4\n章尾张力拍: 章｜『不存在的引句断言』\n", encoding="utf-8"
    )
    result = json.loads(
        g4_chapter_drafting([str(d / "chapters" / "chapter-6.md")], rd=str(d), project_dir=str(d))
    )
    assert any("quote_verbatim" in m for m in result["must_fix"])
