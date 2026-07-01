"""Tests for the complete trigger system (spec sections 6.4-6.6).

Wave 3 Task 6. The trigger system determines which periodic/conditional
skills fire after each chapter completes:

- Arc-cycle (ch%12): memory-distill L2, score-arc, style-learning
- Stratum-cycle (ch%36): memory-distill L4 (first), score-stratum (second) [I14]
- Volume boundary: foreshadowing-resolve, volume-consolidation L3, score-volume,
  review-arc-payoff, memory-distill L5, style-learning, drift-guidance,
  volume expansion (section 6.5)
- Book closure (last chapter): transition to Phase 3
- Genre-config update (section 6.6): drift >= 3 warnings

Write-order constraint [I14]: when ch%36 and volume_boundary both fire,
memory-distill L4 writes data fields first, then score-stratum writes
diagnostic fields. Enforced by the ordered step list.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from shenbi.pipeline.dispatch_helper import DispatchResult
from shenbi.pipeline.state import (
    CheckpointType,
    PipelineState,
)
from shenbi.pipeline.triggers import (
    DRIFT_THRESHOLD,
    STRATUM_INTERVAL,
    STYLE_INTERVAL,
    TRIGGER_STEPS,
    TriggerResult,
    TriggerStep,
    check_genre_config_drift,
    check_triggers,
    get_trigger_steps,
    is_volume_boundary,
    read_volume_boundaries,
    run_triggered_skills,
    volume_snapshot_pending,
)

# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------


def _make_volume_map(project_dir: Path, boundaries: list[int]) -> Path:
    """Create a volume_map.md with given boundary chapter numbers.

    boundaries is a list of last-chapter numbers per volume, e.g.
    [24, 48, 67] means volume 1 ends at ch 24, volume 2 at ch 48,
    volume 3 at ch 67.
    """
    outline = project_dir / "outline"
    outline.mkdir(parents=True, exist_ok=True)
    vm = outline / "volume_map.md"
    lines = ["# Volume Map", ""]
    start = 1
    for i, end in enumerate(boundaries, 1):
        lines.append(f"## Volume {i}")
        lines.append(f"- Chapter Start: {start}")
        lines.append(f"- Chapter End: {end}")
        lines.append("")
        start = end + 1
    vm.write_text("\n".join(lines), encoding="utf-8")
    return vm


def _make_audit_drift(project_dir: Path, warning: str, count: int) -> Path:
    """Create audit_drift.md with repeated warnings."""
    truth = project_dir / "truth"
    truth.mkdir(parents=True, exist_ok=True)
    drift = truth / "audit_drift.md"
    lines = ["# Audit Drift", ""]
    for ch in range(1, count + 1):
        lines.append(f"## Chapter {ch}")
        lines.append(f"- warning: {warning}")
        lines.append("")
    drift.write_text("\n".join(lines), encoding="utf-8")
    return drift


# ---------------------------------------------------------------------------
# TriggerResult defaults
# ---------------------------------------------------------------------------


class TestTriggerResultDefaults:
    def test_all_false_by_default(self):
        r = TriggerResult()
        assert not r.l2_distill
        assert not r.l4_distill
        assert not r.volume_boundary
        assert not r.style_learning
        assert not r.book_closure
        assert not r.score_arc
        assert not r.score_stratum
        assert not r.score_volume
        assert not r.genre_config_update

    def test_any_returns_true_if_any_flag_set(self):
        assert not TriggerResult().any_triggered()
        assert TriggerResult(l2_distill=True).any_triggered()
        assert TriggerResult(book_closure=True).any_triggered()


# ---------------------------------------------------------------------------
# check_triggers: deterministic flag detection (spec section 6.4)
# ---------------------------------------------------------------------------


class TestCheckTriggersArc:
    """ch%12 triggers: l2_distill, score_arc, style_learning."""

    def test_ch12_l2(self):
        r = check_triggers(PipelineState.default("/x"), chapter=12, total_chapters=67)
        assert r.l2_distill
        assert r.style_learning

    def test_ch12_score_arc(self):
        r = check_triggers(PipelineState.default("/x"), chapter=12, total_chapters=67)
        assert r.score_arc

    def test_ch12_not_l4(self):
        r = check_triggers(PipelineState.default("/x"), chapter=12, total_chapters=67)
        assert not r.l4_distill

    def test_ch24_also_l2(self):
        r = check_triggers(PipelineState.default("/x"), chapter=24, total_chapters=67)
        assert r.l2_distill
        assert r.score_arc

    def test_ch11_no_arc_triggers(self):
        r = check_triggers(PipelineState.default("/x"), chapter=11, total_chapters=67)
        assert not r.l2_distill
        assert not r.score_arc
        assert not r.style_learning


class TestCheckTriggersStratum:
    """ch%36 triggers: l4_distill, score_stratum (also fires arc triggers)."""

    def test_ch36_l4(self):
        r = check_triggers(PipelineState.default("/x"), chapter=36, total_chapters=67)
        assert r.l4_distill

    def test_ch36_score_stratum(self):
        r = check_triggers(PipelineState.default("/x"), chapter=36, total_chapters=67)
        assert r.score_stratum

    def test_ch36_also_arc(self):
        # 36 % 12 == 0, so arc triggers also fire
        r = check_triggers(PipelineState.default("/x"), chapter=36, total_chapters=67)
        assert r.l2_distill
        assert r.score_arc

    def test_ch12_not_stratum(self):
        r = check_triggers(PipelineState.default("/x"), chapter=12, total_chapters=67)
        assert not r.score_stratum


class TestCheckTriggersClosure:
    """book_closure fires at the last chapter."""

    def test_last_chapter_closure(self):
        r = check_triggers(PipelineState.default("/x"), chapter=67, total_chapters=67)
        assert r.book_closure

    def test_not_last_chapter(self):
        r = check_triggers(PipelineState.default("/x"), chapter=66, total_chapters=67)
        assert not r.book_closure

    def test_past_last_chapter(self):
        r = check_triggers(PipelineState.default("/x"), chapter=68, total_chapters=67)
        assert r.book_closure


class TestCheckTriggersVolumeBoundary:
    """volume_boundary detection from outline/volume_map.md."""

    def test_volume_boundary_detected(self, tmp_path):
        _make_volume_map(tmp_path, [24, 48, 67])
        state = PipelineState.default(str(tmp_path))
        r = check_triggers(state, chapter=24, total_chapters=67)
        assert r.volume_boundary
        assert r.score_volume
        assert r.style_learning

    def test_not_volume_boundary(self, tmp_path):
        _make_volume_map(tmp_path, [24, 48, 67])
        state = PipelineState.default(str(tmp_path))
        r = check_triggers(state, chapter=23, total_chapters=67)
        assert not r.volume_boundary

    def test_second_volume_boundary(self, tmp_path):
        _make_volume_map(tmp_path, [24, 48, 67])
        state = PipelineState.default(str(tmp_path))
        r = check_triggers(state, chapter=48, total_chapters=67)
        assert r.volume_boundary

    def test_no_volume_map_no_boundary(self, tmp_path):
        state = PipelineState.default(str(tmp_path))
        r = check_triggers(state, chapter=24, total_chapters=67)
        assert not r.volume_boundary


# ---------------------------------------------------------------------------
# Volume boundary parser
# ---------------------------------------------------------------------------


class TestReadVolumeBoundaries:
    def test_parse_markdown_sections(self, tmp_path):
        _make_volume_map(tmp_path, [24, 48, 67])
        boundaries = read_volume_boundaries(tmp_path)
        assert 24 in boundaries
        assert 48 in boundaries
        assert 67 in boundaries

    def test_missing_file_returns_empty(self, tmp_path):
        boundaries = read_volume_boundaries(tmp_path)
        assert len(boundaries) == 0

    def test_is_volume_boundary_direct(self, tmp_path):
        _make_volume_map(tmp_path, [24, 48, 67])
        assert is_volume_boundary(24, tmp_path)
        assert not is_volume_boundary(23, tmp_path)


# ---------------------------------------------------------------------------
# Genre-config drift detection (spec section 6.6)
# ---------------------------------------------------------------------------


class TestGenreConfigDrift:
    def test_drift_at_threshold(self, tmp_path):
        _make_audit_drift(tmp_path, "fatigue_word: XYZ", DRIFT_THRESHOLD)
        state = PipelineState.default(str(tmp_path))
        r = check_triggers(state, chapter=37, total_chapters=67)
        assert r.genre_config_update

    def test_drift_below_threshold(self, tmp_path):
        _make_audit_drift(tmp_path, "fatigue_word: XYZ", DRIFT_THRESHOLD - 1)
        state = PipelineState.default(str(tmp_path))
        r = check_triggers(state, chapter=37, total_chapters=67)
        assert not r.genre_config_update

    def test_drift_disabled_by_config(self, tmp_path):
        _make_audit_drift(tmp_path, "fatigue_word: XYZ", DRIFT_THRESHOLD)
        state = PipelineState.default(str(tmp_path))
        state.config.genre_config_update_on_drift = False
        r = check_triggers(state, chapter=37, total_chapters=67)
        assert not r.genre_config_update

    def test_drift_different_warnings_dont_count(self, tmp_path):
        truth = tmp_path / "truth"
        truth.mkdir(parents=True, exist_ok=True)
        drift = truth / "audit_drift.md"
        lines = ["# Audit Drift", ""]
        for ch, w in enumerate(["A", "B", "C"], 1):
            lines.append(f"## Chapter {ch}")
            lines.append(f"- warning: {w}")
            lines.append("")
        drift.write_text("\n".join(lines), encoding="utf-8")
        state = PipelineState.default(str(tmp_path))
        r = check_triggers(state, chapter=4, total_chapters=67)
        assert not r.genre_config_update

    def test_check_genre_config_drift_direct(self, tmp_path):
        _make_audit_drift(tmp_path, "fatigue_word: XYZ", DRIFT_THRESHOLD)
        assert check_genre_config_drift(tmp_path)

    def test_no_drift_file(self, tmp_path):
        assert not check_genre_config_drift(tmp_path)


# ---------------------------------------------------------------------------
# Trigger step table + execution order (spec section 6.4, [I14])
# ---------------------------------------------------------------------------


class TestTriggerSteps:
    def test_arc_steps_present(self):
        steps = get_trigger_steps(
            TriggerResult(l2_distill=True, score_arc=True, style_learning=True)
        )
        skills = [s.skill for s in steps]
        assert "shenbi-memory-distill" in skills
        assert "shenbi-score-arc" in skills
        assert "shenbi-style-learning" in skills

    def test_volume_steps_present(self):
        r = TriggerResult(volume_boundary=True, score_volume=True, style_learning=True)
        steps = get_trigger_steps(r)
        skills = [s.skill for s in steps]
        assert "shenbi-foreshadowing-resolve" in skills
        assert "shenbi-volume-consolidation" in skills
        assert "shenbi-score-volume" in skills
        assert "shenbi-review-arc-payoff" in skills
        assert "shenbi-drift-guidance" in skills

    def test_style_learning_position_in_volume_block(self):
        """Spec section 6.4: score-volume -> memory-distill L5 ->
        style-learning -> drift-guidance. Style-learning must sit inside the
        volume block (not before it) and fire exactly once.
        """
        r = TriggerResult(volume_boundary=True, score_volume=True, style_learning=True)
        steps = get_trigger_steps(r)
        skills = [s.skill for s in steps]
        # Exactly one style-learning run, at the volume-block position.
        assert skills.count("shenbi-style-learning") == 1
        score_vol_idx = next(i for i, s in enumerate(steps) if s.skill == "shenbi-score-volume")
        l5_idx = next(
            i for i, s in enumerate(steps) if s.skill == "shenbi-memory-distill" and "L5" in s.mode
        )
        style_idx = next(i for i, s in enumerate(steps) if s.skill == "shenbi-style-learning")
        drift_idx = next(i for i, s in enumerate(steps) if s.skill == "shenbi-drift-guidance")
        assert score_vol_idx < l5_idx < style_idx < drift_idx

    def test_arc_style_learning_suppressed_at_volume_boundary(self):
        """At a volume boundary the periodic (arc) style-learning entry is
        suppressed in favor of the volume-block entry, so it never runs twice.
        """
        r = TriggerResult(
            volume_boundary=True,
            score_volume=True,
            style_learning=True,
            l2_distill=True,
            score_arc=True,
        )
        steps = get_trigger_steps(r)
        assert [s.skill for s in steps].count("shenbi-style-learning") == 1

    def test_volume_expansion_skills_present(self):
        r = TriggerResult(volume_boundary=True)
        steps = get_trigger_steps(r)
        skills = [s.skill for s in steps]
        assert "shenbi-character-design" in skills
        assert "shenbi-faction-builder" in skills
        assert "shenbi-location-builder" in skills
        assert "shenbi-relationship-map" in skills
        assert "shenbi-foreshadowing-plant" in skills
        assert "shenbi-plot-thread-weaver" in skills

    def test_empty_result_no_steps(self):
        assert get_trigger_steps(TriggerResult()) == []

    def test_genre_config_step_present(self):
        r = TriggerResult(genre_config_update=True)
        steps = get_trigger_steps(r)
        skills = [s.skill for s in steps]
        assert "shenbi-genre-config" in skills


class TestWriteOrderI14:
    """[I14]: memory-distill L4 before score-stratum when both fire."""

    def test_l4_before_stratum(self):
        r = TriggerResult(
            l2_distill=True,
            l4_distill=True,
            score_arc=True,
            score_stratum=True,
            style_learning=True,
        )
        steps = get_trigger_steps(r)
        l4_idx = next(
            i for i, s in enumerate(steps) if s.skill == "shenbi-memory-distill" and "L4" in s.mode
        )
        stratum_idx = next(i for i, s in enumerate(steps) if s.skill == "shenbi-score-stratum")
        assert l4_idx < stratum_idx

    def test_l2_before_arc(self):
        r = TriggerResult(l2_distill=True, score_arc=True, style_learning=True)
        steps = get_trigger_steps(r)
        l2_idx = next(
            i for i, s in enumerate(steps) if s.skill == "shenbi-memory-distill" and "L2" in s.mode
        )
        arc_idx = next(i for i, s in enumerate(steps) if s.skill == "shenbi-score-arc")
        assert l2_idx < arc_idx


class TestTriggerStepDataclass:
    def test_defaults(self):
        s = TriggerStep("shenbi-test")
        assert s.skill == "shenbi-test"
        assert s.mode == ""
        assert s.output_path == ""
        assert s.requires_g3 is False


# ---------------------------------------------------------------------------
# run_triggered_skills: execution with mock dispatch + gates
# ---------------------------------------------------------------------------


class TestRunTriggeredSkills:
    @patch("shenbi.pipeline.triggers.dispatch_skill")
    @patch("shenbi.pipeline.triggers.run_gate_g4")
    def test_executes_all_arc_steps(self, mock_g4, mock_disp, tmp_path):
        mock_disp.return_value = DispatchResult(True, 0, "{}", "")
        mock_g4.return_value = {"status": "PASS"}
        state = PipelineState.default(str(tmp_path))
        result = TriggerResult(l2_distill=True, score_arc=True, style_learning=True)
        run_triggered_skills(state, tmp_path, 12, result)
        assert mock_disp.call_count == 3

    @patch("shenbi.pipeline.triggers.dispatch_skill")
    @patch("shenbi.pipeline.triggers.run_gate_g4")
    def test_g3_for_scoring_skills(self, mock_g4, mock_disp, tmp_path):
        mock_disp.return_value = DispatchResult(True, 0, "{}", "")
        mock_g4.return_value = {"status": "PASS"}
        state = PipelineState.default(str(tmp_path))
        result = TriggerResult(score_arc=True, l2_distill=True, style_learning=True)
        run_triggered_skills(state, tmp_path, 12, result)
        assert mock_disp.call_count == 3
        assert mock_g4.call_count == 3

    @patch("shenbi.pipeline.triggers.dispatch_skill")
    @patch("shenbi.pipeline.triggers.run_gate_g4")
    def test_volume_boundary_checkpoint(self, mock_g4, mock_disp, tmp_path):
        """Volume boundary raises a checkpoint but does NOT dispatch the
        snapshot -- that is deferred to the caller post-review (Important #2).
        """
        mock_disp.return_value = DispatchResult(True, 0, "{}", "")
        mock_g4.return_value = {"status": "PASS"}
        state = PipelineState.default(str(tmp_path))
        result = TriggerResult(volume_boundary=True, score_volume=True, style_learning=True)
        raised = run_triggered_skills(state, tmp_path, 24, result)
        assert raised is True
        assert state.pending_checkpoint.type == CheckpointType.VOLUME_BOUNDARY
        # snapshot-manage must NOT have been dispatched before the review.
        dispatched = [c.args[0] for c in mock_disp.call_args_list]
        assert "shenbi-snapshot-manage" not in dispatched
        assert volume_snapshot_pending(state)

    @patch("shenbi.pipeline.triggers.dispatch_skill")
    @patch("shenbi.pipeline.triggers.run_gate_g4")
    def test_volume_snapshot_pending_clears_after_review(self, mock_g4, mock_disp, tmp_path):
        """volume_snapshot_pending flips to False once the checkpoint clears."""
        from shenbi.pipeline.machine import clear_checkpoint
        from shenbi.pipeline.state import ReviewDecision

        mock_disp.return_value = DispatchResult(True, 0, "{}", "")
        mock_g4.return_value = {"status": "PASS"}
        state = PipelineState.default(str(tmp_path))
        result = TriggerResult(volume_boundary=True, score_volume=True, style_learning=True)
        run_triggered_skills(state, tmp_path, 24, result)
        assert volume_snapshot_pending(state)
        clear_checkpoint(state, ReviewDecision.APPROVE)
        assert not volume_snapshot_pending(state)

    @patch("shenbi.pipeline.triggers.dispatch_skill")
    @patch("shenbi.pipeline.triggers.run_gate_g4")
    def test_no_checkpoint_for_non_volume(self, mock_g4, mock_disp, tmp_path):
        mock_disp.return_value = DispatchResult(True, 0, "{}", "")
        mock_g4.return_value = {"status": "PASS"}
        state = PipelineState.default(str(tmp_path))
        result = TriggerResult(l2_distill=True, score_arc=True, style_learning=True)
        raised = run_triggered_skills(state, tmp_path, 12, result)
        assert raised is False
        assert state.pending_checkpoint.type == CheckpointType.NONE

    @patch("shenbi.pipeline.triggers.dispatch_skill")
    @patch("shenbi.pipeline.triggers.run_gate_g4")
    def test_dispatch_failure_returns_false(self, mock_g4, mock_disp, tmp_path):
        mock_disp.return_value = DispatchResult(False, 1, "", "error")
        mock_g4.return_value = {"status": "PASS"}
        state = PipelineState.default(str(tmp_path))
        result = TriggerResult(l2_distill=True)
        raised = run_triggered_skills(state, tmp_path, 12, result)
        assert raised is False

    @patch("shenbi.pipeline.triggers.dispatch_skill")
    @patch("shenbi.pipeline.triggers.run_gate_g4")
    def test_g4_failure_returns_false(self, mock_g4, mock_disp, tmp_path):
        mock_disp.return_value = DispatchResult(True, 0, "{}", "")
        mock_g4.return_value = {"status": "FAIL"}
        state = PipelineState.default(str(tmp_path))
        result = TriggerResult(l2_distill=True)
        raised = run_triggered_skills(state, tmp_path, 12, result)
        assert raised is False

    @patch("shenbi.pipeline.triggers.dispatch_skill")
    @patch("shenbi.pipeline.triggers.run_gate_g4")
    def test_no_triggers_no_dispatch(self, mock_g4, mock_disp, tmp_path):
        state = PipelineState.default(str(tmp_path))
        run_triggered_skills(state, tmp_path, 5, TriggerResult())
        assert mock_disp.call_count == 0


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


class TestConstants:
    def test_style_interval(self):
        assert STYLE_INTERVAL == 12

    def test_stratum_interval(self):
        assert STRATUM_INTERVAL == 36

    def test_drift_threshold(self):
        assert DRIFT_THRESHOLD == 3

    def test_trigger_steps_table_not_empty(self):
        assert len(TRIGGER_STEPS) > 0
