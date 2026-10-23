"""Bespoke error-path tests for g4_volume_outlining."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from shenbi.gates.g4.volume_outlining import g4_volume_outlining


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
def test_fails_when_volume_map_missing(tmp_path: Path) -> None:
    project_dir, marker = _setup(tmp_path)
    (project_dir / "outline").mkdir()
    result = _result(g4_volume_outlining([str(marker)], rd=str(project_dir)))
    assert any("G4.vo.not_found" in mf for mf in result["must_fix"])


@pytest.mark.unit
def test_fails_when_no_volumes(tmp_path: Path) -> None:
    project_dir, marker = _setup(tmp_path)
    (project_dir / "outline").mkdir(parents=True)
    (project_dir / "outline" / "volume_map.md").write_text(
        "# Volumes\nno sections\n", encoding="utf-8"
    )
    result = _result(g4_volume_outlining([str(marker)], rd=str(project_dir)))
    assert any("G4.vo.no_volumes" in mf for mf in result["must_fix"])


@pytest.mark.unit
def test_fails_when_volume_incomplete(tmp_path: Path) -> None:
    project_dir, marker = _setup(tmp_path)
    (project_dir / "outline").mkdir(parents=True)
    (project_dir / "outline" / "volume_map.md").write_text(
        "## 第一卷：起源\nSome text\n", encoding="utf-8"
    )
    result = _result(g4_volume_outlining([str(marker)], rd=str(project_dir)))
    assert any("G4.vo.objective" in mf for mf in result["must_fix"])


@pytest.mark.unit
def test_passes_with_complete_volume(tmp_path: Path) -> None:
    project_dir, marker = _setup(tmp_path)
    (project_dir / "outline").mkdir()
    (project_dir / "outline" / "volume_map.md").write_text(
        "## 第一卷：起源\n**Objective**:有\n#### KR1\n#### KR2\n#### KR3\n张力曲线\n跨卷桥接\n",
        encoding="utf-8",
    )
    result = _result(g4_volume_outlining([str(marker)], rd=str(project_dir)))
    assert result["status"] == "PASS"


@pytest.mark.unit
def test_complete_volume_without_quote_line_warns_not_fails(tmp_path: Path) -> None:
    """P2-6: a structurally complete volume lacking a 金句与梗位 line gets a
    WARN check (G4.vo.quote_line), never a must_fix — old volumes stay green.
    """
    project_dir, marker = _setup(tmp_path)
    (project_dir / "outline").mkdir()
    (project_dir / "outline" / "volume_map.md").write_text(
        "## 第一卷：起源\n**Objective**:有\n#### KR1\n#### KR2\n#### KR3\n张力曲线\n跨卷桥接\n",
        encoding="utf-8",
    )
    result = _result(g4_volume_outlining([str(marker)], rd=str(project_dir)))
    assert result["status"] == "PASS"
    assert not any("G4.vo.quote_line" in mf for mf in result.get("must_fix", []))
    assert any(c["id"] == "G4.vo.quote_line" and c["s"] == "WARN" for c in result["checks"])


@pytest.mark.unit
def test_volume_with_quote_line_gets_pass(tmp_path: Path) -> None:
    project_dir, marker = _setup(tmp_path)
    (project_dir / "outline").mkdir()
    (project_dir / "outline" / "volume_map.md").write_text(
        "## 第一卷：起源\n**Objective**:有\n#### KR1\n#### KR2\n#### KR3\n张力曲线\n跨卷桥接\n"
        "金句与梗位：金句「别人穿越送金手指，我穿越送债务。」出场第 1 章；梗位：记账式吐槽；卷末彩蛋：档案卡\n",
        encoding="utf-8",
    )
    result = _result(g4_volume_outlining([str(marker)], rd=str(project_dir)))
    assert result["status"] == "PASS"
    assert any(c["id"] == "G4.vo.quote_line" and c["s"] == "PASS" for c in result["checks"])
