"""Tests for the staging residue cleanup one-off (SDD #21 R3.4)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.oneoff.clean_staging_residue import main

REPO = Path(__file__).resolve().parents[3]


def _make_project(tmp_path: Path) -> Path:
    (tmp_path / "staging" / "plans").mkdir(parents=True)
    (tmp_path / "staging" / "truth").mkdir(parents=True)
    return tmp_path


def test_plan_deleted_only_when_committed_version_exists(tmp_path: Path) -> None:
    proj = _make_project(tmp_path)
    (proj / "staging" / "plans" / "chapter-1-plan.md").write_text("stale draft", encoding="utf-8")
    (proj / "staging" / "plans" / "chapter-2-plan.md").write_text(
        "no committed yet", encoding="utf-8"
    )
    (proj / "plans").mkdir()
    (proj / "plans" / "chapter-1-plan.md").write_text("committed", encoding="utf-8")

    rc = main([str(proj), "--apply"])
    assert rc == 0
    assert not (proj / "staging" / "plans" / "chapter-1-plan.md").exists()
    assert (proj / "staging" / "plans" / "chapter-2-plan.md").exists()  # kept


def test_staged_only_rows_replayed_before_delete(tmp_path: Path, capsys) -> None:
    proj = _make_project(tmp_path)
    staged = proj / "staging" / "truth" / "hooks.md"
    staged.write_text(
        "| hook | note |\n|------|------|\n| a | staged-only |\n| b | also-in-live |\n",
        encoding="utf-8",
    )
    (proj / "staging" / ".staging-meta.json").write_text(
        json.dumps({"truth/hooks.md": {"update_mode": "append_dedup", "key_field": "hook"}}),
        encoding="utf-8",
    )
    live = proj / "truth" / "hooks.md"
    live.parent.mkdir(parents=True, exist_ok=True)
    live.write_text("| hook | note |\n|------|------|\n| b | LIVE |\n", encoding="utf-8")

    rc = main([str(proj), "--apply"])
    assert rc == 0
    assert not staged.exists()
    text = live.read_text(encoding="utf-8")
    assert "staged-only" in text  # missing key replayed
    assert text.count("| b |") == 1 and "LIVE" in text  # live version kept


def test_free_text_without_sidecar_flagged_manual_not_committed(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    proj = _make_project(tmp_path)
    staged = proj / "staging" / "truth" / "current_state.md"
    staged.write_text("# 状态\n自由文本快照", encoding="utf-8")
    # no sidecar entry

    rc = main([str(proj), "--apply"])
    assert rc == 0
    assert staged.exists()  # kept for manual diff
    assert "MANUAL" in capsys.readouterr().out
    assert not (proj / "truth" / "current_state.md").exists()  # never committed


def test_dry_run_touches_nothing(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    proj = _make_project(tmp_path)
    (proj / "staging" / "plans" / "chapter-1-plan.md").write_text("x", encoding="utf-8")
    (proj / "plans").mkdir()
    (proj / "plans" / "chapter-1-plan.md").write_text("committed", encoding="utf-8")
    staged_hook = proj / "staging" / "truth" / "hooks.md"
    staged_hook.write_text("| a | b |", encoding="utf-8")

    rc = main([str(proj)])  # no --apply
    assert rc == 0
    assert "dry-run" in capsys.readouterr().out
    assert (proj / "staging" / "plans" / "chapter-1-plan.md").exists()
    assert staged_hook.exists()
