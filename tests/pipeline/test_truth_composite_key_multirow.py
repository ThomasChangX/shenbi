"""#50 (probe21 adjudication #008): append_dedup targets that legitimately
carry MULTIPLE rows per chapter (particle_ledger: one row per 变动项;
subplot_board: one row per 支线) declared the single-column key ``chapter`` —
a rows-only re-merge annihilated every same-chapter row after the first
(the probe21 ch1 ledger's five rows would collapse to one). The true row
identity is the (章节, 变动项/支线) tuple; the contract must declare the
composite key so the keyed upsert replaces per-row, never per-chapter.
"""

from __future__ import annotations

from pathlib import Path

from shenbi.contracts import load_contract
from shenbi.pipeline.dispatch_helper import _route_append_dedup_write
from shenbi.pipeline.truth_io import upsert_markdown_row

#: Real probe21 ch1 rows (novel-xinghuo-probe21/truth/particle_ledger.md) —
#: five rows sharing the chapter key 「第 1 章」, distinct only by 变动项.
PROBE21_LEDGER_ROWS = [
    "| 第 1 章 | 灰木牌（正面烙「灰」字，边角磨钝） | +1 | 点星礼长衫依判定发放 | 灰籍身份牌，落籍终身，改不了 |",
    "| 第 1 章 | 手背铁章印记「灰」 | +1 | 点星官以细铁章按压手背 | 墨入皮内，抹不掉，边缘发虚 |",
    "| 第 1 章 | 口粮纸（印好格子） | +1 | 场边棚子凭牌发放 | 按周配给，需凭牌领取 |",
    "| 第 1 章 | 钱物 | 0 | 醒来时腰上空空，无牌、无钱 | 南岸船钱约三个月工钱 |",
    "| 第 1 章 | 南仓工账 | 起始 | 灰民被判往南仓做工 | 第一天的账，记下了 |",
]

LEDGER_HEADER = (
    "| 章节 | 变动项 | 收支 | 来源／用途 | 余额或备注 |\n"
    "|------|--------|------|------------|------------|"
)

SUBPLOT_ROWS = [
    "| 第 1 章 | 灰民落籍与核销名单（MH03） | 1 | 点星礼完成，林渡落灰籍 | 核销名单逐月更新 |",
    "| 第 1 章 | 南仓做工攒船钱、南渡南岸 | 1 | 目标确立：约三个月工钱 | 进入南仓做工并逐日记账 |",
]

SUBPLOT_HEADER = (
    "| 章节 | 支线 | 起始章 | 当前阶段 | 下一节点 |\n|------|------|--------|----------|----------|"
)


def test_contract_declares_composite_keys_for_multirow_targets():
    """The contract is the merge-key single source (dispatch reads
    write_semantics[...]['key']); drifting back to ``chapter`` re-arms the
    per-chapter annihilation.
    """
    semantics = load_contract("shenbi-state-settling").get("write_semantics", {})
    assert semantics["truth/particle_ledger.md"]["key"] == "章节,变动项"
    assert semantics["truth/subplot_board.md"]["key"] == "章节,支线"
    # F-4 (probe22 adjudication #009 P2-2): ch2 progressed BOTH cenluo's and
    # zhongbo's arcs; the row identity is (章节, 角色) — the header's own
    # identity column — not chapter. key=chapter could hold only ONE row and
    # the other arc's row was lost while the sidecar declared both.
    assert semantics["truth/emotional_arcs.md"]["key"] == "章节,角色"
    # single-row-per-chapter targets keep the simple chapter key
    assert semantics["truth/current_state.md"]["key"] == "chapter"
    assert semantics["truth/chapter_summaries.md"]["key"] == "chapter"


