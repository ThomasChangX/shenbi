"""Bespoke error-path tests for g4_state_settling.

state_settling dispatches checks based on filenames containing
keywords: current_state, character_matrix, etc. Each test exercises
one business rule by naming the test file appropriately.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from shenbi.gates.g4.state_settling import g4_state_settling


def _run(fps: list[str], rd: str | None = None) -> dict[str, Any]:
    return json.loads(g4_state_settling(fps, rd))


@pytest.mark.unit
def test_fails_when_current_state_missing_position(tmp_path: Path) -> None:
    """File named current_state without position markers -> WARN G4.ss.position (relaxed from FAIL)."""
    f = tmp_path / "current_state.md"
    f.write_text("# State\n\nNo position info.\n", encoding="utf-8")
    result = _run([str(f)])
    # Position check is now a WARN quality target, check ID renamed
    assert any(
        c["id"] == "G4.ss.position" and c["s"] == "WARN" for c in result.get("checks", [])
    ), f"Expected G4.ss.position WARN in checks, got {result.get('checks', [])}"


@pytest.mark.unit
def test_passes_when_current_state_has_position(tmp_path: Path) -> None:
    """File named current_state with ## 位置 -> PASS G4.ss.position."""
    f = tmp_path / "current_state.md"
    f.write_text("# State\n\n## 位置\n森林深处\n", encoding="utf-8")
    result = _run([str(f)])
    assert any(c["id"] == "G4.ss.position" and c["s"] == "PASS" for c in result["checks"])


@pytest.mark.unit
def test_fails_when_character_matrix_missing_chars(tmp_path: Path) -> None:
    """File named character_matrix without character sections -> WARN G4.ss.characters (relaxed from FAIL)."""
    f = tmp_path / "character_matrix.md"
    f.write_text("# Matrix\nNo characters here.\n", encoding="utf-8")
    result = _run([str(f)])
    # Character check is now a WARN quality target, check ID renamed
    assert any(
        c["id"] == "G4.ss.characters" and c["s"] == "WARN" for c in result.get("checks", [])
    ), f"Expected G4.ss.characters WARN in checks, got {result.get('checks', [])}"


@pytest.mark.unit
def test_passes_when_character_matrix_has_chars(tmp_path: Path) -> None:
    """File named character_matrix with ## 角色 -> PASS."""
    f = tmp_path / "character_matrix.md"
    f.write_text("# Matrix\n\n## 角色\n主角\n", encoding="utf-8")
    result = _run([str(f)])
    assert any(c["id"] == "G4.ss.characters" and c["s"] == "PASS" for c in result["checks"])


@pytest.mark.unit
def test_fails_when_pending_hooks_missing_state_keyword(tmp_path: Path) -> None:
    """File named pending_hooks without 'state' keyword -> FAIL."""
    f = tmp_path / "pending_hooks.md"
    f.write_text("# Hooks\n\ndraft content\n", encoding="utf-8")
    result = _run([str(f)])
    assert result["status"] == "FAIL"
    assert any("G4.ss.no_hook_state" in mf for mf in result["must_fix"])


@pytest.mark.unit
def test_fails_when_file_not_found(tmp_path: Path) -> None:
    """Missing file -> FAIL G4.ss.not_found."""
    result = _run([str(tmp_path / "nonexistent.md")])
    assert result["status"] == "FAIL"
    assert any("G4.ss.not_found" in mf for mf in result["must_fix"])


@pytest.mark.unit
def test_skips_on_empty_fps(tmp_path: Path) -> None:
    """Empty fps list -> SKIP."""
    result = _run([])
    assert any(c["id"] == "G4.ss" and c["s"] == "SKIP" for c in result["checks"])


@pytest.mark.unit
def test_passes_when_all_conditions_met(tmp_path: Path) -> None:
    """current_state + character_matrix + pending_hooks all valid -> PASS."""
    d = tmp_path / "sub"
    d.mkdir()
    cs = d / "current_state.md"
    cs.write_text("## 位置变化\n移动\n", encoding="utf-8")
    cm = d / "character_matrix.md"
    cm.write_text("## 已登场角色\n英雄\n", encoding="utf-8")
    ph = d / "pending_hooks.md"
    ph.write_text("state: active\n", encoding="utf-8")
    result = _run([str(cs), str(cm), str(ph)])
    assert result["status"] == "PASS"


@pytest.mark.unit
def test_passes_when_chapter_summaries_has_chapter_headings(tmp_path: Path) -> None:
    """chapter_summaries with '## 第N章' -> PASS G4.ss.summaries (covers g4 40-43)."""
    f = tmp_path / "chapter_summaries.md"
    f.write_text("# Summaries\n\n## 第1章\n内容概括。\n", encoding="utf-8")
    result = _run([str(f)])
    assert any(c["id"] == "G4.ss.summaries" and c["s"] == "PASS" for c in result["checks"])


@pytest.mark.unit
def test_passes_when_emotional_arcs_has_chapter_headings(tmp_path: Path) -> None:
    """emotional_arcs with '### 第N章' -> PASS G4.ss.arcs (covers g4 46-49)."""
    f = tmp_path / "emotional_arcs.md"
    f.write_text("# Arcs\n\n### 第1章\n情感变化。\n", encoding="utf-8")
    result = _run([str(f)])
    assert any(c["id"] == "G4.ss.arcs" and c["s"] == "PASS" for c in result["checks"])


@pytest.mark.unit
def test_passes_when_particle_ledger_has_particle_section(tmp_path: Path) -> None:
    """particle_ledger with '## 粒子账本' -> PASS G4.ss.particle_ledger (covers g4 52-55)."""
    f = tmp_path / "particle_ledger.md"
    f.write_text("# Ledger\n\n## 粒子账本\n- 粒子甲\n", encoding="utf-8")
    result = _run([str(f)])
    assert any(c["id"] == "G4.ss.particle_ledger" and c["s"] == "PASS" for c in result["checks"])
