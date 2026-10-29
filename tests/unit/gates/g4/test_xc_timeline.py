"""spec #75 T3: timeline anchor monotonicity (prose-derived + [FLASHBACK])."""

from __future__ import annotations

from pathlib import Path

import pytest

from shenbi.gates.g4.cross_chapter import (
    CrossChapterContext,
    check_cross_chapter,
    normalize_anchor,
)

FIX = Path(__file__).resolve().parents[4] / "tests/fixtures/cross-chapter-regression"


@pytest.mark.unit
def test_cn_anchor_normalization() -> None:
    assert normalize_anchor("腊月初十", None) == (12, 10)
    assert normalize_anchor("初十", 12) == (12, 10)  # 无月继承
    assert normalize_anchor("腊月初七", None) == (12, 7)
    assert normalize_anchor("正月十五", None) == (1, 15)
    assert normalize_anchor("老塾师走后第七日", None) is None  # 相对锚白名单外


@pytest.mark.integration
def test_wound3_fixture_ch1_ch2() -> None:
    """Wound 3: ch1 day-10 vs ch2 day-7/8 rollback without marker."""
    issues = check_cross_chapter(
        FIX / "chapters" / "chapter-2.md",
        FIX / "chapters" / "chapter-1.md",
        None,
        CrossChapterContext(),
    )
    assert any("时间锚回拨" in i for i in issues)


@pytest.mark.unit
def test_flashback_marker_exempts() -> None:
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        (d / "chapter-1.md").write_text("他数到腊月十八才停下。", encoding="utf-8")
        (d / "chapter-2.md").write_text("回到腊月初五那天。", encoding="utf-8")
        memo = d / "chapter-2-plan.md"
        memo.write_text(
            "- 时间锚: [回拨]腊月初五\n- 余额: 12文\n- POV: 他\n"
            "- 场景1: 1900字｜独立型｜收束钩：x\n",
            encoding="utf-8",
        )
        issues = check_cross_chapter(
            d / "chapter-2.md", d / "chapter-1.md", memo, CrossChapterContext()
        )
        assert not any("时间锚回拨" in i for i in issues)


@pytest.mark.unit
def test_monotonic_forward_passes() -> None:
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        (d / "chapter-1.md").write_text("他数到腊月初十才停下。", encoding="utf-8")
        (d / "chapter-2.md").write_text("到了腊月十五，雪停了。", encoding="utf-8")
        issues = check_cross_chapter(
            d / "chapter-2.md", d / "chapter-1.md", None, CrossChapterContext()
        )
        assert not any("时间锚" in i for i in issues)


@pytest.mark.unit
def test_quantity_units_are_not_bare_days() -> None:
    """Regen v3 XC false positive: the 一十 inside 一百一十石 (110 dan of
    grain) was bare-day-anchored to (11,10), which then flagged ch11's real
    anchor 十一月初三 as a time rollback. Digits followed by a quantity unit
    (石/文/两/斗/升/钱/匹...) are amounts, not dates.
    """
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        (d / "chapter-10.md").write_text(
            "「三十四个人，一百一十石。」他答。库里还剩十七文，差七两二钱。三十升豆。",
            encoding="utf-8",
        )
        (d / "chapter-11.md").write_text("十一月初三，雪。他在页边写下一行。", encoding="utf-8")
        issues = check_cross_chapter(
            d / "chapter-11.md", d / "chapter-10.md", None, CrossChapterContext()
        )
        assert not any("时间锚回拨" in i for i in issues)


def test_interest_rate_phrase_not_a_date_anchor():
    # 2026-10-30 ch33 实弹：「一月三分」（月息三分，利率账目对话）被
    # 裸单字日形态+前瞻缺「分」误判为 (1,3) 日期锚——分是利率/钱分单位，
    # 从不作日字位
    from shenbi.gates.g4.cross_chapter import normalize_anchor

    assert normalize_anchor("「一月三分。」", 1) is None
    assert normalize_anchor("「一月三分，一斗粮压一个月。」他说。", 1) is None
    assert normalize_anchor("月息三分，四个月一百四十四文。", 1) is None
