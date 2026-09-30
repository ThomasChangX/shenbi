"""F340/F341/F304: REJECT redo semantics + parallel staging commit + budget-capture checkpoint."""

from shenbi.exceptions import RetryExhaustedError
from shenbi.pipeline.machine import set_checkpoint
from shenbi.pipeline.state import CheckpointType, PipelineState


def _state() -> PipelineState:
    return PipelineState.default("/tmp/proj")


def test_reject_genesis_complete_rolls_back_cursor():
    """Acceptance: genesis-complete reject -> current_step rolls back (step 17 redo)."""
    from shenbi.pipeline.cli import _apply_reject_redo

    state = _state()
    state.genesis.current_step = 17
    set_checkpoint(state, CheckpointType.GENESIS_COMPLETE)
    _apply_reject_redo(state, state.pending_checkpoint)
    assert state.genesis.current_step == 16


def test_genesis_complete_rollback_unmarks_redo_skill():
    """Fixcheck escalation (2026-09-29): rolling the cursor back without
    un-marking the step's skill left it in genesis.skills_done, so the step-17
    re-dispatch recorded the scorer route as also a generator route and G3.4
    (scorer == generator) failed deterministically 3/3.
    """
    from shenbi.pipeline.cli import _apply_reject_redo

    state = _state()
    state.genesis.current_step = 17
    state.genesis.skills_done = [
        "shenbi-worldbuilding",
        "shenbi-foundation-review",
    ]
    set_checkpoint(state, CheckpointType.GENESIS_COMPLETE)
    _apply_reject_redo(state, state.pending_checkpoint)
    assert state.genesis.current_step == 16
    assert "shenbi-foundation-review" not in state.genesis.skills_done
    assert "shenbi-worldbuilding" in state.genesis.skills_done  # others intact


def test_modify_per_chapter_also_queues_revision():
    """PER_CHAPTER MODIFY also queues chapter-revision (desirable semantics)."""
    from shenbi.pipeline.cli import _queue_re_dispatches

    state = _state()
    set_checkpoint(state, CheckpointType.PER_CHAPTER, chapter=5)
    _queue_re_dispatches(state, state.pending_checkpoint, feedback="改紧节奏")
    assert any(
        d["skill"] == "shenbi-chapter-revision" and d.get("feedback") == "改紧节奏"
        for d in state.pending_re_dispatches
    )


def test_reject_escalation_resets_retry_budget():
    """Acceptance: escalation reject-redo gets a full retry budget."""
    from shenbi.pipeline.cli import _apply_reject_redo

    state = _state()
    state.chapter_loop.retry_counts["ch55-shenbi-chapter-drafting"] = 4
    state.chapter_loop.retry_budget_consumed["ch55-shenbi-chapter-drafting"] = 9
    state.chapter_loop.retry_budget_consumed["ch12-shenbi-other"] = 1
    set_checkpoint(state, CheckpointType.ESCALATION, chapter=55)
    _apply_reject_redo(state, state.pending_checkpoint)
    assert "ch55-shenbi-chapter-drafting" not in state.chapter_loop.retry_counts
    assert "ch55-shenbi-chapter-drafting" not in state.chapter_loop.retry_budget_consumed
    assert (
        state.chapter_loop.retry_budget_consumed["ch12-shenbi-other"] == 1
    )  # other chapter untouched


def test_parallel_auto_mode_commits_staging_no_checkpoint(tmp_path, monkeypatch):
    """Acceptance: --auto parallel post-draft sets no checkpoint, truth lands,
    staging cleared.
    """
    from shenbi.pipeline import chapter_loop as cl

    proj = tmp_path / "proj"
    staging_truth = proj / "staging" / "truth"
    staging_truth.mkdir(parents=True)
    (staging_truth / "world_state.md").write_text("# 世界状态\n", encoding="utf-8")

    state = _state()
    state.project_dir = str(proj)
    state.config.state_settle_review_required = False

    raised = []
    monkeypatch.setattr(cl, "set_checkpoint", lambda *a, **k: raised.append(a))

    # True = auto-commit ran (caller skips the checkpoint and falls through)
    assert cl._auto_settle_parallel(state, proj, chapter=55) is True
    assert not raised, "--auto must not raise a STATE_SETTLE checkpoint"
    assert (proj / "truth" / "world_state.md").exists()
    assert not (proj / "staging" / "truth" / "world_state.md").exists()


