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
    issues = check_prop_handoffs(text, memo_text="", props=props, known_names={"那罕", "帖木哥"})
    assert any("cd.prop_handoff:" in i for i in issues)


def test_pronoun_only_self_handling_not_flagged():
    # spec #80 §4 触发三要件=「非 owner 人名」+实体+交接动词——纯代词自持段
    # （POV 密着叙事常规形态，2026-10-29 ch25 L198 实弹：他从枕下抽出《鉴录》）
    # 不在人名要件内，不触发；硬拒收留给 settle F16s（T8）状态机
    text = "他从枕下抽出《鉴录》，翻到夹着存根的那一页。四个名字，一个没多，一个没少。"
    props = {"半部《鉴录》": {"owner": "那罕"}}
    issues = check_prop_handoffs(
        text, memo_text="", props=props, known_names={"那罕", "帖木哥", "完颜嫂"}
    )
    assert issues == []


def test_unknown_actor_paragraph_degrades_silent():
    # 未入册行为人（无已知人名）+ 交接动词——drafting 层不触发（拿不到非 owner
    # 人名要件），硬拒收仍在 settle F16s；边界入册防回归
    text = "那人把骨哨揣进怀里，转身走了。"
    props = {"火纹骨哨": {"owner": "那罕"}}
    issues = check_prop_handoffs(text, memo_text="", props=props, known_names={"那罕", "帖木哥"})
    assert issues == []


def test_declared_handoff_passes():
    text = "帖木哥把骨哨抽出来，递给那罕。"
    props = {"火纹骨哨": {"owner": "那罕"}}
    memo = "- 火纹骨哨@transfer: 帖木哥→那罕\n"
    issues = check_prop_handoffs(text, memo_text=memo, props=props, known_names={"那罕", "帖木哥"})
    assert issues == []


def test_short_name_form_caught():
    # R3-M2 三形态匹配器：末两字缩称「骨哨」命中（ch20 L230 形态）。
    # spec #80 §4 语义修正（2026-10-29 实弹）：触发须段内有具名非 owner——
    # 原代词主语形（他把骨哨揣进怀里）不构成人名要件，改具名行为人保形
    text = "帖木哥把骨哨揣进怀里，贴身自己那把跟着温了一下。"
    props = {"火纹骨哨": {"owner": "那罕"}}
    issues = check_prop_handoffs(text, memo_text="", props=props, known_names={"那罕", "帖木哥"})
    assert any("cd.prop_handoff:" in i for i in issues)


def test_owner_alias_counts_as_owner_presence():
    # identity 别名=同一人：owner=那罕（narration）时林烽在场视同 owner 在场
    text = "林烽把骨哨揣进怀里。"
    props = {"火纹骨哨": {"owner": "那罕"}}
    issues = check_prop_handoffs(
        text,
        memo_text="",
        props=props,
        known_names={"那罕", "帖木哥", "林烽"},
        owner_aliases={"那罕": {"林烽"}},
    )
    assert issues == []


def test_currency_suffixed_entity_no_short_form_collision():
    # 交易名实体（灯油四文/灯油三文）的金额尾不是短称——「馍四文半」计数
    # 散文不得命中（2026-10-29 ch25 实弹：完颜嫂市场章交易动词+具名+四文半
    # 三要件齐 → 伪交接报）。全键命中仍然有效
    from shenbi.gates.g4.chapter_drafting import entity_in_text

    assert entity_in_text("灯油四文", "馒头四文半，塞给完颜嫂。") is False
    assert entity_in_text("灯油三文", "他数出三文钱。") is False
    assert entity_in_text("灯油四文", "灯油四文收了。") is True
    assert entity_in_text("火纹骨哨", "他把骨哨揣进怀里。") is True


def test_cross_sentence_verb_not_entity_handoff():
    # 句级共现校准（2026-10-29 ch25 实弹二撞）：「他在私账上写下这个数。
    # ……二十二文半还了老周，七文半给了完颜嫂」——交接动词的宾语是钱不是
    # 私账（跨句段落级合并把付钱误判成交账）；人名要件保持段级
    text = "他在私账上写下这个数，笔尖顿了顿。昨日是一百四十三，今天出去三十。三十文里，二十二文半还了老周，七文半给了完颜嫂。"
    props = {"半页私账": {"owner": "那罕"}}
    issues = check_prop_handoffs(
        text, memo_text="", props=props, known_names={"那罕", "完颜嫂", "老周"}
    )
    assert issues == []


def test_same_sentence_real_handoff_still_fires():
    # 真交接（同句实体+动词+具名非 owner）不放松——句级收紧只剥跨句伪报
    text = "他把私账递给完颜嫂看，指给她那一栏空白。"
    props = {"半页私账": {"owner": "那罕"}}
    issues = check_prop_handoffs(text, memo_text="", props=props, known_names={"那罕", "完颜嫂"})
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
