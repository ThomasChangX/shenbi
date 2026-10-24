"""spec #70 release-split unit tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from tools.release_split import (
    CHAPTER_FILE_RE,
    TIERS,
    ChapterInput,
    CutSignals,
    ReleaseSplitError,
    Tier,
    chinese_ordinal,
    classify_pair,
    nonws,
    parse_chapter,
    select_chapter_files,
    tier_of,
)

REPO = Path(__file__).resolve().parents[3]
FIX = REPO / "tests" / "fixtures" / "publish"

TITLES = {1: "明白纸", 2: "城破那日", 3: "两本册子", 4: "一升二合", 5: "例在，人在"}


@pytest.mark.unit
def test_tiers_pinned() -> None:
    assert TIERS["fanqie"] == Tier(floor=2000, target=2200, soft=2400)
    assert TIERS["qidian"] == Tier(floor=2000, target=2700, soft=3000)


@pytest.mark.unit
def test_chapter_file_regex() -> None:
    assert CHAPTER_FILE_RE.match("chapter-1.md")
    assert CHAPTER_FILE_RE.match("chapter-10.md")
    assert not CHAPTER_FILE_RE.match("chapter-1-pre-rev.md")
    assert not CHAPTER_FILE_RE.match("chapter-1-decisions.json")
    assert not CHAPTER_FILE_RE.match("chapter-1-revision-decisions.json")


@pytest.mark.unit
def test_select_orders_numerically_and_rejects_dup(tmp_path: Path) -> None:
    d = tmp_path / "chapters"
    d.mkdir()
    for name in ("chapter-10.md", "chapter-2.md", "chapter-1.md"):
        (d / name).write_text("# Chapter 1:\n\n# t\n\n正文", encoding="utf-8")
    files = select_chapter_files(d)
    assert [f.name for f in files] == ["chapter-1.md", "chapter-2.md", "chapter-10.md"]
    (d / "chapter-01.md").write_text("# Chapter 1:\n\n# t\n\n正文", encoding="utf-8")
    with pytest.raises(ReleaseSplitError, match="同章号"):
        select_chapter_files(d)


@pytest.mark.unit
def test_parse_real_fixtures() -> None:
    gates = {1: (8476, 14), 2: (8049, 15), 3: (7200, 15), 4: (7792, 15), 5: (6517, 22)}
    for n, (gate, h1n) in gates.items():
        ch = parse_chapter(FIX / f"chapter-{n}.md")
        assert isinstance(ch, ChapterInput)
        assert ch.number == n
        assert ch.title == TITLES[n]
        assert ch.gate_chars == gate
        assert ch.h1_nonws == h1n
        # identity: gate - h1 == sum of paragraph nonws
        assert ch.gate_chars - ch.h1_nonws == sum(nonws(p) for p in ch.paragraphs)
        # zero-nonws paragraphs dropped; every paragraph has content
        assert all(nonws(p) > 0 for p in ch.paragraphs)
        # no H1 lines, no META wrappers survive into paragraphs
        assert not any(p.startswith("# ") for p in ch.paragraphs)
        assert not any("META-BEGIN" in p or "PRE_WRITE_CHECK" in p for p in ch.paragraphs)


@pytest.mark.unit
def test_parse_ch5_duplicate_h1_outside_wrapper() -> None:
    ch = parse_chapter(FIX / "chapter-5.md")
    assert ch.title == "例在，人在"
    assert ch.h1_nonws == 22  # 三个 H1：# Chapter 5: + 章题 ×2（含 META 包装外重复行）


@pytest.mark.unit
def test_parse_zero_nonws_paragraph_dropped(tmp_path: Path) -> None:
    f = tmp_path / "chapter-1.md"
    f.write_text("# Chapter 1:\n\n# 题\n\n段一。\n\n　\n\n段二。", encoding="utf-8")
    # U+3000 独占段 = 零非空白字符段
    ch = parse_chapter(f)
    assert ch.paragraphs == ("段一。", "段二。")


@pytest.mark.unit
def test_parse_structural_errors(tmp_path: Path) -> None:
    no_h1 = tmp_path / "chapter-1.md"
    no_h1.write_text("# Chapter 1:\n\n正文一段。", encoding="utf-8")
    with pytest.raises(ReleaseSplitError, match="第二个 H1"):
        parse_chapter(no_h1)
    empty = tmp_path / "chapter-2.md"
    empty.write_text("", encoding="utf-8")
    with pytest.raises(ReleaseSplitError, match="空"):
        parse_chapter(empty)
    no_paras = tmp_path / "chapter-3.md"
    no_paras.write_text(
        "# Chapter 3:\n\n# 题\n\n<!--META-BEGIN-->\n## PRE_WRITE_CHECK\nx\n<!--META-END-->\n",
        encoding="utf-8",
    )
    with pytest.raises(ReleaseSplitError, match="正文段"):
        parse_chapter(no_paras)


_LONG_PLAIN = (
    "他放下笔，走到窗前，看着院子里那棵老槐树在风里晃了很久才停下来，"
    "檐下的水滴一声一声落进缸里，谁也没有说话，屋里只剩灯芯偶尔爆一下的响动。"
)  # >40 非空白字符、不以引号开头、不以？！收尾——零谓词基准段


@pytest.mark.unit
def test_tension_predicates_stack() -> None:
    # “真的吗？ starts with “(c) + ends ？(a) + <=40(b) → +6（未闭合引号构造）
    sig = classify_pair("“真的吗？", "他走了。")
    assert (sig.score, sig.tension, sig.scene, sig.waist) == (6, True, False, False)
    # 常规对话段 “会吗？”：末字符 ” 不触发 (a)；(b)+(c) → +4
    sig_d = classify_pair("“会吗？”", "他走了。")
    assert (sig_d.score, sig_d.tension) == (4, True)
    # 仅 (b)：短陈述句 +2
    sig2 = classify_pair("他放下笔。", "他又拿起来了。")
    assert (sig2.score, sig2.tension, sig2.scene, sig2.waist) == (2, True, False, False)
    # 零谓词：长段收尾于句号
    sig3 = classify_pair(_LONG_PLAIN, "他站了很久。")
    assert (sig3.score, sig3.tension, sig3.scene, sig3.waist) == (0, False, False, False)


@pytest.mark.unit
def test_scene_and_waist_predicates() -> None:
    # prev 全部 >40 非空白字符防 (b) 误触（实测长度 46/56）
    sig = classify_pair(_LONG_PLAIN, "翌日清晨，城里来了消息。")
    assert (sig.score, sig.tension, sig.scene, sig.waist) == (1, False, True, False)
    # prev 以场景转换词开头 → −2 腰斩
    sig_w = classify_pair(
        "翌日，他独自去了城外的码头，一路没有人同行，雪把脚印埋了又起，风从河面上刮过来，割得人脸疼。",
        "码头空着。",
    )
    assert (sig_w.score, sig_w.tension, sig_w.scene, sig_w.waist) == (-2, False, False, True)
    # 相邻双景开场：+1 −2 → −1（叠算净负为正确语义）
    sig_both = classify_pair(
        "入夜，风从北门灌进来，把街上最后一张告示掀到了河里，没有人去捡，更夫的梆子声也比平日短了半拍，像是也怕吵醒什么。",
        "次日船到了。",
    )
    assert (sig_both.score, sig_both.scene, sig_both.waist) == (-1, True, True)
    # 词表外不认：傍晚不在 16 词闭集内
    assert classify_pair(_LONG_PLAIN, "傍晚时分管事来敲门说账房失火这句不在词表。").scene is False


@pytest.mark.unit
def test_end_of_chapter_imaginary_cut() -> None:
    # next_para=None：张力谓词活、场景/腰斩死
    sig = classify_pair("“真的吗？", None)
    assert (sig.score, sig.tension, sig.scene, sig.waist) == (6, True, False, False)
    sig2 = classify_pair(_LONG_PLAIN, None)
    assert (sig2.score, sig2.tension) == (0, False)


@pytest.mark.unit
def test_four_tiers_by_predicate_firing() -> None:
    def mk(score: int, tension: bool, scene: bool, waist: bool) -> CutSignals:
        return CutSignals(score=score, tension=tension, scene=scene, waist=waist)

    assert tier_of(mk(6, True, False, False)) == "tension"
    assert tier_of(mk(2, True, True, True)) == "tension"  # tension 支配
    assert tier_of(mk(1, False, True, False)) == "scene"
    assert tier_of(mk(-1, False, True, True)) == "scene"  # scene 触发而 tension 未触发
    assert tier_of(mk(0, False, False, False)) == "plain"
    assert tier_of(mk(-2, False, False, True)) == "weak"  # 仅腰斩触发


@pytest.mark.unit
def test_chinese_ordinals() -> None:
    digits = ["一", "二", "三", "四", "五", "六", "七", "八", "九"]
    for k in range(1, 10):
        assert chinese_ordinal(k) == digits[k - 1]
    assert chinese_ordinal(10) == "十"
    assert chinese_ordinal(11) == "十一"
    assert chinese_ordinal(20) == "二十"
    assert chinese_ordinal(21) == "二十一"
    assert chinese_ordinal(99) == "九十九"
    with pytest.raises(ValueError):
        chinese_ordinal(0)
    with pytest.raises(ValueError):
        chinese_ordinal(100)
