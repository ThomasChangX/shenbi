"""spec #82 T7 (Task 10): retention_anchor window parameterization."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from shenbi.gates.g4.chapter_planning import g4_chapter_planning

GENRE_BASE: dict[str, Any] = {
    "version": "1",
    "approval": {"decision": "approved"},
    "auditDimensions": {f"d{i}": True for i in range(5)},
    "chapterTypes": {f"t{i}": True for i in range(6)},
    "customRules": [],
    "fatigueWords": {"禁用": []},
    "pacing": {},
    "updated": "",
    "market_params": {
        "payoff_density": {"window": 3, "min": 1},
        "hook_grading": {"max_consecutive_micro": 2},
    },
}

PLAN_NO_ANCHOR = "plan_format: v4\nemotion_tone: 悲\n"


def _mk(tmp_path: Path, *, ch: int, retention: dict[str, Any] | None) -> Path:
    (tmp_path / "plans").mkdir(exist_ok=True)
    (tmp_path / "plans" / f"chapter-{ch}-plan.md").write_text(PLAN_NO_ANCHOR, encoding="utf-8")
    genre = json.loads(json.dumps(GENRE_BASE))
    if retention is not None:
        genre["market_params"]["retention_anchor"] = retention
    (tmp_path / "genre-config.json").write_text(
        json.dumps(genre, ensure_ascii=False), encoding="utf-8"
    )
    return tmp_path


def _mf(tmp_path: Path, ch: int) -> list[str]:
    out = g4_chapter_planning(
        [str(tmp_path / "plans" / f"chapter-{ch}-plan.md")], rd=None, project_dir=str(tmp_path)
    )
    return json.loads(out).get("must_fix", [])


@pytest.mark.unit
def test_past_30_missing_anchor_fails_when_window_open(tmp_path: Path) -> None:
    _mk(tmp_path, ch=40, retention={"from_ch": 1, "to_ch": None})  # None = 全卷
    assert any("missing_retention_anchor" in m for m in _mf(tmp_path, 40))


@pytest.mark.unit
def test_legacy_absent_config_uses_hardcode(tmp_path: Path) -> None:
    """Config absent → 1-30 hardcode (existing-project compat)."""
    _mk(tmp_path, ch=40, retention=None)
    assert not any("missing_retention_anchor" in m for m in _mf(tmp_path, 40))  # 40 outside 1-30
    _mk(tmp_path, ch=25, retention=None)
    assert any("missing_retention_anchor" in m for m in _mf(tmp_path, 25))  # 25 inside


@pytest.mark.unit
def test_window_bounds_respected(tmp_path: Path) -> None:
    _mk(tmp_path, ch=5, retention={"from_ch": 10, "to_ch": 20})
    assert not any("missing_retention_anchor" in m for m in _mf(tmp_path, 5))  # below from_ch
    _mk(tmp_path, ch=15, retention={"from_ch": 10, "to_ch": 20})
    assert any("missing_retention_anchor" in m for m in _mf(tmp_path, 15))  # inside
    _mk(tmp_path, ch=25, retention={"from_ch": 10, "to_ch": 20})
    assert not any("missing_retention_anchor" in m for m in _mf(tmp_path, 25))  # above to_ch
