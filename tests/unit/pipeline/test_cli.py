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
        (tmp_path / "plans").mkdir(exist_ok=True)

        state = PipelineState(
            phase=PipelinePhase.CHAPTER_LOOP,
            chapter_loop=ChapterLoopStateData(current_chapter=1),
        )
        missing = _verify_truth_integrity(state, tmp_path)
        assert missing == []

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
        """MODIFY on CHAPTER_MEMO checkpoint resets step_index to 1."""
        from shenbi.pipeline.cli import ReviewDecision
        from shenbi.pipeline.machine import clear_checkpoint, set_checkpoint
        from shenbi.pipeline.state import (
            CheckpointType,
            PipelinePhase,
            PipelineState,
        )

        state = PipelineState.default(str(tmp_path))
        state.phase = PipelinePhase.CHAPTER_LOOP
        state.chapter_loop.current_chapter = 3
        state.chapter_loop.step_index = 2  # after chapter-planning

        set_checkpoint(
            state, CheckpointType.CHAPTER_MEMO, chapter=3, artifact="plans/chapter-3-plan.md"
        )

        # Simulate MODIFY: step_index should roll back to 1
        cp = state.pending_checkpoint
        clear_checkpoint(state, ReviewDecision.MODIFY)

        if cp.type == CheckpointType.CHAPTER_MEMO:
            state.chapter_loop.step_index = 1
        elif cp.type == CheckpointType.STATE_SETTLE:
            state.chapter_loop.step_index = 6

        assert state.chapter_loop.step_index == 1
        assert state.pending_checkpoint.type == CheckpointType.NONE

    def test_modify_injects_feedback_into_dispatch_prompt(self, tmp_path, monkeypatch):
        """Feedback stored in modify_feedback appears in next dispatch prompt."""
        from shenbi.pipeline.state import PipelineState

        state = PipelineState.default(str(tmp_path))
        state.chapter_loop.modify_feedback = "Fix the pacing in section 3"

        # Simulate dispatch prompt construction (same logic as run_chapter_step)
        prompt = f"Execute chapter-planning for chapter 3. Project dir: {tmp_path}"
        if state.chapter_loop.modify_feedback:
            prompt += f"\n\nHuman review feedback: {state.chapter_loop.modify_feedback}"
            state.chapter_loop.modify_feedback = None

        assert "Fix the pacing in section 3" in prompt
        assert state.chapter_loop.modify_feedback is None  # consumed
