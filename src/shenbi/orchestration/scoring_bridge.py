"""Bridge: run dual-scorer agreement + collapse detection on scoring results."""
from __future__ import annotations

from shenbi.scoring import check_scorer_agreement, flag_score_collapse


def validate_dual_scorer(scores_a: dict[int, float], scores_b: dict[int, float], threshold: float = 5.0) -> dict:
    """Run agreement check; return result with escalation flag if disputed."""
    result = check_scorer_agreement(scores_a, scores_b, threshold)
    return {
        **result,
        "needs_arbitration": not result["agreed"],
    }


def check_single_scorer_collapse(scores: dict[int, float]) -> dict:
    """Run collapse detection on a single scorer's output."""
    return flag_score_collapse(scores)
