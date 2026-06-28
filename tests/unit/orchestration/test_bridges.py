"""Tests for orchestration bridges (spec §6.3, §5.5)."""
import pytest
from pathlib import Path
from shenbi.orchestration.escalation_bridge import parse_resonance_scores
from shenbi.orchestration.scoring_bridge import validate_dual_scorer, check_single_scorer_collapse


@pytest.mark.unit
def test_parse_resonance_scores_extracts_overall():
    import tempfile, os
    content = "| chapter | role | a | b | c | d | overall | conf |\n| N | x | 22 | 20 | 22 | 18 | 82 | high |\n| M | y | 20 | 18 | 20 | 16 | 74 | mid |"
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as f:
        f.write(content)
        f.flush()
        scores = parse_resonance_scores(Path(f.name))
    os.unlink(f.name)
    assert scores == [82.0, 74.0]


@pytest.mark.unit
def test_validate_dual_scorer_flags_dispute():
    a = {1: 90, 2: 95}
    b = {1: 85, 2: 70}
    result = validate_dual_scorer(a, b, threshold=5.0)
    assert result["needs_arbitration"] is True


@pytest.mark.unit
def test_check_single_scorer_collapse_detects_all_95():
    scores = {1: 95, 2: 95, 3: 95}
    result = check_single_scorer_collapse(scores)
    assert result["collapse_suspected"] is True
