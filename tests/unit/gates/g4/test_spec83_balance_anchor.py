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


def test_ling_digit_parses_ch30_healthy_green() -> None:
    # audit-T10 C1 回归钉：ch30:55「余额一百零三文」@现值 103 == 103 → 零 FAIL
    fails, warns = check_balance_value_drift(_text(30), 103)
    assert fails == []


def test_price_total_derivation_skips_fail() -> None:
    # audit-T10 I1：价总额句（句内面价加总=总额）→ FAIL 臂跳过（WARN 面保留）
    ch24_shape = "那罕把这三个数在心里搁了一下：盐十四文，对联纸四文，一共十八文。"
    fails, _ = check_balance_value_drift(ch24_shape, 143)
    assert fails == []  # 18 = 14+4 算术衍生——非章首余额泄漏
    ch25_shape = "「年货十八文，馍四文半。」老周报得干脆，「一共二十二文半。」"
    fails2, _ = check_balance_value_drift(ch25_shape, 143)
    assert fails2 == []  # 22.5 = 18+4.5（半感知）
    ch1_shape = "账是这么算的：月俸一百五十文，扣伙食九十八文，剩五十二文；五十二文里花掉三十五文，剩下的就是这十七文。"
    fails3, _ = check_balance_value_drift(ch1_shape, 17)
    assert fails3 == []  # 52 = 150−98 衍生；尾值 17 == ledger


def test_liang_digit_normalized() -> None:
    # audit-T10 I2：两→二归一（剩两文不再静默丢弃）
    fails, warns = check_balance_value_drift("他摸出钱袋。袋底剩两文，数了两遍。", 2)
    assert fails == [] and warns == []  # ==ledger 绿（解析面活着——非 None 丢弃）


def test_bundle_escalation_list_records_and_file_attribution(tmp_path: Path) -> None:
    # audit-T10 C2 回归钉（清偿核验轮终形）：真实拓扑=各成员自身记录（split-site
    # 写入器逐成员记 G4）；list 形 latest-wins；file 归属排除伴生边车
    import json as _json

    from shenbi.gates.g4.state_settling import _balance_bundle_escalation

    (tmp_path / "outline").mkdir()
    (tmp_path / "outline" / "volume_map.md").write_text(
        "## 第一卷（第1-第4章）\n", encoding="utf-8"
    )
    manifest = {
        "gates": {
            "chapter_loop": {
                "1": {
                    "shenbi-chapter-drafting": {
                        "G4": [  # list 形（追加后）——latest-wins
                            {"ts": "t1", "result": {"checks": []}},
                            {
                                "ts": "t2",
                                "result": {
                                    "checks": [
                                        {
                                            "id": "cd.balance_value_drift",
                                            "file": "chapters/chapter-1.md",
                                            "s": "WARN",
                                        },
                                        # 伴生边车（ch3 非束成员——file 归属排除）
                                        {
                                            "id": "cd.balance_value_drift",
                                            "file": "chapters/chapter-3.md",
                                            "s": "WARN",
                                        },
                                    ]
                                },
                            },
                        ]
                    }
                },
                "2": {
                    "shenbi-chapter-drafting": {
                        "G4": {  # dict 首写形
                            "result": {
                                "checks": [
                                    {
                                        "id": "cd.balance_value_drift",
                                        "file": "chapters/chapter-2.md",
                                        "s": "WARN",
                                    },
                                    {
                                        "id": "G4.cd.golden_slot",
                                        "file": "chapters/chapter-2.md",
                                        "s": "PASS",
                                    },
                                ]
                            }
                        }
                    }
                },
            }
        }
    }
    (tmp_path / "pipeline-manifest.json").write_text(_json.dumps(manifest), encoding="utf-8")
    issues = _balance_bundle_escalation(tmp_path, 1)
    assert issues and "ch1×1" in issues[0] and "ch2×1" in issues[0]
    assert "ch3" not in issues[0]
