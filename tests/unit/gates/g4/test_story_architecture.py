"""Bespoke error-path tests for g4_story_architecture.

story_architecture resolves project_dir = fps[0].parent.parent, so fps[0]
lives at <project_dir>/<sub>/<file> and the checker reads from project_dir.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from shenbi.gates.g4.story_architecture import g4_story_architecture


def _result(s: str) -> dict[str, Any]:
    return json.loads(s)


def _setup(tmp_path: Path) -> tuple[Path, Path]:
    """Build a <project>/<sub>/ tree; return (project_dir, marker file).
    fps[0] lives at <project>/<sub>/<file> so fps[0].parent.parent == project_dir.
    """
    project_dir = tmp_path / "project"
    sub_dir = project_dir / "skill-output"
    sub_dir.mkdir(parents=True)
    marker = sub_dir / "out.md"
    marker.write_text("x", encoding="utf-8")
    return project_dir, marker


@pytest.mark.unit
def test_fails_when_story_frame_missing_conflict(tmp_path: Path) -> None:
    """story_frame.md without surface_conflict -> FAIL G4.sf.missing_surface_conflict."""
    project_dir, marker = _setup(tmp_path)
    outline = project_dir / "outline"
    outline.mkdir(parents=True)
    (outline / "story_frame.md").write_text(
        "---\npersonal_conflict: 复仇\ndeep_conflict: 正义\n---\n# Story\n",
        encoding="utf-8",
    )
    result = _result(g4_story_architecture([str(marker)], rd=str(project_dir)))
    assert result["status"] == "FAIL"
    assert any("G4.sf.missing_surface_conflict" in mf for mf in result["must_fix"])


@pytest.mark.unit
def test_fails_when_story_frame_yaml_error(tmp_path: Path) -> None:
    """story_frame.md with invalid YAML -> FAIL G4.sf.yaml_error."""
    project_dir, marker = _setup(tmp_path)
    outline = project_dir / "outline"
    outline.mkdir(parents=True)
    (outline / "story_frame.md").write_text("---\nbad: : yaml\n---\n# Story\n", encoding="utf-8")
    result = _result(g4_story_architecture([str(marker)], rd=str(project_dir)))
    assert result["status"] == "FAIL"
    assert any("G4.sf.yaml_error" in mf for mf in result["must_fix"])


@pytest.mark.unit
def test_passes_when_all_conflicts_present(tmp_path: Path) -> None:
    """story_frame.md with all three conflicts + volume_map with OKRs -> PASS."""
    project_dir, marker = _setup(tmp_path)
    outline = project_dir / "outline"
    outline.mkdir(parents=True)
    (outline / "story_frame.md").write_text(
        "---\nsurface_conflict: 逃亡\npersonal_conflict: 复仇\ndeep_conflict: 正义\n---\n",
        encoding="utf-8",
    )
    (outline / "volume_map.md").write_text(
        "## 第一卷：起源\n**Objective**: build world\n**Key Results**: introduce hero\n",
        encoding="utf-8",
    )
    (outline / "rhythm_principles.md").write_text("# Rhythm\n\nnon-empty\n", encoding="utf-8")
    result = _result(g4_story_architecture([str(marker)], rd=str(project_dir)))
    assert result["status"] == "PASS"


@pytest.mark.unit
def test_fails_when_volume_map_missing(tmp_path: Path) -> None:
    """Missing volume_map.md -> FAIL G4.volumes.not_found."""
    project_dir, marker = _setup(tmp_path)
    outline = project_dir / "outline"
    outline.mkdir(parents=True)
    result = _result(g4_story_architecture([str(marker)], rd=str(project_dir)))
    assert result["status"] == "FAIL"
    assert any("G4.volumes.not_found" in mf for mf in result["must_fix"])


@pytest.mark.unit
def test_fails_when_volume_has_no_okrs(tmp_path: Path) -> None:
    """volume_map.md with volume but no Objective/KR -> FAIL G4.volumes.obj_kr."""
    project_dir, marker = _setup(tmp_path)
    outline = project_dir / "outline"
    outline.mkdir(parents=True)
    (outline / "volume_map.md").write_text(
        "## 第一卷\nSome content without OKRs.\n", encoding="utf-8"
    )
    result = _result(g4_story_architecture([str(marker)], rd=str(project_dir)))
    assert result["status"] == "FAIL"
    assert any("G4.volumes.obj_kr" in mf for mf in result["must_fix"])
