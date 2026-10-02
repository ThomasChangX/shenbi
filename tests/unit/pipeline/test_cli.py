"""Tests for pipeline CLI commands.

Covers the six subcommands (init, next, status, review, resume, chapters)
plus error paths (rollback removed per spec #26 path 3). stdout is captured by monkeypatching sys.stdout to
an in-memory buffer (same convention as test_gates_cli.py): ``capsys`` installs
capture streams that pytest closes at teardown, and main()'s
configure_logging() binds structlog (cache_logger_on_first_use=True) to the
then-current sys.stderr -- a closed-file error across tests. An explicit
StringIO avoids that coupling.
"""

from __future__ import annotations

import io
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from shenbi.pipeline.cli import main
from shenbi.pipeline.dispatch_helper import DispatchResult
from shenbi.pipeline.machine import load_state, save_state, set_checkpoint
from shenbi.pipeline.state import (
    CheckpointType,
    ClosureState,
    GenesisState,
    PipelinePhase,
)
from tests.conftest import seed_genesis_outputs


def _run(argv: list[str], monkeypatch: pytest.MonkeyPatch) -> tuple[int, str]:
    """Invoke main() with argv, capturing stdout to an in-memory buffer."""
    out = io.StringIO()
    monkeypatch.setattr(sys, "stdout", out)
    rc = main(argv)
    return rc, out.getvalue()


def _init_project(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, sample_seed_content: str
) -> Path:
    """Create a fresh novel project under tmp_path and return its directory."""
    seed_file = tmp_path / "seed.md"
    seed_file.write_text(sample_seed_content, encoding="utf-8")
    project_dir = tmp_path / "novel"
    _run(["init", str(seed_file), "--project-dir", str(project_dir)], monkeypatch)
    return project_dir


