"""spec #83 T10: balance_value_drift dual-surface anchor.

Corpus baselines: ch26 opening 103 vs 113 FAIL; ch23 deep post-payment 143
green with spend exemption, None-state exactly-one-143-WARN; ch1 multi-
timepoint WARN face; price sentences unanchored; ledger parse ==103.
"""

from __future__ import annotations

from pathlib import Path

from shenbi.gates.g4.post_declarations import (
    check_balance_value_drift,
    first_scene_span,
    parse_ledger_current_value,
    parse_spend_events,
)
from shenbi.gates.g4.shadow import GATE_TO_SHADOW_KEY

FIX = Path(__file__).resolve().parents[3] / "fixtures" / "spec83"


def _text(n: int) -> str:
    return (FIX / "chapters" / f"chapter-{n}.md").read_text(encoding="utf-8")


def test_ledger_parse_fixture_value() -> None:
    # r5-C1 锚：真实 ledger 现值行 `| 第 36 章 | 余额一百零三文 |` → 103（末命中行规则）
    ledger = (FIX / "truth" / "particle_ledger.md").read_text(encoding="utf-8")
    assert parse_ledger_current_value(ledger) == 103


def test_ch26_opening_balance_mismatch_fails() -> None:
    # ch26:26 章首（场景 1）「纸包里剩一百零三文」≠ check 时点 113 → FAIL 臂红
    fails, _ = check_balance_value_drift(_text(26), 113)
    assert any("balance_value_drift" in f and "章首" in f for f in fails)


def test_spend_exemption_arithmetic() -> None:
    # 轮 6 I2：带符号 ledger−occurrence——ch23 183−143=+40 ∈ {40} 豁免（符号翻转实现即红）
    fails, warns = check_balance_value_drift(_text(23), 183, spend_events=[40])
    assert fails == []
    assert not any("一百四十三文" in w for w in warns)  # :300 零信号


def test_ch23_none_state_exactly_one_warn() -> None:
    # 轮 7 I1 定稿：None 态 :300 深位命中（143）合法 WARN 恰一条；:351 POST 两命中
    # 被 META 位置排除（183 消息零出现=排除行为证；>1 条 143=META 排除失效）
    fails, warns = check_balance_value_drift(_text(23), 183)
    assert fails == []
    assert not any("一百八十三文" in w for w in warns)
    assert len([w for w in warns if "143" in w]) == 1


def test_ch1_multi_timepoint_warn_face() -> None:
    # ch1 :37 一共十七文（=17 首现绿）→ :39 剩五十二文（≠17 无支出声明）WARN ≥1
    fails, warns = check_balance_value_drift(_text(1), 17)
    assert fails == []
    assert any("52" in w for w in warns)


def test_price_sentence_not_anchored() -> None:
    _, warns = check_balance_value_drift("灯油四文一斤，他买了。", 103)
    assert warns == []


def test_deep_first_occurrence_outside_first_scene_green() -> None:
    # ch23 首现 :300 在场景 3（标记 :26/:107/:228）——非首场景不触发 FAIL
    fails, _ = check_balance_value_drift(_text(23), 183, spend_events=[40])
    assert fails == []


def test_first_scene_span_units() -> None:
    # 坐标系：char offsets（_BALANCE_RE match.start() 可比较）；无标记 None
    ch26 = _text(26)
    span = first_scene_span(ch26)
    assert span is not None and span[0] < span[1]
    idx = ch26.index("纸包里剩一百零三文")
    assert span[0] <= idx < span[1]  # 章首余额句确在首场景
    assert first_scene_span("无标记正文。") is None


def test_parse_spend_events_variants() -> None:
    assert parse_spend_events("- 事件: 支出|四十文|先还债\n") == [40]
    assert parse_spend_events("- 事件: 支出|零文|不涉钱货\n") == []
    assert parse_spend_events("- 事件: 支出|无|\n") == []
    # ch4 复合行中段
    assert parse_spend_events("- 事件: 收入|八文|x｜支出|六文|y\n") == [6]


def test_shadow_registration_rows8_9() -> None:
    assert GATE_TO_SHADOW_KEY["cd.balance_value_drift"] == ("market_params", "balance_anchor")
    assert GATE_TO_SHADOW_KEY["cd.balance_value_drift.bundle"] == (
        "market_params",
        "balance_anchor",
    )
