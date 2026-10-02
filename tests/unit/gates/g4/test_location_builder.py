"""Bespoke error-path tests for g4_location_builder."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from shenbi.gates.g4.location_builder import g4_location_builder


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
def test_fails_when_locations_missing(tmp_path: Path) -> None:
    project_dir, marker = _setup(tmp_path)
    result = _result(g4_location_builder([str(marker)], rd=str(project_dir)))
    assert any("G4.locations.not_found" in mf for mf in result["must_fix"])


@pytest.mark.unit
def test_fails_when_no_location_sections(tmp_path: Path) -> None:
    project_dir, marker = _setup(tmp_path)
    (project_dir / "world").mkdir(parents=True)
    (project_dir / "world" / "locations.md").write_text("# Locations\nnothing\n", encoding="utf-8")
    result = _result(g4_location_builder([str(marker)], rd=str(project_dir)))
    assert any("G4.lb.no_locations" in mf for mf in result["must_fix"])


@pytest.mark.unit
def test_fails_when_location_incomplete(tmp_path: Path) -> None:
    project_dir, marker = _setup(tmp_path)
    (project_dir / "world").mkdir(parents=True)
    (project_dir / "world" / "locations.md").write_text(
        "## 地点：城堡\n### 1. 布局描述\n太小\n### 2. 氛围锚点\n太短\n### 功能事件\nx\n",
        encoding="utf-8",
    )
    result = _result(g4_location_builder([str(marker)], rd=str(project_dir)))
    assert any("G4.lb.complete" in mf for mf in result["must_fix"])


@pytest.mark.unit
def test_passes_with_valid_location(tmp_path: Path) -> None:
    project_dir, marker = _setup(tmp_path)
    (project_dir / "world").mkdir(parents=True)
    layout = "字" * 200
    atmo = "字" * 150
    # Gate requires max(3, round(n*0.5)) valid locations → need ≥6 total, ≥3 valid
    locs = ""
    for i in range(1, 7):
        locs += f"## 地点：城堡{i}\n### 布局描述\n{layout}\n### 氛围锚点\n{atmo}\n### 功能事件\nx\n"
    (project_dir / "world" / "locations.md").write_text(locs, encoding="utf-8")
    result = _result(g4_location_builder([str(marker)], rd=str(project_dir)))
    assert result["status"] == "PASS"


def _full_location(name: str) -> str:
    return (
        f"## 地点：{name}\n### 空间布局\n{'字' * 200}\n"
        f"### 感官锚点\n{'字' * 150}\n### 功能事件\nx\n"
    )


@pytest.mark.unit
def test_line_mid_reference_to_location_heading_not_counted(tmp_path: Path) -> None:
    """probe15 world/locations.md L429: the self-check checklist carries the
    literal ``## 地点:{name}`` inside a non-heading line. The unanchored
    ``re.findall(r"## 地点[::]", ...)`` counted it (9 real → 10) and the
    ``finditer`` section split cut the containing section at the reference —
    the real span lost its tail subsections while the bogus span carried no
    heading at all. Anchored ``^``-line matching must ignore in-line
    references entirely.
    """
    project_dir, marker = _setup(tmp_path)
    (project_dir / "world").mkdir(parents=True)
    # Reference line inside the FIRST section, between its 感官锚点 content
    # and 功能事件: under the unanchored regex the real span lacks 功能事件
    # and the bogus span lacks 布局/氛围 → both invalid, valid 2 < need 3.
    content = _full_location("铁砧港").replace(
        "### 功能事件",
        "- [x] 节标题精确匹配 6 个规定标题（`## 地点：{name}` / `### 功能事件`）\n### 功能事件",
    )
    content += _full_location("九环城") + _full_location("赤锈谷")
    (project_dir / "world" / "locations.md").write_text(content, encoding="utf-8")
    result = _result(g4_location_builder([str(marker)], rd=str(project_dir)))
    assert result["status"] == "PASS", result["must_fix"]


@pytest.mark.unit
def test_locations_denominator_counts_only_line_start_headings(tmp_path: Path) -> None:
    project_dir, marker = _setup(tmp_path)
    (project_dir / "world").mkdir(parents=True)
    content = _full_location("铁砧港") + _full_location("九环城")
    content += "- [x] 节标题精确匹配（`## 地点：{name}`）\n"
    (project_dir / "world" / "locations.md").write_text(content, encoding="utf-8")
    result = _result(g4_location_builder([str(marker)], rd=str(project_dir)))
    # 2 valid of 2 real locations (min_required = max(3, 1) = 3 → FAIL), but
    # the failure must be the completeness ratio on 2 locations — the
    # checklist literal must NOT appear as a 3rd location in the count.
    assert result["status"] == "FAIL"
    assert any(mf.startswith("G4.lb.complete:2/2_") for mf in result["must_fix"]), result[
        "must_fix"
    ]
