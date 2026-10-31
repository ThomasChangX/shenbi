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
    # spec #83 T9：三元 (name, base, delta)——终值=base+delta（旧 2 元 N+1 形废除）
    decls = parse_counter_declarations("- 计数: 鉴录名数 3+1\n- 计数: 他项 5+1")
    assert decls[0] == ("鉴录名数", 3, 1)
    assert decls[1] == ("他项", 5, 1)


def test_parse_ignores_non_counter_lines():
    assert parse_counter_declarations("- 计数说明: 无声明") == []


def test_wound_total_vs_facts_baseline_fails():
    # counter-dup 击杀面①：prose 总数族 2 ≠ facts 现值 3。
    # 面①在 memo 声明该计数器时激活（R2-I4b——ch17 全书口径无声明即跳，
    # 假红防线）；pre-rev 备忘语义=以为基线 2（声明 2+1），与 ch8 基线 3 互斥
    # spec #83 T9：单调断裂判据被基值==facts 口径替代（r5：旧判据对 +0 全误红）——
    # 本伤口现由 base_mismatch 拦（基值 2 ≠ facts 3）
    text = FIXTURE.read_text(encoding="utf-8")
    memo = "- 计数: 鉴录名数 2+1"
    counters = {"鉴录名数": {"value": 3}}
    issues = check_counter_reconciliation(text, memo, counters)
    assert any("cd.counter.base_mismatch" in i for i in issues)


def test_wound_ordinal_vs_memo_declared_fails():
    # 击杀面③：prose 序数「第三个」≠ memo 声明终值 4（3+1）——spec #83 T9：
    # 锚定面要求锚词同句共现（r5 ch30 双误红排除；无锚句不判）
    text = "他把《鉴录》摊开，添了第三个名字——赵三。"
    memo = "- 计数: 鉴录名数 3+1"
    counters = {"鉴录名数": {"value": 3}}
    issues = check_counter_reconciliation(text, memo, counters)
    assert any("cd.counter.prose_mismatch" in i and "序数" in i for i in issues)


def test_green_fixed_ch9_passes():
    # 修复后 ch9：第一页三个名字 ≡ facts 3；序数第四 ≡ 声明 3+1=4
    text = "那罕把《鉴录》摊在膝盖上。第一页三个名字，写得规矩。\n\n他添了第四个名字——赵三。"
    memo = "- 计数: 鉴录名数 3+1"
    counters = {"鉴录名数": {"value": 3}}
    issues = check_counter_reconciliation(text, memo, counters)
    assert issues == []


def test_wound_prose_total_face_fails_alone():
    # audit-T11 I1 回归钉：总数族正则曾缺「个」（_TOTAL_RE 死代码、_re_total
    # 永不匹配自然形）——面①结构死，counter-dup 仅靠面②拦。本钉隔离面①：
    # memo 声明与 facts 单调一致（3+1=4=3+1），prose 总数 2 ∉ {3,4} 独立判红
    # spec #83 T9：锚词同句（「《鉴录》第一页两个名字」一句内共现）；面②（基值）
    # 与 facts 单调一致时静默=面④独立红
    text = "《鉴录》第一页两个名字，墨迹未干。"
    memo = "- 计数: 鉴录名数 3+1"
    counters = {"鉴录名数": {"value": 3}}
    issues = check_counter_reconciliation(text, memo, counters)
    assert any("prose_mismatch" in i and "总数" in i for i in issues)
    assert all("base_mismatch" not in i for i in issues)  # 面③静默=面④独立红


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
    # 击杀面③（spec #83 T9 改口径）：memo 基值 2 ≠ facts 现值 3——旧「N+1≠facts+1」
    # 单调判据被 r5 废除（+0 六章全误红）；断链伤口由 base_mismatch 拦
    text = "他添了第四个名字。"
    memo = "- 计数: 鉴录名数 2+1"
    counters = {"鉴录名数": {"value": 3}}
    issues = check_counter_reconciliation(text, memo, counters)
    assert any("cd.counter.base_mismatch" in i for i in issues)
