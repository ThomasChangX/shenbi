"""Bespoke error-path tests for g4_faction_builder."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from shenbi.gates.g4.faction_builder import g4_faction_builder


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
def test_fails_when_factions_file_missing(tmp_path: Path) -> None:
    """Missing world/factions.md -> FAIL."""
    project_dir, marker = _setup(tmp_path)
    result = _result(g4_faction_builder([str(marker)]))
    assert any("G4.factions.not_found" in mf for mf in result["must_fix"])


@pytest.mark.unit
def test_fails_when_less_than_2_factions(tmp_path: Path) -> None:
    """Only 1 faction -> FAIL."""
    project_dir, marker = _setup(tmp_path)
    world = project_dir / "world"
    world.mkdir(parents=True)
    (world / "factions.md").write_text("## 势力：光明会\n", encoding="utf-8")
    result = _result(g4_faction_builder([str(marker)]))
    assert any("G4.factions.count" in mf for mf in result["must_fix"])


@pytest.mark.unit
def test_passes_with_2_complete_factions(tmp_path: Path) -> None:
    """2 factions with hierarchy, internal, cross, interest -> PASS."""
    project_dir, marker = _setup(tmp_path)
    world = project_dir / "world"
    world.mkdir(parents=True)
    content = ""
    for name in ["光明会", "暗影会"]:
        content += f"## 势力：{name}\n### 层级\n### 内部矛盾\n跨势力动态\n利益驱动\n"
    (world / "factions.md").write_text(content, encoding="utf-8")
    result = _result(g4_faction_builder([str(marker)]))
    assert result["status"] == "PASS"
