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
def test_g4cp_token_truth_table(tmp_path: Path) -> None:
    def run(memo_body: str) -> list[str]:
        memo = tmp_path / "m.md"
        memo.write_text(memo_body, encoding="utf-8")
        import re as _re

        content = memo.read_text(encoding="utf-8")
        out: list[str] = []
        m = _re.search(r"^plan_format[：:]\s*(\S+)\s*$", content, _re.MULTILINE)
        if m and m.group(1) not in ("v1", "v2"):
            out.append("invalid")
        if (
            m
            and m.group(1) == "v2"
            and not _re.search(r"^声口要求[：:].+$", content, _re.MULTILINE)
        ):
            out.append("no_voice_line")
        return out

    assert run("# 第1章 章节备忘\n\nchapter_role: 推进\n") == []  # 缺席=v1
    assert run("plan_format: v3\n") == ["invalid"]
    assert run("plan_format: v2\n") == ["no_voice_line"]
    assert run("plan_format: v2\n声口要求: 账房腔\n") == []


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
    assert not any("voice_density" in m for m in ok.get("must_fix", [])), ok.get("must_fix")
    thin = _V2_CHAPTER.replace("他把这笔我先记下。利息又涨了。这买卖不亏吧？", "他推门。")
    d2 = _mk_v2_project(tmp_path / "b", chapter=thin)
    bad = json.loads(
        g4_chapter_drafting(
            [str(d2 / "chapters" / "chapter-1.md")], rd=str(d2), project_dir=str(d2)
        )
    )
    assert any("voice_density" in m for m in bad.get("must_fix", [])), bad.get("must_fix")


@pytest.mark.unit
def test_g4cd_quote_type_three_point_sync(tmp_path: Path) -> None:
    # memo=静 PRE=燃 POST=静 → FAIL
    mixed = _V2_CHAPTER.replace("本章金句位: 静｜对比｜落点", "本章金句位: 燃｜对比｜落点")
    d = _mk_v2_project(tmp_path / "c", chapter=mixed)
    r = json.loads(
        g4_chapter_drafting([str(d / "chapters" / "chapter-1.md")], rd=str(d), project_dir=str(d))
    )
    assert any("quote_type" in m for m in r.get("must_fix", [])), r.get("must_fix")
    # memo 点缺席（v2 备忘无类型金句位行）→ FAIL
    d2 = _mk_v2_project(tmp_path / "d", memo=_V2_MEMO.replace("金句位: 静｜对比｜落点\n", ""))
    r2 = json.loads(
        g4_chapter_drafting(
            [str(d2 / "chapters" / "chapter-1.md")], rd=str(d2), project_dir=str(d2)
        )
    )
    assert any("quote_type" in m for m in r2.get("must_fix", [])), r2.get("must_fix")
    # PRE 行整体缺席（v2）→ FAIL（非仅 golden WARN）
    d3 = _mk_v2_project(
        tmp_path / "e", chapter=_V2_CHAPTER.replace("- 本章金句位: 静｜对比｜落点\n", "")
    )
    r3 = json.loads(
        g4_chapter_drafting(
            [str(d3 / "chapters" / "chapter-1.md")], rd=str(d3), project_dir=str(d3)
        )
    )
    assert any("quote_type" in m for m in r3.get("must_fix", [])), r3.get("must_fix")


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
