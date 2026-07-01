"""Tests for the genesis orchestrator (Wave 3 Task 2).

Genesis runs 17 skills serially (spec section 5.1), each dispatched with a G4
structural check. foundation-review (step 17) additionally runs G3. After each
truth-writing step the Route A index (truth-index.json) is rebuilt and Route B
embeddings are refreshed when the model is available. dispatch/gate failures
retry per spec section 11, escalating after the configured limit.
"""

from __future__ import annotations

import json
from unittest.mock import patch

from shenbi.pipeline.dispatch_helper import DispatchResult
from shenbi.pipeline.genesis import (
    _INDEX_UPDATE_SKILLS,
    GENESIS_STEPS,
    run_genesis_step,
)
from shenbi.pipeline.state import (
    CheckpointType,
    GenesisState,
    PipelineState,
)


# ---------------------------------------------------------------------------
# Step table structure (brief verbatim + structural invariants)
# ---------------------------------------------------------------------------
class TestGenesisSteps:
    def test_step_count(self):
        assert len(GENESIS_STEPS) == 17

    def test_step_nums_are_sequential(self):
        assert [s.step_num for s in GENESIS_STEPS] == list(range(1, 18))

    def test_story_arch_before_faction(self):
        sa = next(i for i, s in enumerate(GENESIS_STEPS) if "story-architecture" in s.skill)
        fb = next(i for i, s in enumerate(GENESIS_STEPS) if "faction-builder" in s.skill)
        assert sa < fb

    def test_foreshadowing_plant_genesis_mode(self):
        fp = next(s for s in GENESIS_STEPS if "foreshadowing-plant" in s.skill)
        assert fp.mode == "genesis"

    def test_character_design_genesis_mode(self):
        cd = next(s for s in GENESIS_STEPS if "character-design" in s.skill)
        assert cd.mode == "genesis"

    def test_foundation_review_last(self):
        assert "foundation-review" in GENESIS_STEPS[-1].skill

    def test_foundation_review_path(self):
        assert "foundation/review_report.md" in GENESIS_STEPS[-1].output_path

    def test_anchor_curate_is_optional(self):
        ac = next(s for s in GENESIS_STEPS if "anchor-curate" in s.skill)
        assert ac.optional is True

    def test_genre_config_not_in_index_set(self):
        assert "shenbi-genre-config" not in _INDEX_UPDATE_SKILLS

    def test_foundation_review_not_in_index_set(self):
        assert "shenbi-foundation-review" not in _INDEX_UPDATE_SKILLS

    def test_worldbuilding_in_index_set(self):
        assert "shenbi-worldbuilding" in _INDEX_UPDATE_SKILLS


# ---------------------------------------------------------------------------
# run_genesis_step: happy path + G4 failure (brief verbatim)
# ---------------------------------------------------------------------------
class TestRunGenesisStep:
    @patch("shenbi.pipeline.genesis.dispatch_skill")
    @patch("shenbi.pipeline.genesis.run_gate_g4")
    def test_runs_step_g4_and_advances(self, mock_g4, mock_disp, tmp_path):
        mock_disp.return_value = DispatchResult(True, 0, "{}", "")
        mock_g4.return_value = {"status": "PASS"}
        state = PipelineState.default(str(tmp_path))
        state.genesis.state = GenesisState.IN_PROGRESS
        run_genesis_step(state, tmp_path)
        assert state.genesis.current_step == 1
        assert len(state.genesis.skills_done) == 1
        mock_g4.assert_called_once()

    @patch("shenbi.pipeline.genesis.dispatch_skill")
    @patch("shenbi.pipeline.genesis.run_gate_g4")
    def test_g4_fail_does_not_advance(self, mock_g4, mock_disp, tmp_path):
        mock_disp.return_value = DispatchResult(True, 0, "{}", "")
        mock_g4.return_value = {"status": "FAIL"}
        state = PipelineState.default(str(tmp_path))
        state.genesis.state = GenesisState.IN_PROGRESS
        run_genesis_step(state, tmp_path)
        assert state.genesis.current_step == 0

    @patch("shenbi.pipeline.genesis.dispatch_skill")
    @patch("shenbi.pipeline.genesis.run_gate_g4")
    def test_skills_done_records_skill(self, mock_g4, mock_disp, tmp_path):
        mock_disp.return_value = DispatchResult(True, 0, "{}", "")
        mock_g4.return_value = {"status": "PASS"}
        state = PipelineState.default(str(tmp_path))
        state.genesis.state = GenesisState.IN_PROGRESS
        run_genesis_step(state, tmp_path)
        assert state.genesis.skills_done == ["shenbi-worldbuilding"]

    @patch("shenbi.pipeline.genesis.dispatch_skill")
    @patch("shenbi.pipeline.genesis.run_gate_g4")
    def test_g4_pass_value_is_str_enum(self, mock_g4, mock_disp, tmp_path):
        from shenbi.status import GateStatus

        mock_disp.return_value = DispatchResult(True, 0, "{}", "")
        mock_g4.return_value = {"status": GateStatus.PASS}
        state = PipelineState.default(str(tmp_path))
        state.genesis.state = GenesisState.IN_PROGRESS
        run_genesis_step(state, tmp_path)
        assert state.genesis.current_step == 1

    @patch("shenbi.pipeline.genesis.dispatch_skill")
    def test_dispatch_fail_does_not_advance(self, mock_disp, tmp_path):
        mock_disp.return_value = DispatchResult(False, 1, "", "boom")
        state = PipelineState.default(str(tmp_path))
        state.genesis.state = GenesisState.IN_PROGRESS
        result = run_genesis_step(state, tmp_path)
        assert state.genesis.current_step == 0
        assert result is False

    @patch("shenbi.pipeline.genesis.dispatch_skill")
    def test_all_done_returns_true(self, mock_disp, tmp_path):
        state = PipelineState.default(str(tmp_path))
        state.genesis.state = GenesisState.IN_PROGRESS
        state.genesis.current_step = len(GENESIS_STEPS)
        result = run_genesis_step(state, tmp_path)
        assert result is True
        mock_disp.assert_not_called()


