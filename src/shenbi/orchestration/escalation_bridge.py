"""Bridge: parse resonance_trend.md -> check_escalation params (spec §6.3)."""
from __future__ import annotations

import re
from pathlib import Path

from shenbi.skill_utils.escalation.check import check_escalation, EscalationSignal


def parse_resonance_scores(trend_path: Path) -> list[float]:
    """Extract overall scores from resonance_trend.md table rows."""
    content = trend_path.read_text(encoding="utf-8")
    scores: list[float] = []
    for line in content.split("\n"):
        if line.startswith("|") and "overall" not in line.lower():
            cells = [c.strip() for c in line.split("|")[1:-1]]
            if len(cells) >= 7:
                try:
                    val = float(cells[6])
                    if val > 0:
                        scores.append(val)
                except (ValueError, IndexError):
                    pass
    return scores


def run_escalation_check(
    resonance_trend_path: Path,
    sensitivity_blocking: bool = False,
    volume_objective_met: bool = True,
    regeneration_attempts: int = 0,
    arc_score: float | None = None,
    stratum_axis_drift: bool = False,
) -> list[EscalationSignal]:
    """Full bridge: read trend file, call check_escalation."""
    scores = parse_resonance_scores(resonance_trend_path)
    return check_escalation(
        resonance_scores=scores,
        sensitivity_blocking=sensitivity_blocking,
        volume_objective_met=volume_objective_met,
        regeneration_attempts=regeneration_attempts,
        arc_score=arc_score,
        stratum_axis_drift=stratum_axis_drift,
    )
