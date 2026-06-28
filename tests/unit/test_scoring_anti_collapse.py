"""Unit tests for scoring.py anti-collapse extensions (spec §5.5)."""

from __future__ import annotations

import pytest

from shenbi.scoring import check_scorer_agreement, flag_score_collapse


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