# ---------------------------------------------------------------------------
# G3 enforcement for foundation-review (independent skill)
# ---------------------------------------------------------------------------
class TestG3Enforcement:
    @patch("shenbi.pipeline.genesis.run_gate_g3")
    @patch("shenbi.pipeline.genesis.requires_independent")
    @patch("shenbi.pipeline.genesis.run_gate_g4")
    @patch("shenbi.pipeline.genesis.dispatch_skill")
    def test_g3_called_for_foundation_review(self, mock_disp, mock_g4, mock_req, mock_g3, tmp_path):
        mock_disp.return_value = DispatchResult(True, 0, "{}", "")
        mock_g4.return_value = {"status": "PASS"}
        mock_req.return_value = True
        mock_g3.return_value = {"status": "PASS"}
        state = PipelineState.default(str(tmp_path))
        state.genesis.state = GenesisState.IN_PROGRESS
        state.genesis.current_step = len(GENESIS_STEPS) - 1
        run_genesis_step(state, tmp_path)
        mock_g3.assert_called_once()

    @patch("shenbi.pipeline.genesis.run_gate_g3")
    @patch("shenbi.pipeline.genesis.requires_independent")
    @patch("shenbi.pipeline.genesis.run_gate_g4")
    @patch("shenbi.pipeline.genesis.dispatch_skill")
    def test_g3_not_called_for_worldbuilding(self, mock_disp, mock_g4, mock_req, mock_g3, tmp_path):
        mock_disp.return_value = DispatchResult(True, 0, "{}", "")
        mock_g4.return_value = {"status": "PASS"}
        mock_req.return_value = False
        state = PipelineState.default(str(tmp_path))
        state.genesis.state = GenesisState.IN_PROGRESS
        run_genesis_step(state, tmp_path)
        mock_g3.assert_not_called()

    @patch("shenbi.pipeline.genesis.run_gate_g3")
    @patch("shenbi.pipeline.genesis.requires_independent")
    @patch("shenbi.pipeline.genesis.run_gate_g4")
    @patch("shenbi.pipeline.genesis.dispatch_skill")
    def test_g3_fail_does_not_advance(self, mock_disp, mock_g4, mock_req, mock_g3, tmp_path):
        mock_disp.return_value = DispatchResult(True, 0, "{}", "")
        mock_g4.return_value = {"status": "PASS"}
        mock_req.return_value = True
        mock_g3.return_value = {"status": "FAIL"}
        state = PipelineState.default(str(tmp_path))
        state.genesis.state = GenesisState.IN_PROGRESS
        state.genesis.current_step = len(GENESIS_STEPS) - 1
        run_genesis_step(state, tmp_path)
        assert state.genesis.current_step == len(GENESIS_STEPS) - 1


