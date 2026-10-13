"""Chapter-end tension contract sync (adjudication 199 class-level fix).

The G4.cd.no_hook escalation chain (ch59 adjudication 195, ch60 adjudication
199) showed the constraint living only in the correction loop: the drafting
skill produced stylistically varied closers whose merged last-8-paragraph
window carried no literal tension marker, and the POST_WRITE_SELF_CHECK
ticked 章尾好奇心点燃=是 against a zero-marker window (self-check had
drifted from the gate's calibration). The class fix promotes the constraint
into the primary contracts:

1. drafting SKILL.md: 创作原则 #3 explicitly DECOUPLES ending-variety from
   the hard marker (variety must not cancel the marker); PRE_WRITE_CHECK
   consumes 备忘段6's 章尾张力拍 direction; POST_WRITE_SELF_CHECK verifies
   by quoting the hit sentence against the G4.cd word list.
2. planning SKILL.md: 备忘段6 template carries the REQUIRED 章尾张力拍
   line — the upstream direction for the ending beat (ch60's memo lacked
   it, the repeated empirical gap).
3. The word list quoted in the contracts must stay token-identical to the
   G4 gate regex — drift here silently desyncs contract from enforcement.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_REPO = Path(__file__).resolve().parents[3]
_DRAFTING_SKILL = _REPO / "skills" / "shenbi-chapter-drafting" / "SKILL.md"
_PLANNING_SKILL = _REPO / "skills" / "shenbi-chapter-planning" / "SKILL.md"
_GATE_SRC = _REPO / "src" / "shenbi" / "gates" / "g4" / "chapter_drafting.py"


def _gate_tension_tokens() -> list[str]:
    """Extract the G4.cd tension word list from the gate regex literal."""
    src = _GATE_SRC.read_text(encoding="utf-8")
    m = re.search(
        r"但\|然而\|却\|不过\|还\|仍\|依然\|尚未\|未解\|不知\|等待\|没说\|没答\|瞒\|藏", src
    )
    assert m is not None, "G4.cd tension word regex not found in gate source"
    return m.group(0).split("|")


def test_drafting_skill_decouples_variety_from_hard_marker() -> None:
    text = _DRAFTING_SKILL.read_text(encoding="utf-8")
    # 创作原则 #3 must state the two constraints are independent and that
    # variety does not cancel the hard marker (the ch60 over-correction).
    assert "两条独立约束" in text
    assert "不得抵消" in text
    # The hard-marker spec must quote the G4.cd window calibration.
    assert "末 8 个叙述段" in text
    assert "30" in text and "合并窗口" in text


def test_drafting_self_check_calibrated_to_gate_word_list() -> None:
    text = _DRAFTING_SKILL.read_text(encoding="utf-8")
    # Every gate token must appear in the SKILL contract text (the quoted
    # word list drifts silently otherwise).
    for token in _gate_tension_tokens():
        assert token in text, f"gate tension token {token!r} missing from drafting SKILL.md"
    # The self-check must require quoting the hit sentence (self-narrative
    # 是/否 ticks kept passing zero-marker windows — adjudication 199).
    assert "命中原句" in text


def test_drafting_pre_write_check_consumes_memo_tension_beat() -> None:
    text = _DRAFTING_SKILL.read_text(encoding="utf-8")
    assert "章尾张力拍" in text


def test_planning_memo_template_requires_tension_beat_field() -> None:
    text = _PLANNING_SKILL.read_text(encoding="utf-8")
    # 段 6 template must carry the required one-line field so the ending
    # direction comes from upstream planning, not drafting improvisation.
    assert "章尾张力拍" in text
    assert "未答之问" in text and "未说破之瞒" in text and "未合拢之缝" in text


def test_p25_two_branch_self_check_in_writer_contracts() -> None:
    """P2.5 family class fix (adjudication 238): ch70 planning (low+rationale)
    and ch72 drafting (medium w/o rationale) each burned 3 gate attempts + a
    Tier 1 escalation while the rule sat compressed in one dense line. Both
    writer contracts now carry the operationalized two-branch self-check
    naming both empirically-fatal combos.
    """
    for skill in (_DRAFTING_SKILL, _PLANNING_SKILL):
        text = skill.read_text(encoding="utf-8")
        assert "P2.5 二分支自查" in text, skill
        assert "low" in text and "不写" in text  # branch 1: low, no rationale key
        assert "medium" in text and "必写" in text  # branch 2: medium, rationale required


def test_p25_self_check_carries_counting_instruction() -> None:
    """ch92 (adjudication 298): the auto-correct feedback was injected on all
    three attempts — the model miscounts characters at the boundary, not
    misunderstands the rule. The self-check now carries an explicit
    count-after-writing instruction with headroom.
    """
    for skill in (_DRAFTING_SKILL, _PLANNING_SKILL):
        text = skill.read_text(encoding="utf-8")
        assert "≤90 字留余量" in text, skill


def test_paragraph_floor_in_drafting_contract() -> None:
    """Paragraph-floor class fix (adjudications 371/375): two consecutive
    chapters burned 3 gate attempts each on G4.cd.no_visual_scene — extreme
    micro-paragraphing (median 6-7 chars/para, no 8-para window reaching 100
    CJK) driven by over-executing the anti-monologue directive. The floor now
    lives in the primary contract + a calibrated POST_WRITE self-check.
    """
    text = _DRAFTING_SKILL.read_text(encoding="utf-8")
    assert "段落质量下限" in text
    assert "≥100" in text and "带对白/动作的段 ≥4" in text
    assert "成段窗口（G4.cd 视觉场景口径）" in text  # self-check calibrated
