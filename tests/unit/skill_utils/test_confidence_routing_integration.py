"""Integration tests for the confidence→routing path (spec §8.2, §5.4, §10 置信度校准).

These exercise the *complete* deterministic chain an overconfident-but-inaccurate
scorer is subject to: ``calibrate_confidence`` downgrades a reported ``high`` to
``mid`` when the anchor hit-rate is low, and that calibrated level then feeds
``route_block`` so a clear-fail block is rerouted from ``AUTO_REVISE`` to
``HUMAN_REVIEW`` instead of burning revision cycles.

Unlike ``test_calibration.py`` / ``test_routing.py`` (which test each helper in
isolation), these tests compose the two helpers the way ``review-resonance``
actually does, and assert the cross-helper invariant: calibration *changes* the
routing decision.
"""

from __future__ import annotations

import pytest

from shenbi.skill_utils.calibration.confidence import (
    HitRate,
    calibrate_confidence,
)
from shenbi.skill_utils.review_resonance import Routing, route_block


def _calibrate_and_route(
    reported: str,
    hit_rate: float,
    *,
    overall: float,
    threshold: float = 75,
    floors: dict[str, tuple[float, float]] | None = None,
    prior_revisions: int = 0,
):
    """Full §8.2→§5.4 composition: calibrate the reported confidence by anchor
    hit-rate, then route the (already-scored) block with the *calibrated* level.
    """
    calibrated = calibrate_confidence(reported, HitRate(high_confidence=hit_rate))
    return route_block(
        overall=overall,
        threshold=threshold,
        floors=floors or {},
        confidence=calibrated,
        prior_revisions=prior_revisions,
    )


# --- the core §10 integration: calibration changes the routing decision -------


@pytest.mark.unit
def test_overconfident_scorer_rerouted_from_auto_to_human() -> None:
    """High + low hit-rate → mid → clear-fail reroutes AUTO_REVISE→HUMAN_REVIEW.

    The same clear-fail block routes differently depending *only* on whether the
    scorer's reported confidence survives calibration.
    """
    # well-calibrated scorer: hit-rate 0.9 keeps "high" → auto-revise
    ok = _calibrate_and_route("high", 0.9, overall=40, threshold=75)
    assert ok.path is Routing.AUTO_REVISE

    # overconfident scorer: hit-rate 0.6 downgrades to "mid" → human review
    over = _calibrate_and_route("high", 0.6, overall=40, threshold=75)
    assert over.path is Routing.HUMAN_REVIEW

    # the routing decision is genuinely different — calibration had an effect
    assert ok.path is not over.path


@pytest.mark.unit
def test_calibrated_confidence_label_is_carried_by_routing_result() -> None:
    """The routing result reports the *calibrated* level, not the reported one."""
    over = _calibrate_and_route("high", 0.6, overall=40, threshold=75)
    assert over.confidence == "mid"  # downgraded from reported "high"


# --- negative cases: when calibration does NOT change the outcome ------------


@pytest.mark.unit
def test_well_calibrated_high_stays_auto_revise() -> None:
    """hit-rate >= threshold keeps "high" → a clear fail still auto-revises."""
    r = _calibrate_and_route("high", 0.9, overall=40, threshold=75)
    assert r.path is Routing.AUTO_REVISE


@pytest.mark.unit
def test_boundary_hit_rate_keeps_high() -> None:
    """hit-rate == threshold (0.8) is NOT below it → confidence stays "high"."""
    r = _calibrate_and_route("high", 0.8, overall=40, threshold=75)
    assert r.confidence == "high"
    assert r.path is Routing.AUTO_REVISE


@pytest.mark.unit
def test_low_reported_confidence_never_upgraded_and_routes_human() -> None:
    """A "low" report is never upgraded even with a perfect hit-rate → human."""
    r = _calibrate_and_route("low", 0.99, overall=40, threshold=75)
    assert r.confidence == "low"
    assert r.path is Routing.HUMAN_REVIEW


@pytest.mark.unit
def test_calibration_preserves_clear_pass() -> None:
    """A clear pass stays a pass regardless of any confidence downgrade."""
    r = _calibrate_and_route(
        "high",
        0.6,  # downgraded to "mid"
        overall=82,
        threshold=75,
        floors={"情感落地": (22, 20)},
    )
    assert r.path is Routing.PASS


@pytest.mark.unit
def test_calibration_preserves_borderline_human() -> None:
    """A borderline score (within ±5) routes to human regardless of confidence."""
    r = _calibrate_and_route(
        "high",
        0.9,  # stays "high", but the score is borderline
        overall=73,
        threshold=75,
    )
    assert r.path is Routing.HUMAN_REVIEW
    assert r.near_threshold is True


# --- interaction with the revision cap --------------------------------------


@pytest.mark.unit
def test_overconfident_scorer_plus_cap_both_route_human() -> None:
    """Downgraded confidence AND a spent cap both independently force human."""
    # mid confidence alone (under cap) already forces human
    under_cap = _calibrate_and_route("high", 0.6, overall=40, prior_revisions=0)
    assert under_cap.path is Routing.HUMAN_REVIEW

    # at the cap the (high) scorer would also escalate; mid confidence still human
    at_cap = _calibrate_and_route("high", 0.6, overall=40, prior_revisions=2)
    assert at_cap.path is Routing.HUMAN_REVIEW


@pytest.mark.unit
def test_floor_breach_with_overconfident_scorer_routes_human() -> None:
    """Overall well above threshold but a floor breached + mid confidence → human.

    Not a pass (floor breached), not borderline (overall far above), confidence
    calibrated to "mid" → human review rather than auto-revise.
    """
    r = _calibrate_and_route(
        "high",
        0.6,  # downgraded to "mid"
        overall=90,
        threshold=75,
        floors={"情感落地": (18, 20)},  # floor breached
    )
    assert r.path is Routing.HUMAN_REVIEW
    assert r.floor_ok is False


# --- end-to-end CLI chain ----------------------------------------------------


@pytest.mark.unit
def test_full_chain_via_both_clis(capsys, monkeypatch) -> None:
    """Calibration CLI → routing CLI composition reproduces the API-level chain."""
    from shenbi.skill_utils.calibration.confidence import main as cal_main
    from shenbi.skill_utils.review_resonance import main as route_main

    # 1) calibrate: reported high, hit-rate 0.6 → "mid"
    monkeypatch.setattr(
        "sys.argv",
        ["confidence", "--reported", "high", "--high-confidence", "0.6"],
    )
    cal_main()
    import json

    cal_out = json.loads(capsys.readouterr().out)
    assert cal_out["calibrated"] == "mid"
    assert cal_out["downgraded"] is True

    # 2) feed the calibrated level into routing for a clear-fail block
    monkeypatch.setattr(
        "sys.argv",
        [
            "routing",
            "--overall",
            "40",
            "--threshold",
            "75",
            "--confidence",
            cal_out["calibrated"],
            "--prior-revisions",
            "0",
        ],
    )
    route_main()
    route_out = json.loads(capsys.readouterr().out)
    assert route_out["confidence"] == "mid"
    assert route_out["path"] == "human_review"
