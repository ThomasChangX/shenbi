"""Unit tests for skill_utils/escalation/check.py (spec §6.2-6.3)."""

from __future__ import annotations

import pytest

from shenbi.skill_utils.escalation.check import (
    check_escalation,
    detect_score_decline,
)


@pytest.mark.unit
def test_decline_detected_with_clear_downward_trend() -> None:
    # 90, 88, 86, 84, 82 — slope ≈ -2.0 per chapter
    scores = [90.0, 87.0, 84.0, 81.0, 78.0]
    assert detect_score_decline(scores, window=5, slope_threshold=-2.0) is True


@pytest.mark.unit
def test_no_decline_when_scores_stable() -> None:
    scores = [88.0, 90.0, 89.0, 91.0, 88.0]
    assert detect_score_decline(scores, window=5, slope_threshold=-2.0) is False


@pytest.mark.unit
def test_no_decline_when_insufficient_samples() -> None:
    scores = [90.0, 80.0]  # only 2 samples, need 5
    assert detect_score_decline(scores, window=5, slope_threshold=-2.0) is False


@pytest.mark.unit
def test_check_escalation_returns_signal_for_decline() -> None:
    signals = check_escalation(
        resonance_scores=[90.0, 87.0, 84.0, 81.0, 78.0],
        sensitivity_blocking=False,
        volume_objective_met=True,
        regeneration_attempts=1,
    )
    assert any(s.trigger == "score_decline" for s in signals)


@pytest.mark.unit
def test_check_escalation_returns_signal_for_sensitivity_blocking() -> None:
    signals = check_escalation(
        resonance_scores=[90.0, 90.0, 90.0],
        sensitivity_blocking=True,
        volume_objective_met=True,
        regeneration_attempts=0,
    )
    assert any(s.trigger == "sensitivity_blocking" for s in signals)


@pytest.mark.unit
def test_check_escalation_returns_signal_for_volume_objective_missed() -> None:
    signals = check_escalation(
        resonance_scores=[90.0, 90.0, 90.0],
        sensitivity_blocking=False,
        volume_objective_met=False,
        regeneration_attempts=0,
    )
    assert any(s.trigger == "volume_objective_missed" for s in signals)


@pytest.mark.unit
def test_check_escalation_returns_signal_for_regeneration_loop() -> None:
    signals = check_escalation(
        resonance_scores=[90.0, 90.0, 90.0],
        sensitivity_blocking=False,
        volume_objective_met=True,
        regeneration_attempts=3,
    )
    assert any(s.trigger == "regeneration_loop_exhausted" for s in signals)


@pytest.mark.unit
def test_check_escalation_returns_signal_for_arc_score_below_70() -> None:
    signals = check_escalation(
        resonance_scores=[90.0, 90.0, 90.0],
        sensitivity_blocking=False,
        volume_objective_met=True,
        regeneration_attempts=0,
        arc_score=65.0,
    )
    assert any(s.trigger == "arc_score_below_threshold" for s in signals)


@pytest.mark.unit
def test_check_escalation_returns_signal_for_stratum_axis_drift() -> None:
    signals = check_escalation(
        resonance_scores=[90.0, 90.0, 90.0],
        sensitivity_blocking=False,
        volume_objective_met=True,
        regeneration_attempts=0,
        stratum_axis_drift=True,
    )
    assert any(s.trigger == "stratum_axis_drift" for s in signals)


@pytest.mark.unit
def test_check_escalation_no_signals_when_all_healthy() -> None:
    signals = check_escalation(
        resonance_scores=[90.0, 90.0, 90.0, 90.0, 90.0],
        sensitivity_blocking=False,
        volume_objective_met=True,
        regeneration_attempts=0,
    )
    assert signals == []
