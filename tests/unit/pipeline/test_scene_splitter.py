"""spec #72 T3: scene_splitter unit tests (constructed inputs, G0.9 §4)."""

from __future__ import annotations

import pytest

from shenbi.pipeline.scene_splitter import (
    CH_MARKER_RE,
    BundleChapters,
    SceneSplitError,
    chapter_total_chars,
    count_scene_markers,
    pack_scenes,
    parse_scene_declarations,
    split_bundle,
    validate_split,
)

BAND = (2800, 4000)
HOOK1 = "他把第三遍数目又数了一遍。"
HOOK2 = "门在身后轻轻合上了。"
HOOK3 = "那盏灯还亮着，没有人去熄它。"

TITLES = {1: "首章", 2: "次章", 3: "三章", 4: "四章"}


def _scene(size: int, hook: str) -> str:
    return "灯" * size + "\n" + hook


def _bundle(n1: int, n2: int | None, scenes: dict[int, list[tuple[int, str]]]) -> str:
    parts = []
    for n in [n1, n2] if n2 else [n1]:
        # 解剖顺序 = 现行真实章：PRE 块在前、双 H1 其后（PRE 的 strip 边界
        # 是下一个 #/##——H1 在前会把正文整体吞入 PRE 剥除段，见 spec rev5.3）
        seg = [
            f"===CH:{n}===",
            "## PRE_WRITE_CHECK",
            "",
            "- x",
            "",
            f"# 第{n}章",
            f"# {TITLES[n]}",
            "",
            "<!--SCENE-->",
        ]
        for i, (size, hook) in enumerate(scenes[n]):
            if i > 0:
                seg.append("<!--SCENE-->")
            seg.append(_scene(size, hook))
        seg += ["", "## POST_WRITE_SELF_CHECK", "", "- y", ""]
        parts.append("\n".join(seg))
    return "\n\n".join(parts)


# 2 场景章（两独立型 1900+1900=3800 ∈ 带）
SC2 = {1: [(1900, HOOK1), (1900, HOOK2)], 2: [(1950, HOOK3), (1850, HOOK1)]}


def test_split_two_chapters() -> None:
    result = split_bundle(_bundle(1, 2, SC2))
    assert isinstance(result, BundleChapters)
    assert [c.number for c in result.chapters] == [1, 2]
    ch1 = result.chapters[0]
    assert ch1.title == TITLES[1]
    assert "===CH:1===" not in ch1.body
    assert count_scene_markers(ch1.body) == 2
    assert [s.last_line for s in ch1.scenes] == [HOOK1, HOOK2]
    assert ch1.scenes[0].size == 1900 + len(HOOK1)


def test_ch_marker_regex() -> None:
    assert CH_MARKER_RE.match("===CH:47===")
    assert not CH_MARKER_RE.match("===CH:47==")
    assert not CH_MARKER_RE.match("x===CH:47===")


def test_missing_ch_marker_raises() -> None:
    with pytest.raises(SceneSplitError, match="无任何"):
        split_bundle("没有标记的文本")


def test_duplicate_and_disordered_ch_markers() -> None:
    with pytest.raises(SceneSplitError, match="重复"):
        split_bundle("===CH:1===\n# a\n# t\n\n<!--SCENE-->\n灯" * 1 + "\n\n===CH:1===\n# a\n# t\n")
    with pytest.raises(SceneSplitError, match=r"升序|连续"):
        split_bundle("===CH:2===\n# a\n# t\n\n===CH:5===\n# a\n# t\n")


def test_three_chapters_rejected() -> None:
    text = _bundle(1, None, {1: [(1900, HOOK1), (1900, HOOK2)]})
    text += "\n\n" + _bundle(2, None, {2: [(1900, HOOK1), (1900, HOOK2)]})
    text += "\n\n" + _bundle(3, None, {3: [(1900, HOOK1), (1900, HOOK2)]})
    with pytest.raises(SceneSplitError, match="章数 3 > 2"):
        split_bundle(text)


def test_scene_count_below_two() -> None:
    result = split_bundle(_bundle(1, None, {1: [(1900, HOOK1)]}))
    issues = validate_split(result.chapters[0], BAND)
    assert any("scene_count" in i for i in issues)


