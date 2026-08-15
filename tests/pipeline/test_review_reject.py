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
