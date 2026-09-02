"""Tests for orchestration bridges (spec §6.3, §5.5)."""

from pathlib import Path

import pytest

from shenbi.orchestration.escalation_bridge import parse_resonance_scores
from shenbi.orchestration.scoring_bridge import check_single_scorer_collapse, validate_dual_scorer


@pytest.mark.unit
def test_parse_resonance_scores_extracts_overall():
    import os
    import tempfile

    content = "| chapter | role | a | b | c | d | overall | conf |\n| N | x | 22 | 20 | 22 | 18 | 82 | high |\n| M | y | 20 | 18 | 20 | 16 | 74 | mid |"
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
        f.write(content)
        f.flush()
        scores = parse_resonance_scores(Path(f.name))
    os.unlink(f.name)
    assert scores == [82.0, 74.0]


@pytest.mark.unit
def test_validate_dual_scorer_flags_dispute():
    a = {1: 90.0, 2: 95.0}
    b = {1: 85.0, 2: 70.0}
    result = validate_dual_scorer(a, b, threshold=5.0)
    assert result["needs_arbitration"] is True


@pytest.mark.unit
def test_check_single_scorer_collapse_detects_all_95():
    scores = {1: 95.0, 2: 95.0, 3: 95.0}
    result = check_single_scorer_collapse(scores)
    assert result["collapse_suspected"] is True


@pytest.mark.c13_regression
def test_zero_score_row_retained(tmp_path) -> None:
    """F513: a 0 overall score row must be parsed, not dropped."""
    from shenbi.orchestration.escalation_bridge import parse_resonance_scores

    trend = tmp_path / "trend.md"
    trend.write_text(
        """| 章 | 覆盖 | 深度 | 节奏 | 共鸣 | 张力 | 总分 |
|---|---|---|---|---|---|---|
| 1 | 80 | 75 | 70 | 82 | 79 | 78 |
| 2 | 60 | 55 | 58 | 62 | 59 | 0 |
""",
        encoding="utf-8",
    )
    scores = parse_resonance_scores(trend)
    assert 0.0 in scores and len(scores) == 2


@pytest.mark.c13_regression
def test_volume_objective_unknown_skips_not_signals_nor_default_met() -> None:
    """F381: None (unknown) must be an explicit SKIP — neither the old
    default-met silence nor a missed signal.
    """
    from structlog.testing import capture_logs

    from shenbi.skill_utils.escalation.check import check_escalation

    with capture_logs() as logs:
        signals = check_escalation(
            resonance_scores=[80.0, 79.0],
            sensitivity_blocking=False,
            volume_objective_met=None,
            regeneration_attempts=0,
        )
    assert not any(s.trigger == "volume_objective_missed" for s in signals)
    assert any(
        e.get("event") == "volume_objective_unknown_skip"
        for e in logs
        if e.get("log_level") == "warning"
    )
    # False still fires the signal
    signals = check_escalation(
        resonance_scores=[80.0, 79.0],
        sensitivity_blocking=False,
        volume_objective_met=False,
        regeneration_attempts=0,
    )
    assert any(s.trigger == "volume_objective_missed" for s in signals)
