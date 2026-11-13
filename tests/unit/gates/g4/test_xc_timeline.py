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
    assert any("时间锚回拨" in det for _cid, det in issues)


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
        assert not any("时间锚回拨" in det for _cid, det in issues)


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
        assert not any("时间锚" in det for _cid, det in issues)


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
        assert not any("时间锚回拨" in det for _cid, det in issues)


def test_interest_rate_phrase_not_a_date_anchor():
    # 2026-10-30 ch33 实弹：「一月三分」（月息三分，利率账目对话）被
    # 裸单字日形态+前瞻缺「分」误判为 (1,3) 日期锚——分是利率/钱分单位，
    # 从不作日字位
    from shenbi.gates.g4.cross_chapter import normalize_anchor

    assert normalize_anchor("「一月三分。」", 1) is None
    assert normalize_anchor("「一月三分，一斗粮压一个月。」他说。", 1) is None
    assert normalize_anchor("月息三分，四个月一百四十四文。", 1) is None


@pytest.mark.unit
def test_roster_counts_before_pause_punct_are_not_bare_days() -> None:
    """束4 ch42 实弹（2026-11-05）：名册计数「船工十二，」「加护卫二十三；」
    被裸十X/廿X 日形态捕获，carry 月后伪成 (2,12)/(2,23)——前章末锚被推到
    未来，令 ch43 真锚二月初五 误判回拨（伪回拨案根因位）。顿断标点
    （，、；。）前的裸十X/廿X 是计数位，不是日期；初X 形与「二十三那天」
    类非标点后续形保留。
    """
    from shenbi.gates.g4.cross_chapter import (
        _BARE_DAY_INITIAL_RE,
        chapter_last_anchor,
        normalize_anchor,
    )

    # 束4 实弹行（ch42:140/:142 原文）——计数位不再成锚
    assert normalize_anchor("船工十二，厨上二，带路一，护卫四。", 2) is None
    assert (
        normalize_anchor("读第二遍数人数，十九个，加护卫二十三；读第三遍，只看带路那一栏。", 2)
        is None
    )
    # 算术计数（ch17 历史形）：三十六加三十二，六十八
    assert normalize_anchor("他又核了一遍：三十六加三十二，六十八。", 2) is None
    # 价目计数（ch2 历史形）：一张十五，两张二十五
    assert normalize_anchor("「一张十五，两张二十五。」他把钱袋掂了掂。", 2) is None
    # 初X 形不受限（「初」为日位专名）——顿断标点后随仍成锚
    assert normalize_anchor("到了初十，雪没停。", 12) == (12, 10)
    assert _BARE_DAY_INITIAL_RE.search("到了初十，雪没停。") is not None
    # 「二十三那天」非标点后续形保留（真裸日引用）
    assert normalize_anchor("船是二十三那天开的。", 2) == (2, 23)
    # 前章末锚面：ch42 实弹全文形态——末锚回到 (2,4)（二月初四 真锚）
    prev = "二月初四，天刚亮，站门口来了三个人。\n……\n首航人手名册贴在墙上：船工十二，厨上二，带路一，护卫四。\n他读第二遍数人数，十九个，加护卫二十三；读第三遍，只看带路那一栏。\n"
    assert chapter_last_anchor(prev) == (2, 4)


def test_bare_tens_regex_shape_punct_guard() -> None:
    # 形状钉：十X/廿X 裸形态带标点守卫，初X 形无标点守卫（族分裂不变量）
    from shenbi.gates.g4.cross_chapter import _BARE_DAY_INITIAL_RE, _BARE_DAY_RE

    assert _BARE_DAY_RE.search("护卫二十三；") is None
    assert _BARE_DAY_RE.search("船工十二，") is None
    assert _BARE_DAY_RE.search("到了十七。") is None
    assert _BARE_DAY_RE.search("廿三，辰时") is None
    # 非标点后续保留
    assert _BARE_DAY_RE.search("船是二十三那天开的。") is not None
    assert _BARE_DAY_RE.search("过了廿三才动身") is not None
    assert _BARE_DAY_INITIAL_RE.search("初十，") is not None


@pytest.mark.unit
def test_counting_unit_gen_after_tens_not_bare_day() -> None:
    """束5 ch44 实弹（2026-11-06）：算筹计数「第二十三根/二十四根」被裸日
    形态误锚 (2,23)/(2,24)——ch44 末锚被推到未来，ch45 真锚二月初六 误判
    回拨。根=计数单位（日字位从不后接），入 _UNIT_LOOKAHEAD（石/分 同例）。
    """
    from shenbi.gates.g4.cross_chapter import chapter_last_anchor, normalize_anchor

    assert normalize_anchor("数着收：一、二、三……二十四。第二十三根短了一截。", 2) is None
    assert normalize_anchor("归的时候数了一遍，二十四根，一根没少。", 2) is None
    assert normalize_anchor("一遍二十二根，一根三文。", 2) is None
    # ch44 实弹全文形态：末锚回到真值 (2,5)（二月初五夜）
    prev = (
        "二月初五夜，站房只余他这一间点灯。\n"
        "削完他数了一遍：二十四根。\n"
        "他把算筹一根一根收进布袋。第二十三根短了一截。\n"
    )
    assert chapter_last_anchor(prev) == (2, 5)