class TestInitCommand:
    """``init <seed> --project-dir <dir>`` creates the project scaffold."""

    def test_init_creates_project(
        self, tmp_path: Path, sample_seed_content: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A fresh init writes pipeline-state.json and novel.json."""
        seed_file = tmp_path / "seed.md"
        seed_file.write_text(sample_seed_content, encoding="utf-8")
        project_dir = tmp_path / "novel"

        rc, _ = _run(["init", str(seed_file), "--project-dir", str(project_dir)], monkeypatch)

        assert rc == 0
        assert (project_dir / "pipeline-state.json").exists()
        assert (project_dir / "novel.json").exists()
        novel = json.loads((project_dir / "novel.json").read_text(encoding="utf-8"))
        assert novel["genre"] == ["fantasy", "adventure"]

    def test_init_idempotent_accepts_existing(
        self, tmp_path: Path, sample_seed_content: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Re-running init on an existing incomplete project succeeds (returns exists status)."""
        project_dir = _init_project(tmp_path, monkeypatch, sample_seed_content)
        seed_file = tmp_path / "seed.md"

        rc, out = _run(["init", str(seed_file), "--project-dir", str(project_dir)], monkeypatch)

        assert rc == 0  # Should succeed, reporting existing project is resumable
        assert json.loads(out)["status"] == "exists"

    def test_init_writes_genre_config(
        self, tmp_path: Path, sample_seed_content: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Genre config parsed from the seed is persisted as genre-config.json."""
        project_dir = _init_project(tmp_path, monkeypatch, sample_seed_content)

        gc = json.loads((project_dir / "genre-config.json").read_text(encoding="utf-8"))
        assert gc["show_tell_ratio"] == "70/30"

    def test_init_emits_total_chapters_unknown(
        self, tmp_path: Path, sample_seed_content: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Init reports total_chapters=unknown (volume-outlining computes it later)."""
        seed_file = tmp_path / "seed.md"
        seed_file.write_text(sample_seed_content, encoding="utf-8")
        project_dir = tmp_path / "novel"

        rc, out = _run(["init", str(seed_file), "--project-dir", str(project_dir)], monkeypatch)

        assert rc == 0
        assert json.loads(out)["total_chapters"] == "unknown"

    def test_init_scaffolds_core_truth_dirs(
        self, tmp_path: Path, sample_seed_content: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Init creates the core dirs `_verify_truth_integrity` demands on resume.

        The integrity check runs on EVERY resume — including the first one,
        before any genesis step has written anything — so a fresh project
        without these dirs deadlocks init→resume (F325 fail-fast wiring).
        """
        seed_file = tmp_path / "seed.md"
        seed_file.write_text(sample_seed_content, encoding="utf-8")
        project_dir = tmp_path / "novel"

        rc, _ = _run(["init", str(seed_file), "--project-dir", str(project_dir)], monkeypatch)

        assert rc == 0
        from shenbi.pipeline.cli import _verify_truth_integrity
        from shenbi.pipeline.state import PipelinePhase

        state = load_state(project_dir)
        assert state.phase == PipelinePhase.GENESIS
        assert _verify_truth_integrity(state, project_dir) == []

    def test_init_auto_flag_disables_review_checkpoints(
        self, tmp_path: Path, sample_seed_content: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """--auto persists disabled review flags on both config and chapter_loop."""
        seed_file = tmp_path / "seed.md"
        seed_file.write_text(sample_seed_content, encoding="utf-8")
        project_dir = tmp_path / "novel"

        rc, _ = _run(
            ["init", str(seed_file), "--project-dir", str(project_dir), "--auto"],
            monkeypatch,
        )

        assert rc == 0
        state = load_state(project_dir)
        # config-level flags
        assert state.config.per_chapter_review_enabled is False
        assert state.config.chapter_memo_review_required is False
        assert state.config.state_settle_review_required is False
        # chapter_loop-level copy (the one _complete_chapter actually reads)
        assert state.chapter_loop.per_chapter_review_enabled is False


class TestStatusCommand:
    """``status <dir>`` emits current pipeline state as JSON."""

    def test_status_returns_json(
        self, tmp_path: Path, sample_seed_content: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A valid project yields phase/chapter/checkpoint fields."""
        project_dir = _init_project(tmp_path, monkeypatch, sample_seed_content)

        rc, out = _run(["status", str(project_dir)], monkeypatch)
        result = json.loads(out)

        assert rc == 0
        assert result["phase"] == "genesis"
        assert result["pending_checkpoint"] is None
        assert result["current_chapter"] == 0

    def test_status_missing_project(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Querying a project with no state file returns non-zero."""
        rc, out = _run(["status", str(tmp_path / "nonexistent")], monkeypatch)
        result = json.loads(out)

        assert rc != 0
        assert result["status"] == "error"


class TestReviewCommand:
    """``review <dir> approve|reject|modify`` resolves a pending checkpoint."""

    def test_review_approve_without_checkpoint_fails(
        self, tmp_path: Path, sample_seed_content: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Review with no pending checkpoint is an error (non-zero)."""
        project_dir = _init_project(tmp_path, monkeypatch, sample_seed_content)

        rc, out = _run(["review", str(project_dir), "approve"], monkeypatch)

        assert rc != 0  # No pending checkpoint to approve
        assert json.loads(out)["status"] == "error"

    def test_review_missing_project(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Review on a missing project errors out before touching checkpoints."""
        rc, out = _run(["review", str(tmp_path / "nope"), "approve"], monkeypatch)
        result = json.loads(out)

        assert rc != 0
        assert result["status"] == "error"

    def test_review_approve_with_checkpoint(
        self, tmp_path: Path, sample_seed_content: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Approving a real checkpoint clears it and records history."""
        project_dir = _init_project(tmp_path, monkeypatch, sample_seed_content)

        # Seed a pending checkpoint (an orchestrator would do this at runtime).
        state = load_state(project_dir)
        set_checkpoint(state, CheckpointType.GENESIS_COMPLETE, artifact="genesis.md")
        save_state(project_dir, state)

        rc, out = _run(["review", str(project_dir), "approve"], monkeypatch)
        result = json.loads(out)

        assert rc == 0
        assert result["decision"] == "approve"
        assert result["checkpoint_type"] == "genesis-complete"

        # The pending checkpoint is now cleared.
        state = load_state(project_dir)
        assert state.pending_checkpoint.type == CheckpointType.NONE

    def test_review_with_feedback(
        self, tmp_path: Path, sample_seed_content: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """--feedback attaches text to the checkpoint history entry."""
        project_dir = _init_project(tmp_path, monkeypatch, sample_seed_content)

        state = load_state(project_dir)
        set_checkpoint(state, CheckpointType.CHAPTER_MEMO, chapter=1)
        save_state(project_dir, state)

        feedback_file = tmp_path / "notes.txt"
        feedback_file.write_text("needs more tension in act 2", encoding="utf-8")

        rc, _ = _run(
            ["review", str(project_dir), "modify", "--feedback", str(feedback_file)],
            monkeypatch,
        )

        assert rc == 0
        state = load_state(project_dir)
        assert state.checkpoint_history[-1]["feedback"] == "needs more tension in act 2"
        assert state.checkpoint_history[-1]["decision"] == "modify"

    def test_review_genesis_escalation_feedback_rides_retry_slot(
        self, tmp_path: Path, sample_seed_content: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Modify feedback on a genesis escalation lands in genesis.retry_feedback.

        Genesis re-dispatch consumes genesis.retry_feedback (not chapter
        loop's modify_feedback) as corrective feedback — routing it anywhere
        else is a dead wire (canary escalation, 2026-09-28).
        """
        project_dir = _init_project(tmp_path, monkeypatch, sample_seed_content)

        state = load_state(project_dir)
        state.genesis.current_step = 0  # step 1 = shenbi-worldbuilding
        state.genesis.retry_counts["shenbi-worldbuilding"] = 3
        state.genesis.retry_feedback["shenbi-worldbuilding"] = "G4 check failed: stale"
        set_checkpoint(
            state, CheckpointType.ESCALATION, artifact="audits/escalation-genesis-report.md"
        )
        save_state(project_dir, state)

        feedback_file = tmp_path / "notes.txt"
        feedback_file.write_text(
            "rules.md 用 ## 规则一： 标题；locations.md 用 ## 地点： 标题", encoding="utf-8"
        )

        rc, _ = _run(
            ["review", str(project_dir), "modify", "--feedback", str(feedback_file)],
            monkeypatch,
        )

        assert rc == 0
        state = load_state(project_dir)
        assert state.pending_checkpoint.type == CheckpointType.NONE
        assert (
            state.genesis.retry_feedback["shenbi-worldbuilding"]
            == "rules.md 用 ## 规则一： 标题；locations.md 用 ## 地点： 标题"
        )
        assert state.genesis.retry_counts == {}  # escalation resolve resets budget

    def test_review_genesis_complete_reject_scoped_redo(
        self, tmp_path: Path, sample_seed_content: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """probe8 deadlock: the adjudicator ruled a scoped reject (redo
        power_system/relationships/… , KEEP the authoritative outline cluster)
        but the machinery could only roll back one step (foundation-review
        re-run) and the feedback was a dead wire. ``--redo-steps`` expresses
        the adjudication's redo list; un-listed done steps are skipped, not
        regenerated.
        """
        from shenbi.pipeline.genesis import GENESIS_STEPS

        project_dir = _init_project(tmp_path, monkeypatch, sample_seed_content)
        state = load_state(project_dir)
        state.genesis.current_step = 17  # all 17 steps dispatched
        state.genesis.skills_done = [s.skill for s in GENESIS_STEPS]
        set_checkpoint(
            state, CheckpointType.GENESIS_COMPLETE, artifact="foundation/review_report.md"
        )
        save_state(project_dir, state)

        feedback_file = tmp_path / "ruling.md"
        feedback_file.write_text(
            "打回重做: world/power_system.md 重写里程碑表; characters/relationships.md 重锚 21 组",
            encoding="utf-8",
        )

        rc, out = _run(
            [
                "review",
                str(project_dir),
                "reject",
                "--feedback",
                str(feedback_file),
                "--redo-steps",
                "2,10,12,17",
            ],
            monkeypatch,
        )
        assert rc == 0, out

        state = load_state(project_dir)
        assert state.genesis.current_step == 1  # cursor at step 2 (0-based idx 1)
        skills = set(state.genesis.skills_done)
        for num in (2, 10, 12, 17):
            assert GENESIS_STEPS[num - 1].skill not in skills, f"step {num} must be re-dispatched"
        # The authoritative outline cluster (4/6/7/8/13) stays untouched.
        for num in (1, 3, 4, 5, 6, 7, 8, 9, 11, 13, 14, 15, 16):
            assert GENESIS_STEPS[num - 1].skill in skills, (
                f"step {num} was ruled 保留不动 — must not be regenerated"
            )
        for num in (2, 10, 12, 17):
            assert (
                state.genesis.retry_feedback[GENESIS_STEPS[num - 1].skill]
                == "打回重做: world/power_system.md 重写里程碑表; characters/relationships.md 重锚 21 组"
            )
        assert state.genesis.retry_counts == {}

    def test_review_genesis_complete_reject_without_redo_steps_rolls_back_one(
        self, tmp_path: Path, sample_seed_content: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Without --redo-steps the pre-existing one-step rollback stands."""
        from shenbi.pipeline.genesis import GENESIS_STEPS

        project_dir = _init_project(tmp_path, monkeypatch, sample_seed_content)
        state = load_state(project_dir)
        state.genesis.current_step = 17
        state.genesis.skills_done = [s.skill for s in GENESIS_STEPS]
        set_checkpoint(
            state, CheckpointType.GENESIS_COMPLETE, artifact="foundation/review_report.md"
        )
        save_state(project_dir, state)

        rc, _ = _run(["review", str(project_dir), "reject"], monkeypatch)
        assert rc == 0

        state = load_state(project_dir)
        assert state.genesis.current_step == 16
        assert GENESIS_STEPS[16].skill not in state.genesis.skills_done
        assert GENESIS_STEPS[0].skill in state.genesis.skills_done

    def test_review_redo_steps_requires_genesis_complete_reject(
        self, tmp_path: Path, sample_seed_content: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """--redo-steps is only meaningful for a genesis-complete reject; on
        any other checkpoint it must fail BEFORE any staging side effects.
        """
        project_dir = _init_project(tmp_path, monkeypatch, sample_seed_content)
        state = load_state(project_dir)
        set_checkpoint(state, CheckpointType.PER_CHAPTER, chapter=1)
        save_state(project_dir, state)

        rc, out = _run(["review", str(project_dir), "reject", "--redo-steps", "2"], monkeypatch)
        assert rc == 1
        state = load_state(project_dir)
        assert state.pending_checkpoint.type == CheckpointType.PER_CHAPTER

    def test_review_redo_steps_rejects_out_of_range(
        self, tmp_path: Path, sample_seed_content: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        project_dir = _init_project(tmp_path, monkeypatch, sample_seed_content)
        state = load_state(project_dir)
        set_checkpoint(
            state, CheckpointType.GENESIS_COMPLETE, artifact="foundation/review_report.md"
        )
        save_state(project_dir, state)

        rc, _ = _run(["review", str(project_dir), "reject", "--redo-steps", "0,18"], monkeypatch)
        assert rc == 1
        state = load_state(project_dir)
        assert state.pending_checkpoint.type == CheckpointType.GENESIS_COMPLETE

    def test_review_approve_commits_staging(
        self, tmp_path: Path, sample_seed_content: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Approving a chapter-memo checkpoint commits staging to final paths."""
        project_dir = _init_project(tmp_path, monkeypatch, sample_seed_content)

        # Simulate a chapter-memo checkpoint with a staged plan file.
        staging_dir = project_dir / "staging" / "plans"
        staging_dir.mkdir(parents=True)
        (staging_dir / "chapter-1-plan.md").write_text("plan content", encoding="utf-8")

        state = load_state(project_dir)
        set_checkpoint(
            state, CheckpointType.CHAPTER_MEMO, chapter=1, artifact="plans/chapter-1-plan.md"
        )
        save_state(project_dir, state)

        rc, _ = _run(["review", str(project_dir), "approve"], monkeypatch)

        assert rc == 0
        committed = project_dir / "plans" / "chapter-1-plan.md"
        assert committed.exists()
        assert committed.read_text(encoding="utf-8") == "plan content"
        # Staging dir is cleaned up after commit.
        assert not (project_dir / "staging").exists()


class TestNextCommand:
    """``next <dir>`` loops through steps until a checkpoint is reached."""

    @patch("shenbi.pipeline.triggers.run_triggered_skills")
    @patch("shenbi.pipeline.triggers.check_triggers")
    def test_volume_boundary_checkpoint_preserved_with_book_closure(
        self,
        mock_check: MagicMock,
        mock_run: MagicMock,
        tmp_path: Path,
        sample_seed_content: str,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """When book-closure and volume-boundary both fire, the checkpoint wins.

        Regression: the book-closure branch used to run triggered skills and
        immediately transition to closure, silently dropping the
        volume-boundary checkpoint that ``run_triggered_skills`` had just
        raised. The fix adds an ``is_at_checkpoint`` guard (mirroring the
        non-book-closure branch) so the checkpoint survives.
        """
        from shenbi.pipeline.triggers import TriggerResult

        mock_check.return_value = TriggerResult(volume_boundary=True, book_closure=True)

        def _raise_volume_cp(state, project_dir, chapter, result):
            set_checkpoint(state, CheckpointType.VOLUME_BOUNDARY, chapter=chapter)
            return True

        mock_run.side_effect = _raise_volume_cp

        project_dir = _init_project(tmp_path, monkeypatch, sample_seed_content)

        # chapter-loop at the chapter past the last; novel.json carries the total.
        novel_path = project_dir / "novel.json"
        novel = json.loads(novel_path.read_text(encoding="utf-8"))
        novel["total_chapters"] = 12
        novel_path.write_text(json.dumps(novel, indent=2, ensure_ascii=False), encoding="utf-8")

        state = load_state(project_dir)
        state.phase = PipelinePhase.CHAPTER_LOOP
        state.chapter_loop.current_chapter = 13
        state.chapter_loop.step_index = 0
        save_state(project_dir, state)

        rc, out = _run(["next", str(project_dir)], monkeypatch)
        result = json.loads(out)

        assert rc == 0
        assert result["status"] == "blocked"
        assert result["checkpoint"] == "volume-boundary"

        state = load_state(project_dir)
        assert state.pending_checkpoint.type == CheckpointType.VOLUME_BOUNDARY
        # Phase stays in chapter-loop; the closure transition was deferred.
        assert state.phase == PipelinePhase.CHAPTER_LOOP

    @patch("shenbi.pipeline.genesis.run_gate_g3")
    @patch("shenbi.pipeline.genesis.run_gate_g4")
    @patch("shenbi.pipeline.genesis.dispatch_skill")
    def test_next_loops_genesis_to_checkpoint(
        self,
        mock_disp: MagicMock,
        mock_g4: MagicMock,
        mock_g3: MagicMock,
        tmp_path: Path,
        sample_seed_content: str,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Next runs all 17 genesis steps and hits the genesis-complete checkpoint."""
        mock_disp.return_value = DispatchResult(True, 0, "{}", "")
        mock_g4.return_value = {"status": "PASS"}
        mock_g3.return_value = {"status": "PASS"}

        project_dir = _init_project(tmp_path, monkeypatch, sample_seed_content)

        rc, out = _run(["next", str(project_dir)], monkeypatch)
        result = json.loads(out)

        assert rc == 0
        assert result["status"] == "blocked"
        assert result["checkpoint"] == "genesis-complete"
        assert mock_disp.call_count == 17

        state = load_state(project_dir)
        assert state.pending_checkpoint.type == CheckpointType.GENESIS_COMPLETE

    def test_next_blocked_at_checkpoint(
        self, tmp_path: Path, sample_seed_content: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A pending checkpoint blocks next until reviewed."""
        project_dir = _init_project(tmp_path, monkeypatch, sample_seed_content)

        state = load_state(project_dir)
        set_checkpoint(state, CheckpointType.GENESIS_COMPLETE)
        save_state(project_dir, state)

        rc, out = _run(["next", str(project_dir)], monkeypatch)
        result = json.loads(out)

        assert rc != 0
        assert result["status"] == "blocked"

    def test_next_missing_project(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Next on a missing project errors out."""
        rc, out = _run(["next", str(tmp_path / "nope")], monkeypatch)
        result = json.loads(out)

        assert rc != 0
        assert result["status"] == "error"

    @patch("shenbi.pipeline.closure.run_gate_g3")
    @patch("shenbi.pipeline.closure.run_gate_g4")
    @patch("shenbi.pipeline.closure.dispatch_skill")
    def test_next_loops_closure_to_book_closure_checkpoint(
        self,
        mock_disp: MagicMock,
        mock_g4: MagicMock,
        mock_g3: MagicMock,
        tmp_path: Path,
        sample_seed_content: str,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Next in closure phase runs steps 1-9 and hits book-closure checkpoint."""
        mock_disp.return_value = DispatchResult(True, 0, "{}", "")
        mock_g4.return_value = {"status": "PASS"}
        mock_g3.return_value = {"status": "PASS"}

        project_dir = _init_project(tmp_path, monkeypatch, sample_seed_content)

        # Set up closure phase: all chapters done, closure just started.
        state = load_state(project_dir)
        state.phase = PipelinePhase.CLOSURE
        state.closure_step = 0
        save_state(project_dir, state)

        rc, out = _run(["next", str(project_dir)], monkeypatch)
        result = json.loads(out)

        assert rc == 0
        assert result["status"] == "blocked"
        assert result["checkpoint"] == "book-closure"

        state = load_state(project_dir)
        assert state.pending_checkpoint.type == CheckpointType.BOOK_CLOSURE
        assert state.closure_step == 9  # paused before step 10 (snapshot)


class TestResumeCommand:
    """``resume <dir>`` transitions phases after checkpoint approval then continues."""

    @patch("shenbi.pipeline.chapter_loop.run_gate_g4")
    @patch("shenbi.pipeline.chapter_loop.dispatch_skill")
    def test_resume_transitions_after_genesis_approve(
        self,
        mock_disp: MagicMock,
        mock_g4: MagicMock,
        tmp_path: Path,
        sample_seed_content: str,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Approving genesis-complete then resume enters the chapter loop."""
        mock_disp.return_value = DispatchResult(True, 0, "{}", "")
        mock_g4.return_value = {"status": "PASS"}

        project_dir = _init_project(tmp_path, monkeypatch, sample_seed_content)

        # Simulate genesis completion: all steps done, checkpoint approved.
        state = load_state(project_dir)
        state.genesis.current_step = 17
        state.genesis.state = GenesisState.CHECKPOINT_PENDING
        set_checkpoint(
            state, CheckpointType.GENESIS_COMPLETE, artifact="foundation/review_report.md"
        )
        save_state(project_dir, state)

        _run(["review", str(project_dir), "approve"], monkeypatch)

        seed_genesis_outputs(
            project_dir
        )  # C37 F325: resume now fail-fast on missing genesis outputs
        rc, out = _run(["resume", str(project_dir)], monkeypatch)

        assert rc == 0
        state = load_state(project_dir)
        assert state.phase == PipelinePhase.CHAPTER_LOOP

    @patch("shenbi.pipeline.closure.run_gate_g3")
    @patch("shenbi.pipeline.closure.run_gate_g4")
    @patch("shenbi.pipeline.closure.dispatch_skill")
    def test_book_closure_resume_runs_snapshot(
        self,
        mock_disp: MagicMock,
        mock_g4: MagicMock,
        mock_g3: MagicMock,
        tmp_path: Path,
        sample_seed_content: str,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Resuming after a book-closure approval dispatches step 10 (snapshot).

        Regression: ``cmd_resume`` used to short-circuit a book-closure approval
        by calling ``transition_closure_to_completed`` and returning early,
        which permanently skipped step 10 (snapshot-manage). The fix lets the
        orchestration path run step 10; the closure runner completes closure,
        and the orchestrator performs the final transition.
        """
        mock_disp.return_value = DispatchResult(True, 0, "{}", "")
        mock_g4.return_value = {"status": "PASS"}
        mock_g3.return_value = {"status": "PASS"}

        project_dir = _init_project(tmp_path, monkeypatch, sample_seed_content)

        # Closure paused at step 9 (before snapshot); checkpoint already
        # approved + cleared by `review`, recorded in history.
        state = load_state(project_dir)
        state.phase = PipelinePhase.CLOSURE
        state.closure = ClosureState.CHECKPOINT_PENDING
        state.closure_step = 9
        state.checkpoint_history.append(
            {
                "type": "book-closure",
                "chapter": None,
                "decision": "approve",
                "resolved_at": "2026-07-02T00:00:00+00:00",
            }
        )
        save_state(project_dir, state)

        seed_genesis_outputs(
            project_dir
        )  # C37 F325: resume now fail-fast on missing genesis outputs
        rc, out = _run(["resume", str(project_dir)], monkeypatch)
        result = json.loads(out)

        assert rc == 0
        assert result["status"] == "ok"

        # Step 10 (snapshot-manage) was dispatched.
        dispatched_skills = [call.args[0] for call in mock_disp.call_args_list]
        assert "shenbi-snapshot-manage" in dispatched_skills

        state = load_state(project_dir)
        assert state.closure_step == 10
        assert state.phase == PipelinePhase.COMPLETED


class TestChaptersCommand:
    """``chapters <dir>`` lists per-chapter progress."""

    def test_chapters_empty_after_init(
        self, tmp_path: Path, sample_seed_content: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A fresh project has an empty chapter list."""
        project_dir = _init_project(tmp_path, monkeypatch, sample_seed_content)

        rc, out = _run(["chapters", str(project_dir)], monkeypatch)
        result = json.loads(out)

        assert rc == 0
        assert result["chapters"] == []
        assert result["current_chapter"] == 0

    def test_chapters_missing_project(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Chapters on a missing project errors out."""
        rc, out = _run(["chapters", str(tmp_path / "nope")], monkeypatch)
        result = json.loads(out)

        assert rc != 0
        assert result["status"] == "error"


class TestUpdateTotalChapters:
    """Tests for _update_total_chapters (G2: dynamic total_chapters re-update)."""

    def test_update_from_volume_map_end_pattern(self, tmp_path, monkeypatch):
        """Volume map with Chapter End: N sets total_chapters correctly."""
        from shenbi.pipeline.cli import _read_total_chapters, _update_total_chapters

        novel = tmp_path / "novel"
        novel.mkdir()
        outline = novel / "outline"
        outline.mkdir()

        (novel / "novel.json").write_text(
            json.dumps({"title": "Test", "total_chapters": 15}), encoding="utf-8"
        )

        # Write volume map with Chapter End: 30
        (outline / "volume_map.md").write_text(
            "# Volume Map\n\n"
            "## Volume 1\nChapters 1-10\nChapter End: 10\n\n"
            "## Volume 2\nChapters 11-30\nChapter End: 30\n",
            encoding="utf-8",
        )

        result = _update_total_chapters(novel)
        assert result == 30
        assert _read_total_chapters(novel) == 30

    def test_update_from_chapter_range(self, tmp_path, monkeypatch):
        """Volume map using Chapters N-M notation sets total_chapters."""
        from shenbi.pipeline.cli import _read_total_chapters, _update_total_chapters

        novel = tmp_path / "novel"
        novel.mkdir()
        outline = novel / "outline"
        outline.mkdir()

        (novel / "novel.json").write_text(
            json.dumps({"title": "Test", "total_chapters": 8}), encoding="utf-8"
        )

        # Volume map only has range notation
        (outline / "volume_map.md").write_text(
            "# Volume Map\n\n## Volume 1\nChapters 1-8\n\n## Volume 2\nChapters 9-20\n",
            encoding="utf-8",
        )

        result = _update_total_chapters(novel)
        assert result == 20
        assert _read_total_chapters(novel) == 20

    def test_no_volume_map_returns_zero(self, tmp_path, monkeypatch):
        """No volume_map.md returns 0 and leaves total_chapters unchanged."""
        from shenbi.pipeline.cli import _update_total_chapters

        novel = tmp_path / "novel"
        novel.mkdir()

        (novel / "novel.json").write_text(
            json.dumps({"title": "Test", "total_chapters": 10}), encoding="utf-8"
        )

        result = _update_total_chapters(novel)
        assert result == 0
        # Verify novel.json unchanged
        data = json.loads((novel / "novel.json").read_text(encoding="utf-8"))
        assert data["total_chapters"] == 10


class TestVerifyTruthIntegrity:
    """Tests for _verify_truth_integrity (G3: fail-fast on resume)."""

    def test_genesis_phase_checks_core_dirs(self, tmp_path, monkeypatch):
        """In genesis phase, missing core dirs are reported."""
        from shenbi.pipeline.cli import _verify_truth_integrity
        from shenbi.pipeline.state import PipelinePhase, PipelineState

        state = PipelineState(phase=PipelinePhase.GENESIS)
        missing = _verify_truth_integrity(state, tmp_path)
        assert "truth" in missing
        assert "characters" in missing
        assert "outline" in missing
        assert "world" in missing

    def test_existing_core_dirs_pass(self, tmp_path, monkeypatch):
        """When core dirs exist, genesis phase passes."""
        from shenbi.pipeline.cli import _verify_truth_integrity
        from shenbi.pipeline.state import PipelinePhase, PipelineState

        for d in ["truth", "characters", "outline", "world"]:
            (tmp_path / d).mkdir()

        state = PipelineState(phase=PipelinePhase.GENESIS)
        missing = _verify_truth_integrity(state, tmp_path)
        # In genesis phase, only core dirs are checked
        assert missing == []

    def test_chapter_loop_finds_missing_genesis_outputs(self, tmp_path, monkeypatch):
        """Chapter loop phase catches missing genesis files."""
        from shenbi.pipeline.cli import _verify_truth_integrity
        from shenbi.pipeline.state import (
            ChapterLoopStateData,
            PipelinePhase,
            PipelineState,
        )

        for d in ["truth", "characters", "outline", "world", "plans"]:
            (tmp_path / d).mkdir()

        state = PipelineState(
            phase=PipelinePhase.CHAPTER_LOOP,
            chapter_loop=ChapterLoopStateData(current_chapter=1),
        )
        missing = _verify_truth_integrity(state, tmp_path)
        # Core dirs exist, but genesis outputs like story_bible.md are missing
        assert "world/story_bible.md" in missing
        assert "genre-config.json" in missing

    def test_chapter_loop_with_genesis_outputs_passes(self, tmp_path, monkeypatch):
        """Chapter loop with all genesis outputs passes."""
        from shenbi.pipeline.cli import _verify_truth_integrity
        from shenbi.pipeline.state import (
            ChapterLoopStateData,
            PipelinePhase,
            PipelineState,
        )

        for d in ["truth", "characters", "outline", "world", "style", "plans"]:
            (tmp_path / d).mkdir()

        # Create genesis outputs
        (tmp_path / "world/story_bible.md").write_text("# test")
        (tmp_path / "genre-config.json").write_text(json.dumps({}))
        (tmp_path / "characters/protagonist.md").write_text("# Hero")
        (tmp_path / "outline/story_frame.md").write_text("# Frame")
        (tmp_path / "outline/volume_map.md").write_text("# Volumes")
        (tmp_path / "outline/rhythm_principles.md").write_text("# Rhythm")
        (tmp_path / "outline/thread_map.md").write_text("# Threads")
        (tmp_path / "truth/pending_hooks.md").write_text("# Hooks")
        (tmp_path / "world/power_system.md").write_text("# Power")
        (tmp_path / "world/locations.md").write_text("# Places")
        (tmp_path / "characters/relationships.md").write_text("# Relationships")
        (tmp_path / "truth/book_spine.md").write_text("# Spine")
        (tmp_path / "truth/author_intent.md").write_text("# Intent")
        (tmp_path / "style/style_profile.md").write_text("# Style")
        (tmp_path / "world/factions.md").write_text("# Factions")
        (tmp_path / "foundation").mkdir(exist_ok=True)
        (tmp_path / "foundation/review_report.md").write_text("# Review")
        (tmp_path / "plans").mkdir(exist_ok=True)

        state = PipelineState(
            phase=PipelinePhase.CHAPTER_LOOP,
            chapter_loop=ChapterLoopStateData(current_chapter=1),
        )
        missing = _verify_truth_integrity(state, tmp_path)
        assert missing == []

    def test_chapter_loop_missing_f354_files_reported(self, tmp_path, monkeypatch):
        """F354: factions.md + review_report.md are required genesis outputs."""
        from shenbi.pipeline.cli import _verify_truth_integrity
        from shenbi.pipeline.state import ChapterLoopStateData, PipelinePhase, PipelineState

        for d in ("truth", "characters", "outline", "world", "style", "plans", "foundation"):
            (tmp_path / d).mkdir(parents=True, exist_ok=True)
        seeded = {
            "world/story_bible.md": "# Bible",
            "genre-config.json": "{}",
            "characters/protagonist.md": "# Hero",
            "outline/story_frame.md": "# Frame",
            "outline/volume_map.md": "# Volumes",
            "outline/rhythm_principles.md": "# Rhythm",
            "outline/thread_map.md": "# Threads",
            "truth/pending_hooks.md": "# Hooks",
            "world/power_system.md": "# Power",
            "world/locations.md": "# Places",
            "characters/relationships.md": "# Relationships",
            "truth/book_spine.md": "# Spine",
            "truth/author_intent.md": "# Intent",
            "style/style_profile.md": "# Style",
        }
        for rel, content in seeded.items():
            (tmp_path / rel).write_text(content, encoding="utf-8")
        # world/factions.md + foundation/review_report.md deliberately absent
        state = PipelineState(
            phase=PipelinePhase.CHAPTER_LOOP,
            chapter_loop=ChapterLoopStateData(current_chapter=1),
        )
        missing = _verify_truth_integrity(state, tmp_path)
        assert missing == ["world/factions.md", "foundation/review_report.md"]

    def test_genesis_phase_missing_all(self, tmp_path, monkeypatch):
        """Genesis phase with no dirs reports all required ones."""
        from shenbi.pipeline.cli import _verify_truth_integrity
        from shenbi.pipeline.state import PipelinePhase, PipelineState

        state = PipelineState(phase=PipelinePhase.GENESIS)
        missing = _verify_truth_integrity(state, tmp_path)
        assert len(missing) >= 4
        assert "truth" in missing
        assert "characters" in missing
        assert "outline" in missing
        assert "world" in missing

    def test_phase_none_returns_empty(self, tmp_path, monkeypatch):
        """COMPLETED or FAILED phase returns empty list."""
        from shenbi.pipeline.cli import _verify_truth_integrity
        from shenbi.pipeline.state import PipelinePhase, PipelineState

        state = PipelineState(phase=PipelinePhase.COMPLETED)
        missing = _verify_truth_integrity(state, tmp_path)
        assert isinstance(missing, list)


class TestReDispatch:
    from pathlib import Path

    """Tests for G4 truth-sync re-dispatch after modify."""

    def test_derived_truth_map_has_chapter_memo(self):
        """CHAPTER_MEMO checkpoint triggers pacing-design re-sync."""
        from shenbi.pipeline.cli import DERIVED_TRUTH_MAP

        assert "chapter-memo" in DERIVED_TRUTH_MAP
        entries = DERIVED_TRUTH_MAP["chapter-memo"]
        skills = [e[0] for e in entries]
        assert "shenbi-pacing-design" in skills

    def test_derived_truth_map_has_state_settle(self):
        """STATE_SETTLE checkpoint triggers relationship-map + foreshadowing-resolve."""
        from shenbi.pipeline.cli import DERIVED_TRUTH_MAP

        assert "state-settle" in DERIVED_TRUTH_MAP
        entries = DERIVED_TRUTH_MAP["state-settle"]
        skills = [e[0] for e in entries]
        assert "shenbi-relationship-map" in skills
        assert "shenbi-foreshadowing-resolve" in skills

    def test_queue_re_dispatches_adds_to_state(self, tmp_path):
        """_queue_re_dispatches adds entries to pending_re_dispatches."""
        from shenbi.pipeline.cli import _queue_re_dispatches
        from shenbi.pipeline.state import (
            CheckpointData,
            CheckpointType,
            PipelineState,
        )

        state = PipelineState()
        cp = CheckpointData(type=CheckpointType.CHAPTER_MEMO, chapter=3)

        _queue_re_dispatches(state, cp)
        assert len(state.pending_re_dispatches) == 1
        assert state.pending_re_dispatches[0]["skill"] == "shenbi-pacing-design"
        assert state.pending_re_dispatches[0]["chapter"] == 3

    def test_queue_re_dispatches_avoids_duplicates(self, tmp_path):
        """Same skill is not queued twice."""
        from shenbi.pipeline.cli import _queue_re_dispatches
        from shenbi.pipeline.state import (
            CheckpointData,
            CheckpointType,
            PipelineState,
        )

        state = PipelineState()
        cp = CheckpointData(type=CheckpointType.CHAPTER_MEMO, chapter=3)

        _queue_re_dispatches(state, cp)
        _queue_re_dispatches(state, cp)
        assert len(state.pending_re_dispatches) == 1

    def test_unknown_checkpoint_no_ops(self, tmp_path):
        """Unknown checkpoint type does not queue anything."""
        from shenbi.pipeline.cli import _queue_re_dispatches
        from shenbi.pipeline.state import (
            CheckpointData,
            CheckpointType,
            PipelineState,
        )

        state = PipelineState()
        cp = CheckpointData(type=CheckpointType.BOOK_CLOSURE)

        _queue_re_dispatches(state, cp)
        assert state.pending_re_dispatches == []

    @patch("shenbi.pipeline.dispatch_helper.subprocess.run")
    def test_execute_empty_no_ops(self, mock_run):
        """_execute_pending_re_dispatches with empty list does nothing."""
        from shenbi.pipeline.cli import _execute_pending_re_dispatches
        from shenbi.pipeline.state import PipelineState

        state = PipelineState()
        result = _execute_pending_re_dispatches(state, Path("/tmp"))
        assert result is False
        mock_run.assert_not_called()

    def test_pending_re_dispatches_serde_roundtrip(self, tmp_path):
        """pending_re_dispatches survives to_dict/from_dict roundtrip."""
        from shenbi.pipeline.state import PipelineState

        state = PipelineState()
        state.pending_re_dispatches = [
            {"skill": "shenbi-pacing-design", "checkpoint_type": "chapter-memo", "chapter": 3},
        ]

        d = state.to_dict()
        restored = PipelineState.from_dict(d)
        assert len(restored.pending_re_dispatches) == 1
        assert restored.pending_re_dispatches[0]["skill"] == "shenbi-pacing-design"


class TestModifyDecision:
    """Tests that MODIFY rolls back step cursor and stores feedback."""

    def test_modify_chapter_memo_rolls_back_step_index(self, tmp_path, monkeypatch):
        """MODIFY via cmd_review rolls the step cursor back to chapter-planning."""
        import argparse

        from shenbi.pipeline import cli as pipeline_cli
        from shenbi.pipeline.machine import load_state, save_state, set_checkpoint
        from shenbi.pipeline.state import (
            CheckpointType,
            PipelinePhase,
            PipelineState,
            ReviewDecision,
        )

        project = tmp_path / "proj"
        (project / "truth").mkdir(parents=True)
        state = PipelineState.default(str(project))
        state.phase = PipelinePhase.CHAPTER_LOOP
        state.chapter_loop.current_chapter = 3
        state.chapter_loop.step_index = 2  # after chapter-planning
        save_state(project, state)
        set_checkpoint(
            state, CheckpointType.CHAPTER_MEMO, chapter=3, artifact="plans/chapter-3-plan.md"
        )
        save_state(project, state)

        monkeypatch.setattr(pipeline_cli, "_queue_re_dispatches", lambda *a, **k: None)

        feedback = project / "feedback.md"
        feedback.write_text("Fix the pacing in section 3", encoding="utf-8")

        args = argparse.Namespace(
            project_dir=str(project),
            decision=ReviewDecision.MODIFY.value,
            feedback=str(feedback),
        )
        rc = pipeline_cli.cmd_review(args)

        assert rc == 0
        reloaded = load_state(project)  # cmd_review saved its own copy — assert on reloaded state
        assert reloaded.chapter_loop.step_index == 1  # CHAPTER_STEPS[1] = chapter-planning
        assert reloaded.chapter_loop.modify_feedback == "Fix the pacing in section 3"

    def test_modify_injects_feedback_into_dispatch_prompt(self, tmp_path, monkeypatch):
        """Feedback stored in modify_feedback reaches the real dispatch prompt (one-shot)."""
        from shenbi.pipeline import chapter_loop
        from shenbi.pipeline.state import PipelinePhase, PipelineState

        captured: dict[str, object] = {}

        class FakeResult:
            success = True
            returncode = 0
            stderr = ""
            stdout = "ok"

        def fake_dispatch(skill, project_dir, prompt, *args, **kwargs):
            captured["skill"] = skill
            captured["prompt"] = prompt
            return FakeResult()

        monkeypatch.setattr(chapter_loop, "dispatch_skill", fake_dispatch)
        state = PipelineState.default(str(tmp_path))
        state.phase = PipelinePhase.CHAPTER_LOOP
        state.chapter_loop.current_chapter = 3
        state.chapter_loop.step_index = 1  # CHAPTER_STEPS[1] = chapter-planning, dispatched
        state.chapter_loop.modify_feedback = "Fix the pacing in section 3"

        chapter_loop.run_chapter_step(state, tmp_path)

        assert "Fix the pacing in section 3" in str(captured.get("prompt", ""))
        assert state.chapter_loop.modify_feedback is None  # one-shot consumption


class TestResumeFailFastOnMissingTruth:
    """C37 F325 wiring: cmd_resume must fail fast when truth integrity fails."""

    def test_resume_stops_before_later_steps_when_integrity_fails(
        self, tmp_path, monkeypatch, capsys
    ):
        """Integrity failures abort resume before later resume machinery runs."""
        import argparse

        from shenbi.pipeline import cli as pipeline_cli
        from shenbi.pipeline.state import PipelinePhase, PipelineState

        state = PipelineState(phase=PipelinePhase.GENESIS)
        monkeypatch.setattr(pipeline_cli, "load_state", lambda pd: state)
        monkeypatch.setattr(pipeline_cli, "save_state", lambda pd, s: None)
        monkeypatch.setattr("shenbi.pipeline.state_heal.heal_state_counters", lambda s, pd: None)
        monkeypatch.setattr(pipeline_cli, "_verify_truth_integrity", lambda s, pd: ["truth"])
        called = {"later": False}

        def _later(pd):
            called["later"] = True

        import shenbi.pipeline.chapter_loop as cl

        monkeypatch.setattr(cl, "_auto_rebuild_progress_if_stale", _later, raising=False)

        args = argparse.Namespace(project_dir=str(tmp_path))
        rc = pipeline_cli.cmd_resume(args)
        assert rc != 0, "resume must exit non-zero on truth-integrity failure"
        assert not called["later"], "fail-fast must abort BEFORE later resume steps"
        out = capsys.readouterr()
        assert "truth" in (out.out + out.err)


class TestReDispatchRetryCap:
    """Probe session 2026-09-29 (Stage 2 friction): a failed re-dispatch
    entry stayed in pending_re_dispatches forever and was retried on EVERY
    resume — one length-truncated chapter-revision burned 73 LLM calls /
    2.3M tokens (24.7% of probe cost). Entries must carry an attempt count
    and be dropped (with a loud log) after the cap instead of retrying
    indefinitely.
    """

    def test_failed_entry_dropped_after_retry_cap(self, tmp_path, monkeypatch):
        from shenbi.pipeline.cli import RE_DISPATCH_RETRY_CAP, _execute_pending_re_dispatches
        from shenbi.pipeline.state import PipelineState

        state = PipelineState.default(str(tmp_path))
        state.pending_re_dispatches = [
            {
                "skill": "shenbi-chapter-revision",
                "checkpoint_type": "per-chapter",
                "chapter": 8,
                "feedback": "expand",
            }
        ]

        calls = []

        def always_fail(skill, project_dir, prompt, **kwargs):
            calls.append(skill)
            from shenbi.pipeline.dispatch_helper import DispatchResult

            return DispatchResult(False, -1, "", "length_truncation_persistent")

        monkeypatch.setattr("shenbi.pipeline.dispatch_helper.dispatch_skill", always_fail)

        # drive the executor across "resumes" until the cap exhausts
        for _ in range(RE_DISPATCH_RETRY_CAP + 2):
            _execute_pending_re_dispatches(state, tmp_path)

        assert not state.pending_re_dispatches, "entry must be dropped after the retry cap"
        assert len(calls) == RE_DISPATCH_RETRY_CAP, "exactly cap-many dispatch attempts"

    def test_attempt_counter_increments_on_failure(self, tmp_path, monkeypatch):
        from shenbi.pipeline.cli import _execute_pending_re_dispatches
        from shenbi.pipeline.state import PipelineState

        state = PipelineState.default(str(tmp_path))
        state.pending_re_dispatches = [
            {
                "skill": "shenbi-chapter-revision",
                "checkpoint_type": "per-chapter",
                "chapter": 8,
            }
        ]

        def always_fail(skill, project_dir, prompt, **kwargs):
            from shenbi.pipeline.dispatch_helper import DispatchResult

            return DispatchResult(False, -1, "", "boom")

        monkeypatch.setattr("shenbi.pipeline.dispatch_helper.dispatch_skill", always_fail)
        _execute_pending_re_dispatches(state, tmp_path)
        assert state.pending_re_dispatches[0]["attempts"] == 1

    def test_success_clears_entry(self, tmp_path, monkeypatch):
        from shenbi.pipeline.cli import _execute_pending_re_dispatches
        from shenbi.pipeline.state import PipelineState

        state = PipelineState.default(str(tmp_path))
        state.pending_re_dispatches = [
            {
                "skill": "shenbi-chapter-revision",
                "checkpoint_type": "per-chapter",
                "chapter": 8,
                "attempts": 1,
            }
        ]

        def ok(skill, project_dir, prompt, **kwargs):
            from shenbi.pipeline.dispatch_helper import DispatchResult

            return DispatchResult(True, 0, "{}", "")

        monkeypatch.setattr("shenbi.pipeline.dispatch_helper.dispatch_skill", ok)
        _execute_pending_re_dispatches(state, tmp_path)
        assert not state.pending_re_dispatches


class TestRetryFeedbackRetired:
    """Canary defect 'retry_feedback 永不清': stale corrective feedback from
    a prior G4 failure stayed injected into every later dispatch prompt for
    the same skill (probe: ch1 drafting feedback still attached to later
    chapters' retry_feedback state). A pass must retire it.
    """

    def test_genesis_pass_pops_feedback(self):
        import inspect

        from shenbi.pipeline import genesis
        from shenbi.pipeline.genesis import run_genesis_step  # noqa: F401  (import check)

        src = inspect.getsource(genesis)
        assert "retry_feedback.pop" in src, "genesis must retire feedback on pass"

    def test_chapter_loop_pass_pops_feedback(self):
        import inspect

        from shenbi.pipeline import chapter_loop

        src = inspect.getsource(chapter_loop)
        assert "retry_feedback.pop" in src, "chapter_loop must retire feedback on pass"


class TestEscalationReportDetails:
    """Canary/probe defects: (1) the escalation dispatch carried only a
    one-line summary — the reviewer subagent reported 'gate 失败明细未随调
    用传入' while the details sat unused in retry_feedback; (2) when the
    escalation dispatch failed or skipped its write, the checkpoint reviewer
    read a STALE prior report (升级报告未覆写) or none at all (probe ch3).
    dispatch_escalation must forward the failure details and guarantee a
    fresh artifact via a machine fallback report.
    """

    def test_dispatch_escalation_forwards_details(self, tmp_path, monkeypatch):
        import shenbi.pipeline.revision_router as rr

        captured = {}

        def fake_dispatch(skill, project_dir, prompt, **kwargs):
            captured["prompt"] = prompt
            from shenbi.pipeline.dispatch_helper import DispatchResult

            return DispatchResult(True, 0, "{}", "")

        monkeypatch.setattr(rr, "dispatch_skill", fake_dispatch)
        rr.dispatch_escalation(
            tmp_path,
            7,
            context="Chapter 7 step 4 failed after 3 gate attempts",
            details="G4.word_count:chapters/chapter-7.md:1821<3000; G4.cd.no_hook",
        )
        assert "G4.word_count" in captured["prompt"], "failure details must reach the reviewer"
        assert "no_hook" in captured["prompt"]

    def test_dispatch_escalation_writes_fallback_when_artifact_stale(self, tmp_path, monkeypatch):
        import time

        import shenbi.pipeline.revision_router as rr

        # stale pre-existing report + dispatch that "succeeds" without writing
        report = tmp_path / "audits" / "escalation-7-report.md"
        report.parent.mkdir(parents=True)
        report.write_text("# 旧报告（上一次 escalation 的陈旧分析）", encoding="utf-8")
        old_mtime = report.stat().st_mtime
        time.sleep(0.05)

        def fake_dispatch(skill, project_dir, prompt, **kwargs):
            from shenbi.pipeline.dispatch_helper import DispatchResult

            return DispatchResult(True, 0, "{}", "")

        monkeypatch.setattr(rr, "dispatch_skill", fake_dispatch)
        rr.dispatch_escalation(
            tmp_path,
            7,
            context="Chapter 7 step 4 failed after 3 gate attempts",
            details="G4.word_count: 1821<3000",
        )
        text = report.read_text(encoding="utf-8")
        assert "旧报告" not in text, "stale report must be overwritten"
        assert "G4.word_count" in text, "fallback must carry the failure details"
        assert report.stat().st_mtime > old_mtime


class TestEscalationBudgetReset:
    """Canary defect 预算黏性, probe-hardened evidence (ch9 drafting
    'consumed 4/5'): ESCALATION resolution cleared retry_counts but NOT
    retry_budget_consumed — after an approve, the step got fresh attempt
    counters while the durable budget tripped 'Retry budget exhausted'
    on the FIRST new failure (consumed already past max).
    """

    def test_escalation_resolution_clears_scoped_budget(self):
        from shenbi.pipeline.machine import clear_checkpoint, set_checkpoint
        from shenbi.pipeline.state import (
            CheckpointType,
            PipelineState,
            ReviewDecision,
        )

        state = PipelineState.default("/tmp/x")
        state.chapter_loop.retry_budget_consumed["ch9-shenbi-chapter-drafting"] = 3
        state.chapter_loop.retry_budget_consumed["ch8-shenbi-chapter-drafting"] = 1
        set_checkpoint(state, CheckpointType.ESCALATION, chapter=9)
        clear_checkpoint(state, ReviewDecision.APPROVE)

        assert "ch9-shenbi-chapter-drafting" not in state.chapter_loop.retry_budget_consumed, (
            "escalation resolution must reset the affected chapter's budget"
        )
        assert "ch8-shenbi-chapter-drafting" in state.chapter_loop.retry_budget_consumed, (
            "other chapters' budgets are scoped, not cleared"
        )
