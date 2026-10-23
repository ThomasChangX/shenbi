"""Tests for tools/plan_craft_backfill.py — the craft-contract migration.

The 2026-10-23 G4.cp hard gates (emotion_tone / payoff 拍 / 留存锚) are a
breaking change for in-flight project artifacts; this tool is the shipped
migration path (AGENTS.md discipline: field-adding batches must ship
backfill in the same batch). The integration test proves the full loop:
legacy plan fails the gate → backfill --apply → same plan passes.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from shenbi.gates.g4.chapter_planning import g4_chapter_planning
from tools.plan_craft_backfill import RETENTION_WINDOW, backfill_text

REPO_ROOT = Path(__file__).resolve().parents[2]


def _legacy_plan(chapter: int = 5) -> str:
    """A pre-2026-10-23 valid memo: every check of its era passes, none of
    the three craft declarations present.
    """
    content = "# Plan\n\n"
    for i in range(1, 9):
        content += f"## {i}. Section {i}\n"
        if i == 1:
            content += "chapter_role: 推进\n"
        elif i == 5:
            content += "关键抉择\n"
        elif i == 7:
            content += "open advance\n"
        else:
            content += "content\n"
    return content


def _run_gate(fp: Path) -> dict[str, Any]:
    return json.loads(g4_chapter_planning([str(fp)]))


@pytest.mark.unit
def test_legacy_plan_fails_gate_then_backfill_makes_it_pass(tmp_path: Path) -> None:
    """The breaking-change loop: legacy plan → 3 new must_fix → backfill → PASS."""
    plans = tmp_path / "plans"
    plans.mkdir()
    fp = plans / "chapter-005-plan.md"
    fp.write_text(_legacy_plan(), encoding="utf-8")

    before = _run_gate(fp)
    assert before["status"] == "FAIL"
    joined = " ".join(str(mf) for mf in before["must_fix"])
    for new_id in (
        "missing_emotion_tone",
        "missing_payoff_beat",
        "missing_retention_anchor",
    ):
        assert new_id in joined

    import subprocess

    result = subprocess.run(
        [
            "uv",
            "run",
            "python",
            str(REPO_ROOT / "tools" / "plan_craft_backfill.py"),
            str(tmp_path),
            "--apply",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "1 patched" in result.stdout

    after = _run_gate(fp)
    assert after["status"] == "PASS", after.get("must_fix")


@pytest.mark.unit
def test_dry_run_is_default_and_writes_nothing(tmp_path: Path) -> None:
    content = _legacy_plan()
    new_content, actions = backfill_text(content, n=5)
    assert len(actions) == 3  # pure function computes the patch; CLI decides write
    assert "emotion_tone" in new_content and "payoff" in new_content

    plans = tmp_path / "plans"
    plans.mkdir()
    fp = plans / "chapter-005-plan.md"
    fp.write_text(content, encoding="utf-8")
    import subprocess

    result = subprocess.run(
        [
            "uv",
            "run",
            "python",
            str(REPO_ROOT / "tools" / "plan_craft_backfill.py"),
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "DRY-RUN" in result.stdout
    assert fp.read_text(encoding="utf-8") == content


@pytest.mark.unit
def test_idempotent_second_run_is_noop(tmp_path: Path) -> None:
    content = _legacy_plan()
    once, actions1 = backfill_text(content, n=5)
    assert len(actions1) == 3
    twice, actions2 = backfill_text(once, n=5)
    assert actions2 == []
    assert twice == once


@pytest.mark.unit
def test_chapter_31_gets_no_retention_anchor(tmp_path: Path) -> None:
    content = _legacy_plan(chapter=31)
    new_content, actions = backfill_text(content, n=31)
    assert "§2 留存锚" not in actions  # gate SKIPs N>30; backfill must not lie
    assert len(actions) == 2  # emotion_tone + payoff 拍 only
    assert "留存锚" not in new_content


@pytest.mark.unit
def test_window_boundary_matches_gate(tmp_path: Path) -> None:
    """N=30 is inclusive (same boundary as G4.cp)."""
    _, actions = backfill_text(_legacy_plan(), n=RETENTION_WINDOW)
    assert any("留存锚" in a for a in actions)


@pytest.mark.unit
def test_nonstandard_memo_without_sections_is_skipped() -> None:
    _, actions = backfill_text("# just a title\nno sections\n", n=5)
    assert actions and actions[0].startswith("SKIP")
