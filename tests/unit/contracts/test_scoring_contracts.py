from __future__ import annotations

import pytest
from pydantic import ValidationError

from shenbi.contracts.registry import REGISTRY
from shenbi.contracts.skills._scoring_base import (
    AGGREGATION_FORMULA,
    ROUTE_A_WEIGHT,
    ROUTE_C_SOFT_WEIGHT,
    ScoreReport,
)
from shenbi.contracts.thresholds import T1_PASS as TIER_ADVANCE_THRESHOLD
from shenbi.contracts.thresholds import TEST_PASS as PASS_THRESHOLD


def test_thresholds_explicit() -> None:
    assert PASS_THRESHOLD == 90
    assert TIER_ADVANCE_THRESHOLD == 94
    assert ROUTE_C_SOFT_WEIGHT == 0.6
    assert ROUTE_A_WEIGHT == 0.4


def test_aggregation_formula_declared() -> None:
    assert "final_score" in AGGREGATION_FORMULA
    assert "ROUTE_C_SOFT_WEIGHT" in AGGREGATION_FORMULA


def test_hard_binary_fail_blocks_pass() -> None:
    r = ScoreReport(
        route_c_hard_binary_pass=2,
        route_c_hard_binary_total=3,
        route_c_soft_score=95.0,
        route_a_score=90.0,
    )
    # hard_binary failure is an audit flag; does NOT zero final_score (Parfit round-1)
    assert r.hard_binary_gate_failed is True
    assert r.final_score > 0.0  # weighted average, not zeroed
    assert r.passed is False


def test_all_pass_perfect_score() -> None:
    r = ScoreReport(
        route_c_hard_binary_pass=3,
        route_c_hard_binary_total=3,
        route_c_soft_score=100.0,
        route_a_score=100.0,
    )
    assert r.hard_binary_gate_failed is False
    assert r.final_score == 100.0
    assert r.passed is True
    assert r.tier_advance_eligible is True


def test_boundary_exactly_90_passes() -> None:
    r = ScoreReport(
        route_c_hard_binary_pass=1,
        route_c_hard_binary_total=1,
        route_c_soft_score=100.0,
        route_a_score=75.0,
    )
    assert r.final_score == 90.0
    assert r.passed is True


def test_just_below_90_fails() -> None:
    r = ScoreReport(
        route_c_hard_binary_pass=1,
        route_c_hard_binary_total=1,
        route_c_soft_score=90.0,
        route_a_score=74.0,
    )
    assert r.final_score < PASS_THRESHOLD
    assert r.passed is False


def test_computed_fields_in_model_dump() -> None:
    r = ScoreReport(
        route_c_hard_binary_pass=1,
        route_c_hard_binary_total=1,
        route_c_soft_score=90.0,
        route_a_score=90.0,
    )
    dump = r.model_dump()
    assert "final_score" in dump
    assert "passed" in dump
    assert "tier_advance_eligible" in dump


def test_rejects_pass_exceeds_total() -> None:
    with pytest.raises(ValidationError):
        ScoreReport(
            route_c_hard_binary_pass=5,
            route_c_hard_binary_total=3,
            route_c_soft_score=90.0,
            route_a_score=90.0,
        )


def test_registry_includes_scoring_skills() -> None:
    assert "shenbi-score-arc" in REGISTRY
    assert "shenbi-score-stratum" in REGISTRY
    assert "shenbi-score-volume" in REGISTRY