def test_parallel_review_required_defers_to_checkpoint(tmp_path):
    """review_required=True -> _auto_settle_parallel returns False without
    committing (the caller raises the STATE_SETTLE checkpoint).
    """
    from shenbi.pipeline import chapter_loop as cl

    proj = tmp_path / "proj"
    staging_truth = proj / "staging" / "truth"
    staging_truth.mkdir(parents=True)
    (staging_truth / "world_state.md").write_text("# 世界状态\n", encoding="utf-8")

    state = _state()
    state.project_dir = str(proj)
    state.config.state_settle_review_required = True

    assert cl._auto_settle_parallel(state, proj, chapter=55) is False
    # staging untouched — the human review flow owns it now
    assert (proj / "staging" / "truth" / "world_state.md").exists()
    assert not (proj / "truth" / "world_state.md").exists()


def test_orchestrate_captures_retry_exhausted(tmp_path, monkeypatch):
    """Acceptance: budget exhaustion produces an ESCALATION checkpoint (no
    traceback) and the budget trail survives on state for save_state.
    """
    from shenbi.pipeline import cli as cli_mod
    from shenbi.pipeline.state import PipelinePhase

    state = _state()
    state.project_dir = str(tmp_path)
    state.chapter_loop.retry_budget_consumed["ch55-x"] = 99

    def boom(*a, **k):
        raise RetryExhaustedError("budget gone")

    monkeypatch.setattr("shenbi.pipeline.chapter_loop.run_chapter_step", boom)
    monkeypatch.setattr("shenbi.pipeline.genesis.run_genesis_step", boom)
    monkeypatch.setattr("shenbi.pipeline.closure.run_closure_step", boom)
    state.phase = PipelinePhase.CHAPTER_LOOP

    cli_mod._orchestrate_to_checkpoint(state, tmp_path)  # must NOT raise

    assert state.pending_checkpoint is not None
    assert state.pending_checkpoint.type == CheckpointType.ESCALATION
    assert state.chapter_loop.retry_budget_consumed["ch55-x"] == 99


def test_cmd_review_reject_wired(tmp_path, monkeypatch):
    """F340 wiring: cmd_review's REJECT path actually calls _apply_reject_redo."""
    import argparse

    from shenbi.pipeline import cli as cli_mod

    proj = tmp_path / "proj"
    proj.mkdir()
    state = PipelineState.default(str(proj))
    state.genesis.current_step = 17
    set_checkpoint(state, CheckpointType.GENESIS_COMPLETE)

    monkeypatch.setattr(cli_mod, "load_state", lambda pd: state)
    monkeypatch.setattr(cli_mod, "save_state", lambda pd, st: None)
    monkeypatch.setattr(cli_mod, "emit_json", lambda payload: None)
    args = argparse.Namespace(decision="reject", feedback=None, project_dir=str(proj))

    rc = cli_mod.cmd_review(args)
    assert rc in (0, None)
    assert state.genesis.current_step == 16  # redo cursor via the real path


