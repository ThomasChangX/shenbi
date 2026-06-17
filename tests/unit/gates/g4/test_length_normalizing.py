"""Bespoke error-path tests for g4_length_normalizing."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from shenbi.gates.g4.length_normalizing import g4_length_normalizing


def _run(fps: list[str], rd: str | None = None) -> dict[str, Any]:
    return json.loads(g4_length_normalizing(fps, rd))


@pytest.mark.unit
def test_fails_when_file_not_found(tmp_path: Path) -> None:
    result = _run([str(tmp_path / "nonexistent.md")])
    assert any("G4.ln.not_found" in mf for mf in result["must_fix"])


@pytest.mark.unit
def test_fails_when_no_report_block(tmp_path: Path) -> None:
    f = tmp_path / "ch.md"
    f.write_text("# 章节\n正文。\n", encoding="utf-8")
    result = _run([str(f)])
    assert any("G4.ln.no_report" in mf for mf in result["must_fix"])


@pytest.mark.unit
def test_passes_when_no_normalization_needed(tmp_path: Path) -> None:
    f = tmp_path / "ch.md"
    f.write_text("# 章节\n正文内容。\n## 归一化报告\n不触发无需归一化。\n", encoding="utf-8")
    result = _run([str(f)])
    assert any(c.get("id") == "G4.ln.word_count" and c["s"] == "PASS" for c in result["checks"])


@pytest.mark.unit
def test_fails_when_below_floor(tmp_path: Path) -> None:
    f = tmp_path / "ch.md"
    f.write_text("# 章节\n正文\n## 归一化报告\n已归一化。\n", encoding="utf-8")
    result = _run([str(f)])
    assert any("G4.ln.below_floor" in mf for mf in result["must_fix"])


@pytest.mark.unit
def test_skips_on_empty_fps(tmp_path: Path) -> None:
    result = _run([])
    assert any(c["id"] == "G4.ln" and c["s"] == "SKIP" for c in result["checks"])
