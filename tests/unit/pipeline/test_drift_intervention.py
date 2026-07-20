"""Tests for linguistic drift detection and 3-tier intervention."""

from shenbi.skill_utils.drift_detection.linguistic_drift import (
    compute_linguistic_metrics,
    detect_drift,
)


def test_intervention_triggers_on_degraded_text():
    """3-tier intervention should fire when system term density exceeds thresholds."""
    normal = "林风站在山顶，望着远方。" * 20
    degraded = "冷在场于第七层深度。冷值7.3，在场度0.89。" * 20

    baseline = compute_linguistic_metrics(normal)
    current = compute_linguistic_metrics(degraded)
    result = detect_drift(current, baseline)

    assert result.is_drift
    assert result.severity in ("WARN", "HARD", "ESCALATE")
    assert len(result.message) > 20
