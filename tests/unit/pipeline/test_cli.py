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

import pytest

from shenbi.pipeline.cli import main
from shenbi.pipeline.machine import load_state, save_state, set_checkpoint
from shenbi.pipeline.state import CheckpointType


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


class TestNextCommand:
    """``next <dir>`` advances toward the next checkpoint (Wave 3 placeholder)."""

    def test_next_not_implemented_when_clear(
        self, tmp_path: Path, sample_seed_content: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """With no pending checkpoint, next reports not_implemented (Wave 3)."""
        project_dir = _init_project(tmp_path, monkeypatch, sample_seed_content)

        rc, out = _run(["next", str(project_dir)], monkeypatch)
        result = json.loads(out)

        assert rc == 0
        assert result["status"] == "not_implemented"

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


class TestResumeCommand:
    """``resume <dir>`` behaves like next (Wave 3 placeholder)."""

    def test_resume_delegates_to_next(
        self, tmp_path: Path, sample_seed_content: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Resume returns the same not_implemented status as next."""
        project_dir = _init_project(tmp_path, monkeypatch, sample_seed_content)

        rc, out = _run(["resume", str(project_dir)], monkeypatch)
        result = json.loads(out)

        assert rc == 0
        assert result["status"] == "not_implemented"


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
