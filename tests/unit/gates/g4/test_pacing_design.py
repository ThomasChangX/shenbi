"""Bespoke error-path tests for g4_pacing_design."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from shenbi.gates.g4.pacing_design import g4_pacing_design


def _setup(tmp_path: Path) -> tuple[Path, Path]:
    project_dir = tmp_path / "project"
    sub_dir = project_dir / "skill-output"
    sub_dir.mkdir(parents=True)
    marker = sub_dir / "out.md"
    marker.write_text("x", encoding="utf-8")
    return project_dir, marker


def _result(s: str) -> dict[str, Any]:
    return json.loads(s)


@pytest.mark.unit
def test_fails_when_rhythm_missing(tmp_path: Path) -> None:
    project_dir, marker = _setup(tmp_path)
    (project_dir / "outline").mkdir()
    result = _result(g4_pacing_design([str(marker)]))
    assert any("G4.rhythm.not_found" in mf for mf in result["must_fix"])


@pytest.mark.unit
def test_fails_when_beats_missing(tmp_path: Path) -> None:
    project_dir, marker = _setup(tmp_path)
    (project_dir / "outline").mkdir(parents=True)
    (project_dir / "outline" / "rhythm_principles.md").write_text(
        "# Rhythm\nno beats\n", encoding="utf-8"
    )
    result = _result(g4_pacing_design([str(marker)]))
    assert any(mf.startswith("G4.pd.beats") for mf in result["must_fix"])


@pytest.mark.unit
def test_fails_without_three_lines(tmp_path: Path) -> None:
    project_dir, marker = _setup(tmp_path)
    (project_dir / "outline").mkdir(parents=True)
    (project_dir / "outline" / "rhythm_principles.md").write_text(
        "铺垫升级爆发余波QUESTFIRE\n战斗日常对话探索\n", encoding="utf-8"
    )
    result = _result(g4_pacing_design([str(marker)]))
    assert any("G4.pd.three_lines" in mf for mf in result["must_fix"])


@pytest.mark.unit
def test_passes_with_complete_rhythm(tmp_path: Path) -> None:
    project_dir, marker = _setup(tmp_path)
    (project_dir / "outline").mkdir(parents=True)
    (project_dir / "outline" / "rhythm_principles.md").write_text(
        "铺垫 升级 爆发 余波\nQUEST FIRE CONSTELLATION\n战斗 对话 日常 探索 修炼 阴谋\n单调性\n",
        encoding="utf-8",
    )
    result = _result(g4_pacing_design([str(marker)]))
    assert result["status"] == "PASS"
