"""Unit tests for skill_utils/review_resonance/routing.py (spec §5.4 三路径分流)."""

from __future__ import annotations

import json

import pytest

from shenbi.skill_utils.review_resonance import (
    MAX_AUTO_REVISIONS,
    Routing,
    main,
    route_block,
)

# --- brief contract tests (verbatim) -----------------------------------------


@pytest.mark.unit
def test_clear_pass_when_above_threshold() -> None:
    r = route_block(
        overall=82,
        threshold=75,
        floors={"情感落地": (22, 20)},
        confidence="high",
        prior_revisions=0,
    )
    assert r.path is Routing.PASS


@pytest.mark.unit
def test_clear_fail_auto_revise() -> None:
    r = route_block(overall=40, threshold=75, floors={}, confidence="high", prior_revisions=0)
    assert r.path is Routing.AUTO_REVISE


@pytest.mark.unit
def test_borderline_goes_to_human() -> None:
    r = route_block(
        overall=73, threshold=75, floors={}, confidence="high", prior_revisions=0
    )  # within ±5
    assert r.path is Routing.HUMAN_REVIEW


@pytest.mark.unit
def test_low_confidence_goes_to_human() -> None:
    r = route_block(overall=40, threshold=75, floors={}, confidence="low", prior_revisions=0)
    assert r.path is Routing.HUMAN_REVIEW


@pytest.mark.unit
def test_third_clear_fail_escalates_to_human() -> None:
    r = route_block(overall=40, threshold=75, floors={}, confidence="high", prior_revisions=2)
    assert r.path is Routing.HUMAN_REVIEW  # cap reached, no more auto-revise


# --- edge cases & boundary conditions ----------------------------------------


@pytest.mark.unit
def test_floor_violation_routes_to_next_path_even_when_overall_passes() -> None:
    """Overall well above threshold but a dimension floor is breached -> not PASS.

    overall 90 is far above threshold 75 (not borderline), yet score 18 < floor 20
    blocks the clear pass. High confidence, under cap -> AUTO_REVISE.
    """
    r = route_block(
        overall=90,
        threshold=75,
        floors={"情感落地": (18, 20)},
        confidence="high",
        prior_revisions=0,
    )
    assert r.path is Routing.AUTO_REVISE
    assert r.floor_ok is False


@pytest.mark.unit
def test_floor_exactly_at_threshold_passes() -> None:
    """Score == floor is a valid pass (>= is inclusive)."""
    r = route_block(
        overall=82,
        threshold=75,
        floors={"情感落地": (20, 20)},
        confidence="high",
        prior_revisions=0,
    )
    assert r.path is Routing.PASS


@pytest.mark.unit
def test_borderline_upper_edge_is_five_below() -> None:
    """abs(overall - threshold) == 5 is the inclusive edge of 'near'."""
    r = route_block(overall=70, threshold=75, floors={}, confidence="high", prior_revisions=0)
    assert r.path is Routing.HUMAN_REVIEW
    assert r.near_threshold is True


@pytest.mark.unit
def test_borderline_above_threshold_but_near_still_human() -> None:
    """Slightly above threshold (within 5) but with a floor breach -> human.

    It cannot PASS (floor breached) and overall is within ±5 -> HUMAN_REVIEW.
    """
    r = route_block(
        overall=77,
        threshold=75,
        floors={"情感落地": (18, 20)},
        confidence="high",
        prior_revisions=0,
    )
    assert r.path is Routing.HUMAN_REVIEW


@pytest.mark.unit
def test_second_auto_revise_still_allowed() -> None:
    """prior_revisions == 1 is under the cap of 2 -> still AUTO_REVISE."""
    r = route_block(overall=40, threshold=75, floors={}, confidence="high", prior_revisions=1)
    assert r.path is Routing.AUTO_REVISE


@pytest.mark.unit
def test_cap_boundary_is_two() -> None:
    """prior_revisions == MAX_AUTO_REVISIONS (2) escalates; 1 does not."""
    assert (
        route_block(
            overall=40,
            threshold=75,
            floors={},
            confidence="high",
            prior_revisions=MAX_AUTO_REVISIONS,
        ).path
        is Routing.HUMAN_REVIEW
    )
    assert (
        route_block(
            overall=40,
            threshold=75,
            floors={},
            confidence="high",
            prior_revisions=MAX_AUTO_REVISIONS - 1,
        ).path
        is Routing.AUTO_REVISE
    )


@pytest.mark.unit
def test_low_confidence_escalates_to_human_even_under_cap() -> None:
    """Low confidence always wins -> human, independent of the revision cap."""
    r = route_block(overall=40, threshold=75, floors={}, confidence="low", prior_revisions=5)
    assert r.path is Routing.HUMAN_REVIEW


@pytest.mark.unit
def test_routing_values_are_strenum_strings() -> None:
    assert Routing.PASS == "pass"
    assert Routing.AUTO_REVISE == "auto_revise"
    assert Routing.HUMAN_REVIEW == "human_review"


@pytest.mark.unit
def test_revision_loop_is_frozen() -> None:
    import dataclasses

    r = route_block(overall=40, threshold=75, floors={}, confidence="high", prior_revisions=0)
    with pytest.raises(dataclasses.FrozenInstanceError):
        r.path = Routing.PASS  # type: ignore[misc]


# --- CLI ---------------------------------------------------------------------


@pytest.mark.unit
def test_main_cli_outputs_json(capsys, monkeypatch) -> None:
    monkeypatch.setattr(
        "sys.argv",
        [
            "routing.py",
            "--overall",
            "40",
            "--threshold",
            "75",
            "--confidence",
            "high",
            "--prior-revisions",
            "0",
        ],
    )
    main()
    out = json.loads(capsys.readouterr().out)
    assert out["path"] == "auto_revise"
    assert out["overall"] == 40
    assert out["threshold"] == 75
    assert out["floor_ok"] is True
