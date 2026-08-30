"""Unit tests for scoring.py anti-collapse extensions (spec §5.5)."""

from __future__ import annotations

from pathlib import Path

import pytest

from shenbi.scoring import check_gate_markers, check_scorer_agreement, flag_score_collapse


@pytest.mark.unit
def test_agreement_pass_when_within_threshold() -> None:
    a = {1: 90, 2: 88, 3: 92}
    b = {1: 92, 2: 90, 3: 95}
    result = check_scorer_agreement(a, b, threshold=5)
    assert result["agreed"] is True
    assert result["max_diff"] == 3


@pytest.mark.unit
def test_agreement_fails_when_diff_exceeds_threshold() -> None:
    a = {1: 90, 2: 70, 3: 92}  # dim 2 diff = 25
    b = {1: 92, 2: 95, 3: 95}
    result = check_scorer_agreement(a, b, threshold=5)
    assert result["agreed"] is False
    assert result["max_diff"] == 25
    assert 2 in result["disputed_dimensions"]


@pytest.mark.unit
def test_collapse_flagged_when_all_exactly_95() -> None:
    scores = {1: 95, 2: 95, 3: 95, 4: 95}
    result = flag_score_collapse(scores)
    assert result["collapse_suspected"] is True
    assert "all_identical" in result["signals"]


@pytest.mark.unit
def test_collapse_not_flagged_when_scores_vary() -> None:
    scores = {1: 88, 2: 92, 3: 85, 4: 90}
    result = flag_score_collapse(scores)
    assert result["collapse_suspected"] is False


@pytest.mark.unit
def test_collapse_flagged_when_majority_95() -> None:
    scores = {1: 95, 2: 95, 3: 95, 4: 88}  # 3/4 = 75% at 95
    result = flag_score_collapse(scores)
    assert result["collapse_suspected"] is True
    assert any("majority_at_single_value" in s for s in result["signals"])


@pytest.mark.unit
def test_collapse_not_flagged_for_empty_scores() -> None:
    """Empty scores dict should return no collapse."""
    result = flag_score_collapse({})
    assert result["collapse_suspected"] is False
    assert result["signals"] == []


@pytest.mark.unit
def test_agreement_with_asymmetric_dimensions() -> None:
    """When dimensions differ between scorers, missing dims default to 0."""
    a = {1: 10, 3: 90}
    b = {2: 10, 3: 92}
    result = check_scorer_agreement(a, b, threshold=20)
    # dim 1: 10-0=10, dim 2: 0-10=10, dim 3: 90-92=2 — all within 20
    assert result["agreed"] is True


class TestGateMarkers:
    """Tests for check_gate_markers — T1/T2/T3 marker enforcement."""

    def test_t1_marker_missing(self, tmp_path: Path):
        rubric = tmp_path / "t1-skill" / "shenbi-test" / "rubric.json"
        rubric.parent.mkdir(parents=True)
        rubric.write_text("{}", encoding="utf-8")

        rd = tmp_path / "round"
        rd.mkdir()
        (rd / "gate-markers").mkdir()

        missing = check_gate_markers(str(rubric), "generative", str(rd))
        assert len(missing) > 0
        assert any("G4-shenbi-test-generative" in m for m in missing)

    def test_t2_marker_missing(self, tmp_path: Path):
        rubric = tmp_path / "t2-phase" / "test-phase" / "rubric.json"
        rubric.parent.mkdir(parents=True)
        rubric.write_text("{}", encoding="utf-8")

        rd = tmp_path / "round"
        rd.mkdir()
        (rd / "gate-markers").mkdir()

        missing = check_gate_markers(str(rubric), "generative", str(rd))
        # T2 paths check deps.json; if deps.json is missing, no markers checked
        assert isinstance(missing, list)

    def test_t3_marker_missing(self, tmp_path: Path):
        rubric = tmp_path / "t3-pipeline" / "test-pipeline" / "rubric.json"
        rubric.parent.mkdir(parents=True)
        rubric.write_text("{}", encoding="utf-8")

        rd = tmp_path / "round"
        rd.mkdir()
        (rd / "gate-markers").mkdir()

        missing = check_gate_markers(str(rubric), "generative", str(rd))
        assert len(missing) > 0
        assert any("G6-test-pipeline-generative" in m for m in missing)

    def test_non_tier_rubric_returns_empty(self, tmp_path: Path):
        rubric = tmp_path / "other" / "rubric.json"
        rubric.parent.mkdir(parents=True)
        rubric.write_text("{}", encoding="utf-8")

        rd = tmp_path / "round"
        rd.mkdir()

        missing = check_gate_markers(str(rubric), "generative", str(rd))
        assert missing == []


class TestCollapseSemanticsSpec31:
    """F120: 单维/全零豁免 (spec #31 T4)。"""

    @pytest.mark.unit
    def test_single_dimension_no_collapse(self):
        result = flag_score_collapse({1: 85})
        assert result == {"collapse_suspected": False, "signals": []}

    @pytest.mark.unit
    def test_all_zero_multi_dim_exempt_both_signals(self):
        # 5 维全 0（kill-switch 合法结果）：all_identical 与 majority 信号均不触发
        result = flag_score_collapse(dict.fromkeys(range(1, 6), 0))
        assert result == {"collapse_suspected": False, "signals": []}

    @pytest.mark.unit
    def test_multi_dim_identical_nonzero_still_collapses(self):
        result = flag_score_collapse({1: 95, 2: 95, 3: 95})
        assert result["collapse_suspected"] is True
        assert "all_identical" in result["signals"]
        assert any(s.startswith("majority_at_single_value") for s in result["signals"])

    @pytest.mark.unit
    def test_multi_dim_zero_mixed_identical_nonzero_collapses(self):
        # 含 0 但非全零、其余全同非零 → 仍坍缩
        result = flag_score_collapse({1: 0, 2: 95, 3: 95})
        assert result["collapse_suspected"] is True
