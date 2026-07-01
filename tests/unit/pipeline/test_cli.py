"""Tests for pipeline CLI commands.

Covers all seven subcommands (init, next, status, review, resume, chapters,
rollback) plus error paths. stdout is captured by monkeypatching sys.stdout to
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

    def test_init_idempotent_rejects_existing(
        self, tmp_path: Path, sample_seed_content: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Re-running init on an existing project fails (non-zero)."""
        project_dir = _init_project(tmp_path, monkeypatch, sample_seed_content)
        seed_file = tmp_path / "seed.md"

        rc, out = _run(["init", str(seed_file), "--project-dir", str(project_dir)], monkeypatch)

        assert rc != 0  # Should fail on duplicate init
        assert json.loads(out)["status"] == "error"

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

        rc, out = _run(["resume", str(project_dir)], monkeypatch)
        result = json.loads(out)

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


class TestRollbackCommand:
    """``rollback <dir> --chapter <N>`` restores a snapshot (Wave 3/4 placeholder)."""

    def test_rollback_not_implemented(
        self, tmp_path: Path, sample_seed_content: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Rollback reports not_implemented until snapshot integration lands."""
        project_dir = _init_project(tmp_path, monkeypatch, sample_seed_content)

        rc, out = _run(["rollback", str(project_dir), "--chapter", "2"], monkeypatch)
        result = json.loads(out)

        assert rc == 0
        assert result["status"] == "not_implemented"
