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
    initial_n,
    nonws,
    parse_chapter,
    plan_releases,
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


def _mk_ch(paras: list[str], gate: int | None = None, h1: int = 0) -> ChapterInput:
    """Constructed structural ChapterInput (G0.9 dual-track: 非真实产物断言)."""
    body = sum(nonws(p) for p in paras)
    return ChapterInput(
        path=Path("chapter-0.md"),
        number=0,
        title="t",
        gate_chars=gate if gate is not None else body + h1,
        h1_nonws=h1,
        paragraphs=tuple(paras),
    )


@pytest.mark.unit
def test_initial_n_formula_edges() -> None:
    fq = TIERS["fanqie"]
    qd = TIERS["qidian"]
    assert initial_n(1999, fq) == 1  # < 2×floor → 单更
    assert initial_n(3999, fq) == 1  # 单更（软上限 +66% 合法形态）
    assert initial_n(4000, fq) == 2  # 2×2000 恰可分
    assert initial_n(4801, fq) == 2  # ceil=3 → 1600<2000 → 2
    assert initial_n(10000, fq) == 5  # 5×2000 恰
    assert initial_n(10001, fq) == 5
    assert initial_n(10400, fq) == 5
    assert initial_n(12500, fq) == 6
    assert initial_n(7792, fq) == 3  # ch4 回退分支：ceil=4 → 1948<2000 → 3
    assert initial_n(7200, fq) == 3  # 恰 3×2400
    assert initial_n(2999, qd) == 1
    assert initial_n(3000, qd) == 1  # qidian 单更恰软上限
    assert initial_n(6001, qd) == 3  # qidian 回退分支不可达：ceil=3 → 2000.33>=2000


@pytest.mark.unit
def test_plan_releases_real_fixtures_fanqie() -> None:
    """仿真定稿回归锚（spec §5 rev6）。"""
    fq = TIERS["fanqie"]
    expected = {
        1: [2029, 2237, 2003, 2193],
        2: [2322, 2746, 2966],  # 初始 n=4，选择第 2 步可行域空 → 降档 m=3
        3: [2211, 2237, 2737],
        4: [2224, 2581, 2972],  # §2 回退 7792→3
        5: [2059, 2007, 2429],
    }
    for n, sizes in expected.items():
        ch = parse_chapter(FIX / f"chapter-{n}.md")
        groups, m = plan_releases(ch, initial_n(ch.gate_chars, fq), fq)
        got = [sum(nonws(p) for p in ch.paragraphs[s:e]) for s, e in groups]
        assert m == len(sizes), f"ch{n}: m={m} != {len(sizes)}"
        assert got == sizes, f"ch{n}: {got} != {sizes}"
        assert all(x >= fq.floor for x in got)


@pytest.mark.unit
def test_plan_releases_qidian_anchors() -> None:
    qd = TIERS["qidian"]
    for n in (1, 2, 3, 4, 5):  # qidian 双档带内约束全章断言
        ch = parse_chapter(FIX / f"chapter-{n}.md")
        groups, m = plan_releases(ch, initial_n(ch.gate_chars, qd), qd)
        got = [sum(nonws(p) for p in ch.paragraphs[s:e]) for s, e in groups]
        assert m == 3
        assert all(x >= qd.floor for x in got)
    ch1 = parse_chapter(FIX / "chapter-1.md")
    groups, m = plan_releases(ch1, initial_n(ch1.gate_chars, qd), qd)
    got = [sum(nonws(p) for p in ch1.paragraphs[s:e]) for s, e in groups]
    assert (m, got) == (3, [2483, 2875, 3104])


@pytest.mark.unit
def test_plan_releases_razor_slack_downgrade() -> None:
    """Razor-slack 构造：m=4 首带无候选 → 降档 4→3（真 ch2 同机制）。"""
    fq = TIERS["fanqie"]
    paras = ["字" * 2680, "句" * 2680, "词" * 2680]
    ch = _mk_ch(paras, gate=8055, h1=15)  # ceil(8055/2400)=4, 8055/4=2013>=2000
    groups, m = plan_releases(ch, initial_n(ch.gate_chars, fq), fq)
    assert m == 3
    sizes = [sum(nonws(p) for p in ch.paragraphs[s:e]) for s, e in groups]
    assert sizes == [2680, 2680, 2680]
    assert all(x >= fq.floor for x in sizes)


