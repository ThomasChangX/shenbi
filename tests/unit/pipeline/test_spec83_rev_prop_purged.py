"""spec #83 T2: rev.prop_purged revision revalidation — r5 corpus baselines.

Zero-revision corpus all green (44 structured lines); purge red (entity in
pre-rev prose, gone in revised prose); legal absence green (held prop with
zero in-prose presence is a legal narrative state — relative predicate core).
"""

from __future__ import annotations

from pathlib import Path

from shenbi.gates.g4.shadow import GATE_TO_SHADOW_KEY
from shenbi.pipeline.chapter_loop import check_prop_purge_on_revision, parse_prop_lines

FIX = Path(__file__).resolve().parents[2] / "fixtures" / "spec83"


def _chapter(n: int) -> str:
    return (FIX / "chapters" / f"chapter-{n}.md").read_text(encoding="utf-8")


def test_parse_prop_lines_both_forms_deduped() -> None:
    plan = (FIX / "plans" / "chapter-28-plan.md").read_text(encoding="utf-8")
    lines = parse_prop_lines(plan)
    assert "火纹骨哨" in lines and "半部《鉴录》" in lines  # @hold 形（ch28:86/:87）
    assert len(lines) == len(set(lines))  # 同实体双声明形（@hold+物象:）去重保序


def test_zero_revision_corpus_all_green() -> None:
    # r5 回放：全语料零删改现状全绿（相对谓词 pre==post → 左元真右元假不成立……
    # 实为两侧同真 → 不红）
    text = _chapter(28)
    plan = (FIX / "plans" / "chapter-28-plan.md").read_text(encoding="utf-8")
    assert parse_prop_lines(plan)  # @hold + 物象: 行非空（ch28 实测形态）
    assert check_prop_purge_on_revision(text, text, plan, chapter=28) == []


def test_purge_detected() -> None:
    # 修订删尽红：真实章基底构造 post（结构测试豁免面）——pre 命中 post 不命中
    text = _chapter(28)
    plan = (FIX / "plans" / "chapter-28-plan.md").read_text(encoding="utf-8")
    purged = text.replace("骨哨", "口哨")  # 物象名整段消失形
    fails = check_prop_purge_on_revision(text, purged, plan, chapter=28)
    assert any("骨哨" in f and "rev.prop_purged:chapters/chapter-28.md" in f for f in fails)


def test_legal_absence_stays_green() -> None:
    # 零提及 → pre 侧不命中 → 谓词左元 false → 不红（相对口径核心；ch4/6/27 类）
    plan = "- 物象: 灰底采买旗|那罕\n"
    assert check_prop_purge_on_revision("别的正文", "改后的别的正文", plan, chapter=33) == []


def test_decl_block_excluded_by_strip_on_both_sides() -> None:
    # 两侧同口径 strip：PRE/POST 声明块自含物象名不得使 pre 侧恒真（r5.1 钉）
    plan = "- 物象: 火纹骨哨|那罕\n"
    prose_only = "正文一段。\n"
    with_decl = (
        prose_only + "\n## POST_WRITE_SELF_CHECK\n- [ ] 章尾张力（G4.cd 口径）: 火纹哨收好\n"
    )
    # with_decl 的声明块含「火纹哨」（三形短称命中）——strip 后两侧等价 → 不红
    assert check_prop_purge_on_revision(with_decl, prose_only, plan, chapter=28) == []


def test_shadow_registration_row3() -> None:
    assert GATE_TO_SHADOW_KEY["rev.prop_purged"] == ("market_params", "prop_purge_guard")
