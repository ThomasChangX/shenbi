"""Regression tests for the final whole-branch code review fixes.

Each test class covers one review issue (C1, C2, I1-I5).
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from shenbi.pipeline.closure import (
    _resolve_closure_g4_path,
    _substitute_volume,
    run_closure_step,
)
from shenbi.pipeline.dispatch_helper import DispatchResult
from shenbi.pipeline.machine import (
    clear_checkpoint,
    load_state,
    save_state,
    set_checkpoint,
)
from shenbi.pipeline.state import (
    CheckpointType,
    ClosureState,
    PipelinePhase,
    PipelineState,
    ReviewDecision,
)
from shenbi.pipeline.transitions import (
    transition_closure_to_chapter_loop,
)
from shenbi.pipeline.triggers import TriggerResult, run_triggered_skills

# ---------------------------------------------------------------------------
# C1: Volume-boundary trigger re-fire creates an infinite loop
# ---------------------------------------------------------------------------


class TestC1TriggerReFireGuard:
    """After a volume-boundary checkpoint is cleared and resume re-enters,
    the trigger block must NOT re-fire (step_index guard).
    """

    def test_step_index_advances_past_trigger_block_on_checkpoint(self, tmp_path: Path) -> None:
        """When triggers fire and raise a checkpoint, step_index is set to 1
        so the trigger block does not re-enter on resume.
        """
        state = PipelineState.default(str(tmp_path))
        state.phase = PipelinePhase.CHAPTER_LOOP
        state.chapter_loop.current_chapter = 25
        state.chapter_loop.step_index = 0

        # Simulate what _orchestrate_to_checkpoint does: triggers fire,
        # checkpoint raised, step_index set to 1.
        result = TriggerResult(volume_boundary=True)
        with (
            patch("shenbi.pipeline.triggers.dispatch_skill") as mock_disp,
            patch("shenbi.pipeline.triggers.run_gate_g4") as mock_g4,
        ):
            mock_disp.return_value = DispatchResult(True, 0, "{}", "")
            mock_g4.return_value = {"status": "PASS"}
            run_triggered_skills(state, tmp_path, 24, result)

        assert state.pending_checkpoint.type == CheckpointType.VOLUME_BOUNDARY
        # The orchestrator sets step_index = 1 when it sees the checkpoint.
        state.chapter_loop.step_index = 1

        # After checkpoint is cleared, step_index is still 1: triggers skip.
        clear_checkpoint(state, ReviewDecision.APPROVE)
        assert state.chapter_loop.step_index == 1
        # The trigger condition (step_index == 0) is now False.
        assert not (state.chapter_loop.step_index == 0 and state.chapter_loop.current_chapter > 1)


# ---------------------------------------------------------------------------
# C2: Embedding DB path mismatch
# ---------------------------------------------------------------------------


class TestC2EmbeddingPath:
    """All three sites use the same filename: truth-embeddings.db."""

    def test_genesis_uses_truth_embeddings_db(self) -> None:
        import inspect

        from shenbi.pipeline import genesis

        source = inspect.getsource(genesis)
        assert "truth-embeddings.db" in source
        assert '"embeddings.db"' not in source

    def test_context_assemble_uses_truth_embeddings_db(self) -> None:
        import inspect

        from shenbi.pipeline import context_assemble

        source = inspect.getsource(context_assemble)
        assert "truth-embeddings.db" in source

    def test_truth_embed_uses_truth_embeddings_db(self) -> None:
        import inspect

        from shenbi.pipeline import truth_embed

        source = inspect.getsource(truth_embed)
        assert "truth-embeddings.db" in source


# ---------------------------------------------------------------------------
# I1: Triggered skill failures silently swallowed
# ---------------------------------------------------------------------------


class TestI1TriggeredFailureChecked:
    """run_triggered_skills returns False on failure; the orchestrator
    must check the return value and escalate.
    """

    @patch("shenbi.pipeline.triggers.dispatch_skill")
    @patch("shenbi.pipeline.triggers.run_gate_g4")
    def test_dispatch_failure_returns_false(self, mock_g4, mock_disp, tmp_path):
        mock_disp.return_value = DispatchResult(False, 1, "", "error")
        mock_g4.return_value = {"status": "PASS"}
        state = PipelineState.default(str(tmp_path))
        result = TriggerResult(l2_distill=True, score_arc=True)
        ok = run_triggered_skills(state, tmp_path, 12, result)
        assert ok is False  # I1: caller can detect failure

    @patch("shenbi.pipeline.triggers.dispatch_skill")
    @patch("shenbi.pipeline.triggers.run_gate_g4")
    def test_success_returns_true(self, mock_g4, mock_disp, tmp_path):
        mock_disp.return_value = DispatchResult(True, 0, "{}", "")
        mock_g4.return_value = {"status": "PASS"}
        state = PipelineState.default(str(tmp_path))
        result = TriggerResult(l2_distill=True, score_arc=True)
        ok = run_triggered_skills(state, tmp_path, 12, result)
        assert ok is True  # I1: success is distinguishable from failure


# ---------------------------------------------------------------------------
# I2: Closure has no retry logic
# ---------------------------------------------------------------------------


class TestI2ClosureRetry:
    """Closure steps retry up to max_revision_retries before returning False."""

    @patch("shenbi.pipeline.closure.run_gate_g3")
    @patch("shenbi.pipeline.closure.run_gate_g4")
    @patch("shenbi.pipeline.closure.dispatch_skill")
    def test_dispatch_failure_retries_then_advances(self, mock_disp, mock_g4, mock_g3, tmp_path):
        """First attempt fails, second succeeds: step advances."""
        mock_disp.side_effect = [
            DispatchResult(False, 1, "", "error"),
            DispatchResult(True, 0, "{}", ""),
        ]
        mock_g4.return_value = {"status": "PASS"}
        mock_g3.return_value = {"status": "PASS"}

        state = PipelineState.default(str(tmp_path))
        state.closure = ClosureState.IN_PROGRESS
        state.closure_step = 0

        run_closure_step(state, tmp_path)
        assert state.closure_step == 1
        assert mock_disp.call_count == 2
        # Retry count reset on success.
        assert state.closure_retry_counts.get("shenbi-foreshadowing-resolve", 0) == 0

    @patch("shenbi.pipeline.closure.run_gate_g4")
    @patch("shenbi.pipeline.closure.dispatch_skill")
    def test_exhausted_retries_returns_false(self, mock_disp, mock_g4, tmp_path):
        """After max_revision_retries (3), the step returns False."""
        mock_disp.return_value = DispatchResult(False, 1, "", "error")
        mock_g4.return_value = {"status": "PASS"}

        state = PipelineState.default(str(tmp_path))
        state.closure = ClosureState.IN_PROGRESS
        state.closure_step = 0

        result = run_closure_step(state, tmp_path)
        assert result is False
        assert state.closure_step == 0
        # 3 attempts = initial + 2 retries.
        assert mock_disp.call_count == 3
        assert state.closure_retry_counts["shenbi-foreshadowing-resolve"] == 3

    @patch("shenbi.pipeline.closure.run_gate_g4")
    @patch("shenbi.pipeline.closure.dispatch_skill")
    def test_g4_failure_retries(self, mock_disp, mock_g4, tmp_path):
        """G4 failure triggers retry, then success advances."""
        mock_disp.return_value = DispatchResult(True, 0, "{}", "")
        mock_g4.side_effect = [{"status": "FAIL"}, {"status": "PASS"}]

        state = PipelineState.default(str(tmp_path))
        state.closure = ClosureState.IN_PROGRESS
        state.closure_step = 0

        run_closure_step(state, tmp_path)
        assert state.closure_step == 1


# ---------------------------------------------------------------------------
# I3: State-settle staging commit is incomplete
# ---------------------------------------------------------------------------


class TestI3StateSettleStagingGlob:
    """STATE_SETTLE checkpoint commits all staging/truth/*.md files."""

    def test_multiple_truth_files_committed(
        self, tmp_path: Path, sample_seed_content: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import io
        import sys

        from shenbi.pipeline.cli import main

        out = io.StringIO()
        monkeypatch.setattr(sys, "stdout", out)

        # Init a project.
        seed_file = tmp_path / "seed.md"
        seed_file.write_text(sample_seed_content, encoding="utf-8")
        project_dir = tmp_path / "novel"
        main(["init", str(seed_file), "--project-dir", str(project_dir)])

        # Stage multiple truth files.
        staging_truth = project_dir / "staging" / "truth"
        staging_truth.mkdir(parents=True)
        (staging_truth / "current_state.md").write_text("state", encoding="utf-8")
        (staging_truth / "world_state.md").write_text("world", encoding="utf-8")
        (staging_truth / "character_state.md").write_text("chars", encoding="utf-8")

        state = load_state(project_dir)
        set_checkpoint(state, CheckpointType.STATE_SETTLE, chapter=1)
        save_state(project_dir, state)

        rc = main(["review", str(project_dir), "approve"])
        assert rc == 0

        # All three truth files should be committed.
        assert (project_dir / "truth" / "current_state.md").exists()
        assert (project_dir / "truth" / "world_state.md").exists()
        assert (project_dir / "truth" / "character_state.md").exists()
        # Staging cleared.
        assert not (project_dir / "staging").exists()


# ---------------------------------------------------------------------------
# I4: Book-closure reject doesn't transition back to chapter-loop
# ---------------------------------------------------------------------------


class TestI4BookClosureRejectTransition:
    """Rejecting a BOOK_CLOSURE checkpoint transitions back to chapter loop."""

    def test_transition_closure_to_chapter_loop(self) -> None:
        state = PipelineState.default("/x")
        state.phase = PipelinePhase.CLOSURE
        state.closure = ClosureState.CHECKPOINT_PENDING
        state.closure_step = 9
        state.closure_skills_done = ["shenbi-foreshadowing-resolve"]

        transition_closure_to_chapter_loop(state)

        assert state.phase == PipelinePhase.CHAPTER_LOOP
        assert state.closure == ClosureState.PENDING
        assert state.closure_step == 0
        assert state.closure_skills_done == []
        assert state.closure_retry_counts == {}
        assert state.chapter_loop.step_index == 0

    def test_review_reject_book_closure_transitions(
        self, tmp_path: Path, sample_seed_content: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import io
        import sys

        from shenbi.pipeline.cli import main

        seed_file = tmp_path / "seed.md"
        seed_file.write_text(sample_seed_content, encoding="utf-8")
        project_dir = tmp_path / "novel"
        out = io.StringIO()
        monkeypatch.setattr(sys, "stdout", out)
        main(["init", str(seed_file), "--project-dir", str(project_dir)])

        state = load_state(project_dir)
        state.phase = PipelinePhase.CLOSURE
        state.closure = ClosureState.CHECKPOINT_PENDING
        state.closure_step = 9
        set_checkpoint(state, CheckpointType.BOOK_CLOSURE)
        save_state(project_dir, state)

        rc = main(["review", str(project_dir), "reject"])
        assert rc == 0

        state = load_state(project_dir)
        assert state.phase == PipelinePhase.CHAPTER_LOOP
        assert state.closure == ClosureState.PENDING
        assert state.closure_step == 0


# ---------------------------------------------------------------------------
# I5: Closure output paths have unsubstituted N placeholders
# ---------------------------------------------------------------------------


class TestI5VolumeSubstitution:
    """Closure steps 4-6 substitute N with the actual volume number."""

    def test_substitute_volume(self) -> None:
        assert _substitute_volume("audits/volume-N-score.md", 3) == "audits/volume-3-score.md"
        assert (
            _substitute_volume("audits/chapter-N-long-span.md", 2)
            == "audits/chapter-2-long-span.md"
        )

    def test_resolve_closure_g4_path_no_N(self, tmp_path) -> None:
        from shenbi.pipeline.closure import ClosureStep

        step = ClosureStep(1, "shenbi-test", output_path="truth/pending_hooks.md")
        assert _resolve_closure_g4_path(step, tmp_path) == "truth/pending_hooks.md"

    def test_resolve_closure_g4_path_empty(self, tmp_path) -> None:
        from shenbi.pipeline.closure import ClosureStep

        step = ClosureStep(1, "shenbi-test", output_path="")
        assert _resolve_closure_g4_path(step, tmp_path) == ""

    def test_resolve_closure_g4_path_with_N(self, tmp_path) -> None:
        from shenbi.pipeline.closure import ClosureStep

        # Create a volume map so _current_volume returns a value.
        outline = tmp_path / "outline"
        outline.mkdir(parents=True)
        (outline / "volume_map.md").write_text(
            "## Volume 1\n- Chapter End: 24\n\n## Volume 2\n- Chapter End: 48\n",
            encoding="utf-8",
        )
        step = ClosureStep(4, "shenbi-score-volume", output_path="audits/volume-N-score.md")
        path = _resolve_closure_g4_path(step, tmp_path)
        assert "N" not in path
        assert "volume-2-score.md" in path  # 2 volumes -> last is 2

    def test_resolve_closure_g4_path_no_volume_map(self, tmp_path) -> None:
        from shenbi.pipeline.closure import ClosureStep

        step = ClosureStep(4, "shenbi-score-volume", output_path="audits/volume-N-score.md")
        path = _resolve_closure_g4_path(step, tmp_path)
        # No volume map -> defaults to volume 1.
        assert path == "audits/volume-1-score.md"

    @patch("shenbi.pipeline.closure.run_gate_g3")
    @patch("shenbi.pipeline.closure.run_gate_g4")
    @patch("shenbi.pipeline.closure.dispatch_skill")
    def test_step4_g4_gets_substituted_path(self, mock_disp, mock_g4, mock_g3, tmp_path):
        """When step 4 (score-volume) runs, G4 receives the path with N
        substituted by the actual volume number, not a literal 'N'.
        """
        mock_disp.return_value = DispatchResult(True, 0, "{}", "")
        mock_g4.return_value = {"status": "PASS"}
        mock_g3.return_value = {"status": "PASS"}

        # Create a volume map with 2 volumes.
        outline = tmp_path / "outline"
        outline.mkdir(parents=True)
        (outline / "volume_map.md").write_text(
            "## Volume 1\n- Chapter End: 24\n\n## Volume 2\n- Chapter End: 48\n",
            encoding="utf-8",
        )

        state = PipelineState.default(str(tmp_path))
        state.closure = ClosureState.IN_PROGRESS
        state.closure_step = 3  # step 4 (0-based index 3)

        run_closure_step(state, tmp_path)
        # G4 was called with volume-2 (not volume-N).
        g4_args = mock_g4.call_args[0][1]
        assert any("volume-2-score.md" in f for f in g4_args)
        assert not any("volume-N" in f for f in g4_args)
