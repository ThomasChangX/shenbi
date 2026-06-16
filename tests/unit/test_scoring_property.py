"""Property-based tests for shenbi.scoring using Hypothesis.

These tests verify invariants that must hold across the entire input domain,
not just hand-picked edge cases. They complement the unit tests in
test_scoring.py by exploring the input space automatically.
"""

from __future__ import annotations

from typing import Any

from hypothesis import given
from hypothesis import strategies as st

from shenbi.scoring import Dimension, classify, compute_score, validate_scores

# --- classify invariants -------------------------------------------------


@given(st.integers(min_value=0, max_value=100))
def test_classify_always_returns_one_of_four_labels(score: int) -> None:
    label = classify(score)
    assert label in {"PASS (excellent)", "PASS (acceptable)", "CONDITIONAL", "FAIL"}


@given(st.integers(min_value=90, max_value=100))
def test_classify_returns_excellent_at_or_above_90(score: int) -> None:
    assert classify(score) == "PASS (excellent)"


@given(st.integers(min_value=75, max_value=89))
def test_classify_returns_acceptable_between_75_and_89(score: int) -> None:
    assert classify(score) == "PASS (acceptable)"


@given(st.integers(min_value=60, max_value=74))
def test_classify_returns_conditional_between_60_and_74(score: int) -> None:
    assert classify(score) == "CONDITIONAL"


@given(st.integers(min_value=0, max_value=59))
def test_classify_returns_fail_below_60(score: int) -> None:
    assert classify(score) == "FAIL"


# --- compute_score invariants -------------------------------------------


def _dimensions_strategy(
    min_size: int = 1, max_size: int = 5
) -> st.SearchStrategy[list[Dimension]]:
    """Build dimensions with weights 1..100 — guaranteed non-zero so
    compute_score doesn't short-circuit on total_weight=0.
    """
    return st.lists(
        st.builds(
            Dimension,
            num=st.integers(min_value=1, max_value=10),
            name=st.text(min_size=1, max_size=5),
            weight=st.integers(min_value=1, max_value=100),
        ),
        min_size=min_size,
        max_size=max_size,
        unique_by=lambda d: d["num"],
    )


@given(
    dims=_dimensions_strategy(),
    scores=st.dictionaries(
        keys=st.integers(min_value=1, max_value=10),
        values=st.integers(min_value=0, max_value=100),
        min_size=1,
    ),
)
def test_compute_score_is_always_in_zero_to_one_hundred(
    dims: list[Dimension], scores: dict[int, Any]
) -> None:
    """Weighted average of in-range values stays in range regardless of
    weight distribution or which dimensions are missing scores.
    """
    score = compute_score(dims, scores)
    assert 0 <= score <= 100


@given(
    dims=_dimensions_strategy(),
    scores=st.dictionaries(
        keys=st.integers(min_value=1, max_value=10),
        values=st.integers(min_value=0, max_value=100),
    ),
)
def test_kill_switch_always_returns_zero(dims: list[Dimension], scores: dict[int, Any]) -> None:
    assert compute_score(dims, scores, kill_switch_triggered=True) == 0


@given(
    dims=st.lists(
        st.builds(
            Dimension,
            num=st.integers(min_value=1, max_value=10),
            name=st.just("x"),
            weight=st.integers(min_value=1, max_value=100),
        ),
        min_size=2,
        max_size=2,
        unique_by=lambda d: d["num"],
    ),
    value=st.integers(min_value=0, max_value=100),
)
def test_uniform_score_equals_that_score(dims: list[Dimension], value: int) -> None:
    """If every dimension gets the same score, the weighted average equals
    that score — regardless of how the weights split.
    """
    scores = {d["num"]: value for d in dims}
    assert compute_score(dims, scores) == float(value)


@given(
    dims=st.lists(
        st.builds(
            Dimension,
            num=st.integers(min_value=1, max_value=10),
            name=st.just("x"),
            weight=st.integers(min_value=1, max_value=100),
        ),
        min_size=1,
        max_size=4,
        unique_by=lambda d: d["num"],
    ),
)
def test_all_zero_scores_produces_zero(dims: list[Dimension]) -> None:
    scores = {d["num"]: 0 for d in dims}
    assert compute_score(dims, scores) == 0


@given(
    dims=st.lists(
        st.builds(
            Dimension,
            num=st.integers(min_value=1, max_value=10),
            name=st.just("x"),
            weight=st.integers(min_value=1, max_value=100),
        ),
        min_size=1,
        max_size=4,
        unique_by=lambda d: d["num"],
    ),
)
def test_all_perfect_scores_produces_one_hundred(dims: list[Dimension]) -> None:
    scores = {d["num"]: 100 for d in dims}
    assert compute_score(dims, scores) == 100


# --- validate_scores invariants -----------------------------------------


@given(
    dims=st.lists(
        st.builds(
            Dimension,
            num=st.integers(min_value=1, max_value=10),
            name=st.just("x"),
            weight=st.integers(min_value=1, max_value=100),
        ),
        min_size=1,
        max_size=4,
        unique_by=lambda d: d["num"],
    ),
)
def test_valid_complete_scores_validate_clean(dims: list[Dimension]) -> None:
    """When scores cover every dimension with values in range, validation
    succeeds with no errors.
    """
    scores = {d["num"]: 50 for d in dims}
    is_valid, errors = validate_scores(scores, dims)
    assert is_valid is True
    assert errors == []


@given(
    out_of_range=st.integers(min_value=101, max_value=1000),
)
def test_score_above_100_is_always_rejected(out_of_range: int) -> None:
    dims = [Dimension(num=1, name="x", weight=100)]
    is_valid, errors = validate_scores({1: out_of_range}, dims)
    assert is_valid is False
    assert any("out of range" in e for e in errors)


@given(
    below_floor=st.integers(min_value=-1000, max_value=-1),
)
def test_negative_score_is_always_rejected(below_floor: int) -> None:
    dims = [Dimension(num=1, name="x", weight=100)]
    is_valid, errors = validate_scores({1: below_floor}, dims)
    assert is_valid is False
    assert any("out of range" in e for e in errors)