def test_emotional_arcs_dual_arc_rows_coexist():
    """F-4 acceptance: a chapter with two progressing arcs keeps both rows —
    real probe22 ch2 rows (岑落 + 钟伯).
    """
    base = (
        "# 情绪弧线\n\n"
        "| 章节 | 角色 | 起始情绪 | 转折事件 | 章末情绪 |\n"
        "|---|---|---|---|---|\n"
        "| 第 1 章 | 岑落 | 灰雨里麻木而克制的日常 | 西三巷两客者被销名 | 沉默的承担 |\n"
    )
    ch2_cenluo = (
        "| 第 2 章 | 岑落 | 沉静的日常 | 钟伯请抄「自离」三份、收存抄本与撕页 | "
        "沉静中生出戒备——「笔也招人」之诫入耳 |"
    )
    ch2_zhongbo = (
        "| 第 2 章 | 钟伯 | 失子后的隐忍 | 请岑落照原样抄三份，一份焚给亡者 | "
        "稍得依托，临别以「笔招人」相警 |"
    )
    merged = base
    for row in (ch2_cenluo, ch2_zhongbo):
        merged = upsert_markdown_row(merged, row, "章节,角色")
    data_rows = [l for l in merged.split("\n") if l.startswith("| 第 2 章")]
    assert len(data_rows) == 2, f"second arc row annihilated: {merged!r}"
    assert ch2_cenluo in merged and ch2_zhongbo in merged
    # the ch1 row is untouched
    assert merged.count("| 第 1 章 |") == 1


def test_ledger_remerge_preserves_same_chapter_multi_rows():
    """Rows-only re-merge (reject-retry, re-settlement) must replace per
    (章节, 变动项) row — the probe21 five-row ledger survives intact and a
    corrected row lands in place.
    """
    base = "# 资源账本\n\n" + LEDGER_HEADER + "\n" + "\n".join(PROBE21_LEDGER_ROWS) + "\n"
    corrected = PROBE21_LEDGER_ROWS[0].replace("+1 | 点星礼长衫依判定发放", "+1 | 点星礼补发")
    increment = "\n".join([corrected, *PROBE21_LEDGER_ROWS[1:]])

    merged = base
    for line in increment.split("\n"):
        if line.strip():
            merged = upsert_markdown_row(merged, line, "章节,变动项")

    data_rows = [l for l in merged.split("\n") if l.startswith("| 第")]
    assert len(data_rows) == 5, f"same-chapter rows annihilated: {len(data_rows)} left"
    assert corrected in merged  # corrected row replaced its own key in place
    for row in PROBE21_LEDGER_ROWS[1:]:
        assert row in merged  # untouched siblings preserved verbatim


def test_subplot_remerge_preserves_same_chapter_rows():
    base = "# 支线进度板\n\n" + SUBPLOT_HEADER + "\n" + "\n".join(SUBPLOT_ROWS) + "\n"
    merged = base
    for line in SUBPLOT_ROWS:
        merged = upsert_markdown_row(merged, line, "章节,支线")
    data_rows = [l for l in merged.split("\n") if l.startswith("| 第")]
    assert len(data_rows) == 2, f"same-chapter rows annihilated: {len(data_rows)} left"


#: Real probe22 ch2 rows (novel-xinghuo-probe22/truth/character_matrix.md) —
#: the 交互表 keys on the (角色A, 角色B) tuple; a NEW pair in a later chapter
#: must land INSIDE that table, not strand at EOF (F-1).
MATRIX_HEADER = "| 角色A | 角色B | 关系定位 | 秘密 | 触发事件 | 信任度 |\n|---|---|---|---|---|---|"

MATRIX_ROW_CH1 = "| 岑落 | 管事 | 无档者×册籍执掌者 | 无 | 点工销名，客者不计伤亡 | 持平 |"
MATRIX_ROW_CH2 = (
    "| 岑落 | 钟伯 | 无档写字人×失子矿工（受托与请托） | 岑落第三本账记「来处」，未启 | "
    "请抄「自离」页三份，一份托存、一份焚给亡者 | 相托 |"
)

MATRIX_STATE_BLOCK = (
    "## 第1章状态增量\n\n### 岑落\n\n- 当前状态: 存活，栖身矿场窄檐\n- 最后更新章: 1\n"
)


def test_new_composite_key_row_inserts_into_its_table_not_eof():
    """F-1 (probe22 adjudication #009 R4): a new (角色A, 角色B) pair arrived
    while trailing state sections occupied EOF — _key_table_tail compared the
    WHOLE spec 「角色A,角色B」 against single header cells, matched nothing,
    and the row stranded after the 第1章状态增量 block until a human review
    moved it back into the table.
    """
    existing = MATRIX_HEADER + "\n" + MATRIX_ROW_CH1 + "\n" + MATRIX_STATE_BLOCK
    merged = upsert_markdown_row(existing, MATRIX_ROW_CH2, "角色A,角色B")
    lines = merged.split("\n")

    row_idx = lines.index(MATRIX_ROW_CH2)
    ch1_idx = lines.index(MATRIX_ROW_CH1)
    heading_idx = lines.index("## 第1章状态增量")
    assert ch1_idx < row_idx < heading_idx, (
        f"new interaction pair stranded outside its table (row at {row_idx}, "
        f"heading at {heading_idx}): {lines}"
    )
    assert lines[-1].strip() != MATRIX_ROW_CH2  # not EOF-appended


