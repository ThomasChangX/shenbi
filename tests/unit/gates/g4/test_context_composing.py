"""Bespoke error-path tests for g4_context_composing.

context_composing validates the layer-based P1-P7 section titles (spec
§3.5) and non-empty P1+P2 content. Obsolete flat-model titles are rejected.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from shenbi.gates.g4.context_composing import g4_context_composing


def _run(fps: list[str], rd: str | None = None) -> dict[str, Any]:
    return json.loads(g4_context_composing(fps, rd))


def _valid_output() -> str:
    """A context-composing output with all 9 layer-based sections."""
    return (
        "## P1 章节备忘\n"
        "本章备忘内容。\n"
        "## P2 书脊（L5）\n"
        "书脊常青层。\n"
        "## P3 当前大弧（L4）\n"
        "大弧合成。\n"
        "## P4 当前卷摘要（L3）\n"
        "卷摘要。\n"
        "## P5 当前弧段（L2）\n"
        "弧段合成。\n"
        "## P6 近章拍点（L1）\n"
        "近章拍点。\n"
        "## P7 世界铁律与文风\n"
        "铁律与文风。\n"
        "## 近章结尾多样性\n"
        "结尾多样性。\n"
        "## Hook 债务简报\n"
        "债务简报。\n"
    )


@pytest.mark.unit
def test_fails_when_section_titles_missing(tmp_path: Path) -> None:
    """File missing layer-based section titles -> FAIL G4.cc.sections."""
    f = tmp_path / "ctx.md"
    f.write_text("## P1 章节备忘\n内容\n", encoding="utf-8")
    result = _run([str(f)])
    assert result["status"] == "FAIL"
    assert any("G4.cc.sections" in mf for mf in result["must_fix"])


@pytest.mark.unit
def test_passes_with_all_layer_sections(tmp_path: Path) -> None:
    """File with all 9 layer-based sections -> PASS G4.cc.sections."""
    f = tmp_path / "ctx.md"
    f.write_text(_valid_output(), encoding="utf-8")
    result = _run([str(f)])
    assert result["status"] == "PASS"
    assert any(c["id"] == "G4.cc.sections" and c["s"] == "PASS" for c in result["checks"])


@pytest.mark.unit
def test_rejects_obsolete_flat_titles(tmp_path: Path) -> None:
    """Old flat-model titles (P3 活跃伏笔) -> FAIL G4.cc.obsolete_titles."""
    f = tmp_path / "ctx.md"
    f.write_text(_valid_output() + "## P3 活跃伏笔\n旧标题\n", encoding="utf-8")
    result = _run([str(f)])
    assert result["status"] == "FAIL"
    assert any("obsolete_titles" in mf for mf in result["must_fix"])


@pytest.mark.unit
def test_fails_when_p1p2_empty(tmp_path: Path) -> None:
    """File with empty P1 content -> FAIL G4.cc.p1p2_empty."""
    f = tmp_path / "ctx.md"
    # All sections present but P1 body empty.
    f.write_text(_valid_output().replace("本章备忘内容。\n", ""), encoding="utf-8")
    result = _run([str(f)])
    assert result["status"] == "FAIL"
    assert any("G4.cc.p1p2_empty" in mf for mf in result["must_fix"])


@pytest.mark.unit
def test_passes_with_non_empty_p1p2(tmp_path: Path) -> None:
    """File with non-empty P1+P2 -> PASS G4.cc.p1p2."""
    f = tmp_path / "ctx.md"
    f.write_text(_valid_output(), encoding="utf-8")
    result = _run([str(f)])
    assert any(c["id"] == "G4.cc.p1p2" and c["s"] == "PASS" for c in result["checks"])


@pytest.mark.unit
def test_fails_when_file_not_found(tmp_path: Path) -> None:
    """Missing file -> FAIL G4.cc.not_found."""
    result = _run([str(tmp_path / "nonexistent.md")])
    assert result["status"] == "FAIL"
    assert any("G4.cc.not_found" in mf for mf in result["must_fix"])


@pytest.mark.unit
def test_skips_on_empty_fps(tmp_path: Path) -> None:
    """Empty fps list -> SKIP."""
    result = _run([])
    assert any(c["id"] == "G4.cc" and c["s"] == "SKIP" for c in result["checks"])
