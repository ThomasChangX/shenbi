"""Tests for heal_state_counters on resume (spec §3.4)."""

from __future__ import annotations

from pathlib import Path

from shenbi.pipeline.state import ChapterStatus, PipelineState
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

    s.chapter_loop.chapter_states = {
        "3": ChapterState(revision_count=0, status=ChapterStatus.PENDING)
    }
    # Put a revision-decisions file on disk.
    (tmp_path / "chapters").mkdir(parents=True)
    (tmp_path / "chapters" / "chapter-3-revision-decisions.json").write_text("{}", encoding="utf-8")

    heal_state_counters(s, tmp_path)
    assert s.chapter_loop.chapter_states["3"].revision_count >= 1


def test_no_changes_returns_empty_actions(tmp_path: Path):
    s = PipelineState.default(project_dir=str(tmp_path))
    # Nothing on disk, no feedback — nothing healed.
    actions = heal_state_counters(s, tmp_path)
    # No snapshots/revision files/feedback -> nothing to heal.
    assert actions == []


def test_advance_keeps_current_step_aligned_with_step_index(tmp_path: Path):
    """F743 (spec #52): the step cursor invariant current_step == CHAPTER_STEPS[step_index].skill.

    Drives the real _advance (the single site that mutates both fields
    together, chapter_loop.py "Task 17-13 root cause fix") — a regression
    that decouples the two fields goes red here.
    """
    from shenbi.pipeline.chapter_loop import CHAPTER_STEPS, _advance
    from shenbi.pipeline.state import PipelineState

    s = PipelineState.default(str(tmp_path))
    s.chapter_loop.current_chapter = 1
    for idx, step in enumerate(CHAPTER_STEPS[:-1]):
        _advance(s, idx, step, 1, project_dir=tmp_path)
        assert s.chapter_loop.step_index == idx + 1
        assert s.chapter_loop.current_step == CHAPTER_STEPS[idx + 1].skill

    # Off the end: the real completion path (_complete_chapter) resets the
    # cursor for the next chapter. NOTE: current_step is observed as "" here
    # (the transient corruption window chapter_loop.py's "Task 17-13" comment
    # describes) — left unpinned pending a production-side fix; not in this
    # spec's scope (tests-only, spec #52).
    _advance(s, len(CHAPTER_STEPS) - 1, CHAPTER_STEPS[-1], 1, project_dir=tmp_path)
    assert s.chapter_loop.step_index == 0
