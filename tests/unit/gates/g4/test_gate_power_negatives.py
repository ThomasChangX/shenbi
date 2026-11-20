"""Spec #116 T4: real-chapter mutation → gate FAIL red tests (prose face)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

FIX_DIR = Path(__file__).resolve().parents[3] / "fixtures" / "gate-power"  # NB2：parents[3]=tests/


def _g4(fixture_name: str) -> dict[str, Any]:
    fp = str(FIX_DIR / fixture_name)
    from shenbi.gates.g4.chapter_drafting import g4_chapter_drafting

    return json.loads(g4_chapter_drafting([fp], str(FIX_DIR), str(FIX_DIR), repo_root=None))


def test_hook_killed_real_chapter_fails_hook_gate() -> None:
    """真实章变异→FAIL：章尾窗口张力全部抹除（spec 验收 5 最低子集之一）。"""
    res = _g4("chapter-1-hook-killed.md")
    mf = res.get("must_fix", [])
    assert any(m.startswith("G4.cd.no_hook:") for m in mf), mf[:3]


def test_protagonist_vanished_real_chapter_fails_presence_gate() -> None:
    """C2：真臂=protagonist_absent（major_chars 属他门；SKIP 需 characters 前置物）。"""
    res = _g4("chapter-1-protagonist-vanished.md")
    mf = res.get("must_fix", [])
    assert any(m.startswith("G4.cd.protagonist_absent:") for m in mf), mf[:3]


def test_transition_flooded_real_chapter_fails_transition_gate() -> None:
    res = _g4("chapter-1-transition-flooded.md")
    mf = res.get("must_fix", [])
    assert any(m.startswith("G4.transition:") for m in mf), mf[:3]


# ── spec #116 T4 Task 3：其余 in-scope 门变异负例（12 FAIL 组＋5 WARN-only＋5 helper 级）──


def test_scene_visuals_stripped_fails_concreteness_gate() -> None:
    """尾窗段视觉动词/对白全数剥除 → 全窗口无 vn/di 段 → no_visual_scene."""
    res = _g4("chapter-1-scene-visuals-stripped.md")
    mf = res.get("must_fix", [])
    assert any(m.startswith("G4.cd.no_visual_scene:") for m in mf), mf[:3]


def test_scene_markers_removed_fails_scene_count_gate() -> None:
    """场景标记行删除（--full：裁片本无标记，红须来自变异非裁片副作用，NB6）."""
    res = _g4("chapter-1-scene-markers-removed.md")
    mf = res.get("must_fix", [])
    assert any(m.startswith("G4.cd.scene_count:") and "<2" in m for m in mf), mf[:3]


def test_fatigue_flooded_fails_fatigue_gate() -> None:
    """「他心中暗道。」×9 段尾追加（FATIGUE_BASE 暗道面）→ 9>8."""
    res = _g4("chapter-1-fatigue-flooded.md")
    mf = res.get("must_fix", [])
    assert any(m.startswith("G4.fatigue:") and ">8" in m for m in mf), mf[:3]


def test_meta_injected_fails_meta_gate() -> None:
    """META_NARRATIVE 闭集词段（由此可见/综上所述）插入 → meta."""
    res = _g4("chapter-1-meta-injected.md")
    mf = res.get("must_fix", [])
    assert any(m.startswith("G4.meta:") and "由此可见" in m for m in mf), mf[:3]


def test_word_count_truncated_fails_word_count_gate() -> None:
    """正文截断（保 PRE/POST 块）→ total < floor（--full 面，NB6）."""
    res = _g4("chapter-1-word-count-truncated.md")
    mf = res.get("must_fix", [])
    assert any(m.startswith("G4.word_count:") and "<" in m for m in mf), mf[:3]


def test_post_removed_fails_post_check_gate() -> None:
    """删 POST META 块 → post_check（--full：裁片不含 POST，红须来自变异，NB6）."""
    res = _g4("chapter-1-post-removed.md")
    mf = res.get("must_fix", [])
    assert any(m.startswith("G4.post_check:") for m in mf), mf[:3]


def test_pre_removed_fails_pre_check_gate() -> None:
    """删 PRE META 块 → pre_check（--full 面，同 NB6）."""
    res = _g4("chapter-1-pre-removed.md")
    mf = res.get("must_fix", [])
    assert any(m.startswith("G4.pre_check:") for m in mf), mf[:3]


def test_voice_stripped_fails_voice_density_gate() -> None:
    """口癖短语→中性语（v4 memo＋真实卡 catchphrases 前置物）→ signals<min."""
    res = _g4("chapter-1-voice-stripped.md")
    mf = res.get("must_fix", [])
    assert any(m.startswith("G4.cd.voice_density:") for m in mf), mf[:3]


def test_hookdecl_mismatched_fails_scene_hook_match_gate() -> None:
    """Plan 场景2 收束钩改「悬念」形 vs 章尾实拍 → scene_hook_match（场景2 臂）.

    被测章=post-removed 全章件（SCENE 标记在）；变异产物=plans/chapter-1-plan.md。
    """
    res = _g4("chapter-1-post-removed.md")
    mf = res.get("must_fix", [])
    assert any(m.startswith("G4.cd.scene_hook_match:") and "场景2" in m for m in mf), mf[:3]


def test_post_quote_broken_fails_post_quote_verbatim_gate() -> None:
    """POST 金句位引句改一字 → 声明子句缺席 FAIL 臂（--full 面）."""
    res = _g4("chapter-1-post-quote-broken.md")
    mf = res.get("must_fix", [])
    assert any(m.startswith("G4.cd.post_quote_verbatim:") and "声明子句缺席" in m for m in mf), mf[
        :3
    ]


def test_post_transition_lied_fails_post_transition_cross_gate() -> None:
    """章中注入连接词而 POST 仍报转折 0 → post_transition_cross FAIL（--full 面）."""
    res = _g4("chapter-1-post-transition-lied.md")
    mf = res.get("must_fix", [])
    assert any(m.startswith("G4.cd.post_transition_cross:") for m in mf), mf[:3]


def test_golden_emptied_warns_golden_slot() -> None:
    """PRE 金句位值→无 → golden_slot WARN 行（负例=WARN-only，非 must_fix）."""
    res = _g4("chapter-1-golden-emptied.md")
    rows = [c for c in res["checks"] if c["id"] == "G4.cd.golden_slot"]
    assert rows and rows[0]["s"] == "WARN" and "PRE lacks" in rows[0]["r"], rows


def test_post_wordcount_lied_warns_precision() -> None:
    """POST 总计改半（3625→1812）→ post_wordcount_precision WARN 行（I2）."""
    res = _g4("chapter-1-post-wordcount-lied.md")
    rows = [c for c in res["checks"] if c["id"] == "cd.post_wordcount_precision"]
    assert rows and rows[0]["s"] == "WARN" and "1812" in rows[0]["r"], rows


# ── WARN-only 组（负例=断言 check 行 s=="WARN"；surge/post_wordcount 无 mf 臂）──


def test_surge_killed_warns_surge_quota_gap(tmp_path: Path) -> None:
    """尾窗长句切短 → surge 0 < quota 1 → WARN 行.

    实跑面=剥 provenance 头的 tmp 副本：头块 4 行 ASCII ≥35 字会被 segment_sentences
    计为 surge 句（fixture 元数据伪影——真实章无此头，strip_narrative_body 不剥
    通用 HTML 注释属设计面非门缺陷；报告＋README 登记，供 Task 4/5 消费）。
    """
    from shenbi.gates.g4.chapter_drafting import g4_chapter_drafting

    src = (FIX_DIR / "chapter-1-surge-killed.md").read_text(encoding="utf-8")
    ch = tmp_path / "chapter-1-surge-killed.md"
    ch.write_text(src.split("-->\n\n", 1)[1], encoding="utf-8")
    res = json.loads(g4_chapter_drafting([str(ch)], str(tmp_path), str(tmp_path), repo_root=None))
    rows = [c for c in res["checks"] if c["id"] == "G4.cd.surge"]
    assert rows and rows[0]["s"] == "WARN" and "0 < quota 1" in rows[0]["r"], rows


def test_simile_flooded_warns_pileup_side() -> None:
    """堆叠 6 喻体句 → per_1000 > 4（堆叠侧；基线裁片为干侧 0.0——侧别钉死）."""
    res = _g4("chapter-1-simile-flooded.md")
    rows = [c for c in res["checks"] if c["id"] == "G4.cd.simile_band"]
    assert rows and rows[0]["s"] == "WARN" and rows[0].get("per_1000", 0.0) > 4.0, rows


def test_ending_repeated_helper_three_ledger_closers() -> None:
    """Helper 级：三真实章尾窗各追记账目收束句 → ending_archetype_of 三连「账目形态」."""
    from shenbi.gates.g4.chapter_drafting import ending_archetype_of

    names = (
        "chapter-1-ending-ledgered.md",
        "chapter-2-ending-ledgered.md",
        "chapter-3-ending-ledgered.md",
    )
    arch = [ending_archetype_of((FIX_DIR / n).read_text(encoding="utf-8")) for n in names]
    assert arch == ["账目形态"] * 3, arch


# ── helper 级红测（truth/历史上下文；构造性输入 inline，G0.9 允许面）──


def test_prop_handoff_helper_flags_undeclared_handoff() -> None:
    """物象+交接动词+非 owner 人名共现而备忘无声明 → cd.prop_handoff issue."""
    from shenbi.gates.g4.chapter_drafting import check_prop_handoffs

    prose = "小满把骨哨递给那罕，转身走了。"
    issues = check_prop_handoffs(prose, "", {"骨哨": {"owner": "老驼"}}, {"小满", "老驼"}, {})
    assert issues and "cd.prop_handoff" in issues[0] and "骨哨" in issues[0], issues


def test_counter_reconciliation_helper_flags_plan_prose_conflict() -> None:
    """N+M 声明基值≠facts 现值＋正文总数/序数 ∉ 允许集 → counter 三臂 issue."""
    from shenbi.gates.g4.chapter_drafting import check_counter_reconciliation

    memo = "- 计数: 鉴录名数 5+1"
    prose = "《鉴录》上如今共六个名字。鉴录里第七个名字空着。"
    issues = check_counter_reconciliation(prose, memo, {"鉴录名数": {"value": 4}}, fp="x.md")
    assert any(i.startswith("cd.counter.base_mismatch") for i in issues), issues
    assert any(i.startswith("cd.counter.prose_mismatch") for i in issues), issues


def test_balance_drift_skip_path_warns_when_ledger_absent() -> None:
    """Balance 实勘：facts/ledger 缺席 → WARN 可见 skip（负例=附录 A 实弹 7 FAIL 已证）."""
    res = _g4("chapter-1-hook-killed.md")
    rows = [c for c in res["checks"] if c["id"] == "cd.balance_value_drift"]
    assert rows and rows[0]["s"] == "WARN" and "particle_ledger.md absent" in rows[0]["r"], rows


def test_quote_verbatim_full_pipeline_fails_on_nonverbatim_anchor() -> None:
    """全管线：v4 memo『』锚定引句（plan 原句）≠ 章尾实拍 → quote_verbatim FAIL 臂."""
    res = _g4("chapter-1-fatigue-flooded.md")
    mf = res.get("must_fix", [])
    assert any(m.startswith("G4.cd.quote_verbatim:") and "不在本章正文" in m for m in mf), mf[:3]


def test_hook_type_rotation_full_pipeline_fails_on_same_type() -> None:
    """全管线：ch0 台账与 ch1 memo 同「悬念钩」→ hook_type_rotation FAIL（ch1）."""
    res = _g4("chapter-1-meta-injected.md")
    mf = res.get("must_fix", [])
    assert any(m.startswith("G4.cd.hook_type_rotation:ch1:") for m in mf), mf[:3]


def test_content_duplicated_fails_content_overlap_gate() -> None:
    """从比对章（chapter-3.md 同目录）复制 13 段 append 章尾 → 指纹占比 >40%（I3 三条件齐）."""
    res = _g4("project-output/chapters/chapter-1-duplicated.md")
    mf = res.get("must_fix", [])
    assert any(m.startswith("G4.cd.content_overlap:") for m in mf), mf[:3]


def test_payoff_stripped_warns_payoff_density() -> None:
    """Spec #118 T8：chapter-9 plan 的 **payoff 拍** 轴登记被删 → payoff_density WARN 行.

    负例=WARN-only（该门无 mf 臂）；变异产物=plans/chapter-9-plan.md
    （引擎 payoff_axis_stripped）＋配对章 chapter-9-payoff-stripped.md（verbatim
    --full）。窗口 k∈{7,8,9}：7/8 plan fixture 缺席＋9 轴被删 → 无轴 WARN 必发。
    """
    res = _g4("chapter-9-payoff-stripped.md")
    rows = [c for c in res["checks"] if c["id"] == "G4.cd.payoff_density"]
    assert rows and rows[0]["s"] == "WARN" and "无轴登记" in rows[0]["r"], rows


def test_voice_density_two_level_three_states(tmp_path: Path) -> None:
    """Spec #118 T1 裁定 B 三态：0 FAIL / 1 类在场过＋密度 WARN / ≥2 纯 PASS.

    构造性输入（G0.9 允许面——结构级样本基于真实 fixture）：复用重生成后的
    voice-stripped fixture（signals=0）＋真实卡/plan 前置物，逐态注入。
    """
    import shutil

    from shenbi.gates.g4.chapter_drafting import g4_chapter_drafting

    for label, inject, want_fail, want_warn in (
        ("absent", "", True, False),  # signals=0 → FAIL（=旧测同 fixture 面）
        ("presence-only", "他心想：这笔我先记下。", False, True),  # 真实卡口癖原串逐字在场 → 1 类
        (
            "dense",
            "他心想：这笔我先记下。入账的时辰到了。",
            False,
            False,
        ),  # 口癖＋账房动词「入账」→ 2 类
    ):
        d = tmp_path / label
        d.mkdir()
        for sub in ("characters", "plans"):
            shutil.copytree(FIX_DIR / sub, d / sub, dirs_exist_ok=True)
        base = (FIX_DIR / "chapter-1-voice-stripped.md").read_text(encoding="utf-8")
        (d / "chapter-1.md").write_text(base.rstrip("\n") + f"\n\n{inject}\n", encoding="utf-8")
        res = json.loads(
            g4_chapter_drafting([str(d / "chapter-1.md")], str(d), str(d), repo_root=None)
        )
        mf = res.get("must_fix", [])
        warn_rows = [
            c for c in res["checks"] if c["id"] == "G4.cd.voice_density" and c["s"] == "WARN"
        ]
        assert any(m.startswith("G4.cd.voice_density:") for m in mf) == want_fail, (label, mf[:3])
        assert bool(warn_rows) == want_warn, (label, warn_rows)


def test_voice_old_key_maps_to_density_arm(tmp_path: Path) -> None:
    """Spec #118 T1(a) 映射钉：genre-config 旧键 min_per_chapter=2 时 signals=1 的章不 FAIL（密度 WARN 在）.

    旧键若映射进 hard 臂，两级化裁定在携带旧覆盖的项目（vol1 实况）上静默
    不生效——本钉把「旧键→密度臂」语义锁进断言（风险 M-6 测试断言义务）。
    """
    import json as _json
    import shutil

    from shenbi.gates.g4.chapter_drafting import g4_chapter_drafting

    d = tmp_path / "proj"
    d.mkdir()
    for sub in ("characters", "plans"):
        shutil.copytree(FIX_DIR / sub, d / sub, dirs_exist_ok=True)
    (d / "genre-config.json").write_text(
        json.dumps({"market_params": {"voice_density_min": {"min_per_chapter": 2}}}),
        encoding="utf-8",
    )
    base = (FIX_DIR / "chapter-1-voice-stripped.md").read_text(encoding="utf-8")
    (d / "chapter-1.md").write_text(
        base.rstrip("\n") + "\n\n他心想：这笔我先记下。\n", encoding="utf-8"
    )
    res = _json.loads(
        g4_chapter_drafting([str(d / "chapter-1.md")], str(d), str(d), repo_root=None)
    )
    mf = res.get("must_fix", [])
    assert not any(m.startswith("G4.cd.voice_density:") for m in mf), mf[:3]
    warn_rows = [c for c in res["checks"] if c["id"] == "G4.cd.voice_density" and c["s"] == "WARN"]
    assert warn_rows and "1<2" in warn_rows[0]["r"], warn_rows


def test_hook_single_char_only_warns_not_fails() -> None:
    """Spec #118 T2 裁定 A：单字-only 命中→WARN 行非 FAIL（三态中间档）.

    fixture=引擎 hook_single_only 变异（多字→『还』、？→。、数字串→数）——
    多字/？/账目行臂全灭、单字臂保留。
    """
    res = _g4("chapter-1-hook-single-only.md")
    rows = [c for c in res["checks"] if c["id"] == "G4.cd.chapter_end_hook"]
    mf = res.get("must_fix", [])
    assert rows and rows[0]["s"] == "WARN" and "单字" in rows[0]["r"], rows
    assert not any(m.startswith("G4.cd.no_hook:") for m in mf), mf[:3]
