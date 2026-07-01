"""End-to-end integration test for Wave 1 foundation.

Exercises the full Wave 1 flow across every module from the preceding tasks:
state dataclasses (T1), machine load/save/transitions (T2), filelock_utils
(T3), seed_parser (T4), checkpoint staging (T5), and the CLI (T6).

stdout is captured by monkeypatching sys.stdout to an in-memory buffer rather
 than using ``capsys``: ``configure_logging()`` binds structlog
(``cache_logger_on_first_use=True``) to the then-current sys.stderr, and
``capsys`` closes its capture streams at teardown — a closed-file error across
tests. An explicit StringIO avoids that coupling (same convention as
test_cli.py).
"""

from __future__ import annotations

import io
import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from shenbi.pipeline.cli import main
from shenbi.pipeline.dispatch_helper import DispatchResult
from shenbi.pipeline.machine import load_state, save_state, set_checkpoint
from shenbi.pipeline.state import CheckpointType, PipelinePhase


def _run(argv: list[str], monkeypatch: pytest.MonkeyPatch) -> tuple[int, str]:
    """Invoke main() with argv, capturing stdout to an in-memory buffer."""
    out = io.StringIO()
    monkeypatch.setattr(sys, "stdout", out)
    rc = main(argv)
    return rc, out.getvalue()


def _init(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, sample_seed_content: str) -> Path:
    """Create a fresh novel project under tmp_path and return its directory."""
    seed_file = tmp_path / "seed.md"
    seed_file.write_text(sample_seed_content, encoding="utf-8")
    project_dir = tmp_path / "novel"
    _run(["init", str(seed_file), "--project-dir", str(project_dir)], monkeypatch)
    return project_dir


