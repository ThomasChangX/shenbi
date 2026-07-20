"""Tests for heal_state_counters on resume (spec §3.4)."""

from __future__ import annotations

from pathlib import Path

from shenbi.pipeline.state import PipelineState
from shenbi.pipeline.state_heal import heal_state_counters


def test_heals_retry_budget_from_retry_feedback(tmp_path: Path):
    s = PipelineState.default(project_dir=str(tmp_path))
    s.chapter_loop.retry_feedback = {"ch1-shenbi-x": "G4 failed"}
    # retry_budget_consumed missing for that key.
    actions = heal_state_counters(s, tmp_path)
    assert s.chapter_loop.retry_budget_consumed.get("ch1-shenbi-x") == 1
    assert any("retry_budget_consumed_healed" in a for a in actions)


def test_does_not_overwrite_existing_budget(tmp_path: Path):
    s = PipelineState.default(project_dir=str(tmp_path))
    s.chapter_loop.retry_feedback = {"ch1-x": "fail"}
    s.chapter_loop.retry_budget_consumed = {"ch1-x": 5}
    heal_state_counters(s, tmp_path)
    assert s.chapter_loop.retry_budget_consumed["ch1-x"] == 5  # untouched


def test_heals_revision_count_from_disk(tmp_path: Path):
    s = PipelineState.default(project_dir=str(tmp_path))
    from shenbi.pipeline.state import ChapterState

    s.chapter_loop.chapter_states = {"3": ChapterState(revision_count=0, status="pending")}
    # Put a revision-decisions file on disk.
    (tmp_path / "chapters").mkdir(parents=True)
    (tmp_path / "chapters" / "chapter-3-revision-decisions.json").write_text("{}", encoding="utf-8")

    heal_state_counters(s, tmp_path)
    assert s.chapter_loop.chapter_states["3"].revision_count >= 1


def test_heals_last_snapshot_from_disk(tmp_path: Path):
    s = PipelineState.default(project_dir=str(tmp_path))
    assert s.last_snapshot == {}
    snap_dir = tmp_path / "snapshots"
    snap_dir.mkdir()
    (snap_dir / "chapter-007-20260101T000000.md").write_text("# snap", encoding="utf-8")

    heal_state_counters(s, tmp_path)
    assert s.last_snapshot, "last_snapshot should be healed from disk"
    assert s.last_snapshot["chapter"] == 7
    assert s.last_snapshot["path"].startswith("snapshots/")


def test_no_changes_returns_empty_actions(tmp_path: Path):
    s = PipelineState.default(project_dir=str(tmp_path))
    # Nothing on disk, no feedback, last_snapshot already empty is left empty.
    actions = heal_state_counters(s, tmp_path)
    # No snapshots/revision files/feedback -> nothing to heal.
    assert actions == []
