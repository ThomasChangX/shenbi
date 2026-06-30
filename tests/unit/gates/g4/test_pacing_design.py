"""Tests for g4_pacing_design (rewritten: structured Pydantic validation)."""

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
    assert result["status"] == "FAIL"


@pytest.mark.unit
def test_fails_when_beats_missing(tmp_path: Path) -> None:
    project_dir, marker = _setup(tmp_path)
    (project_dir / "outline").mkdir(parents=True)
    (project_dir / "outline" / "rhythm_principles.md").write_text(
        "# Rhythm\nno beat data here\n", encoding="utf-8"
    )
    result = _result(g4_pacing_design([str(marker)]))
    assert result["status"] == "FAIL"


@pytest.mark.unit
def test_fails_without_three_lines(tmp_path: Path) -> None:
    project_dir, marker = _setup(tmp_path)
    (project_dir / "outline").mkdir(parents=True)
    (project_dir / "outline" / "rhythm_principles.md").write_text(
        "铺垫 25% 升级 25% 爆发 25% 余波 25%\nQUEST FIRE\n",
        encoding="utf-8",
    )
    result = _result(g4_pacing_design([str(marker)]))
    assert result["status"] == "FAIL"
    assert any(
        "CONSTELLATION" in mf or "narrative lines" in mf for mf in result.get("must_fix", [])
    )


@pytest.mark.unit
def test_fails_when_beat_sum_wrong(tmp_path: Path) -> None:
    project_dir, marker = _setup(tmp_path)
    (project_dir / "outline").mkdir(parents=True)
    (project_dir / "outline" / "rhythm_principles.md").write_text(
        "铺垫 20% 升级 20% 爆发 20% 余波 20%\nQUEST 40% FIRE 35% CONSTELLATION 25%\n",
        encoding="utf-8",
    )
    result = _result(g4_pacing_design([str(marker)]))
    assert result["status"] == "FAIL"


@pytest.mark.unit
def test_passes_with_complete_rhythm(tmp_path: Path) -> None:
    project_dir, marker = _setup(tmp_path)
    (project_dir / "outline").mkdir(parents=True)
    (project_dir / "outline" / "rhythm_principles.md").write_text(
        "铺垫 25% 升级 30% 爆发 25% 余波 20%\n"
        "QUEST 40% FIRE 35% CONSTELLATION 25%\n"
        "战斗 对话 日常 探索 修炼 阴谋 逃亡 揭示\n",
        encoding="utf-8",
    )
    result = _result(g4_pacing_design([str(marker)]))
    assert result["status"] == "PASS"
