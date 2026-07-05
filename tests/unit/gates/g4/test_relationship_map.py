"""Bespoke error-path tests for g4_relationship_map."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from shenbi.gates.g4.relationship_map import g4_relationship_map


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
def test_fails_when_relationships_missing(tmp_path: Path) -> None:
    project_dir, marker = _setup(tmp_path)
    (project_dir / "characters").mkdir(parents=True)
    result = _result(g4_relationship_map([str(marker)], rd=str(project_dir)))
    assert any("G4.rel.not_found" in mf for mf in result["must_fix"])


@pytest.mark.unit
def test_fails_when_less_than_3_pairs(tmp_path: Path) -> None:
    project_dir, marker = _setup(tmp_path)
    (project_dir / "characters").mkdir(parents=True)
    (project_dir / "characters" / "relationships.md").write_text(
        "## 关系对：A-B\n", encoding="utf-8"
    )
    result = _result(g4_relationship_map([str(marker)], rd=str(project_dir)))
    assert any("G4.rm.pairs" in mf for mf in result["must_fix"])


@pytest.mark.unit
def test_fails_when_character_matrix_missing(tmp_path: Path) -> None:
    project_dir, marker = _setup(tmp_path)
    (project_dir / "characters").mkdir(parents=True)
    pairs = ""
    for p in [(1, 2), (3, 4), (5, 6)]:
        pairs += f"## 关系对：{p[0]}-{p[1]}\n**利益根基**:有\nSYMMETRIC\n演化轨迹有起始状态\n"
    (project_dir / "characters" / "relationships.md").write_text(pairs, encoding="utf-8")
    result = _result(g4_relationship_map([str(marker)], rd=str(project_dir)))
    # Should fail because character_matrix.md doesn't exist
    assert any("G4.rm.character_matrix" in mf for mf in result["must_fix"])


@pytest.mark.unit
def test_passes_with_complete_data(tmp_path: Path) -> None:
    project_dir, marker = _setup(tmp_path)
    (project_dir / "characters").mkdir(parents=True)
    pairs = ""
    for p in [(1, 2), (3, 4), (5, 6)]:
        pairs += f"## 关系对：{p[0]}-{p[1]}\n**利益根基**:有\nSYMMETRIC\n演化轨迹有起始状态\n"
    (project_dir / "characters" / "relationships.md").write_text(pairs, encoding="utf-8")
    (project_dir / "truth").mkdir(parents=True)
    (project_dir / "truth" / "character_matrix.md").write_text("# Characters\n", encoding="utf-8")
    result = _result(g4_relationship_map([str(marker)], rd=str(project_dir)))
    assert result["status"] == "PASS"
