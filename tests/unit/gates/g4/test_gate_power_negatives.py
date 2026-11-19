"""Spec #116 T4: real-chapter mutation → gate FAIL red tests (prose face)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

FIX_DIR = Path(__file__).resolve().parents[3] / "fixtures" / "gate-power"  # NB2：parents[3]=tests/


def _g4(fixture_name: str) -> dict[str, Any]:
    fp = str(FIX_DIR / fixture_name)
    from shenbi.gates.g4.chapter_drafting import g4_chapter_drafting

    return json.loads(g4_chapter_drafting([fp], str(FIX_DIR), str(FIX_DIR), repo_root=None))


def test_hook_killed_real_chapter_fails_hook_gate() -> None:
    """真实章变异→FAIL：章尾窗口张力全部抹除（spec 验收 5 最低子集之一）。"""
    res = _g4("chapter-1-hook-killed.md")
    mf = res.get("must_fix", [])
    assert any(m.startswith("G4.cd.no_hook:") for m in mf), mf[:3]


def test_protagonist_vanished_real_chapter_fails_presence_gate() -> None:
    """C2：真臂=protagonist_absent（major_chars 属他门；SKIP 需 characters 前置物）。"""
    res = _g4("chapter-1-protagonist-vanished.md")
    mf = res.get("must_fix", [])
    assert any(m.startswith("G4.cd.protagonist_absent:") for m in mf), mf[:3]


def test_transition_flooded_real_chapter_fails_transition_gate() -> None:
    res = _g4("chapter-1-transition-flooded.md")
    mf = res.get("must_fix", [])
    assert any(m.startswith("G4.transition:") for m in mf), mf[:3]
