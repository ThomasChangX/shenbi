"""Bespoke error-path tests for g4_plot_thread_weaver."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from shenbi.gates.g4.plot_thread_weaver import g4_plot_thread_weaver


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
def test_fails_when_thread_map_missing(tmp_path: Path) -> None:
    """Missing thread_map.md -> FAIL."""
    project_dir, marker = _setup(tmp_path)
    outline = project_dir / "outline"
    outline.mkdir(parents=True)
    result = _result(g4_plot_thread_weaver([str(marker)], rd=str(project_dir)))
    assert any("G4.thread.not_found" in mf for mf in result["must_fix"])


@pytest.mark.unit
def test_fails_when_no_lines(tmp_path: Path) -> None:
    """thread_map.md without A/B/C lines -> FAIL."""
    project_dir, marker = _setup(tmp_path)
    outline = project_dir / "outline"
    outline.mkdir(parents=True)
    (outline / "thread_map.md").write_text("# Threads\nsomething\n", encoding="utf-8")
    result = _result(g4_plot_thread_weaver([str(marker)], rd=str(project_dir)))
    assert any("G4.pt.lines" in mf for mf in result["must_fix"])


@pytest.mark.unit
def test_passes_with_valid_thread_map(tmp_path: Path) -> None:
    """thread_map.md with A/B/C, table, blank detection -> PASS."""
    project_dir, marker = _setup(tmp_path)
    outline = project_dir / "outline"
    outline.mkdir(parents=True)
    (outline / "thread_map.md").write_text(
        "## A 长线\ncontent\n## B 中线\ncontent\n"
        "## C 短线\ncontent\n"
        "| col1 | col2 | col3 |\n| a | b | c |\n| d | e | f |\n"
        "空白检测\n",
        encoding="utf-8",
    )
    result = _result(g4_plot_thread_weaver([str(marker)], rd=str(project_dir)))
    assert result["status"] == "PASS"
