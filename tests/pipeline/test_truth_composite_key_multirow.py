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
    # single-row-per-chapter targets keep the simple chapter key
    assert semantics["truth/current_state.md"]["key"] == "chapter"
    assert semantics["truth/chapter_summaries.md"]["key"] == "chapter"


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