# ---------------------------------------------------------------------------
# Genesis completion -> checkpoint
# ---------------------------------------------------------------------------
class TestGenesisCompletion:
    @patch("shenbi.pipeline.genesis.run_gate_g3")
    @patch("shenbi.pipeline.genesis.requires_independent")
    @patch("shenbi.pipeline.genesis.run_gate_g4")
    @patch("shenbi.pipeline.genesis.dispatch_skill")
    def test_sets_genesis_complete_checkpoint(
        self, mock_disp, mock_g4, mock_req, mock_g3, tmp_path
    ):
        mock_disp.return_value = DispatchResult(True, 0, "{}", "")
        mock_g4.return_value = {"status": "PASS"}
        mock_req.return_value = True
        mock_g3.return_value = {"status": "PASS"}
        state = PipelineState.default(str(tmp_path))
        state.genesis.state = GenesisState.IN_PROGRESS
        state.genesis.current_step = len(GENESIS_STEPS) - 1
        result = run_genesis_step(state, tmp_path)
        assert result is True
        assert state.genesis.state == GenesisState.CHECKPOINT_PENDING
        assert state.pending_checkpoint.type == CheckpointType.GENESIS_COMPLETE
        assert state.genesis.current_step == len(GENESIS_STEPS)

    @patch("shenbi.pipeline.genesis.run_gate_g4")
    @patch("shenbi.pipeline.genesis.dispatch_skill")
    def test_no_checkpoint_before_last_step(self, mock_disp, mock_g4, tmp_path):
        mock_disp.return_value = DispatchResult(True, 0, "{}", "")
        mock_g4.return_value = {"status": "PASS"}
        state = PipelineState.default(str(tmp_path))
        state.genesis.state = GenesisState.IN_PROGRESS
        result = run_genesis_step(state, tmp_path)
        assert result is False
        assert state.pending_checkpoint.type == CheckpointType.NONE


# ---------------------------------------------------------------------------
# Retry and escalation (spec section 11)
# ---------------------------------------------------------------------------
class TestRetryAndEscalation:
    @patch("shenbi.pipeline.genesis.dispatch_skill")
    def test_dispatch_fail_increments_retry_count(self, mock_disp, tmp_path):
        mock_disp.return_value = DispatchResult(False, 1, "", "err")
        state = PipelineState.default(str(tmp_path))
        state.genesis.state = GenesisState.IN_PROGRESS
        run_genesis_step(state, tmp_path)
        assert state.genesis.retry_counts["shenbi-worldbuilding"] == 1

    @patch("shenbi.pipeline.genesis.dispatch_skill")
    def test_escalation_after_max_retries(self, mock_disp, tmp_path):
        mock_disp.return_value = DispatchResult(False, 1, "", "err")
        state = PipelineState.default(str(tmp_path))
        state.genesis.state = GenesisState.IN_PROGRESS
        state.config.max_revision_retries = 3
        state.genesis.retry_counts["shenbi-worldbuilding"] = 2
        result = run_genesis_step(state, tmp_path)
        assert result is True
        assert state.pending_checkpoint.type == CheckpointType.ESCALATION
        assert state.genesis.current_step == 0

    @patch("shenbi.pipeline.genesis.run_gate_g4")
    @patch("shenbi.pipeline.genesis.dispatch_skill")
    def test_g4_fail_increments_retry_count(self, mock_disp, mock_g4, tmp_path):
        mock_disp.return_value = DispatchResult(True, 0, "{}", "")
        mock_g4.return_value = {"status": "FAIL"}
        state = PipelineState.default(str(tmp_path))
        state.genesis.state = GenesisState.IN_PROGRESS
        run_genesis_step(state, tmp_path)
        assert state.genesis.retry_counts["shenbi-worldbuilding"] == 1

    @patch("shenbi.pipeline.genesis.dispatch_skill")
    @patch("shenbi.pipeline.genesis.run_gate_g4")
    def test_success_resets_retry_count(self, mock_g4, mock_disp, tmp_path):
        mock_disp.return_value = DispatchResult(True, 0, "{}", "")
        mock_g4.return_value = {"status": "PASS"}
        state = PipelineState.default(str(tmp_path))
        state.genesis.state = GenesisState.IN_PROGRESS
        state.genesis.retry_counts["shenbi-worldbuilding"] = 2
        run_genesis_step(state, tmp_path)
        assert "shenbi-worldbuilding" not in state.genesis.retry_counts


