"""#53 (probe21 adjudication #009): a chapter-scoped checkpoint reviewed while
the chapter-loop cursor sits on a LATER chapter must never rewind the step
cursor — the reject of probe21's stale ch1 STATE_SETTLE set ``step_index=7``
with ``current_chapter=2``, sending the un-drafted ch2 straight into
settle→audit→revision (ghost chain, fabricated truth). The redo belongs to
the checkpoint's OWN chapter and travels through the re-dispatch queue.
"""

from __future__ import annotations

import argparse

import pytest

from shenbi.pipeline import cli as cli_mod
from shenbi.pipeline.machine import set_checkpoint
from shenbi.pipeline.state import CheckpointType, PipelinePhase, PipelineState


def _chapter_state(current: int, step: int) -> PipelineState:
    state = PipelineState.default("/tmp/probe21-ghost")
    state.phase = PipelinePhase.CHAPTER_LOOP
    state.chapter_loop.current_chapter = current
    state.chapter_loop.step_index = step
    return state


class _OK:
    success = True
    returncode = 0
    stdout = ""
    stderr = ""


@pytest.mark.parametrize(
    ("cp_type", "queued_skill"),
    [
        (CheckpointType.STATE_SETTLE, "shenbi-state-settling"),
        (CheckpointType.CHAPTER_MEMO, "shenbi-chapter-planning"),
    ],
)
def test_mismatch_reject_defers_redo_to_re_dispatch_queue(cp_type, queued_skill):
    """REJECT of an older chapter's checkpoint: cursor frozen, redo queued
    under the checkpoint's chapter with the feedback wired.
    """
    state = _chapter_state(current=2, step=0)
    set_checkpoint(state, cp_type, chapter=1)
    cli_mod._apply_reject_redo(state, state.pending_checkpoint, feedback="塌缩须修复")
    assert state.chapter_loop.current_chapter == 2
    assert state.chapter_loop.step_index == 0
    entries = [e for e in state.pending_re_dispatches if e["skill"] == queued_skill]
    assert len(entries) == 1, state.pending_re_dispatches
    entry = entries[0]
    assert entry["chapter"] == 1
    assert entry["checkpoint_type"] == cp_type.value
    assert entry.get("feedback") == "塌缩须修复"


def test_mismatch_reject_volume_boundary_freezes_cursor():
    """VOLUME_BOUNDARY's step-0 rewind is positional (re-runs the trigger
    fan-out at the CURRENT chapter top) — at a chapter mismatch it would
    fan out the wrong chapter. Freeze with no queue entry.
    """
    state = _chapter_state(current=2, step=5)
    set_checkpoint(state, CheckpointType.VOLUME_BOUNDARY, chapter=1)
    cli_mod._apply_reject_redo(state, state.pending_checkpoint)
    assert state.chapter_loop.step_index == 5
    assert state.chapter_loop.current_chapter == 2
    assert state.pending_re_dispatches == []


def test_match_reject_still_rewinds_in_place():
    """Regression: same-chapter rejects keep the in-loop redo semantics."""
    state = _chapter_state(current=3, step=9)
    set_checkpoint(state, CheckpointType.STATE_SETTLE, chapter=3)
    cli_mod._apply_reject_redo(state, state.pending_checkpoint)
    assert state.chapter_loop.step_index == 7
    assert state.pending_re_dispatches == []

    state = _chapter_state(current=3, step=4)
    set_checkpoint(state, CheckpointType.CHAPTER_MEMO, chapter=3)
    cli_mod._apply_reject_redo(state, state.pending_checkpoint)
    assert state.chapter_loop.step_index == 1
    assert state.pending_re_dispatches == []


def test_mismatch_modify_freezes_cursor_and_queues_redo(tmp_path, monkeypatch):
    """The MODIFY branch of cmd_review rewinds the same two step cursors —
    it needs the identical mismatch guard (probe21 adjudication #009 named
    both sites).
    """
    proj = tmp_path / "proj"
    proj.mkdir()
    state = PipelineState.default(str(proj))
    state.phase = PipelinePhase.CHAPTER_LOOP
    state.chapter_loop.current_chapter = 2
    state.chapter_loop.step_index = 9
    set_checkpoint(state, CheckpointType.STATE_SETTLE, chapter=1)

    monkeypatch.setattr(cli_mod, "load_state", lambda pd: state)
    monkeypatch.setattr(cli_mod, "save_state", lambda pd, st: None)
    monkeypatch.setattr(cli_mod, "emit_json", lambda payload: None)
    fb = tmp_path / "fb.md"
    fb.write_text("塌缩须修复", encoding="utf-8")
    args = argparse.Namespace(decision="modify", feedback=str(fb), project_dir=str(proj))

    rc = cli_mod.cmd_review(args)
    assert rc in (0, None)
    assert state.chapter_loop.current_chapter == 2
    assert state.chapter_loop.step_index == 9
    entries = [e for e in state.pending_re_dispatches if e["skill"] == "shenbi-state-settling"]
    assert len(entries) == 1, state.pending_re_dispatches
    assert entries[0]["chapter"] == 1
    assert entries[0].get("feedback") == "塌缩须修复"


