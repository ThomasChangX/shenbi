"""Bespoke error-path tests for g4_context_composing.

context_composing checks for P1-P7 labels and non-empty P1+P2 content.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from shenbi.gates.g4.context_composing import g4_context_composing


def _run(fps: list[str], rd: str | None = None) -> dict[str, Any]:
    return json.loads(g4_context_composing(fps, rd))


@pytest.mark.unit
def test_fails_when_p_labels_missing(tmp_path: Path) -> None:
    """File missing some P labels -> FAIL G4.cc.labels."""
    f = tmp_path / "ctx.md"
    f.write_text("P1: intro\nP2: body\n", encoding="utf-8")
    result = _run([str(f)])
    assert result["status"] == "FAIL"
    assert any("G4.cc.labels" in mf for mf in result["must_fix"])


@pytest.mark.unit
def test_passes_with_all_p_labels(tmp_path: Path) -> None:
    """File with all 7 P labels -> PASS G4.cc.labels."""
    content = "\n".join(f"P{i}: content for {i}" for i in range(1, 8))
    f = tmp_path / "ctx.md"
    f.write_text(content, encoding="utf-8")
    result = _run([str(f)])
    assert any(c["id"] == "G4.cc.labels" and c["s"] == "PASS" for c in result["checks"])


@pytest.mark.unit
def test_fails_when_p1p2_empty(tmp_path: Path) -> None:
    """File with empty P1 content -> FAIL G4.cc.p1p2_empty."""
    f = tmp_path / "ctx.md"
    f.write_text("P1:\nP2: body\nP3: x\nP4: x\nP5: x\nP6: x\nP7: x\n", encoding="utf-8")
    result = _run([str(f)])
    assert result["status"] == "FAIL"
    assert any("G4.cc.p1p2_empty" in mf for mf in result["must_fix"])


@pytest.mark.unit
def test_passes_with_non_empty_p1p2(tmp_path: Path) -> None:
    """File with non-empty P1+P2 -> PASS G4.cc.p1p2."""
    f = tmp_path / "ctx.md"
    f.write_text(
        "P1: introduction\nP2: body text\nP3: x\nP4: x\nP5: x\nP6: x\nP7: x\n", encoding="utf-8"
    )
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