@pytest.mark.unit
def test_plan_releases_collapse_to_forced_single() -> None:
    """构造 4500 = 1200/2100/1200：m=2 两候选皆出可行域 → 塌缩 m=1。"""
    fq = TIERS["fanqie"]
    ch = _mk_ch(["字" * 1200, "句" * 2100, "词" * 1200], gate=4500)
    groups, m = plan_releases(ch, initial_n(ch.gate_chars, fq), fq)
    assert m == 1
    assert groups == [(0, 3)]


@pytest.mark.unit
def test_plan_releases_single_release_short_chapter() -> None:
    fq = TIERS["fanqie"]
    ch = _mk_ch(["短章" * 300], gate=1199)  # body 600 < 2×floor
    groups, m = plan_releases(ch, initial_n(ch.gate_chars, fq), fq)
    assert m == 1 and groups == [(0, 1)]


@pytest.mark.unit
def test_plan_releases_scoring_moves_cut() -> None:
    """同窗候选打分差改变切点：窗口内三候选，张力段边界（+4）胜过 0 分与 +2 分者。"""
    fq = TIERS["fanqie"]
    a = "他" * 2050  # >40、不以引号开头、句号收尾基准长段（0 分）
    t = "“会吗？”"  # (b)+(c) → +4（末字符 ” 不触发 (a)）
    f = "灯苗矮下去又立起来。"  # (b) → +2
    b = "词" * 2051
    ch = _mk_ch([a, t, f, b])  # body = 2050+5+10+2051 = 4116, gate 同
    # n=2（ceil(4116/2400)=2, 4116/2=2058>=2000）；t_1=2058, half=(15*4116)//200=308
    # 窗口 [1750, 2366]：边界 2050(0 分)/2055(+4)/2065(+2) → 选 2055
    groups, m = plan_releases(ch, initial_n(ch.gate_chars, fq), fq)
    assert m == 2
    sizes = [sum(nonws(p) for p in ch.paragraphs[s:e]) for s, e in groups]
    assert sizes == [2055, 2061]
    assert all(x >= fq.floor for x in sizes)


@pytest.mark.unit
def test_plan_releases_tie_break_earlier() -> None:
    """窗口内两候选同分 → 取更早边界（spec §3.2 平手裁决）。"""
    fq = TIERS["fanqie"]
    a = "他" * 2050
    f1 = "灯苗矮下去又立起来。"  # (b) +2
    f2 = "火苗立起来又矮下去。"  # (b) +2——与 f1 同分
    b = "词" * 2051
    ch = _mk_ch([a, f1, f2, b])  # body = 2050+10+10+2051 = 4121
    # n=2, t_1=2060.5, half=309 → 窗口 [1752, 2369]；边界 2050(0)/2060(+2)/2070(+2)
    # 平手取更早 → 切 2060 → 更1 = 2060
    groups, m = plan_releases(ch, initial_n(ch.gate_chars, fq), fq)
    assert m == 2
    sizes = [sum(nonws(p) for p in ch.paragraphs[s:e]) for s, e in groups]
    assert sizes[0] == 2060


@pytest.mark.unit
def test_plan_releases_fallback_nearest_when_window_empty() -> None:
    """窗口∩可行域无候选而可行域有候选 → 距离最近者（spec §3.2 回退分支）。"""
    fq = TIERS["fanqie"]
    # body 5200，边界 2200/3200；t_1=2600, half=(15*5200)//200=390 → 窗口 [2210,2990] 空
    ch = _mk_ch(["字" * 2200, "句" * 1000, "词" * 2000])
    groups, m = plan_releases(ch, initial_n(ch.gate_chars, fq), fq)
    assert m == 2
    sizes = [sum(nonws(p) for p in ch.paragraphs[s:e]) for s, e in groups]
    assert sizes == [2200, 3000]  # |2200−2600|=400 < |3200−2600|=600 → 取 2200


@pytest.mark.unit
def test_plan_releases_fallback_tie_takes_earlier() -> None:
    """回退分支等距平手 → 取更早边界。"""
    fq = TIERS["fanqie"]
    # body 5200，边界 2000/3200 各距 t_1=2600 六百 → 平手取早 → 切 2000
    ch = _mk_ch(["字" * 2000, "句" * 1200, "词" * 2000])
    groups, m = plan_releases(ch, initial_n(ch.gate_chars, fq), fq)
    assert m == 2
    sizes = [sum(nonws(p) for p in ch.paragraphs[s:e]) for s, e in groups]
    assert sizes == [2000, 3200]
