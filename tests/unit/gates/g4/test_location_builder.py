"""Bespoke error-path tests for g4_location_builder."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from shenbi.gates.g4.location_builder import g4_location_builder


def _setup(tmp_path: Path) -> tuple[Path, Path]:
    project_dir = tmp_path / "project"; sub_dir = project_dir / "skill-output"
    sub_dir.mkdir(parents=True); marker = sub_dir / "out.md"
    marker.write_text("x", encoding="utf-8")
    return project_dir, marker

def _result(s: str) -> dict[str, Any]:
    return json.loads(s)

@pytest.mark.unit
def test_fails_when_locations_missing(tmp_path: Path) -> None:
    project_dir, marker = _setup(tmp_path)
    result = _result(g4_location_builder([str(marker)]))
    assert any("G4.locations.not_found" in mf for mf in result["must_fix"])

@pytest.mark.unit
def test_fails_when_no_location_sections(tmp_path: Path) -> None:
    project_dir, marker = _setup(tmp_path)
    (project_dir / "world").mkdir(parents=True)
    (project_dir / "world" / "locations.md").write_text("# Locations\nnothing\n", encoding="utf-8")
    result = _result(g4_location_builder([str(marker)]))
    assert any("G4.lb.no_locations" in mf for mf in result["must_fix"])

@pytest.mark.unit
def test_fails_when_location_incomplete(tmp_path: Path) -> None:
    project_dir, marker = _setup(tmp_path)
    (project_dir / "world").mkdir(parents=True)
    (project_dir / "world" / "locations.md").write_text(
        "## 地点：城堡\n### 1. 布局描述\n太小\n### 2. 氛围锚点\n太短\n### 功能事件\nx\n",
        encoding="utf-8")
    result = _result(g4_location_builder([str(marker)]))
    assert any("G4.lb.complete" in mf for mf in result["must_fix"])

@pytest.mark.unit
def test_passes_with_valid_location(tmp_path: Path) -> None:
    project_dir, marker = _setup(tmp_path)
    (project_dir / "world").mkdir(parents=True)
    layout = "字" * 200; atmo = "字" * 150
    (project_dir / "world" / "locations.md").write_text(
        f"## 地点：城堡\n### 布局描述\n{layout}\n### 氛围锚点\n{atmo}\n### 功能事件\nx\n",
        encoding="utf-8")
    result = _result(g4_location_builder([str(marker)]))
    assert result["status"] == "PASS"
