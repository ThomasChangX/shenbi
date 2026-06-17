"""Unit tests for skill_utils/chapter_pattern/compute_pattern.py."""

from __future__ import annotations

import pytest

from shenbi.skill_utils.chapter_pattern.compute_pattern import (
    PATTERNS,
    check_distribution,
    classify_entropy,
    compute_consecutive,
    compute_entropy,
    compute_transition_matrix,
)


@pytest.mark.unit
def test_compute_consecutive_returns_zero_for_empty() -> None:
    result = compute_consecutive([])
    for pattern in PATTERNS:
        assert result[pattern] == 0


@pytest.mark.unit
def test_compute_consecutive_detects_single_run() -> None:
    result = compute_consecutive(["引入", "引入", "引入", "转折"])
    assert result["引入"] == 3
    assert result["转折"] == 1


@pytest.mark.unit
def test_compute_consecutive_resets_max_run_on_pattern_change() -> None:
    """When a pattern repeats, breaks, then repeats, compute_consecutive
    keeps the longest run length per pattern (not the total count).
    """
    result = compute_consecutive(["引入", "引入", "转折", "引入"])
    assert result["引入"] == 2  # longest run of 引入 is 2, not 3
    assert result["转折"] == 1


@pytest.mark.unit
def test_compute_consecutive_handles_single_pattern() -> None:
    result = compute_consecutive(["引入"])
    assert result["引入"] == 1


@pytest.mark.unit
def test_compute_entropy_is_zero_for_single_repeated_pattern() -> None:
    entropy, _ = compute_entropy(["引入"] * 10)
    assert entropy == pytest.approx(0.0, abs=0.01)


@pytest.mark.unit
def test_compute_entropy_is_high_for_uniform_distribution() -> None:
    entropy, _ = compute_entropy(list(PATTERNS))
    assert entropy > 2.0  # near-max entropy for 13 patterns


@pytest.mark.unit
def test_compute_entropy_distribution_freqs_sum_to_one() -> None:
    _, dist = compute_entropy(["引入", "转折", "引入"])
    total = sum(d["frequency"] for d in dist if d["count"] > 0)
    assert total == pytest.approx(1.0, abs=0.01)


@pytest.mark.unit
def test_classify_entropy_returns_excellent_for_high_entropy() -> None:
    label, _ = classify_entropy(2.6)
    assert label == "优秀"


@pytest.mark.unit
def test_classify_entropy_returns_severe_for_low_entropy() -> None:
    label, _ = classify_entropy(0.5)
    assert label == "严重单调"


@pytest.mark.unit
def test_classify_entropy_returns_healthy_for_mid_range() -> None:
    label, _ = classify_entropy(2.1)
    assert label == "健康"


@pytest.mark.unit
def test_check_distribution_returns_none_when_patterns_below_window() -> None:
    """Fewer patterns than recent_n -> returns None."""
    result = check_distribution(["引入", "转折"], recent_n=5)
    assert result is None


@pytest.mark.unit
def test_check_distribution_returns_pass_when_unique_meets_required() -> None:
    """Sufficient unique patterns in window -> pass=True."""
    patterns = ["引入", "升级", "转折", "揭示", "决战"]
    result = check_distribution(patterns, recent_n=5)
    assert result is not None
    assert result["unique_patterns"] >= result["required"]
    assert result["pass"] is True


@pytest.mark.unit
def test_compute_transition_matrix_returns_list_of_row_dicts() -> None:
    """compute_transition_matrix returns list[dict] keyed by 'from'/'to'."""
    patterns = ["引入", "升级", "转折", "升级"]
    matrix = compute_transition_matrix(patterns)
    assert isinstance(matrix, list)
    assert len(matrix) == len(PATTERNS)
    assert all("from" in row and "to" in row for row in matrix)


@pytest.mark.unit
def test_compute_transition_matrix_handles_empty() -> None:
    matrix = compute_transition_matrix([])
    assert isinstance(matrix, list)
    assert len(matrix) == len(PATTERNS)


@pytest.mark.unit
def test_compute_entropy_handles_empty_input() -> None:
    entropy, dist = compute_entropy([])
    assert entropy == 0.0
    assert dist == []


