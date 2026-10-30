"""spec #82 Task 10: shadow-promotion lint tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.lint_shadow_promotion import check_promotion

GENRE = {
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
        "cold_streak_cap": {"max": 3, "shadow": True},
        "hot_hook_floor": {"window": 10, "min": 1, "shadow": False},
    },
}


def _mk(tmp_path: Path, *, warn_chapters: dict[str, list[int]], ledger: str | None = None) -> Path:
    (tmp_path / "genre-config.json").write_text(
        json.dumps(GENRE, ensure_ascii=False), encoding="utf-8"
    )
    lines = []
    for gate, chapters in warn_chapters.items():
        for ch in chapters:
            lines.append(
                json.dumps(
                    {
                        "seq": 1,
                        "action": "WARN",
                        "actor": "chapter-loop",
                        "actor_role": "SYSTEM",
                        "target": f"ch{ch}",
                        "gate": "shadow",
                        "payload": {"chapter": ch, "item": f"[shadow] G4.{gate}:x"},
                        "schema_version": 1,
                        "signature": "0" * 64,
                        "prev_signature": "0" * 64,
                    },
                    ensure_ascii=False,
                )
            )
    if lines:
        (tmp_path / "trace.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
    if ledger:
        (tmp_path / "ledger.md").write_text(ledger, encoding="utf-8")
    return tmp_path


@pytest.mark.unit
def test_two_clean_bundles_flagged(tmp_path: Path) -> None:
    _mk(tmp_path, warn_chapters={"cp.cold_streak_window": [37, 38]})
    f = check_promotion(tmp_path, None)
    assert any("cold_streak_window" in x and "转正" in x for x in f)


@pytest.mark.unit
def test_single_bundle_not_flagged(tmp_path: Path) -> None:
    _mk(tmp_path, warn_chapters={"cp.cold_streak_window": [37]})
    f = check_promotion(tmp_path, None)
    assert not any("cold_streak" in x for x in f)


@pytest.mark.unit
def test_promoted_gate_not_flagged(tmp_path: Path) -> None:
    # hot_hook_floor shadow:false in GENRE — WARN events for it are ignored
    _mk(tmp_path, warn_chapters={"cp.hot_hook_window": [37, 38]})
    f = check_promotion(tmp_path, None)
    assert not any("hot_hook" in x for x in f)


@pytest.mark.unit
def test_misfire_ruling_resets_streak(tmp_path: Path) -> None:
    _mk(
        tmp_path,
        warn_chapters={"cp.cold_streak_window": [37, 38]},
        ledger="- shadow 误伤：cold_streak_window ch38（金句位燃误判）",
    )
    f = check_promotion(tmp_path, tmp_path / "ledger.md")
    assert not any("cold_streak" in x and "转正" in x for x in f)


@pytest.mark.unit
def test_no_trace_degrades_visible(tmp_path: Path) -> None:
    _mk(tmp_path, warn_chapters={})
    f = check_promotion(tmp_path, None)
    assert any("无 shadow WARN 事件" in x for x in f)