_STUB_SUBPLOT_BASE = """---
type: truth
category: subplot
status: initialized
---

> 此文件由 state-settling 首次运行时填充实际数据。

## 待填充

- 各支线当前阶段与下一节点
"""


def test_staging_merge_activates_composite_keys_on_stub_base(tmp_path: Path):
    """probe22 adjudication #006 P1-2, simulated verdict: merging two
    same-chapter subplot rows onto a headerless stub base collapsed them to
    one (first-column degradation). With the #38 extension the bootstrap
    appends the contract header FIRST, so the (章节, 支线) key activates and
    both rows coexist — header above rows, no separator-less table.
    """
    live = tmp_path / "truth" / "subplot_board.md"
    live.parent.mkdir(parents=True)
    live.write_text(_STUB_SUBPLOT_BASE, encoding="utf-8")
    _route_append_dedup_write(
        tmp_path,
        "staging/truth/subplot_board.md",
        "\n".join(SUBPLOT_ROWS),
        key_field="章节,支线",
    )
    staged = (tmp_path / "staging" / "truth" / "subplot_board.md").read_text(encoding="utf-8")
    data_rows = [l for l in staged.split("\n") if l.startswith("| 第")]
    assert len(data_rows) == 2, f"composite key inactive on stub base: {staged!r}"
    header_idx = staged.index("| 章节 | 支线 |")
    sep_idx = staged.index("|---")
    first_row_idx = staged.index(data_rows[0])
    assert header_idx < sep_idx < first_row_idx


def test_reemitted_contract_header_dropped_on_chapter_key_file(tmp_path: Path):
    """probe22 adjudication #006 F-1 follow-up: chapter-keyed files declare
    the ENGLISH key (``chapter``) while the model re-emits the CHINESE
    contract header (「章节」…), which upsert's header detection cannot
    recognize — the row stranded at EOF after the data rows. The merge owns
    the header (bootstrap wrote it); a unit equal to the registered header
    is dropped, never merged as data.
    """
    live = tmp_path / "truth" / "current_state.md"
    live.parent.mkdir(parents=True)
    live.write_text(_STUB_SUBPLOT_BASE, encoding="utf-8")
    header = "| 章节 | 位置 | 时间锚 | 主角处境 | 势力态势 | 待处理压力 |"
    increment = "| 第 1 章 | 黑脉矿场 | 灰雨第三日 | 无档之身 | 册籍三分 | 西三巷道塌方\n" + header
    _route_append_dedup_write(
        tmp_path, "staging/truth/current_state.md", increment, key_field="chapter"
    )
    staged = (tmp_path / "staging" / "truth" / "current_state.md").read_text(encoding="utf-8")
    assert staged.count(header) == 1  # bootstrap's copy only — re-emission dropped
    assert staged.index(header) < staged.index("| 第 1 章 |")  # header leads the table


def test_staging_route_remerge_keeps_multi_row_ledger(tmp_path: Path):
    """End-to-end through the dispatch write path: a FILLED live base plus a
    rows-only re-emission must stage the SAME five rows — this is the exact
    shape of the probe21 ch1 re-settlement that collapsed.
    """
    live = tmp_path / "truth" / "particle_ledger.md"
    live.parent.mkdir(parents=True)
    live.write_text(
        "# 资源账本\n\n" + LEDGER_HEADER + "\n" + "\n".join(PROBE21_LEDGER_ROWS) + "\n",
        encoding="utf-8",
    )

    increment = "\n".join(PROBE21_LEDGER_ROWS)
    _route_append_dedup_write(
        tmp_path, "staging/truth/particle_ledger.md", increment, key_field="章节,变动项"
    )

    staged = (tmp_path / "staging" / "truth" / "particle_ledger.md").read_text(encoding="utf-8")
    staged_rows = [l for l in staged.split("\n") if l.startswith("| 第")]
    assert len(staged_rows) == 5, f"staged collapse: {len(staged_rows)} rows"
    for row in PROBE21_LEDGER_ROWS:
        assert row in staged
    assert not staged_rows[-1].startswith("| 第 2 章")  # no fabricated next chapter