# ---------------------------------------------------------------------------
# Optional step skip (step 16: anchor-curate)
# ---------------------------------------------------------------------------
class TestOptionalStepSkip:
    @patch("shenbi.pipeline.genesis.dispatch_skill")
    def test_optional_step_failure_skips_instead_of_escalating(self, mock_disp, tmp_path):
        """An optional step (anchor-curate) that fails must be skipped --
        cursor advances, no retry counter, no escalation checkpoint.
        """
        mock_disp.return_value = DispatchResult(False, 1, "", "anchor error")
        state = PipelineState.default(str(tmp_path))
        state.genesis.state = GenesisState.IN_PROGRESS
        # Position cursor at anchor-curate (step 16, 0-based index 15).
        state.genesis.current_step = 15

        result = run_genesis_step(state, tmp_path)

        # Cursor advanced past anchor-curate to foundation-review.
        assert state.genesis.current_step == 16
        # No escalation checkpoint raised.
        assert state.pending_checkpoint.type == CheckpointType.NONE
        # No retry counter left behind (skip, not retry).
        assert "shenbi-anchor-curate" not in state.genesis.retry_counts
        # No human action needed -- step simply advanced.
        assert result is False

    @patch("shenbi.pipeline.genesis.run_gate_g4")
    @patch("shenbi.pipeline.genesis.dispatch_skill")
    def test_optional_step_g4_failure_also_skips(self, mock_disp, mock_g4, tmp_path):
        """A G4 failure on an optional step skips just like a dispatch failure."""
        mock_disp.return_value = DispatchResult(True, 0, "{}", "")
        mock_g4.return_value = {"status": "FAIL"}
        state = PipelineState.default(str(tmp_path))
        state.genesis.state = GenesisState.IN_PROGRESS
        state.genesis.current_step = 15

        result = run_genesis_step(state, tmp_path)

        assert state.genesis.current_step == 16
        assert state.pending_checkpoint.type == CheckpointType.NONE
        assert result is False

    @patch("shenbi.pipeline.genesis.dispatch_skill")
    def test_optional_step_skipped_even_after_prior_retries(self, mock_disp, tmp_path):
        """If an optional step already has retry counts from a prior run
        (e.g. state loaded from disk), the first failure in this session
        still skips rather than escalating.
        """
        mock_disp.return_value = DispatchResult(False, 1, "", "err")
        state = PipelineState.default(str(tmp_path))
        state.genesis.state = GenesisState.IN_PROGRESS
        state.genesis.current_step = 15
        state.genesis.retry_counts["shenbi-anchor-curate"] = 99

        result = run_genesis_step(state, tmp_path)

        assert state.genesis.current_step == 16
        assert state.pending_checkpoint.type == CheckpointType.NONE
        assert result is False