def test_mismatch_settle_redo_entry_carries_prompt_and_re_raises(tmp_path, monkeypatch):
    """End-to-end through the queue executor: the mismatch-queued settle redo
    dispatches with a real corrective prompt ([Chapter N] + redo instruction
    + feedback, staging-gated) and its success re-raises STATE_SETTLE for the
    CHECKPOINT's chapter — the human reviews the redo, exactly like the
    audit-routed re-settlement it descends from.
    """
    state = _chapter_state(current=2, step=0)
    set_checkpoint(state, CheckpointType.STATE_SETTLE, chapter=1)
    cli_mod._apply_reject_redo(state, state.pending_checkpoint, feedback="塌缩须修复")

    # #51 preconditions: the redo targets a DRAFTED chapter and stages truth
    (tmp_path / "chapters").mkdir(exist_ok=True)
    (tmp_path / "chapters" / "chapter-1.md").write_text("# Chapter 1\n正文\n", encoding="utf-8")
    staged = tmp_path / "staging" / "truth"
    staged.mkdir(parents=True, exist_ok=True)
    (staged / "current_state.md").write_text(
        "| 章节 | 位置 | 时间锚 | 主角处境 | 势力态势 | 待处理压力 |\n"
        "| ---- | ---- | ------ | -------- | -------- | ---------- |\n"
        "| 第 1 章 | 南仓 | 第1日 | 入仓 | 平稳 | 工钱未结 |\n",
        encoding="utf-8",
    )

    calls: list[tuple[str, bool, str]] = []

    def _fake_dispatch(skill, project_dir, prompt, **kwargs):
        calls.append((skill, bool(kwargs.get("uses_staging")), prompt))
        return _OK()

    monkeypatch.setattr("shenbi.pipeline.dispatch_helper.dispatch_skill", _fake_dispatch)
    assert cli_mod._execute_pending_re_dispatches(state, tmp_path) is True

    skill, staging, prompt = calls[0]
    assert skill == "shenbi-state-settling"
    assert staging is True
    assert "[Chapter 1]" in prompt
    assert "Re-settle" in prompt  # non-empty redo instruction, not a bare chapter tag
    assert "塌缩须修复" in prompt
    cp = state.pending_checkpoint
    assert cp is not None and cp.type == CheckpointType.STATE_SETTLE
    assert cp.chapter == 1
    assert state.pending_re_dispatches == []


def test_mismatch_memo_redo_re_raises_chapter_memo(tmp_path, monkeypatch):
    """The memo redo re-dispatch lands on staging (chapter-planning is a
    gated writer) — without re-raising CHAPTER_MEMO the staged plan would be
    orphaned with no commit gate.
    """
    state = _chapter_state(current=2, step=4)
    set_checkpoint(state, CheckpointType.CHAPTER_MEMO, chapter=1)
    cli_mod._apply_reject_redo(state, state.pending_checkpoint, feedback="重排第1章")

    # the SUT is the mismatch-queue mechanics — the staged plan's structural
    # gate is faked green (its real behavior is owned by the G4 suites)
    monkeypatch.setattr(cli_mod, "run_gate_g4", lambda *a, **kw: {"status": "PASS", "must_fix": []})
    calls: list[tuple[str, bool]] = []

    def _fake_dispatch(skill, project_dir, prompt, **kwargs):
        calls.append((skill, bool(kwargs.get("uses_staging"))))
        return _OK()

    monkeypatch.setattr("shenbi.pipeline.dispatch_helper.dispatch_skill", _fake_dispatch)
    assert cli_mod._execute_pending_re_dispatches(state, tmp_path) is True

    assert calls == [("shenbi-chapter-planning", True)], calls
    cp = state.pending_checkpoint
    assert cp is not None and cp.type == CheckpointType.CHAPTER_MEMO
    assert cp.chapter == 1
