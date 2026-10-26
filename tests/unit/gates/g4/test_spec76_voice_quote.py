"""Spec #76 gate branches: plan_format truth table, v2 density, quote-type
three-point sync, meme grammar (plan T2/T3 tdd_red_green debt).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from shenbi.gates.g4.chapter_drafting import g4_chapter_drafting
from shenbi.gates.g4.chapter_planning import g4_chapter_planning
from shenbi.gates.g4.volume_outlining import g4_volume_outlining

_V2_CHAPTER = """---
provenance: real-output
---

# Chapter N

正文。他把这笔我先记下。利息又涨了。这买卖不亏吧？

<!--META-BEGIN-->
## PRE_WRITE_CHECK

- 本章金句位: 静｜对比｜落点
- 其他: x

## POST_WRITE_SELF_CHECK

- [x] 金句位: 静｜对比｜落点原文
<!--META-END-->
"""

_V2_MEMO = """# 第1章 章节备忘

## 1. 当前任务

plan_format: v2
chapter_role: 推进
emotion_tone: 平
**payoff 拍**: 推进｜低
声口要求: 账房腔+自嘲反问；口癖「这笔我先记下」
金句位: 静｜对比｜落点
"""


def _mk_v2_project(tmp_path: Path, memo: str = _V2_MEMO, chapter: str = _V2_CHAPTER) -> Path:
    (tmp_path / "plans").mkdir(parents=True, exist_ok=True)
    (tmp_path / "chapters").mkdir(parents=True, exist_ok=True)
    (tmp_path / "characters").mkdir(parents=True, exist_ok=True)
    (tmp_path / "characters" / "protagonist.md").write_text(
        "---\nname: 林烽\nvoice_profile:\n  catchphrases:\n    - 这笔我先记下。\n---\n卡。\n",
        encoding="utf-8",
    )
    (tmp_path / "genre-config.json").write_text(
        json.dumps(
            {
                "chapter_word": {"default": 3200, "min": 2800, "max": 4000},
                "market_params": {
                    "payoff_density": {"window": 3, "min": 1},
                    "emotion_band": {"window": 1, "min": 1},
                    "hook_grading": {"max_consecutive_micro": 2},
                    "voice_density_min": {"min_per_chapter": 2},
                },
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "plans" / "chapter-1-plan.md").write_text(memo, encoding="utf-8")
    (tmp_path / "chapters" / "chapter-1.md").write_text(chapter, encoding="utf-8")
    return tmp_path


@pytest.mark.unit
def test_g4cp_token_truth_table_real_gate(tmp_path: Path) -> None:
    """Real-gate invocation (I2-prime rewrite; the old copy was tautological)."""

    def run_memo(memo: str, tag: str) -> list[str]:
        d = tmp_path / tag
        (d / "plans").mkdir(parents=True, exist_ok=True)
        (d / "plans" / "chapter-1-plan.md").write_text(memo, encoding="utf-8")
        r = json.loads(
            g4_chapter_planning(
                [str(d / "plans" / "chapter-1-plan.md")], rd=str(d), project_dir=str(d)
            )
        )
        return r.get("must_fix", [])

    base = (
        "# 第1章 章节备忘\n\n## 1. 当前任务\n\nchapter_role: 推进\n"
        "emotion_tone: 平\n**payoff 拍**: 推进｜低\n"
    )
    # 缺席 = v1 默认（无 plan_format/voice FAIL 行）
    assert not any("plan_format" in m or "voice_line" in m for m in run_memo(base, "a"))
    # v4 非法（v3 已合法——#78）
    assert any(
        "plan_format" in m and "invalid" in m for m in run_memo(base + "plan_format: v4\n", "b")
    )
    # v2 缺声口要求行
    assert any("voice_line" in m for m in run_memo(base + "plan_format: v2\n", "c"))
    # v2 齐备
    assert not any(
        "plan_format" in m or "voice_line" in m
        for m in run_memo(base + "plan_format: v2\n声口要求: 账房腔+自嘲反问\n", "d")
    )


@pytest.mark.unit
def test_g4cp_full_gate_v2(tmp_path: Path) -> None:
    d = _mk_v2_project(tmp_path)
    result = json.loads(
        g4_chapter_planning([str(d / "plans" / "chapter-1-plan.md")], rd=str(d), project_dir=str(d))
    )
    # v2 备忘合法（令牌+声口行在）
    assert "G4.cp.plan_format" not in str(result.get("must_fix", []))


@pytest.mark.unit
def test_g4cd_v2_density_pass_and_fail(tmp_path: Path) -> None:
    d = _mk_v2_project(tmp_path)
    ok = json.loads(
        g4_chapter_drafting([str(d / "chapters" / "chapter-1.md")], rd=str(d), project_dir=str(d))
    )
    assert not any("G4.cd.voice_density" in m for m in ok.get("must_fix", [])), ok.get("must_fix")
    thin = _V2_CHAPTER.replace("他把这笔我先记下。利息又涨了。这买卖不亏吧？", "他推门。")
    d2 = _mk_v2_project(tmp_path / "b", chapter=thin)
    bad = json.loads(
        g4_chapter_drafting(
            [str(d2 / "chapters" / "chapter-1.md")], rd=str(d2), project_dir=str(d2)
        )
    )
    assert any("G4.cd.voice_density" in m for m in bad.get("must_fix", [])), bad.get("must_fix")


@pytest.mark.unit
def test_g4cd_quote_type_three_point_sync(tmp_path: Path) -> None:
    # 全一致（静/静/静）→ PASS（C1 回归钉：memo 点须贡献类型——_memo_text 赋值）
    okd = _mk_v2_project(tmp_path / "ok")
    rok = json.loads(
        g4_chapter_drafting(
            [str(okd / "chapters" / "chapter-1.md")], rd=str(okd), project_dir=str(okd)
        )
    )
    assert not any("G4.cd.quote_type" in m for m in rok.get("must_fix", [])), rok.get("must_fix")
    # memo=静 PRE=燃 POST=静 → FAIL
    mixed = _V2_CHAPTER.replace("本章金句位: 静｜对比｜落点", "本章金句位: 燃｜对比｜落点")
    d = _mk_v2_project(tmp_path / "c", chapter=mixed)
    r = json.loads(
        g4_chapter_drafting([str(d / "chapters" / "chapter-1.md")], rd=str(d), project_dir=str(d))
    )
    assert any("G4.cd.quote_type" in m for m in r.get("must_fix", [])), r.get("must_fix")
    # memo 点缺席（v2 备忘无类型金句位行）→ FAIL
    d2 = _mk_v2_project(tmp_path / "d", memo=_V2_MEMO.replace("金句位: 静｜对比｜落点\n", ""))
    r2 = json.loads(
        g4_chapter_drafting(
            [str(d2 / "chapters" / "chapter-1.md")], rd=str(d2), project_dir=str(d2)
        )
    )
    assert any("G4.cd.quote_type" in m for m in r2.get("must_fix", [])), r2.get("must_fix")
    # PRE 行整体缺席（v2）→ FAIL（非仅 golden WARN）
    d3 = _mk_v2_project(
        tmp_path / "e", chapter=_V2_CHAPTER.replace("- 本章金句位: 静｜对比｜落点\n", "")
    )
    r3 = json.loads(
        g4_chapter_drafting(
            [str(d3 / "chapters" / "chapter-1.md")], rd=str(d3), project_dir=str(d3)
        )
    )
    assert any("G4.cd.quote_type" in m for m in r3.get("must_fix", [])), r3.get("must_fix")


@pytest.mark.unit
def test_g4vo_meme_grammar() -> None:
    good = "## 第一卷：x（第1—10章）\n\n**金句、母题物象与梗位**: 梗位复用：「班味」、记账式吐槽｜金句：x\n"
    bad = "## 第一卷：x（第1—10章）\n\n**金句、母题物象与梗位**: 梗位复用：记账式吐槽类｜金句：x\n"
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        proj = Path(td)
        (proj / "outline").mkdir()
        (proj / "outline" / "volume_map.md").write_text(good, encoding="utf-8")
        r1 = json.loads(g4_volume_outlining([str(proj / "outline" / "volume_map.md")], rd=td))
        (proj / "outline" / "volume_map.md").write_text(bad, encoding="utf-8")
        r2 = json.loads(g4_volume_outlining([str(proj / "outline" / "volume_map.md")], rd=td))
    assert not any("meme_grammar" in m for m in r1.get("must_fix", []))
    assert any("meme_grammar" in m for m in r2.get("must_fix", []))


_V3_MEMO = """# 第1章 章节备忘