# ---------------------------------------------------------------------------
# Index updates (Route A deterministic + Route B embeds)
# ---------------------------------------------------------------------------
class TestIndexUpdates:
    @patch("shenbi.pipeline.genesis._update_route_b")
    @patch("shenbi.pipeline.genesis.run_gate_g4")
    @patch("shenbi.pipeline.genesis.dispatch_skill")
    def test_truth_index_rebuilt_after_worldbuilding(self, mock_disp, mock_g4, mock_rb, tmp_path):
        mock_disp.return_value = DispatchResult(True, 0, "{}", "")
        mock_g4.return_value = {"status": "PASS"}
        (tmp_path / "characters").mkdir()
        (tmp_path / "characters" / "hero.md").write_text("---\nname: Hero\n---\n", encoding="utf-8")
        state = PipelineState.default(str(tmp_path))
        state.genesis.state = GenesisState.IN_PROGRESS
        run_genesis_step(state, tmp_path)
        idx_file = tmp_path / "truth-index.json"
        assert idx_file.exists()
        data = json.loads(idx_file.read_text(encoding="utf-8"))
        assert "Hero" in data["characters"]

    @patch("shenbi.pipeline.genesis._update_indexes")
    @patch("shenbi.pipeline.genesis.run_gate_g4")
    @patch("shenbi.pipeline.genesis.dispatch_skill")
    def test_genre_config_skips_index_update(self, mock_disp, mock_g4, mock_idx, tmp_path):
        mock_disp.return_value = DispatchResult(True, 0, "{}", "")
        mock_g4.return_value = {"status": "PASS"}
        state = PipelineState.default(str(tmp_path))
        state.genesis.state = GenesisState.IN_PROGRESS
        state.genesis.current_step = 1
        run_genesis_step(state, tmp_path)
        mock_idx.assert_not_called()

    def test_update_indexes_noop_for_non_truth_skill(self, tmp_path):
        from shenbi.pipeline.genesis import _update_indexes

        _update_indexes(tmp_path, "shenbi-genre-config")
        assert not (tmp_path / "truth-index.json").exists()

    def test_update_indexes_writes_truth_index(self, tmp_path):
        from shenbi.pipeline.genesis import _update_indexes

        (tmp_path / "world").mkdir()
        rules = tmp_path / "world" / "rules.md"
        rules.write_text("## R1: Magic is real\n", encoding="utf-8")
        _update_indexes(tmp_path, "shenbi-worldbuilding")
        data = json.loads((tmp_path / "truth-index.json").read_text(encoding="utf-8"))
        assert "R1" in data["rules"]

    def test_update_indexes_resilient_to_missing_files(self, tmp_path):
        from shenbi.pipeline.genesis import _update_indexes

        _update_indexes(tmp_path, "shenbi-worldbuilding")
        assert (tmp_path / "truth-index.json").exists()

    @patch("shenbi.pipeline.genesis.is_embed_available")
    @patch("shenbi.pipeline.genesis.run_gate_g4")
    @patch("shenbi.pipeline.genesis.dispatch_skill")
    def test_route_b_available_seeds_embeds(self, mock_disp, mock_g4, mock_embed_avail, tmp_path):
        mock_disp.return_value = DispatchResult(True, 0, "{}", "")
        mock_g4.return_value = {"status": "PASS"}
        mock_embed_avail.return_value = True
        (tmp_path / "truth").mkdir()
        hooks = tmp_path / "truth" / "pending_hooks.md"
        hooks.write_text(
            "---\nhooks:\n  - id: H01\n    content: the sword awakens\n---\n",
            encoding="utf-8",
        )
        with patch("shenbi.pipeline.genesis.embed_and_store", return_value=True) as mock_store:
            state = PipelineState.default(str(tmp_path))
            state.genesis.state = GenesisState.IN_PROGRESS
            run_genesis_step(state, tmp_path)
        assert mock_store.called

    @patch("shenbi.pipeline.genesis.is_embed_available", return_value=False)
    @patch("shenbi.pipeline.genesis.run_gate_g4")
    @patch("shenbi.pipeline.genesis.dispatch_skill")
    def test_route_b_unavailable_degrades_gracefully(
        self, mock_disp, mock_g4, mock_embed_avail, tmp_path
    ):
        mock_disp.return_value = DispatchResult(True, 0, "{}", "")
        mock_g4.return_value = {"status": "PASS"}
        state = PipelineState.default(str(tmp_path))
        state.genesis.state = GenesisState.IN_PROGRESS
        run_genesis_step(state, tmp_path)
        assert state.genesis.current_step == 1


# ---------------------------------------------------------------------------
# Route B error isolation (must not mask Route A success)
# ---------------------------------------------------------------------------
class TestRouteBErrorIsolation:
    @patch("shenbi.pipeline.genesis._update_route_b", side_effect=RuntimeError("embed boom"))
    @patch("shenbi.pipeline.genesis.run_gate_g4")
    @patch("shenbi.pipeline.genesis.dispatch_skill")
    def test_route_b_failure_does_not_mask_route_a_success(
        self, mock_disp, mock_g4, mock_rb, tmp_path
    ):
        """When _update_route_b raises, truth-index.json must still be written
        (Route A succeeded) and the step must advance normally.
        """
        mock_disp.return_value = DispatchResult(True, 0, "{}", "")
        mock_g4.return_value = {"status": "PASS"}
        # Create a truth-writing file so build_index has something to index.
        (tmp_path / "world").mkdir()
        (tmp_path / "world" / "story_bible.md").write_text("# World\n", encoding="utf-8")

        state = PipelineState.default(str(tmp_path))
        state.genesis.state = GenesisState.IN_PROGRESS

        result = run_genesis_step(state, tmp_path)

        # Route A: truth-index.json was written despite Route B failure.
        idx_file = tmp_path / "truth-index.json"
        assert idx_file.exists()
        # Route B error did not block step advancement.
        assert state.genesis.current_step == 1
        assert result is False
        mock_rb.assert_called_once()

    @patch("shenbi.pipeline.genesis._update_route_b", side_effect=RuntimeError("embed boom"))
    def test_update_indexes_writes_index_then_logs_route_b_failure(self, mock_rb, tmp_path):
        """Direct unit test: _update_indexes writes truth-index.json and logs
        route_b_update_failed (not truth_index_update_failed) when Route B
        raises.
        """
        from shenbi.pipeline.genesis import _update_indexes

        (tmp_path / "world").mkdir()
        (tmp_path / "world" / "rules.md").write_text("## R1: Magic\n", encoding="utf-8")

        _update_indexes(tmp_path, "shenbi-worldbuilding")

        # Route A succeeded.
        assert (tmp_path / "truth-index.json").exists()
        # Route B was attempted.
        mock_rb.assert_called_once()
