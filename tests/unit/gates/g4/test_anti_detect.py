"""Bespoke error-path tests for g4_anti_detect."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from shenbi.gates.g4.anti_detect import g4_anti_detect


def _run(fps: list[str], rd: str | None = None) -> dict[str, Any]:
    return json.loads(g4_anti_detect(fps, rd))

@pytest.mark.unit
def test_fails_when_no_report_block(tmp_path: Path) -> None:
    """Without ## 改写报告 -> FAIL."""
    f = tmp_path / "ch.md"
    f.write_text("# 章节\n内容。\n", encoding="utf-8")
    result = _run([str(f)])
    assert any("G4.ad.no_report" in mf for mf in result["must_fix"])

@pytest.mark.unit
def test_passes_with_report_and_table(tmp_path: Path) -> None:
    """## 改写报告 with table-row techniques -> PASS."""
    f = tmp_path / "ch.md"
    f.write_text("# 章节\n\n## 改写报告\n| 技巧 | 说明 |\n| 替换 | 动\n", encoding="utf-8")
    result = _run([str(f)])
    assert any(c.get("id") == "G4.ad.techniques" and c["s"] == "PASS" for c in result["checks"])

@pytest.mark.unit
def test_fails_when_no_techniques_in_report(tmp_path: Path) -> None:
    """## 改写报告 but no table/list techniques -> FAIL."""
    f = tmp_path / "ch.md"
    f.write_text("# 章节\n\n## 改写报告\n只是描述。\n", encoding="utf-8")
    result = _run([str(f)])
    assert any("G4.ad.no_techniques" in mf for mf in result["must_fix"])

@pytest.mark.unit
def test_fails_when_file_not_found(tmp_path: Path) -> None:
    """Missing file -> FAIL."""
    result = _run([str(tmp_path / "nonexistent.md")])
    assert any("G4.ad.not_found" in mf for mf in result["must_fix"])

@pytest.mark.unit
def test_skips_on_empty_fps(tmp_path: Path) -> None:
    """Empty fps -> SKIP."""
    result = _run([])
    assert any(c["id"] == "G4.ad" and c["s"] == "SKIP" for c in result["checks"])
