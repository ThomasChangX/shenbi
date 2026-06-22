"""Unit tests for skill_utils/calibration/confidence.py (spec §8.2 置信度校准)."""

from __future__ import annotations

import pytest

from shenbi.skill_utils.calibration.confidence import (
    HitRate,
    calibrate_confidence,
)


@pytest.mark.unit
def test_high_confidence_downgraded_when_anchor_hitrate_low() -> None:
    # scorer reported "high" but only hit 60% of anchors it judged high -> downgrade to mid
    assert calibrate_confidence("high", HitRate(high_confidence=0.6, threshold=0.8)) == "mid"


@pytest.mark.unit
def test_high_confidence_kept_when_hitrate_ok() -> None:
    assert calibrate_confidence("high", HitRate(high_confidence=0.9, threshold=0.8)) == "high"


@pytest.mark.unit
def test_low_never_upgraded() -> None:
    assert calibrate_confidence("low", HitRate(high_confidence=0.99, threshold=0.8)) == "low"