@pytest.mark.unit
def test_patterns_constant_has_13_entries() -> None:
    """Spec: 13 narrative patterns."""
    assert len(PATTERNS) == 13


# ---------------------------------------------------------------------------
# Error-path / boundary tests (PR-52 Step 13)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_compute_entropy_single_element_list_is_zero() -> None:
    """A single-pattern list (one chapter) has zero entropy."""
    entropy, terms = compute_entropy(["引入"])
    assert entropy == 0.0
    assert terms  # still returns per-pattern terms


@pytest.mark.unit
def test_compute_consecutive_all_unique_patterns_yields_all_ones() -> None:
    """All-unique patterns -> every pattern's max run is 0 except those present (run 1)."""
    result = compute_consecutive(["引入", "升级", "转折", "决战"])
    assert result["引入"] == 1
    assert result["升级"] == 1
    assert result["转折"] == 1
    assert result["决战"] == 1
    # Patterns never appearing have max run 0.
    assert result["日常"] == 0


@pytest.mark.unit
def test_check_distribution_sparse_patterns_flagged() -> None:
    """A window whose unique-pattern count is below required -> pass=False."""
    # 5-chapter window, required for window 5 is 3 unique patterns.
    patterns = ["引入", "引入", "引入", "引入", "引入"]  # only 1 unique
    result = check_distribution(patterns, recent_n=5)
    assert result is not None
    assert result["unique_patterns"] == 1
    assert result["required"] == 3
    assert result["pass"] is False


@pytest.mark.unit
def test_compute_transition_matrix_single_element_has_no_transitions() -> None:
    """A single-element list has no transitions -> all 'to' counts are 0."""
    matrix = compute_transition_matrix(["引入"])
    assert isinstance(matrix, list)
    assert len(matrix) == len(PATTERNS)
    yinru_row = next(r for r in matrix if r["from"] == "引入")
    assert sum(yinru_row["to"].values()) == 0


@pytest.mark.unit
def test_classify_entropy_boundary_values() -> None:
    """Thresholds are exclusive on the upper bound: classify returns the
    lower bracket at an exact boundary value.

    h > 2.5 -> 优秀; at h==2.5 it is 健康 (2.5 not > 2.5).
    """
    assert classify_entropy(2.6)[0] == "优秀"
    assert classify_entropy(2.5)[0] == "健康"  # boundary falls through
    assert classify_entropy(2.0)[0] == "轻度单调"  # 2.0 not > 2.0
    assert classify_entropy(1.5)[0] == "中度单调"  # 1.5 not > 1.5
    assert classify_entropy(1.0)[0] == "严重单调"  # 1.0 not > 1.0
    assert classify_entropy(0.5)[0] == "严重单调"

@pytest.mark.unit
def test_check_consecutive_equal_threshold_med_warning() -> None:
    """check_consecutive_warnings: max_run == threshold -> 'med' level warning."""
    from shenbi.skill_utils.chapter_pattern.compute_pattern import check_consecutive_warnings
    consecutive = {"决战": 2, "日常": 1}  # MAX_CONSECUTIVE for "决战" is 2
    warnings = check_consecutive_warnings(consecutive)
    assert any(w["level"] == "med" for w in warnings)

@pytest.mark.unit
def test_classify_entropy_zero_falls_through() -> None:
    """classify_entropy(0) falls through all thresholds -> '严重单调'."""
    from shenbi.skill_utils.chapter_pattern.compute_pattern import classify_entropy
    label, _ = classify_entropy(0.0)
    assert label == "严重单调"

@pytest.mark.unit
def test_check_consecutive_above_threshold_high_warning() -> None:
    """check_consecutive_warnings: max_run > threshold -> 'high' level."""
    from shenbi.skill_utils.chapter_pattern.compute_pattern import check_consecutive_warnings
    consecutive = {"决战": 3}  # MAX_CONSECUTIVE for "决战" is 2, so 3 > 2
    warnings = check_consecutive_warnings(consecutive)
    assert any(w["level"] == "high" for w in warnings)