def test_gray_zone_scene() -> None:
    result = split_bundle(_bundle(1, None, {1: [(1450, HOOK1), (1450, HOOK2)]}))
    issues = validate_split(result.chapters[0], BAND)
    assert any("scene_domain" in i for i in issues)
    assert any("灰域" in i for i in issues)


def test_band_edges() -> None:
    # 3 配对型 950×3=2850 ∈ 带
    ok = split_bundle(_bundle(1, None, {1: [(950, HOOK1), (950, HOOK2), (950, HOOK3)]}))
    assert validate_split(ok.chapters[0], BAND) == []
    # 章和 2700 < 2800（3×900）→ chapter_band 违例（和取带内规则）
    bad = split_bundle(_bundle(1, None, {1: [(900, HOOK1), (900, HOOK2), (900, HOOK3)]}))
    issues = validate_split(bad.chapters[0], BAND)
    assert any("chapter_band" in i for i in issues)
    # 边界字符校准：PRE/POST/标记行不计入；双 H1 计入（现行 total_chars 口径——
    # v1 release 侧另以 h1_nonws 单独扣除，gate 侧含 H1）
    import re as _re

    h1_nonws = len(_re.sub(r"\s", "", "# 第1章")) + len(_re.sub(r"\s", "", "# 首章"))  # = 7
    assert chapter_total_chars(ok.chapters[0].body) == (
        3 * 950 + len(HOOK1) + len(HOOK2) + len(HOOK3) + h1_nonws
    )


def test_composition_2scene_must_be_2a() -> None:
    # 2 场景 2×1300（配对型组合）→ 组合违例（2 场景章须两独立型）
    result = split_bundle(_bundle(1, None, {1: [(1300, HOOK1), (1300, HOOK2)]}))
    issues = validate_split(result.chapters[0], BAND)
    assert any("composition" in i and "2 场景" in i for i in issues)


def test_composition_3scene_one_ind_two_pair_ok() -> None:
    result = split_bundle(_bundle(1, None, {1: [(1900, HOOK1), (950, HOOK2), (950, HOOK3)]}))
    assert validate_split(result.chapters[0], BAND) == []


def test_pack_scenes_pairs_in_band() -> None:
    assert pack_scenes([950, 950], (1800, 2800)) == [[950, 950]]
    assert pack_scenes([1900], (1800, 2800)) == [[1900]]
    assert pack_scenes([1900, 950, 950, 1900], (1800, 2800)) == [[1900], [950, 950], [1900]]


def test_pack_scenes_cross_2800_none() -> None:
    # 前章尾配对型 + 本章首独立型上沿：950 + 1950 = 2900 > 2800 → None
    assert pack_scenes([950, 1950], (1800, 2800)) is None
    # 单场景 > max → None
    assert pack_scenes([2900], (1800, 2800)) is None
    # 收组时欠重且无法再扩 → None
    assert pack_scenes([1900, 950], (1800, 2800)) is None


def test_pack_scenes_greedy_multi() -> None:
    groups = pack_scenes([950, 950, 950, 950], (1800, 2800))
    assert groups == [[950, 950], [950, 950]]


def test_parse_scene_declarations() -> None:
    memo = (
        "### 场景预算与收束钩（#72 粒度契约）\n"
        "- 场景1: 1900字｜独立型｜收束钩：他把数目又数了一遍。\n"
        "- 场景2: 1350字｜配对型｜收束钩：门合上了。\n"
        "- 章尾钩：那盏灯还亮着。\n"
    )
    decls = parse_scene_declarations(memo)
    assert decls == [
        (1, 1900, "独立型", "他把数目又数了一遍。"),
        (2, 1350, "配对型", "门合上了。"),
    ]
    assert parse_scene_declarations("无场景块的旧备忘") == []


def test_empty_scene_segment_raises() -> None:
    text = (
        "===CH:1===\n# 第1章\n# 题\n\n<!--SCENE-->\n<!--SCENE-->\n灯" * 1900 + "\n" + HOOK1 + "\n"
    )
    with pytest.raises(SceneSplitError, match="空段"):
        split_bundle(text)
