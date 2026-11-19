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


# ── spec #116 T4 Task 3：其余 in-scope 门变异负例（12 FAIL 组＋5 WARN-only＋5 helper 级）──


def test_scene_visuals_stripped_fails_concreteness_gate() -> None:
    """尾窗段视觉动词/对白全数剥除 → 全窗口无 vn/di 段 → no_visual_scene."""
    res = _g4("chapter-1-scene-visuals-stripped.md")
    mf = res.get("must_fix", [])
    assert any(m.startswith("G4.cd.no_visual_scene:") for m in mf), mf[:3]


def test_scene_markers_removed_fails_scene_count_gate() -> None:
    """场景标记行删除（--full：裁片本无标记，红须来自变异非裁片副作用，NB6）."""
    res = _g4("chapter-1-scene-markers-removed.md")
    mf = res.get("must_fix", [])
    assert any(m.startswith("G4.cd.scene_count:") and "<2" in m for m in mf), mf[:3]


def test_fatigue_flooded_fails_fatigue_gate() -> None:
    """「他心中暗道。」×9 段尾追加（FATIGUE_BASE 暗道面）→ 9>8."""
    res = _g4("chapter-1-fatigue-flooded.md")
    mf = res.get("must_fix", [])
    assert any(m.startswith("G4.fatigue:") and ">8" in m for m in mf), mf[:3]


def test_meta_injected_fails_meta_gate() -> None:
    """META_NARRATIVE 闭集词段（由此可见/综上所述）插入 → meta."""
    res = _g4("chapter-1-meta-injected.md")
    mf = res.get("must_fix", [])
    assert any(m.startswith("G4.meta:") and "由此可见" in m for m in mf), mf[:3]
