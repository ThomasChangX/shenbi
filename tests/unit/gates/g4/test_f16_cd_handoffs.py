"""T5: F16 G4.cd——正文无源交付拍拦截 + 实体副本 + XC 吸收（spec #80 §4 F16）。

伤口语料=真实导出 fixtures（G0.9）；facts 态种子=测试内构造（spec §3 豁免面）。
"""

from __future__ import annotations

import json
from pathlib import Path

from shenbi.gates.g4.chapter_drafting import check_prop_handoffs
from shenbi.gates.g4.chapter_planning import g4_chapter_planning

FIXTURE = Path("tests/fixtures/invariant-mutants/ch20-name-swap-prop-break.md")


def test_wound_undeclared_handoff_fails():
    text = FIXTURE.read_text(encoding="utf-8")
    # fixture L218 区域：帖木哥从灯座下抽出骨哨、这个你揣着——交接动词+非 owner
    props = {"火纹骨哨": {"owner": "那罕"}}
    issues = check_prop_handoffs(text, memo_text="", props=props)
    assert any("cd.prop_handoff:" in i for i in issues)


def test_declared_handoff_passes():
    text = "帖木哥把骨哨抽出来，递给那罕。"
    props = {"火纹骨哨": {"owner": "那罕"}}
    memo = "- 火纹骨哨@transfer: 帖木哥→那罕\n"
    issues = check_prop_handoffs(text, memo_text=memo, props=props)
    assert issues == []


def test_short_name_form_caught():
    # R3-M2 三形态匹配器：末两字缩称「骨哨」命中（ch20 L230 形态）
    text = "他把骨哨揣进怀里，贴身自己那把跟着温了一下。"
    props = {"火纹骨哨": {"owner": "那罕"}}
    issues = check_prop_handoffs(text, memo_text="", props=props)
    assert any("cd.prop_handoff:" in i for i in issues)


def test_copy_entity_coexistence_green():
    # 修复后 ch20 双实体并存全绿（plan 副本语义硬约束）
    fixed = (FIXTURE.parent / "ch20-fixed-green.md").read_text(encoding="utf-8")
    props = {"火纹骨哨": {"owner": "那罕"}}
    # 修复文本中交付由帖木哥给出且 memo（backfill 后）声明 帖木哥支 acquire
    memo = "- 火纹骨哨·帖木哥支@acquire: 那罕（ch20 灯座交付）\n"
    issues = check_prop_handoffs(fixed, memo_text=memo, props=props)
    # 主线哨（owner=那罕）不经手转移；帖木哥支是新实体不在 props 键内
    assert issues == []


def test_owner_self_handoff_not_flagged():
    # owner 自己的动作（那罕把骨哨揣进怀里）不是转移
    text = "那罕把骨哨揣进怀里。"
    props = {"火纹骨哨": {"owner": "那罕"}}
    issues = check_prop_handoffs(text, memo_text="", props=props)
    assert issues == []


# ── audit-T4 M2 补：hold 分支 wrong-owner FAIL ──


def test_hold_wrong_owner_fails_at_cp(tmp_path: Path):
    facts_dir = tmp_path / "truth" / "facts"
    facts_dir.mkdir(parents=True, exist_ok=True)
    (facts_dir / "props.json").write_text(
        json.dumps(
            {
                "$schema": "shenbi-facts-v1",
                "dim": "props",
                "facts": {"火纹骨哨": {"entity": "火纹骨哨", "owner": "那罕", "events": []}},
                "ops_log": [],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    plans = tmp_path / "plans"
    plans.mkdir(exist_ok=True)
    memo = plans / "chapter-5-plan.md"
    memo.write_text(
        "---\nplan_format: v3\n---\n\n# 备忘\n\n- 火纹骨哨@hold: 老驼\n",
        encoding="utf-8",
    )
    out = g4_chapter_planning([str(memo)], project_dir=str(tmp_path))
    assert "cp.prop_decl:" in out


# ── audit-T5 I3 补：XC 吸收/回退回归守卫 ──


def test_xc_absorption_stands_down_with_facts(tmp_path: Path):
    from shenbi.gates.g4.cross_chapter import (
        CrossChapterContext,
        check_cross_chapter,
    )

    ch = tmp_path / "chapter-2.md"
    ch.write_text("他把骨哨递给帖木哥。", encoding="utf-8")
    prev = tmp_path / "chapter-1.md"
    prev.write_text("开头。", encoding="utf-8")
    ctx_absorbed = CrossChapterContext(props_facts={"火纹骨哨": "那罕"})
    issues = check_cross_chapter(ch, prev, None, ctx_absorbed)
    assert not any("物象" in i for i in issues)  # 职责已让位 G4.cd


def test_xc_fallback_full_severity_without_facts(tmp_path: Path):
    from shenbi.gates.g4.cross_chapter import (
        CrossChapterContext,
        check_cross_chapter,
    )

    ch = tmp_path / "chapter-2.md"
    ch.write_text("他把骨哨递给帖木哥。", encoding="utf-8")
    prev = tmp_path / "chapter-1.md"
    prev.write_text("开头。", encoding="utf-8")
    ctx_fallback = CrossChapterContext()  # 无 facts：全 severity 回退层
    issues = check_cross_chapter(ch, prev, None, ctx_fallback)
    # registry 缺席 → known_props 空 → 无物象可查（不炸即回退层健在）
    assert isinstance(issues, list)