## 1. 当前任务

plan_format: v3
chapter_role: 推进
emotion_tone: 平
**payoff 拍**: 推进｜轴(债)｜-192文
章尾张力拍: [微]未答之问
声口要求: 账房腔+自嘲反问
金句位: 静｜对比｜落点
"""


@pytest.mark.unit
def test_g4cp_v3_obligations(tmp_path: Path) -> None:
    def run(memo: str, tag: str) -> list[str]:
        d = tmp_path / tag
        (d / "plans").mkdir(parents=True, exist_ok=True)
        (d / "plans" / "chapter-1-plan.md").write_text(memo, encoding="utf-8")
        r = json.loads(
            g4_chapter_planning(
                [str(d / "plans" / "chapter-1-plan.md")], rd=str(d), project_dir=str(d)
            )
        )
        return r.get("must_fix", [])

    base = _V3_MEMO
    # v3 齐备 → 无 v3/v2 义务 FAIL
    assert not any(
        "tension_tier" in m or "payoff_axis" in m or "voice_line" in m for m in run(base, "a")
    )
    # 缺分级行
    assert any(
        "tension_tier" in m for m in run(base.replace("章尾张力拍: [微]未答之问\n", ""), "b")
    )
    # payoff 缺轴
    assert any(
        "payoff_axis" in m
        for m in run(
            base.replace("**payoff 拍**: 推进｜轴(债)｜-192文", "**payoff 拍**: 推进｜低"), "c"
        )
    )
    # v3 ⊇ v2：缺声口行仍 FAIL
    assert any("voice_line" in m for m in run(base.replace("声口要求: 账房腔+自嘲反问\n", ""), "d"))


@pytest.mark.unit
def test_g4cd_v3_micro_hook_run(tmp_path: Path) -> None:
    d = _mk_v2_project(tmp_path, memo=_V3_MEMO)
    for k in (1, 2, 3):
        (d / "plans" / f"chapter-{k}-plan.md").write_text(
            _V3_MEMO.replace("# 第1章", f"# 第{k}章"), encoding="utf-8"
        )
    (d / "chapters" / "chapter-3.md").write_text(
        _V2_CHAPTER.replace("本章金句位: 静｜对比｜落点", "本章金句位: 静｜对比｜落点"),
        encoding="utf-8",
    )
    # 锚章 ch3：窗口 1..3 全微钩 → run 3 > cap 2 → FAIL
    r = json.loads(
        g4_chapter_drafting([str(d / "chapters" / "chapter-3.md")], rd=str(d), project_dir=str(d))
    )
    assert any("G4.cd.micro_hook_run" in m for m in r.get("must_fix", [])), r.get("must_fix")
