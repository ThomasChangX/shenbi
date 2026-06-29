"""Tests for the chapter_role requirement in g4_chapter_planning (Task 2.4).

A valid chapter plan must now declare a `chapter_role` token (one of
高潮/兑现/推进/转折/过渡/铺垫) so that review-resonance can calibrate its
threshold against the chapter's narrative function (spec §5.1).
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest

from shenbi.gates.g4.chapter_planning import g4_chapter_planning

REPO_ROOT = Path(__file__).resolve().parents[4]
SKILL_MD = REPO_ROOT / "skills" / "shenbi-chapter-planning" / "SKILL.md"


def _run(fps: list[str], rd: str | None = None) -> dict[str, Any]:
    return json.loads(g4_chapter_planning(fps, rd))


def _valid_plan(role: str | None = None) -> str:
    """A plan that satisfies every G4.cp check; `role` injected into §1 when given."""
    content = "# Plan\n\n"
    for i in range(1, 9):
        content += f"## {i}. Section {i}\n"
        if i == 1:
            content += "三面墙\n"
            if role:
                content += f"chapter_role: {role}\n"
        elif i == 5:
            content += "关键抉择\n"
        elif i == 7:
            content += "open advance\n"
        else:
            content += "content\n"
    return content


@pytest.mark.unit
def test_plan_without_chapter_role_fails_g4(tmp_path: Path) -> None:
    """Otherwise-valid plan missing chapter_role -> FAIL with G4.cp.missing_chapter_role."""
    f = tmp_path / "chapter-001-plan.md"
    f.write_text(_valid_plan(role=None), encoding="utf-8")
    result = _run([str(f)])
    assert result["status"] == "FAIL"
    assert any("G4.cp.missing_chapter_role" in mf for mf in result["must_fix"])


@pytest.mark.unit
@pytest.mark.parametrize("role", ["高潮", "兑现", "推进", "转折", "过渡", "铺垫"])
def test_plan_with_chapter_role_passes(tmp_path: Path, role: str) -> None:
    """Plan declaring any allowed chapter_role value -> PASS."""
    f = tmp_path / "chapter-001-plan.md"
    f.write_text(_valid_plan(role=role), encoding="utf-8")
    result = _run([str(f)])
    assert result["status"] == "PASS"
    assert any(c["id"] == "G4.cp.chapter_role" and c["s"] == "PASS" for c in result["checks"])


@pytest.mark.unit
def test_chapter_role_accepts_fullwidth_colon(tmp_path: Path) -> None:
    """A fullwidth colon is also a valid separator for the chapter_role token."""
    f = tmp_path / "chapter-001-plan.md"
    content = _valid_plan(role=None).replace("三面墙\n", "三面墙\nchapter_role：高潮\n")
    f.write_text(content, encoding="utf-8")
    result = _run([str(f)])
    assert result["status"] == "PASS"


def _template_role_line() -> str:
    """Extract the verbatim chapter_role line from the fenced §1 template block
    in SKILL.md (e.g. `chapter_role: 高潮`).
    """
    text = SKILL_MD.read_text(encoding="utf-8")
    for block in re.findall(r"```markdown\n(.*?)```", text, re.DOTALL):
        if "chapter_role" in block:
            m = re.search(r"(.*chapter_role.*)", block)
            if m:
                return m.group(1).strip()
    raise AssertionError("chapter_role line not found in a markdown template block")


def _valid_plan_raw_role_line(raw_role_line: str) -> str:
    """Plan satisfying every G4.cp check; injects a raw chapter_role line into §1."""
    content = "# Plan\n\n"
    for i in range(1, 9):
        content += f"## {i}. Section {i}\n"
        if i == 1:
            content += "三面墙\n"
            content += f"{raw_role_line}\n"
        elif i == 5:
            content += "关键抉择\n"
        elif i == 7:
            content += "open advance\n"
        else:
            content += "content\n"
    return content


@pytest.mark.unit
def test_canonical_template_role_token_passes_g4(tmp_path: Path) -> None:
    r"""Regression guard (P2 fix): the literal chapter_role token shown in the §1
    template of SKILL.md must pass the G4 checker. If the template is reverted to
    the bold form (**chapter_role**), this test fails — the asterisks are neither
    whitespace nor a colon, so the checker regex breaks and no value matches.
    """
    role_line = _template_role_line()
    assert "**" not in role_line, (
        "SKILL.md template renders chapter_role in bold; G4 regex would not match"
    )
    f = tmp_path / "chapter-001-plan.md"
    f.write_text(_valid_plan_raw_role_line(role_line), encoding="utf-8")
    result = _run([str(f)])
    assert result["status"] == "PASS"
    assert any(c["id"] == "G4.cp.chapter_role" and c["s"] == "PASS" for c in result["checks"])


@pytest.mark.unit
def test_invalid_chapter_role_value_rejected(tmp_path: Path) -> None:
    """A chapter_role with a non-canonical value (无效) is rejected: the checker
    regex value set (高潮/兑现/推进/转折/过渡/铺垫) does not match, so
    G4.cp.missing_chapter_role fires (the 值非法 contract in SKILL.md).
    """
    f = tmp_path / "chapter-001-plan.md"
    f.write_text(_valid_plan(role="无效"), encoding="utf-8")
    result = _run([str(f)])
    assert result["status"] == "FAIL"
    assert any("G4.cp.missing_chapter_role" in mf for mf in result["must_fix"])
