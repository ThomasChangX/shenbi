"""#51 (probe21 adjudication #009): the ghost chain ran un-intercepted —
(a) the settle re-dispatch path NEVER re-ran G4 (the in-loop settle runs it;
the queue executor did not), and (b) nothing checked that
``chapters/chapter-N.md`` EXISTS before dispatching the draft-consuming
writers, so a settle for an un-drafted chapter fabricated truth that poisoned
every later file. Both guards live at the two dispatch sites: the re-dispatch
executor and the in-loop chapter step.
"""

from __future__ import annotations

from pathlib import Path

from shenbi.pipeline import cli as cli_mod
from shenbi.pipeline.state import CheckpointType, PipelinePhase, PipelineState, ReviewDecision


class _OK:
    success = True
    returncode = 0
    stdout = ""
    stderr = ""


def _queued_state(skill: str, chapter: int, checkpoint_type: str = "per-chapter") -> PipelineState:
    state = PipelineState.default("/tmp/probe21-ghost")
    state.phase = PipelinePhase.CHAPTER_LOOP
    state.chapter_loop.current_chapter = 2
    state.pending_re_dispatches = [
        {
            "skill": skill,
            "checkpoint_type": checkpoint_type,
            "chapter": chapter,
            "feedback": None,
        }
    ]
    return state


def _make_draft(project: Path, chapter: int) -> None:
    """#51 precondition: draft-consuming re-dispatches legitimately require
    chapters/chapter-N.md — fixtures that model a real (drafted) chapter.
    """
    d = project / "chapters"
    d.mkdir(exist_ok=True)
    (d / f"chapter-{chapter}.md").write_text(
        f"# Chapter {chapter}\n正文第{chapter}章\n", encoding="utf-8"
    )


def _make_staged_truth(project: Path) -> None:
    """Give the settle re-dispatch a non-empty G4 file list (staging truth)."""
    t = project / "staging" / "truth"
    t.mkdir(parents=True, exist_ok=True)
    (t / "current_state.md").write_text(
        "| 章节 | 位置 | 时间锚 | 主角处境 | 势力态势 | 待处理压力 |\n"
        "| ---- | ---- | ------ | -------- | -------- | ---------- |\n"
        "| 第 2 章 | 南仓 | 第2日 | 入仓 | 平稳 | 工钱未结 |\n",
        encoding="utf-8",
    )


def test_redispatch_g4_failure_is_budgeted_retry_not_checkpoint(tmp_path, monkeypatch):
    """A re-dispatch whose output FAILS the structural gate must consume an
    attempt with the must-fix wired into the next prompt — never re-raise the
    review checkpoint over unvalidated staging (the interception layer that
    was missing when the ghost chain fabricated ch2 truth un-gated).
    """
    state = _queued_state("shenbi-state-settling", 2)
    _make_draft(tmp_path, 2)
    _make_staged_truth(tmp_path)
    monkeypatch.setattr(
        "shenbi.pipeline.dispatch_helper.dispatch_skill",
        lambda *a, **kw: _OK(),
    )
    gate_results = [
        {"status": "FAIL", "must_fix": ["G4.ss.missing_evidence: staging/truth/current_state.md"]},
        {"status": "PASS", "must_fix": []},
    ]
    monkeypatch.setattr(
        cli_mod,
        "run_gate_g4",
        lambda *a, **kw: gate_results.pop(0),
    )

    assert cli_mod._execute_pending_re_dispatches(state, tmp_path) is True
    # attempt 1: G4 fail -> stays queued with attempts=1, no STATE_SETTLE raise
    assert len(state.pending_re_dispatches) == 1
    entry = state.pending_re_dispatches[0]
    assert entry["attempts"] == 1
    assert "G4.ss.missing_evidence" in (entry.get("feedback") or "")
    assert state.pending_checkpoint is not None
    assert state.pending_checkpoint.type == CheckpointType.ESCALATION  # blocks advancement

    from shenbi.pipeline.machine import clear_checkpoint

    clear_checkpoint(state, ReviewDecision.APPROVE)
    # attempt 2: dispatch ok + G4 pass -> consumed + checkpoint re-raised for review
    assert cli_mod._execute_pending_re_dispatches(state, tmp_path) is True
    assert state.pending_re_dispatches == []
    cp = state.pending_checkpoint
    assert cp is not None and cp.type == CheckpointType.STATE_SETTLE
    assert cp.chapter == 2


