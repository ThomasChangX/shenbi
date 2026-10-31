"""spec #83 T9: counter anchor N+M parsing + three FAIL arms + anchored prose.

r5 corpus baselines: ch28 dual declaration (4+0 vs 4 +1) -> plan_conflict
red; +0 six chapters base==facts all green; ch9 temporal 3+1 green at
check-time facts=3; ch30 ship-list/rhetorical/POST anchoring negatives.
"""

from __future__ import annotations

from pathlib import Path

from shenbi.gates.g4.chapter_drafting import (
    check_counter_reconciliation,
    parse_counter_declarations,
)
from shenbi.gates.g4.shadow import GATE_TO_SHADOW_KEY

FIX = Path(__file__).resolve().parents[3] / "fixtures" / "spec83"


def _plan() -> str:
    return (FIX / "plans" / "chapter-28-plan.md").read_text(encoding="utf-8")


def test_parse_n_plus_m_full_forms() -> None:
    # r5 回放：旧正则全语料 9 条声明仅捕 2 条（+0 六章全盲）——N+M 全形态含空格变体
    decls = parse_counter_declarations(
        "- 计数: 鉴录名数 4+0\n- 计数: 鉴录名数 4 +1\n- 计数: 鉴录名数 3+1\n"
    )
    assert (
        ("鉴录名数", 4, 0) in decls and ("鉴录名数", 4, 1) in decls and ("鉴录名数", 3, 1) in decls
    )


def test_plan_conflict_ch28_dual_declaration() -> None:
    # ch28 :88 4+0（final 4）vs :100 4 +1（final 5）→ finals {4,5} 互斥稳红
    text = (FIX / "chapters" / "chapter-28.md").read_text(encoding="utf-8")
    issues = check_counter_reconciliation(
        text, _plan(), {"鉴录名数": {"value": 4}}, fp="chapters/chapter-28.md"
    )
    assert any("cd.counter.plan_conflict" in i for i in issues)


def test_base_mismatch_and_plus_zero_green() -> None:
    # +0 六章 base4==facts4 全绿；base≠facts 红（r5 回放：r4 旧判据对 +0 全误红）
    issues_bad = check_counter_reconciliation(
        "正文。", "- 计数: 鉴录名数 5+0\n", {"鉴录名数": {"value": 4}}, fp="x"
    )
    assert any("cd.counter.base_mismatch" in i for i in issues_bad)
    issues_ok = check_counter_reconciliation(
        "正文。", "- 计数: 鉴录名数 4+0\n", {"鉴录名数": {"value": 4}}, fp="x"
    )
    assert not any("base_mismatch" in i or "plan_conflict" in i for i in issues_ok)


def test_ch9_temporal_green_with_check_time_facts() -> None:
    # r5.1：ch9 3+1 在 check 时点 facts=3 时序绿（照抄终态 4 会得红测）
    issues = check_counter_reconciliation(
        "正文。", "- 计数: 鉴录名数 3+1\n", {"鉴录名数": {"value": 3}}, fp="x"
    )
    assert not any("base_mismatch" in i or "plan_conflict" in i for i in issues)


def test_prose_anchor_same_sentence_ch30() -> None:
    # ch30 回放：:154《鉴录》上四个名字 真命中；:58 船单七个名字（无锚词）排除；
    # :176 一个名字（修辞）排除；:186 POST 行剥 META 排除——双误红全消
    ch30 = (FIX / "chapters" / "chapter-30.md").read_text(encoding="utf-8")
    issues = check_counter_reconciliation(
        ch30, "- 计数: 鉴录名数 4+0\n", {"鉴录名数": {"value": 4}}, fp="x"
    )
    assert not any("prose_mismatch" in i for i in issues)
    # 负控制：锚词同句异值红（四个→五个不在允许集）
    fake = "《鉴录》上五个名字排开。\n"
    issues_red = check_counter_reconciliation(
        fake, "- 计数: 鉴录名数 4+0\n", {"鉴录名数": {"value": 4}}, fp="x"
    )
    assert any("prose_mismatch" in i for i in issues_red)


def test_ordinal_face_kept() -> None:
    # characterization：F17 序数判定保留（final 5 == 序数 5）
    issues = check_counter_reconciliation(
        "第五个名字", "- 计数: 鉴录名数 4+1\n", {"鉴录名数": {"value": 4}}, fp="x"
    )
    assert issues == []


def test_unknown_counter_emission_id_first() -> None:
    # :623-626 旧发射 `cd.counter:{fp}:…`（无 G4. 前缀）——扩族同步改 id-first 由调用点测试承载；
    # 此处钉 shadow 登记（§10 行 5/6/7）
    for row in ("plan_conflict", "base_mismatch", "prose_mismatch"):
        assert GATE_TO_SHADOW_KEY[f"cd.counter.{row}"] == ("market_params", "counter_anchor")


def test_zero_revision_single_decl_no_conflict() -> None:
    # 单声明章（ch25/26/27/29/30/36 形）：4+0 单条不触发 plan_conflict
    issues = check_counter_reconciliation(
        "正文。", "- 计数: 鉴录名数 4+0\n", {"鉴录名数": {"value": 4}}, fp="x"
    )
    assert not any("plan_conflict" in i for i in issues)