def test_f304_checkpoint_carries_chapter_and_reject_resets(tmp_path, monkeypatch):
    """I1 interplay: F304's ESCALATION carries the chapter (chapter-loop phase)
    so a REJECT resets that step's durable budget; a chapter-less fallback
    clears all chapter-scoped budgets.
    """
    from shenbi.pipeline import cli as cli_mod
    from shenbi.pipeline.state import PipelinePhase

    state = _state()
    state.project_dir = str(tmp_path)
    state.phase = PipelinePhase.CHAPTER_LOOP
    state.chapter_loop.current_chapter = 57
    state.chapter_loop.retry_budget_consumed["ch57-x"] = 99

    def boom(*a, **k):
        raise RetryExhaustedError("budget gone")

    monkeypatch.setattr("shenbi.pipeline.chapter_loop.run_chapter_step", boom)
    monkeypatch.setattr("shenbi.pipeline.genesis.run_genesis_step", boom)
    monkeypatch.setattr("shenbi.pipeline.closure.run_closure_step", boom)
    cli_mod._orchestrate_to_checkpoint(state, tmp_path)
    assert state.pending_checkpoint.chapter == 57

    from shenbi.pipeline.cli import _apply_reject_redo

    _apply_reject_redo(state, state.pending_checkpoint)
    assert "ch57-x" not in state.chapter_loop.retry_budget_consumed

    # chapter-less fallback clears everything chapter-scoped
    state2 = _state()
    state2.chapter_loop.retry_budget_consumed["ch3-a"] = 5
    state2.chapter_loop.retry_budget_consumed["ch9-b"] = 6
    set_checkpoint(state2, CheckpointType.ESCALATION)  # no chapter
    _apply_reject_redo(state2, state2.pending_checkpoint)
    assert state2.chapter_loop.retry_budget_consumed == {}


def test_reject_cursor_rollback_chapter_memo_and_state_settle():
    from shenbi.pipeline.cli import _apply_reject_redo

    state = _state()
    state.chapter_loop.step_index = 4
    set_checkpoint(state, CheckpointType.CHAPTER_MEMO, chapter=3)
    _apply_reject_redo(state, state.pending_checkpoint)
    assert state.chapter_loop.step_index == 1

    set_checkpoint(state, CheckpointType.STATE_SETTLE, chapter=3)
    state.chapter_loop.step_index = 9
    _apply_reject_redo(state, state.pending_checkpoint)
    assert state.chapter_loop.step_index == 7


def test_reject_volume_boundary_rearms_trigger_fanout():
    from shenbi.pipeline.cli import _apply_reject_redo

    state = _state()
    state.chapter_loop.step_index = 5
    set_checkpoint(state, CheckpointType.VOLUME_BOUNDARY, chapter=55)
    _apply_reject_redo(state, state.pending_checkpoint)
    assert state.chapter_loop.step_index == 0


def test_cmd_review_chapter_escalation_reject_feedback_is_wired(tmp_path, monkeypatch):
    """GAP-a (fixcheck ch1, 17:17 evidence): a chapter-phase ESCALATION
    reject's 1385-char repair feedback never entered any 17:22-17:33
    re-dispatch prompt — the routing block was gated on phase == GENESIS
    and _apply_reject_redo only resets budgets. The feedback must land in
    chapter_loop.retry_feedback[chN-skill] for the failing step
    (step_index points at the un-completed step); the redo dispatch
    injects it via _append_feedback_injections.
    """
    import argparse

    from shenbi.pipeline import cli as cli_mod
    from shenbi.pipeline.state import PipelinePhase

    proj = tmp_path / "proj"
    proj.mkdir()
    state = PipelineState.default(str(proj))
    state.phase = PipelinePhase.CHAPTER_LOOP
    state.chapter_loop.current_chapter = 3
    state.chapter_loop.step_index = 7  # CHAPTER_STEPS[7] = state-settling
    set_checkpoint(state, CheckpointType.ESCALATION, chapter=3)

    monkeypatch.setattr(cli_mod, "load_state", lambda pd: state)
    monkeypatch.setattr(cli_mod, "save_state", lambda pd, st: None)
    monkeypatch.setattr(cli_mod, "emit_json", lambda payload: None)

    fb = tmp_path / "fb.md"
    fb.write_text("重做指令：逐字保留 live 基底", encoding="utf-8")
    args = argparse.Namespace(decision="reject", feedback=str(fb), project_dir=str(proj))

    rc = cli_mod.cmd_review(args)
    assert rc in (0, None)
    assert (
        state.chapter_loop.retry_feedback.get("ch3-shenbi-state-settling")
        == "重做指令：逐字保留 live 基底"
    ), state.chapter_loop.retry_feedback
