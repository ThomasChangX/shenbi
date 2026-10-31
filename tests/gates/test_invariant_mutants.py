"""Spec #80 §3/T11: 变异体全被拦=网眼无洞的机器证明。

per-mutant check-id 断言：合并语料不得掩盖死门——name-swap ⇒ F15 红、
prop-chain-break ⇒ F16 红、counter-dup ⇒ F17 红，各自独立断言。
G0.9: 语料=真实伤口导出 fixtures（ch20 pre-rev / ch9 pre-rev / ch8 基线节选）；
facts 态种子=测试内构造（spec §3 豁免面——从 ch08 基线 fixture 派生 count=3，
fixture 非死件，plan R1-M9 接线断言）。
绿语料对极（防误报面，spec §7 验收 3 的 T11 半）：修复后 ch20 + 声明完备种子
⇒ F15/F16 零 FAIL；修复后 ch9 文本 ⇒ F17 零 FAIL（终态种子对极在 T13
test_facts_backfill.py）。
"""

from __future__ import annotations

from pathlib import Path

import pytest

from shenbi.gates.g4.chapter_drafting import (
    _ORDINAL_RE,
    check_counter_reconciliation,
    check_prop_handoffs,
)
from shenbi.gates.g4.cross_chapter import check_narration_name, cn_amount

FIX = Path("tests/fixtures/invariant-mutants")
CH08_BASELINE = FIX / "ch08-counter-baseline.md"
CH09_DUP = FIX / "ch09-counter-dup.md"
CH20_WOUND = FIX / "ch20-name-swap-prop-break.md"
CH20_GREEN = FIX / "ch20-fixed-green.md"


def _ch08_baseline_count() -> int:
    """Derive the 鉴录名数 baseline (3) from the ch08 fixture ordinal."""
    ordinals = [
        cn_amount(m.group(1))
        for m in _ORDINAL_RE.finditer(CH08_BASELINE.read_text(encoding="utf-8"))
    ]
    counts = [v for v in ordinals if v is not None]
    assert counts, "ch08 baseline fixture lost its ordinal line"
    return counts[-1]


@pytest.mark.unit
def test_ch08_baseline_derives_count_three():
    # 接线断言（plan R1-M9）：ch8 基线语料「添第三个名字」⇒ 鉴录名数=3。
    # counter-dup 的互斥判红依赖这个 3 不是硬编码。
    assert _ch08_baseline_count() == 3


@pytest.mark.unit
def test_mutant_name_swap_killed_by_f15():
    # ch20 pre-rev：叙述段林烽×10+（主语误名伤口）⇒ F15 必须拦
    identity = {"narration_name": "那罕", "from_ch": 3, "aliases": ["林烽"]}
    issues = check_narration_name(CH20_WOUND.read_text(encoding="utf-8"), identity, "", chapter=20)
    assert any(i.startswith("XC.narration_name:") for i in issues)


@pytest.mark.unit
def test_mutant_prop_chain_break_killed_by_f16():
    # ch20 pre-rev L218：帖木哥交哨无 memo 声明（无源交付伤口）⇒ F16 必须拦。
    # known_names 传生产同款 roster（spec §4 人名要件，2026-10-29 实弹校准）
    props = {"火纹骨哨": {"owner": "那罕"}}
    issues = check_prop_handoffs(
        CH20_WOUND.read_text(encoding="utf-8"),
        "",
        props,
        known_names={"那罕", "帖木哥", "林烽"},
    )
    assert any("cd.prop_handoff:" in i for i in issues)


@pytest.mark.unit
def test_mutant_counter_dup_killed_by_f17():
    # ch9 pre-rev「第一页两个名字」vs ch8 基线 3（跨文件互斥）⇒ F17 必须拦。
    # 基线值从 ch08 fixture 派生（非硬编码 3）——mutant 语料与基线语料同源对账
    counters = {"鉴录名数": {"value": _ch08_baseline_count()}}
    memo = "- 计数: 鉴录名数 2+1"  # pre-rev 备忘：把赵三当第三个——与 ch8 冲突
    issues = check_counter_reconciliation(CH09_DUP.read_text(encoding="utf-8"), memo, counters)
    # spec #83 T9：子 id 形 cd.counter.<arm>:（r5 基值==facts 口径——base_mismatch 拦本 mutant）
    assert any("cd.counter." in i for i in issues)


# ── 绿语料对极（防误报面；完整 as-of 终态断言在 T13 test_facts_backfill）──


@pytest.mark.unit
def test_green_ch20_fixed_passes_f15_and_f16():
    text = CH20_GREEN.read_text(encoding="utf-8")
    identity = {"narration_name": "那罕", "from_ch": 3, "aliases": ["林烽"]}
    assert check_narration_name(text, identity, "", chapter=20) == []
    props = {"火纹骨哨": {"owner": "那罕"}}
    memo = "- 火纹骨哨·帖木哥支@acquire: 那罕（ch20 灯座交付）\n"
    assert check_prop_handoffs(text, memo_text=memo, props=props) == []


@pytest.mark.unit
def test_green_ch9_fixed_passes_f17():
    # 修复后 ch9：第一页三个名字 ≡ 基线 3；序数第四 ≡ 声明 3+1=4
    text = "那罕把《鉴录》摊在膝盖上。第一页三个名字，写得规矩。\n\n他添了第四个名字——赵三。"
    memo = "- 计数: 鉴录名数 3+1"
    counters = {"鉴录名数": {"value": _ch08_baseline_count()}}
    assert check_counter_reconciliation(text, memo, counters) == []
