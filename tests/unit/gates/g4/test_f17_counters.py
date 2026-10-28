"""T7: F17——计数器三方对账（spec #80 §4 F17；ch8↔ch9 计数互斥伤口）。"""

from __future__ import annotations

from pathlib import Path

from shenbi.gates.g4.chapter_drafting import (
    check_counter_reconciliation,
    parse_counter_declarations,
)

FIXTURE = Path("tests/fixtures/invariant-mutants/ch09-counter-dup.md")
GREEN = Path("tests/fixtures/invariant-mutants/ch20-fixed-green.md")


def test_parse_counter_declaration():
    # R4-M4: int = 声明值 N+1（解析后值），非基值 N
    decls = parse_counter_declarations("- 计数: 鉴录名数 3+1\n- 计数: 他项 5+1")
    assert decls[0] == ("鉴录名数", 4)
    assert decls[1] == ("他项", 6)


def test_parse_ignores_non_counter_lines():
    assert parse_counter_declarations("- 计数说明: 无声明") == []


def test_wound_total_vs_facts_baseline_fails():
    # counter-dup 击杀面①：prose 总数族 2 ≠ facts 现值 3。
    # 面①在 memo 声明该计数器时激活（R2-I4b——ch17 全书口径无声明即跳，
    # 假红防线）；pre-rev 备忘语义=以为基线 2（声明 2+1），与 ch8 基线 3 互斥
    text = FIXTURE.read_text(encoding="utf-8")
    memo = "- 计数: 鉴录名数 2+1"
    counters = {"鉴录名数": {"value": 3}}
    issues = check_counter_reconciliation(text, memo, counters)
    assert any("cd.counter:" in i for i in issues)


def test_wound_ordinal_vs_memo_declared_fails():
    # 击杀面③：prose 序数「第三个」≠ memo 声明值 4（3+1）
    text = "他添了第三个名字——赵三。"
    memo = "- 计数: 鉴录名数 3+1"
    counters = {"鉴录名数": {"value": 3}}
    issues = check_counter_reconciliation(text, memo, counters)
    assert any("cd.counter:" in i for i in issues)


def test_green_fixed_ch9_passes():
    # 修复后 ch9：第一页三个名字 ≡ facts 3；序数第四 ≡ 声明 3+1=4
    text = "那罕把《鉴录》摊在膝盖上。第一页三个名字，写得规矩。\n\n他添了第四个名字——赵三。"
    memo = "- 计数: 鉴录名数 3+1"
    counters = {"鉴录名数": {"value": 3}}
    issues = check_counter_reconciliation(text, memo, counters)
    assert issues == []


def test_page_qualifier_ignored():
    # R5-M3：页范围总数锚忽略页限定词，取全局计数器比对
    text = "第一页三个名字，写得规矩。"
    counters = {"鉴录名数": {"value": 3}}
    issues = check_counter_reconciliation(text, memo_text="", counters=counters)
    assert issues == []


def test_no_declaration_warn_skip():
    # 激活规则 R2-I4b：memo 无该计数器声明 ⇒ WARN skip（函数直调形态=空 issues，
    # WARN 判定在 g4.cd 调用点——R3-M1）
    text = "第一页两个名字。"  # 与 facts 3 不符，但无声明
    counters = {"鉴录名数": {"value": 3}}
    issues = check_counter_reconciliation(text, memo_text="", counters=counters)
    assert issues == []


def test_memo_n_plus_one_vs_facts_fails():
    # 击杀面②：memo 2+1=3 ≠ facts 3+1=4
    text = "他添了第四个名字。"
    memo = "- 计数: 鉴录名数 2+1"
    counters = {"鉴录名数": {"value": 3}}
    issues = check_counter_reconciliation(text, memo, counters)
    assert any("cd.counter:" in i for i in issues)
