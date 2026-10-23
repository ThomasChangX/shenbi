"""Craft-declaration fields for G4.cp + the ledger hook form for G4.cd.

P1 batch (2026-10-23, 对照《诡秘之主》《炮火弧线》商业节奏审计): the memo must
declare `emotion_tone` (抑扬排程, five-value vocabulary aligned with
rhythm_principles monotony detection) and a `payoff 拍` (爽点兑现声明);
chapters inside the retention window (first 30) must declare a `留存锚` line.
G4.cd accepts a cold ledger line (>=2 arabic digits, no tension word) as a
legal chapter-end hook form (账目钩).
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest

from shenbi.gates.g4.chapter_drafting import g4_chapter_drafting
from shenbi.gates.g4.chapter_planning import g4_chapter_planning

REPO_ROOT = Path(__file__).resolve().parents[4]
SKILL_MD = REPO_ROOT / "skills" / "shenbi-chapter-planning" / "SKILL.md"


def _run_cp(fps: list[str], rd: str | None = None) -> dict[str, Any]:
    return json.loads(g4_chapter_planning(fps, rd))


def _plan(
    *,
    chapter: int = 5,
    emotion_tone: str | None = "悲",
    payoff: str | None = "**payoff 拍**: [扮猪吃虎｜中兑现]",
    anchor: str | None = "**留存锚**: [情感锤]",
) -> str:
    """A plan satisfying every G4.cp check; new craft fields injectable."""
    content = "# Plan\n\n"
    for i in range(1, 9):
        content += f"## {i}. Section {i}\n"
        if i == 1:
            content += "chapter_role: 推进\n"
            if emotion_tone:
                content += f"emotion_tone: {emotion_tone}\n"
            if payoff:
                content += f"{payoff}\n"
        elif i == 2:
            if anchor:
                content += f"{anchor}\n"
        elif i == 5:
            content += "关键抉择\n"
        elif i == 7:
            content += "open advance\n"
        else:
            content += "content\n"
    return content


# ---------------------------------------------------------------------------
# emotion_tone (P1-2 抑扬排程)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_plan_without_emotion_tone_fails_g4(tmp_path: Path) -> None:
    f = tmp_path / "chapter-005-plan.md"
    f.write_text(_plan(emotion_tone=None), encoding="utf-8")
    result = _run_cp([str(f)])
    assert result["status"] == "FAIL"
    assert any("G4.cp.missing_emotion_tone" in mf for mf in result["must_fix"])


@pytest.mark.unit
@pytest.mark.parametrize("tone", ["悲", "喜", "怒", "惧", "平"])
def test_plan_with_valid_emotion_tone_passes(tmp_path: Path, tone: str) -> None:
    f = tmp_path / "chapter-005-plan.md"
    f.write_text(_plan(emotion_tone=tone), encoding="utf-8")
    result = _run_cp([str(f)])
    assert result["status"] == "PASS"
    assert any(c["id"] == "G4.cp.emotion_tone" and c["s"] == "PASS" for c in result["checks"])


@pytest.mark.unit
def test_invalid_emotion_tone_value_rejected(tmp_path: Path) -> None:
    f = tmp_path / "chapter-005-plan.md"
    f.write_text(_plan(emotion_tone="emo"), encoding="utf-8")
    result = _run_cp([str(f)])
    assert result["status"] == "FAIL"
    assert any("G4.cp.missing_emotion_tone" in mf for mf in result["must_fix"])


# ---------------------------------------------------------------------------
# payoff 拍 (P1-1 爽点兑现声明)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_plan_without_payoff_beat_fails_g4(tmp_path: Path) -> None:
    f = tmp_path / "chapter-005-plan.md"
    f.write_text(_plan(payoff=None), encoding="utf-8")
    result = _run_cp([str(f)])
    assert result["status"] == "FAIL"
    assert any("G4.cp.missing_payoff_beat" in mf for mf in result["must_fix"])


@pytest.mark.unit
def test_payoff_beat_no_payoff_escape_is_legal(tmp_path: Path) -> None:
    """A no-payoff escape value ("无" plus reason) is a legal payoff
    declaration — not every chapter pays off.
    """
    f = tmp_path / "chapter-005-plan.md"
    f.write_text(_plan(payoff="**payoff 拍**: 无（纯蓄压章，下章大兑现）"), encoding="utf-8")
    result = _run_cp([str(f)])
    assert result["status"] == "PASS"
    assert any(c["id"] == "G4.cp.payoff_beat" and c["s"] == "PASS" for c in result["checks"])


@pytest.mark.unit
def test_payoff_beat_bare_form_also_matches(tmp_path: Path) -> None:
    """A non-bold `payoff 拍: ...` line still satisfies the checker."""
    f = tmp_path / "chapter-005-plan.md"
    f.write_text(_plan(payoff="payoff 拍: 经商｜小兑现"), encoding="utf-8")
    result = _run_cp([str(f)])
    assert result["status"] == "PASS"


# ---------------------------------------------------------------------------
# 留存锚 (P1-4 前 30 章留存窗口)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_early_chapter_without_retention_anchor_fails(tmp_path: Path) -> None:
    f = tmp_path / "chapter-005-plan.md"
    f.write_text(_plan(anchor=None), encoding="utf-8")
    result = _run_cp([str(f)])
    assert result["status"] == "FAIL"
    assert any("G4.cp.missing_retention_anchor" in mf for mf in result["must_fix"])


@pytest.mark.unit
def test_early_chapter_non_anchor_escape_is_legal(tmp_path: Path) -> None:
    f = tmp_path / "chapter-005-plan.md"
    f.write_text(_plan(anchor="**留存锚**: 非锚章"), encoding="utf-8")
    result = _run_cp([str(f)])
    assert result["status"] == "PASS"
    assert any(c["id"] == "G4.cp.retention_anchor" and c["s"] == "PASS" for c in result["checks"])


@pytest.mark.unit
def test_chapter_31_without_anchor_is_skipped(tmp_path: Path) -> None:
    """Outside the retention window the anchor line is not required."""
    f = tmp_path / "chapter-031-plan.md"
    f.write_text(_plan(anchor=None), encoding="utf-8")
    result = _run_cp([str(f)])
    assert result["status"] == "PASS"
    assert any(c["id"] == "G4.cp.retention_anchor" and c["s"] == "SKIP" for c in result["checks"])


# ---------------------------------------------------------------------------
# Canonical-template guard: SKILL.md template tokens must pass the gate
# (same regression discipline as test_chapter_planning_role.py)
# ---------------------------------------------------------------------------


def _template_lines(token: str) -> list[str]:
    text = SKILL_MD.read_text(encoding="utf-8")
    lines: list[str] = []
    for block in re.findall(r"```markdown\n(.*?)```", text, re.DOTALL):
        for line in block.splitlines():
            if token in line and ":" in line:
                lines.append(line.strip())
    assert lines, f"token {token} not found in any markdown template block"
    return lines


@pytest.mark.unit
def test_canonical_emotion_tone_template_passes(tmp_path: Path) -> None:
    f = tmp_path / "chapter-005-plan.md"
    f.write_text(
        _plan(emotion_tone=None).replace(
            "chapter_role: 推进\n", "chapter_role: 推进\nemotion_tone: 悲\n"
        ),
        encoding="utf-8",
    )
    result = _run_cp([str(f)])
    assert result["status"] == "PASS"


@pytest.mark.unit
def test_canonical_payoff_and_anchor_templates_pass(tmp_path: Path) -> None:
    payoff_line = _template_lines("payoff 拍")[0]
    anchor_line = _template_lines("留存锚")[0]
    f = tmp_path / "chapter-005-plan.md"
    content = _plan(payoff=None, anchor=None)
    content = content.replace(
        "chapter_role: 推进\n", f"chapter_role: 推进\n{payoff_line}\n"
    ).replace("## 2. Section 2\n", f"## 2. Section 2\n{anchor_line}\n")
    f.write_text(content, encoding="utf-8")
    result = _run_cp([str(f)])
    assert result["status"] == "PASS", result["must_fix"]


# ---------------------------------------------------------------------------
# G4.cd 账目钩 (P1-3): cold ledger line as a legal chapter-end hook
# ---------------------------------------------------------------------------


def _run_cd(fps: list[str], rd: str | None = None) -> dict[str, Any]:
    return json.loads(g4_chapter_drafting(fps, rd))


_BODY = "他沿着矿道往前走，看了看手里的名册，又放回怀里。" * 140


@pytest.mark.unit
def test_ledger_line_ending_satisfies_hook_gate(tmp_path: Path) -> None:
    """A cold ledger closer (>=2 arabic digits, no tension word, no question)
    is the 账目钩 form from the seed's 章末钩七型 — it must pass G4.cd.
    """
    ending = "\n\n".join(
        [
            "他回到帐房，把今日的册子摊开，一列一列核对下去。",
            "核到最后一行，他停住了笔，把那页纸单独折了起来。",
            "册页的末尾写着：本季阵亡 41 人，抚恤分作 82 户。",
            "他把册子合上，压在灯下，吹熄了蜡烛。",
        ]
    )
    ch = tmp_path / "chapter-001.md"
    ch.write_text(f"# 章节\n\n{_BODY}\n\n{ending}\n", encoding="utf-8")
    result = _run_cd([str(ch)])
    assert not any("G4.cd.no_hook" in m for m in result.get("must_fix", []))


@pytest.mark.unit
def test_single_digit_flat_ending_still_fails_hook_gate(tmp_path: Path) -> None:
    """Non-vacuous control: one stray digit is not a ledger line."""
    flat = "\n\n".join(
        [
            "他回到了家中坐下来，安安静静地吃了一碗温热的饭食，洗净了手上的尘土。",
            "他躺到草席上面，闭上了眼睛，听着屋顶上面细碎的风声过了一阵。",
            "第二日清晨的钟声敲响之前，他睡得很沉，一个梦也没有做成。",
            "这一天平淡无奇地过去了，同之前的许多个日子一模一样，只记下 3 笔。",
        ]
    )
    ch = tmp_path / "chapter-001.md"
    ch.write_text(f"# 章节\n\n{_BODY}\n\n{flat}\n", encoding="utf-8")
    result = _run_cd([str(ch)])
    assert any("G4.cd.no_hook" in m for m in result.get("must_fix", []))
