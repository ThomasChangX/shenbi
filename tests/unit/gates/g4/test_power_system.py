"""Bespoke error-path tests for g4_power_system."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any
import pytest
from shenbi.gates.g4.power_system import g4_power_system

def _setup(tmp_path: Path) -> tuple[Path, Path]:
    project_dir = tmp_path / "project"; sub_dir = project_dir / "skill-output"
    sub_dir.mkdir(parents=True); marker = sub_dir / "out.md"
    marker.write_text("x", encoding="utf-8")
    return project_dir, marker

def _result(s: str) -> dict[str, Any]:
    return json.loads(s)

@pytest.mark.unit
def test_fails_when_power_system_missing(tmp_path: Path) -> None:
    project_dir, marker = _setup(tmp_path)
    result = _result(g4_power_system([str(marker)]))
    assert any("G4.ps.not_found" in mf for mf in result["must_fix"])

@pytest.mark.unit
def test_fails_with_few_table_rows(tmp_path: Path) -> None:
    project_dir, marker = _setup(tmp_path)
    (project_dir / "world").mkdir(parents=True)
    (project_dir / "world" / "power_system.md").write_text(
        "| a |\n| b |\n| c |\n", encoding="utf-8")
    result = _result(g4_power_system([str(marker)]))
    assert any("G4.ps.level_table_rows" in mf for mf in result["must_fix"])

@pytest.mark.unit
def test_fails_when_advancement_missing(tmp_path: Path) -> None:
    project_dir, marker = _setup(tmp_path)
    (project_dir / "world").mkdir(parents=True)
    (project_dir / "world" / "power_system.md").write_text(
        "| a | b | c | d | e |\nNo advancement\n", encoding="utf-8")
    result = _result(g4_power_system([str(marker)]))
    assert any("G4.ps.advancement_rules" in mf for mf in result["must_fix"])

@pytest.mark.unit
def test_passes_with_complete_power_system(tmp_path: Path) -> None:
    project_dir, marker = _setup(tmp_path)
    (project_dir / "world").mkdir(parents=True)
    content = "| a | b | c | d | e | f |\n" * 6
    content += "## 进阶\n进阶规则内容\n"
    content += "能做和不能做的事情\n"
    content += "## 代价\n代价类型\n"
    content += "力量上限\n跨级战斗\n"
    (project_dir / "world" / "power_system.md").write_text(content, encoding="utf-8")
    result = _result(g4_power_system([str(marker)]))
    assert result["status"] == "PASS"
