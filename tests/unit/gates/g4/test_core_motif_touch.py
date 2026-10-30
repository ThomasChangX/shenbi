"""spec #82 T6 (Task 9): core_motif_touch gate + per-marker-chain lint."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from shenbi.gates.g4.chapter_planning import g4_chapter_planning

GENRE = {
    "version": "1",
    "approval": {"decision": "approved"},
    "auditDimensions": {f"d{i}": True for i in range(5)},
    "chapterTypes": {f"t{i}": True for i in range(6)},
    "customRules": [],
    "fatigueWords": {"禁用": []},
    "updated": "",
    "pacing": {"core_motif_touch": {"max_gap": 6, "shadow": False}},
    "market_params": {
        "payoff_density": {"window": 3, "min": 1},
        "hook_grading": {"max_consecutive_micro": 2},
    },
}

PLAN = """plan_format: v4
emotion_tone: 悲
留存锚: 非锚章
**payoff 拍**: 类型｜轴(债)｜中兑现
章尾张力拍: 章｜『他数到第三遍，门被推开一半。』
章尾钩型: 悬念钩
"""


def _mk(
    tmp_path: Path,
    *,
    ch: int = 45,
    markers: dict[int, list[str]] | None = None,
    genre: dict[str, Any] | None = None,
) -> Path:
    (tmp_path / "plans").mkdir(exist_ok=True)
    (tmp_path / "plans" / f"chapter-{ch}-plan.md").write_text(PLAN, encoding="utf-8")
    (tmp_path / "genre-config.json").write_text(
        json.dumps(genre or GENRE, ensure_ascii=False), encoding="utf-8"
    )
    if markers:
        state = {
            "project_dir": str(tmp_path),
            "chapter_loop": {
                "current_chapter": ch,
                "chapter_states": {
                    str(n): {"declared": {"节点标记集": m}, "status": "complete"}
                    for n, m in markers.items()
                },
            },
        }
        (tmp_path / "pipeline-state.json").write_text(
            json.dumps(state, ensure_ascii=False), encoding="utf-8"
        )
    return tmp_path


def _mf(tmp_path: Path, ch: int) -> list[str]:
    out = g4_chapter_planning(
        [str(tmp_path / "plans" / f"chapter-{ch}-plan.md")], rd=None, project_dir=str(tmp_path)
    )
    return json.loads(out).get("must_fix", [])


@pytest.mark.unit
def test_gap_seven_fails(tmp_path: Path) -> None:
    # last 轮回触点◆ at ch38, current ch45 → gap 7 > 6
    _mk(tmp_path, ch=45, markers={38: ["轮回触点◆"], 40: ["萤回触◆"], 43: ["萤回触◆"]})
    assert any("core_motif_touch" in m for m in _mf(tmp_path, 45))


@pytest.mark.unit
def test_gap_six_passes(tmp_path: Path) -> None:
    _mk(tmp_path, ch=44, markers={38: ["轮回触点◆"]})  # gap 6 ≤ 6
    assert not any("core_motif_touch" in m for m in _mf(tmp_path, 44))


@pytest.mark.unit
def test_any_marker_union_does_not_mask(tmp_path: Path) -> None:
    """audit-plan R2/I1: 萤回触◆ must NOT mask a broken 轮回 chain (single
    chain per marker type — the union variant passed vol-1's 16-chapter
    drought with gaps ≤7 via 萤 markers).
    """
    _mk(tmp_path, ch=45, markers={38: ["轮回触点◆"], 41: ["萤回触◆"], 43: ["萤回触◆"]})
    assert any(
        "core_motif_touch" in m for m in _mf(tmp_path, 45)
    )  # union max gap 3 — must still FAIL


@pytest.mark.unit
def test_vol1_drought_specimen_fails(tmp_path: Path) -> None:
    """ch21-36 zero 轮回触点◆ (vol-1 specimen: last marker ch20)."""
    markers = {20: ["轮回触点◆"]}
    for n in range(21, 36):
        markers[n] = ["萤回触◆"] if n in (22, 29, 35) else []
    _mk(tmp_path, ch=36, markers=markers)
    assert any("core_motif_touch" in m for m in _mf(tmp_path, 36))


@pytest.mark.unit
def test_no_config_skips_gate(tmp_path: Path) -> None:
    genre = json.loads(json.dumps(GENRE))
    del genre["pacing"]["core_motif_touch"]
    _mk(tmp_path, ch=45, markers={38: ["轮回触点◆"]}, genre=genre)
    assert not any("core_motif_touch" in m for m in _mf(tmp_path, 45))
