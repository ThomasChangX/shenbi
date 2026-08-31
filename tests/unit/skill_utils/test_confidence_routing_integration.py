"""Confidence-calibration tests (spec §8.2 / spec #33 T1b).

The three-path routing composition was deleted with the dead model
(spec #33 T1b): production routing authority is
``pipeline/revision_router.route_chapter_revision`` and the revision cap is
``pipeline/revision_router.MAX_AUTO_REVISIONS``. These tests retain the
confidence face and pin the framework-path invariants: calibration downgrades
overconfident scorers, never upgrades, and the migrated cap escalates.
"""

from __future__ import annotations

from pathlib import Path

from shenbi.pipeline.confidence_calibration import (
    calibrate_and_patch_trend,
    compute_anchor_hit_rate,
    record_anchor_outcome,
)
from shenbi.pipeline.revision_router import revision_cap_exceeded
from shenbi.skill_utils.calibration.confidence import HitRate, calibrate_confidence


def test_overconfident_scorer_downgraded() -> None:
    assert calibrate_confidence("high", HitRate(high_confidence=0.25)) == "mid"


def test_well_calibrated_high_stays() -> None:
    assert calibrate_confidence("high", HitRate(high_confidence=0.9)) == "high"


def test_boundary_hit_rate_keeps_high() -> None:
    assert calibrate_confidence("high", HitRate(high_confidence=0.8)) == "high"


def test_low_reported_never_upgraded() -> None:
    assert calibrate_confidence("low", HitRate(high_confidence=1.0)) == "low"


def test_framework_path_downgrades_trend_confidence(tmp_path: Path) -> None:
    truth = tmp_path / "truth" / "resonance_trend.md"
    truth.parent.mkdir(parents=True)
    truth.write_text("| 5 | 高潮 | 70 | 65 | 80 | 75 | 72 | high |  |\n", encoding="utf-8")
    for n, high, correct in [(1, 2, 0), (2, 1, 0), (3, 1, 0)]:
        record_anchor_outcome(tmp_path, n, high, correct)
    hr = compute_anchor_hit_rate(tmp_path)
    assert hr is not None and hr.high_confidence == 0.0
    calibrate_and_patch_trend(tmp_path, 5, "high", overall=72)
    assert "| 5 | 高潮 | 70 | 65 | 80 | 75 | 72 | mid |  |" in truth.read_text(encoding="utf-8")


def test_migrated_cap_escalates_beyond_two_revisions() -> None:
    assert revision_cap_exceeded(3)
    assert calibrate_confidence("high", HitRate(high_confidence=0.25)) == "mid"