def test_redispatch_draft_missing_blocks_without_dispatch(tmp_path, monkeypatch):
    """A settle re-dispatch whose chapter draft does not exist must NEVER
    dispatch (no fabrication attempt, no cost) — the entry is dropped and the
    escalation names the missing file.
    """
    state = _queued_state("shenbi-state-settling", 2)

    def _must_not_dispatch(*a, **kw):
        raise AssertionError("dispatched settle for a chapter with no draft")

    monkeypatch.setattr("shenbi.pipeline.dispatch_helper.dispatch_skill", _must_not_dispatch)

    assert cli_mod._execute_pending_re_dispatches(state, tmp_path) is True
    assert state.pending_re_dispatches == []
    cp = state.pending_checkpoint
    assert cp is not None and cp.type == CheckpointType.ESCALATION
    assert "chapter-2.md" in (cp.context or "")


def test_inloop_settle_and_lifecycle_draft_precheck(tmp_path, monkeypatch):
    """The in-loop draft-consuming steps (foreshadowing-lifecycle step 7,
    state-settling step 8) raise an escalation BEFORE dispatch when the
    chapter draft is absent — probe21's ghost chain entered exactly here.
    """
    from shenbi.pipeline import chapter_loop as cl

    def _must_not_dispatch(*a, **kw):
        raise AssertionError("dispatched a draft-consuming step with no draft")

    monkeypatch.setattr("shenbi.pipeline.chapter_loop.dispatch_skill", _must_not_dispatch)

    for step_index in (7, 8):  # spec #72: [7]=foreshadowing, [8]=state-settling
        state = PipelineState.default(str(tmp_path))
        state.phase = PipelinePhase.CHAPTER_LOOP
        state.chapter_loop.current_chapter = 2
        state.chapter_loop.step_index = step_index
        assert cl.run_chapter_step(state, tmp_path) is True
        cp = state.pending_checkpoint
        assert cp is not None and cp.type == CheckpointType.ESCALATION, step_index
        assert "chapter-2.md" in (cp.context or ""), step_index


def test_inloop_settle_proceeds_when_draft_exists(tmp_path, monkeypatch):
    """Guard is a precheck, not a block: with the draft present the settle
    step dispatches normally (dispatch faked; the checkpoint flow after it is
    owned by the existing tests).
    """
    from shenbi.pipeline import chapter_loop as cl

    (tmp_path / "chapters").mkdir(exist_ok=True)
    (tmp_path / "chapters" / "chapter-2.md").write_text("# Chapter 2\n正文\n", encoding="utf-8")
    dispatched: list[str] = []
    monkeypatch.setattr(
        "shenbi.pipeline.chapter_loop.dispatch_skill",
        lambda skill, *a, **kw: dispatched.append(skill) or _OK(),
    )
    # silence the post-dispatch machinery (G4 etc.) — the precheck is the SUT
    monkeypatch.setattr(
        "shenbi.pipeline.chapter_loop.run_gate_g4",
        lambda *a, **kw: {"status": "PASS", "must_fix": []},
    )

    state = PipelineState.default(str(tmp_path))
    state.phase = PipelinePhase.CHAPTER_LOOP
    state.chapter_loop.current_chapter = 2
    state.chapter_loop.step_index = 8  # spec #72: settling idx after scene-split insert
    cl.run_chapter_step(state, tmp_path)
    assert dispatched == ["shenbi-state-settling"]