class TestWave1E2E:
    """Full-flow integration across all Wave 1 modules."""

    def test_init_then_status_flow(
        self, tmp_path: Path, sample_seed_content: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Full flow: init -> status -> review (no checkpoint yet)."""
        seed_file = tmp_path / "seed.md"
        seed_file.write_text(sample_seed_content, encoding="utf-8")
        project_dir = tmp_path / "novel"

        # Step 1: init
        rc = main(["init", str(seed_file), "--project-dir", str(project_dir)])
        assert rc == 0

        # Step 2: status should show genesis phase
        rc = main(["status", str(project_dir)])
        assert rc == 0

        state = load_state(project_dir)
        assert state.phase.value == "genesis"
        assert state.genesis.state.value == "in-progress"

        # Step 3: init again should fail (idempotency)
        rc = main(["init", str(seed_file), "--project-dir", str(project_dir)])
        assert rc != 0

    def test_review_without_checkpoint_fails(
        self, tmp_path: Path, sample_seed_content: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Review should fail when no checkpoint is pending."""
        seed_file = tmp_path / "seed.md"
        seed_file.write_text(sample_seed_content, encoding="utf-8")
        project_dir = tmp_path / "novel"

        main(["init", str(seed_file), "--project-dir", str(project_dir)])

        rc = main(["review", str(project_dir), "approve"])
        assert rc != 0

    def test_project_has_all_expected_files(
        self, tmp_path: Path, sample_seed_content: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """After init, project should have novel.json, genre-config.json,
        genesis-context/, pipeline-state.json.
        """
        seed_file = tmp_path / "seed.md"
        seed_file.write_text(sample_seed_content, encoding="utf-8")
        project_dir = tmp_path / "novel"

        main(["init", str(seed_file), "--project-dir", str(project_dir)])

        assert (project_dir / "pipeline-state.json").exists()
        assert (project_dir / "novel.json").exists()
        assert (project_dir / "genre-config.json").exists()
        assert (project_dir / "genesis-context").is_dir()

    def test_full_checkpoint_review_cycle(
        self, tmp_path: Path, sample_seed_content: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Complete flow: init -> status -> checkpoint -> review -> status.

        Simulates an orchestrator setting a genesis-complete checkpoint, then
        drives the full review cycle through the CLI and verifies the pipeline
        state transitions correctly at each stage. This exercises every Wave 1
        module in sequence (state, machine, filelock, seed_parser, cli).
        """
        project_dir = _init(tmp_path, monkeypatch, sample_seed_content)

        # --- init -> status: genesis in-progress, no checkpoint ---
        rc, out = _run(["status", str(project_dir)], monkeypatch)
        status = json.loads(out)
        assert rc == 0
        assert status["phase"] == "genesis"
        assert status["pending_checkpoint"] is None

        # --- simulate orchestrator setting a genesis-complete checkpoint ---
        state = load_state(project_dir)
        set_checkpoint(
            state,
            CheckpointType.GENESIS_COMPLETE,
            artifact="genesis-context/world.md",
        )
        save_state(project_dir, state)

        # status now reports the pending checkpoint
        rc, out = _run(["status", str(project_dir)], monkeypatch)
        status = json.loads(out)
        assert rc == 0
        assert status["pending_checkpoint"] == "genesis-complete"
        assert status["checkpoint_artifact"] == "genesis-context/world.md"

        # --- review approve clears the checkpoint ---
        rc, out = _run(["review", str(project_dir), "approve"], monkeypatch)
        result = json.loads(out)
        assert rc == 0
        assert result["decision"] == "approve"
        assert result["checkpoint_type"] == "genesis-complete"

        # --- post-review status: checkpoint cleared, history recorded ---
        rc, out = _run(["status", str(project_dir)], monkeypatch)
        status = json.loads(out)
        assert rc == 0
        assert status["pending_checkpoint"] is None

        state = load_state(project_dir)
        assert len(state.checkpoint_history) == 1
        assert state.checkpoint_history[0]["type"] == "genesis-complete"
        assert state.checkpoint_history[0]["decision"] == "approve"

    def test_full_json_output_is_well_formed(
        self, tmp_path: Path, sample_seed_content: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Every CLI command emits valid JSON on stdout (G2 contract)."""
        project_dir = _init(tmp_path, monkeypatch, sample_seed_content)

        # Mock genesis dispatch so next actually runs orchestration without
        # hitting real subprocess calls (skill CLIs not available in test env).
        with (
            patch("shenbi.pipeline.genesis.dispatch_skill") as mock_disp,
            patch("shenbi.pipeline.genesis.run_gate_g4") as mock_g4,
        ):
            mock_disp.return_value = DispatchResult(True, 0, "{}", "")
            mock_g4.return_value = {"status": "PASS"}

        for argv in (
            ["status", str(project_dir)],
            ["chapters", str(project_dir)],
            ["next", str(project_dir)],
            ["resume", str(project_dir)],
            ["rollback", str(project_dir), "--chapter", "1"],
        ):
            rc, out = _run(argv, monkeypatch)
            # next/resume may return blocked (rc=1) at a checkpoint;
            # every command must still emit valid JSON regardless of rc.
            json.loads(out)

    def test_pipeline_state_persists_across_commands(
        self, tmp_path: Path, sample_seed_content: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """State mutations survive across CLI invocations (file-backed durability)."""
        project_dir = _init(tmp_path, monkeypatch, sample_seed_content)

        # Mutate state directly (simulating an orchestrator step)
        state = load_state(project_dir)
        state.chapter_loop.current_chapter = 3
        state.phase = PipelinePhase.CHAPTER_LOOP
        save_state(project_dir, state)

        # A fresh CLI invocation must see the persisted mutation
        rc, out = _run(["status", str(project_dir)], monkeypatch)
        status = json.loads(out)
        assert rc == 0
        assert status["phase"] == "chapter-loop"
        assert status["current_chapter"] == 3

    def test_reject_then_retry_checkpoint(
        self, tmp_path: Path, sample_seed_content: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Review reject clears the checkpoint, allowing a new one to be set."""
        project_dir = _init(tmp_path, monkeypatch, sample_seed_content)

        # First checkpoint
        state = load_state(project_dir)
        set_checkpoint(state, CheckpointType.CHAPTER_MEMO, chapter=1)
        save_state(project_dir, state)

        # Reject it
        rc, _ = _run(["review", str(project_dir), "reject"], monkeypatch)
        assert rc == 0

        # Pipeline is clear — a new checkpoint can be set
        state = load_state(project_dir)
        assert state.pending_checkpoint.type == CheckpointType.NONE
        assert len(state.checkpoint_history) == 1
        assert state.checkpoint_history[0]["decision"] == "reject"

        # Second checkpoint (retry)
        set_checkpoint(state, CheckpointType.CHAPTER_MEMO, chapter=1)
        save_state(project_dir, state)

        rc, out = _run(["status", str(project_dir)], monkeypatch)
        status = json.loads(out)
        assert rc == 0
        assert status["pending_checkpoint"] == "chapter-memo"

        # Approve the retry
        rc, _ = _run(["review", str(project_dir), "approve"], monkeypatch)
        assert rc == 0

        state = load_state(project_dir)
        assert len(state.checkpoint_history) == 2
        assert state.checkpoint_history[0]["decision"] == "reject"
        assert state.checkpoint_history[1]["decision"] == "approve"


class TestEndToEndErrorPaths:
    """Error scenarios that span multiple modules."""

    def test_status_on_missing_project(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Status on a non-existent project returns a clean error."""
        rc, out = _run(["status", str(tmp_path / "ghost")], monkeypatch)
        assert rc != 0
        assert json.loads(out)["status"] == "error"

    def test_review_on_missing_project(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Review on a non-existent project returns a clean error."""
        rc, out = _run(["review", str(tmp_path / "ghost"), "approve"], monkeypatch)
        assert rc != 0
        assert json.loads(out)["status"] == "error"

    def test_next_blocked_at_checkpoint_then_unblocked(
        self,
        tmp_path: Path,
        sample_seed_content: str,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Next is blocked while a checkpoint is pending, unblocks after review."""
        project_dir = _init(tmp_path, monkeypatch, sample_seed_content)

        state = load_state(project_dir)
        set_checkpoint(state, CheckpointType.GENESIS_COMPLETE)
        save_state(project_dir, state)

        # Pending checkpoint: next is blocked
        rc, out = _run(["next", str(project_dir)], monkeypatch)
        result = json.loads(out)
        assert rc != 0
        assert result["status"] == "blocked"

        # Review approve: next is unblocked and resumes the pipeline
        _run(["review", str(project_dir), "approve"], monkeypatch)

        # After approving genesis-complete, resume transitions to chapter-loop
        # and runs until the chapter-memo checkpoint (step 2).
        with (
            patch("shenbi.pipeline.chapter_loop.dispatch_skill") as mock_ch_disp,
            patch("shenbi.pipeline.chapter_loop.run_gate_g4") as mock_ch_g4,
        ):
            mock_ch_disp.return_value = DispatchResult(True, 0, "{}", "")
            mock_ch_g4.return_value = {"status": "PASS"}

            rc, out = _run(["resume", str(project_dir)], monkeypatch)
            result = json.loads(out)
            assert rc == 0
            assert result["status"] == "blocked"
            assert result["checkpoint"] == "chapter-memo"
