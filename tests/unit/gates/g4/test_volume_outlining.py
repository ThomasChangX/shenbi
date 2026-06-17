"""Bespoke error-path tests for g4_volume_outlining."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any
import pytest
from shenbi.gates.g4.volume_outlining import g4_volume_outlining

def _setup(tmp_path: Path) -> tuple[Path, Path]:
    project_dir = tmp_path / "project"; sub_dir = project_dir / "skill-output"
    sub_dir.mkdir(parents=True); marker = sub_dir / "out.md"
    marker.write_text("x", encoding="utf-8")
    return project_dir, marker

def _result(s: str) -> dict[str, Any]:
    return json.loads(s)

@pytest.mark.unit
def test_fails_when_volume_map_missing(tmp_path: Path) -> None:
    project_dir, marker = _setup(tmp_path)
    (project_dir / "outline").mkdir()
    result = _result(g4_volume_outlining([str(marker)]))
    assert any("G4.vo.not_found" in mf for mf in result["must_fix"])

@pytest.mark.unit
def test_fails_when_no_volumes(tmp_path: Path) -> None:
    project_dir, marker = _setup(tmp_path)
    (project_dir / "outline").mkdir(parents=True)
    (project_dir / "outline" / "volume_map.md").write_text(
        "# Volumes\nno sections\n", encoding="utf-8")
    result = _result(g4_volume_outlining([str(marker)]))
    assert any("G4.vo.no_volumes" in mf for mf in result["must_fix"])

@pytest.mark.unit
def test_fails_when_volume_incomplete(tmp_path: Path) -> None:
    project_dir, marker = _setup(tmp_path)
    (project_dir / "outline").mkdir(parents=True)
    (project_dir / "outline" / "volume_map.md").write_text(
        "## 第一卷：起源\nSome text\n", encoding="utf-8")
    result = _result(g4_volume_outlining([str(marker)]))
    assert any("G4.vo.objective" in mf for mf in result["must_fix"])

@pytest.mark.unit
def test_passes_with_complete_volume(tmp_path: Path) -> None:
    project_dir, marker = _setup(tmp_path)
    (project_dir / "outline").mkdir(parents=True)
    (project_dir / "outline" / "volume_map.md").write_text(
        "## 第一卷：起源\n**Objective**:有\n#### KR1\n#### KR2\n#### KR3\n"
        "张力曲线\n跨卷桥接\n", encoding="utf-8")
    result = _result(g4_volume_outlining([str(marker)]))
    assert result["status"] == "PASS"
