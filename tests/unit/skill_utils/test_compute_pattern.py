"""Unit tests for skill_utils/chapter_pattern/compute_pattern.py."""

from __future__ import annotations

import pytest

from shenbi.skill_utils.chapter_pattern.compute_pattern import (
    DEFAULT_MAX_CONSECUTIVE,
    PATTERNS,
    check_distribution,
    classify_entropy,
    compute_consecutive,
    compute_entropy,
    compute_transition_matrix,
)


@pytest.mark.unit
def test_compute_consecutive_returns_zero_for_empty() -> None:
    """F667: keys track the input set, so no input -> no vocab-padded rows."""
    result = compute_consecutive([])
    assert result == {}
    assert PATTERNS  # vocab still defined for other consumers


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
def test_compute_entropy_counts_out_of_vocab_labels() -> None:
    """F647 (spec #32): entropy must sum over ALL labels in the input
    (denominator is len(patterns)), not only in-vocab PATTERNS — out-of-vocab
    labels previously vanished from the sum, systematically underestimating H.
    """
    # 50/50 split between an in-vocab and an out-of-vocab label: H = 1.0 bit.
    entropy, terms = compute_entropy(["引入", "未分类"])
    assert entropy == pytest.approx(1.0, abs=1e-4)
    # The out-of-vocab label keeps its row in the per-pattern breakdown.
    assert any(t["pattern"] == "未分类" and t["count"] == 1 for t in terms)


@pytest.mark.unit
def test_compute_entropy_out_of_vocab_only_input_full_zero() -> None:
    """All-out-of-vocab input: single label -> H == 0, with the label present."""
    entropy, terms = compute_entropy(["未分类"] * 5)
    assert entropy == 0.0
    assert any(t["pattern"] == "未分类" and t["count"] == 5 for t in terms)


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
    # F667: absent patterns no longer get vocab-padded zero rows.
    assert "日常" not in result


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


@pytest.mark.unit
def test_main_with_stdin_json(monkeypatch: pytest.MonkeyPatch) -> None:
    """main() reads from stdin when argv[1] is '-'."""
    import io
    import json
    import sys

    from shenbi.skill_utils.chapter_pattern.compute_pattern import main

    data = json.dumps([{"num": 1, "pattern": "引入"}])
    monkeypatch.setattr(sys, "argv", ["compute_pattern.py", "-"])
    monkeypatch.setattr(sys, "stdin", io.StringIO(data))
    out = io.StringIO()
    monkeypatch.setattr(sys, "stdout", out)
    main()
    result = json.loads(out.getvalue())
    assert result["sample"]["chapters"] == 1


# --- spec #14 T3: F667 out-of-vocab patterns preserved ---


@pytest.mark.unit
def test_compute_consecutive_keys_equal_input_set() -> None:
    """F667: keys are exactly the patterns present, in sorted order."""
    result = compute_consecutive(["未分类", "未分类", "未分类", "未分类", "引入"])
    assert list(result) == sorted({"未分类", "引入"})
    assert result["未分类"] == 4


@pytest.mark.unit
def test_compute_consecutive_empty_returns_empty_dict() -> None:
    """F667: no vocab-padding of absent patterns (was: zero rows for all vocab)."""
    assert compute_consecutive([]) == {}


@pytest.mark.unit
def test_check_consecutive_warnings_covers_out_of_vocab() -> None:
    from shenbi.skill_utils.chapter_pattern.compute_pattern import (
        check_consecutive_warnings,
    )

    warnings = check_consecutive_warnings({"未分类": 4})
    assert warnings and warnings[0]["pattern"] == "未分类"
    assert warnings[0]["max_run"] == 4
    assert warnings[0]["threshold"] == DEFAULT_MAX_CONSECUTIVE


@pytest.mark.unit
def test_compute_transition_matrix_includes_out_of_vocab() -> None:
    """F667: 未分类 transitions appear (superset grid: vocab + input)."""
    rows = compute_transition_matrix(["引入", "未分类", "未分类"])
    sources = {r["from"] for r in rows}
    assert "未分类" in sources
    unc = next(r for r in rows if r["from"] == "未分类")
    assert unc["to"]["未分类"] == 1
    assert any(r["from"] == "引入" and r["to"]["未分类"] == 1 for r in rows)


@pytest.mark.unit
def test_main_max_consecutive_includes_out_of_vocab(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """F667: main() max_consecutive rows follow compute_consecutive keys."""
    import io
    import json
    import sys

    from shenbi.skill_utils.chapter_pattern.compute_pattern import main

    data = json.dumps([{"num": i, "pattern": "未分类"} for i in range(1, 5)])
    monkeypatch.setattr(sys, "argv", ["compute_pattern.py", "-"])
    monkeypatch.setattr(sys, "stdin", io.StringIO(data))
    out = io.StringIO()
    monkeypatch.setattr(sys, "stdout", out)
    main()
    result = json.loads(out.getvalue())
    assert result["max_consecutive"] == [{"pattern": "未分类", "max_run": 4}]
    assert any(
        w["pattern"] == "未分类" and w["max_run"] == 4 for w in result["consecutive_warnings"]
    )


@pytest.mark.unit
def test_compute_consecutive_empty_label_does_not_crash() -> None:
    """Stage-8 audit: falsy pattern labels never enter the run loop — no max() on empty."""
    result = compute_consecutive(["引入", "", "引入"])
    assert result == {"引入": 1}
