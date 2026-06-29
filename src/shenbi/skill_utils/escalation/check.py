r"""check.py — human-escalation trigger detection (spec §6.2-6.3).

Deterministic helper that evaluates escalation conditions for the
auto-approve system. When any condition fires, the orchestrator must
summon human review instead of continuing auto-batch. All triggers are
deterministic: linear-regression slope on raw scores, boolean audit
flags, integer loop counters.

Usage (CLI):
  python -m shenbi.skill_utils.escalation \\
      --resonance-scores 90,88,86,84,82 \\
      --sensitivity-blocking false \\
      --volume-objective-met true \\
      --regeneration-attempts 1
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass


@dataclass(frozen=True)
class EscalationSignal:
    trigger: str
    detail: str


def detect_score_decline(
    scores: list[float], window: int = 5, slope_threshold: float = -2.0
) -> bool:
    """Linear regression slope on last `window` overall scores.

    Returns True if the slope (points per chapter) is steeper downward
    than slope_threshold (i.e. slope < slope_threshold, both negative).
    Requires at least `window` samples; fewer -> no trigger.
    """
    recent = scores[-window:]
    if len(recent) < window:
        return False
    n = len(recent)
    x_mean = (n - 1) / 2  # x = 0,1,...,n-1
    y_mean = sum(recent) / n
    numerator = sum((i - x_mean) * (y - y_mean) for i, y in enumerate(recent))
    denominator = sum((i - x_mean) ** 2 for i in range(n))
    if denominator == 0:
        return False
    slope = numerator / denominator
    return slope < slope_threshold


def check_escalation(
    resonance_scores: list[float],
    sensitivity_blocking: bool,
    volume_objective_met: bool,
    regeneration_attempts: int,
    arc_score: float | None = None,
    stratum_axis_drift: bool = False,
    window: int = 5,
    slope_threshold: float = -2.0,
    regen_loop_limit: int = 3,
    arc_threshold: float = 70.0,
) -> list[EscalationSignal]:
    """Evaluate all escalation conditions (spec §6.2).

    Returns a list of fired EscalationSignals. Empty list = no escalation.
    """
    signals: list[EscalationSignal] = []

    if detect_score_decline(resonance_scores, window, slope_threshold):
        recent = resonance_scores[-window:]
        signals.append(
            EscalationSignal(
                trigger="score_decline",
                detail=f"linear regression slope on last {window} scores < {slope_threshold}: {recent}",
            )
        )

    if sensitivity_blocking:
        signals.append(
            EscalationSignal(
                trigger="sensitivity_blocking",
                detail="sensitivity audit reported BLOCKING severity",
            )
        )

    if not volume_objective_met:
        signals.append(
            EscalationSignal(
                trigger="volume_objective_missed",
                detail="volume Objective not achieved (score-volume binary check)",
            )
        )

    if regeneration_attempts >= regen_loop_limit:
        signals.append(
            EscalationSignal(
                trigger="regeneration_loop_exhausted",
                detail=f"same goal unmet after {regeneration_attempts} regeneration attempts (limit {regen_loop_limit})",
            )
        )

    if arc_score is not None and arc_score < arc_threshold:
        signals.append(
            EscalationSignal(
                trigger="arc_score_below_threshold",
                detail=f"arc score {arc_score} < {arc_threshold} (spec §6.2)",
            )
        )

    if stratum_axis_drift:
        signals.append(
            EscalationSignal(
                trigger="stratum_axis_drift",
                detail="protagonist arc drifted from declared ending (score-stratum detected, spec §6.2)",
            )
        )

    return signals


def main() -> None:
    """CLI: print escalation signals as JSON."""
    parser = argparse.ArgumentParser(
        prog="escalation", description="Detect human-escalation triggers (spec §6.2)."
    )
    parser.add_argument("--resonance-scores", required=True, help="Comma-separated overall scores.")
    parser.add_argument("--sensitivity-blocking", default="false", help="true/false.")
    parser.add_argument("--volume-objective-met", default="true", help="true/false.")
    parser.add_argument("--regeneration-attempts", type=int, default=0)
    parser.add_argument(
        "--arc-score", type=float, default=None, help="Latest arc score (spec §6.2 trigger)"
    )
    parser.add_argument(
        "--stratum-axis-drift", default="false", help="true/false (spec §6.2 trigger)"
    )
    args = parser.parse_args()

    scores = [float(x) for x in args.resonance_scores.split(",")]
    signals = check_escalation(
        resonance_scores=scores,
        sensitivity_blocking=args.sensitivity_blocking.lower() == "true",
        volume_objective_met=args.volume_objective_met.lower() == "true",
        regeneration_attempts=args.regeneration_attempts,
        arc_score=args.arc_score,
        stratum_axis_drift=args.stratum_axis_drift.lower() == "true",
    )
    print(
        json.dumps(
            [{"trigger": s.trigger, "detail": s.detail} for s in signals], ensure_ascii=False
        )
    )
