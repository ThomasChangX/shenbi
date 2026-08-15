"""Unit tests for the spec #6 shared extractors (density-scoped home).

These are unit-level probes of _shared.py / contracts.paths behaviors not
covered by the tests/pipeline/ acceptance files: regex edge shapes, section
scoping, sentinel parsing, and the boundary-set derivation inputs.
"""

from pathlib import Path

from shenbi.contracts.paths import (
    PathContext,
    parse_path_context,
    resolve_contract_path,
)
from shenbi.pipeline._shared import (
    BridgeRow,
    _read_cn_volume_boundaries,
    bridges_for_chapter,
    read_bridges,
    read_chapter_node,
)

FIXTURE = Path(__file__).resolve().parents[2] / "fixtures" / "volume-map-xinghuo.md"


def test_cn_boundaries_section_cut_at_any_h2_header():
    """A trailing `## 汇总` section must not donate a range line to volume 5."""
    text = (
        "## 第一卷：A（第1-10章）\n**章节范围**: 第1章 - 第10章（共10章）\n\n"
        "## 汇总\n**章节范围**: 第1章 - 第5章\n"
    )
    assert _read_cn_volume_boundaries(text) == {10}


def test_cn_volume_header_requires_colon():
    text = "## 第二卷 B\n**章节范围**: 第1章 - 第20章\n"
    assert _read_cn_volume_boundaries(text) == set()


def test_cn_chinese_numeral_volume_headers_parse():
    text = "## 第十一卷：X\n**章节范围**: 第1章 - 第120章\n"
    assert _read_cn_volume_boundaries(text) == {120}


def test_read_chapter_node_rejects_bare_english_row():
    assert read_chapter_node("| 5 | role | content |\n", 5) is None


def test_read_chapter_node_prefers_first_match():
    text = "| 第3章 | 起 | 先 |\n| 第3章 | 后 | 再 |\n"
    assert read_chapter_node(text, 3) == {"role": "起", "content": "先"}


def test_read_bridges_skips_sequel_rows_before_warn():
    """续作 rows are filtered by predicate before activation parsing — a
    sequel row with a numeric activation never surfaces.
    """
    text = (
        "### 跨卷桥接\n| # | 钩子内容 | 类型 | 带入卷 | 预期激活章 | 当前状态 |\n"
        "| 1 | 续作钩子 | 物品 | 《续作》 | 第1章 | 已种植 |\n"
        "| 2 | 本书钩子 | 事件 | 第2卷 | 第9章 | 已种植 |\n"
    )
    rows = read_bridges(text)
    assert [r.content for r in rows] == ["本书钩子"]


def test_read_bridges_full_width_range_form():
    text = (
        "### 跨卷桥接\n| # | 钩子内容 | 类型 | 带入卷 | 预期激活章 | 当前状态 |\n"
        "| 1 | 全形区间 | 事件 | 第2卷 | 第10章 - 第12章 | 已种植 |\n"
    )
    assert read_bridges(text)[0].activation == 10


def test_bridges_for_chapter_includes_target_volume_label():
    b = [BridgeRow("钩子", "物品", "第3卷", 10, "已种植")]
    assert bridges_for_chapter(b, 12) == ["第3卷 桥接: 钩子 (activates Ch 10)"]


def test_parse_path_context_tolerant_token_shapes():
    """No-`=` tokens are ignored; trailing-`=` values degrade to str sentinels."""
    ctx = parse_path_context("[path-context] chapter=4 bogus arc=2=")
    assert ctx is not None and ctx.chapter == 4
    assert ctx.arc == "2="  # tolerant str sentinel, not a crash


def test_resolve_contract_path_family_none_falls_back():
    ctx = PathContext(volume=2)  # arc missing
    assert resolve_contract_path("audits/arc-N-score.md", 7, ctx) == "audits/arc-7-score.md"


def test_real_fixture_bridge_density_probe():
    """Fixture-level sanity: 16 this-book rows across 5 sections (R6)."""
    rows = read_bridges(FIXTURE.read_text(encoding="utf-8"))
    assert len(rows) == 16
    assert {r.target_volume for r in rows} == {"第2卷", "第3卷", "第4卷", "第5卷"}
