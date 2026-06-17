"""Bespoke error-path tests for g4_foreshadowing_track."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any
import pytest
from shenbi.gates.g4.foreshadowing_track import g4_foreshadowing_track

def _setup(tmp_path: Path) -> tuple[Path, Path]:
    project_dir = tmp_path / "project"; sub_dir = project_dir / "skill-output"
    sub_dir.mkdir(parents=True); marker = sub_dir / "out.md"
    marker.write_text("x", encoding="utf-8")
    return project_dir, marker

def _result(s: str) -> dict[str, Any]:
    return json.loads(s)

@pytest.mark.unit
def test_fails_when_pending_hooks_missing(tmp_path: Path) -> None:
    project_dir, marker = _setup(tmp_path)
    (project_dir / "truth").mkdir()
    result = _result(g4_foreshadowing_track([str(marker)]))
    assert any("G4.ft.not_found" in mf for mf in result["must_fix"])

@pytest.mark.unit
def test_fails_when_no_state_changes(tmp_path: Path) -> None:
    project_dir, marker = _setup(tmp_path)
    (project_dir / "truth").mkdir(parents=True)
    (project_dir / "truth" / "pending_hooks.md").write_text(
        "# Hooks\njust text\n", encoding="utf-8")
    result = _result(g4_foreshadowing_track([str(marker)]))
    assert any("G4.ft.no_changes" in mf for mf in result["must_fix"])

@pytest.mark.unit
def test_fails_when_no_chapter_refs(tmp_path: Path) -> None:
    project_dir, marker = _setup(tmp_path)
    (project_dir / "truth").mkdir(parents=True)
    (project_dir / "truth" / "pending_hooks.md").write_text(
        "# Hooks\n操作: PLANTED\n", encoding="utf-8")
    result = _result(g4_foreshadowing_track([str(marker)]))
    assert any("G4.ft.chapter_refs" in mf for mf in result["must_fix"])

@pytest.mark.unit
def test_passes_with_changes_and_refs(tmp_path: Path) -> None:
    project_dir, marker = _setup(tmp_path)
    (project_dir / "truth").mkdir(parents=True)
    (project_dir / "truth" / "pending_hooks.md").write_text(
        "# Hooks\n操作: PLANTED\n第1章 第2章\n", encoding="utf-8")
    result = _result(g4_foreshadowing_track([str(marker)]))
    assert result["status"] == "PASS"
