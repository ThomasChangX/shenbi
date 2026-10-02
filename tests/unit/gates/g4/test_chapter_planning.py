"""Bespoke error-path tests for g4_chapter_planning.

chapter_planning checks each input file for 8 sections, golden-3 rules,
section 5 choice, and section 7 hook ops.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from shenbi.gates.g4.chapter_planning import g4_chapter_planning


def _run(fps: list[str], rd: str | None = None) -> dict[str, Any]:
    return json.loads(g4_chapter_planning(fps, rd))


@pytest.mark.unit
def test_fails_when_less_than_8_sections(tmp_path: Path) -> None:
    """Plan file with < 8 numbered sections -> FAIL G4.cp.sections."""
    f = tmp_path / "chapter-001-plan.md"
    f.write_text("# Plan\n\n## 1. Intro\n## 2. Body\n", encoding="utf-8")
    result = _run([str(f)])
    assert result["status"] == "FAIL"
    assert any("G4.cp.sections" in mf for mf in result["must_fix"])


@pytest.mark.unit
def test_passes_with_all_8_sections(tmp_path: Path) -> None:
    """Plan file with all 8 sections -> PASS G4.cp.sections."""
    f = tmp_path / "chapter-001-plan.md"
    sections = "\n".join(f"## {i}. Section {i}\ncontent\n" for i in range(1, 9))
    f.write_text("# Plan\n\n" + sections, encoding="utf-8")
    result = _run([str(f)])
    assert any(c["id"] == "G4.cp.sections" and c["s"] == "PASS" for c in result["checks"])


@pytest.mark.unit
def test_golden_3_checks_chapter_1_three_walls(tmp_path: Path) -> None:
    """Chapter 1 plan missing '三面墙' -> WARN G4.cp.golden_1 (relaxed from FAIL)."""
    f = tmp_path / "chapter-1-plan.md"
    f.write_text(
        "# Plan\n\n## 1. Start\n## 2. Middle\n## 3. End\n## 4. Choice\n## 5. Key\n## 6. Turn\n## 7. Hook\n## 8. Close\n",
        encoding="utf-8",
    )
    result = _run([str(f)])
    # Golden rules are now aspirational quality targets → WARN only
    assert any(
        c["id"] == "G4.cp.golden_1" and c["s"] == "WARN" for c in result.get("checks", [])
    ), f"Expected G4.cp.golden_1 WARN in checks, got {result.get('checks', [])}"


@pytest.mark.unit
def test_fails_when_s5_choice_missing(tmp_path: Path) -> None:
    """Section 5 without 关键抉择 -> WARN G4.cp.s5_choice (relaxed from FAIL)."""
    sections = "\n".join(f"## {i}. Section {i}\ncontent\n" for i in range(1, 9))
    f = tmp_path / "chapter-001-plan.md"
    f.write_text("# Plan\n\n" + sections, encoding="utf-8")
    result = _run([str(f)])
    # Section 5 关键抉择 is now a quality bonus → WARN only
    assert any(
        c["id"] == "G4.cp.s5_choice" and c["s"] == "WARN" for c in result.get("checks", [])
    ), f"Expected G4.cp.s5_choice WARN in checks, got {result.get('checks', [])}"


@pytest.mark.unit
def test_skips_golden_for_non_123_chapters(tmp_path: Path) -> None:
    """Chapter N with N>3 -> golden check SKIPs."""
    sections = "\n".join(f"## {i}. Section {i}\ncontent\n" for i in range(1, 9))
    f = tmp_path / "chapter-005-plan.md"
    f.write_text("# Plan\n\n" + sections, encoding="utf-8")
    result = _run([str(f)])
    assert any(c["id"] == "G4.cp.golden" and c["s"] == "SKIP" for c in result["checks"])


@pytest.mark.unit
def test_fails_when_file_not_found(tmp_path: Path) -> None:
    """Missing file -> FAIL G4.cp.not_found."""
    result = _run([str(tmp_path / "nonexistent.md")])
    assert result["status"] == "FAIL"
    assert any("G4.cp.not_found" in mf for mf in result["must_fix"])


@pytest.mark.unit
def test_skips_on_empty_fps(tmp_path: Path) -> None:
    """Empty fps list -> SKIP."""
    result = _run([])
    assert any(c["id"] == "G4.cp" and c["s"] == "SKIP" for c in result["checks"])


@pytest.mark.unit
def test_passes_when_all_conditions_met(tmp_path: Path) -> None:
    """Valid plan with all 8 sections, golden content, s5 choice, s7 hooks -> PASS."""
    content = "# Plan\n\n"
    for i in range(1, 9):
        content += f"## {i}. Section {i}\n"
        if i == 1:
            content += "三面墙\n"
            content += "chapter_role: 高潮\n"
        elif i == 5:
            content += "关键抉择\n"
        elif i == 7:
            content += "open advance\n"
        else:
            content += "content\n"
    f = tmp_path / "chapter-001-plan.md"
    f.write_text(content, encoding="utf-8")
    result = _run([str(f)])
    assert result["status"] == "PASS"


def test_g4_cp_hard_fails_english_chapter_heading_residue(tmp_path):
    """#27 (probe17 adjudications #003→#005): the '# Chapter N:' English
    heading is banned by the skill contract; two prose re-pins failed to
    eliminate it because the write-path injector was RE-ADDING it after
    every compliant model output (#28 fixed the injector). With written
    plans now equal to model output, the gate enforces the ban machine-side
    — no third prose re-pin.
    """
    import json

    from shenbi.gates.g4.chapter_planning import g4_chapter_planning

    body = "# 第1章 章节备忘\n\n## 1. 当前任务\nchapter_role: 过渡/铺垫\n"
    for i in range(2, 9):
        body += f"\n## {i}. 段落{i}内容。\n"

    clean = tmp_path / "plans"
    clean.mkdir()
    f1 = clean / "chapter-1-plan.md"
    f1.write_text(body, encoding="utf-8")
    ok = json.loads(g4_chapter_planning([str(f1)], rd=str(tmp_path)))
    assert not any("english_heading" in m for m in ok.get("must_fix", []))

    dirty = tmp_path / "plans2"
    dirty.mkdir()
    f2 = dirty / "chapter-1-plan.md"
    f2.write_text("# Chapter 1:\n\n" + body, encoding="utf-8")
    bad = json.loads(g4_chapter_planning([str(f2)], rd=str(tmp_path)))
    assert any("G4.cp.english_heading" in m for m in bad.get("must_fix", [])), bad.get("must_fix")
