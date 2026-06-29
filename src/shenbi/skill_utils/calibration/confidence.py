"""confidence.py — confidence calibration by anchor hit-rate (spec §8.2 置信度校准).

LLM scorers systematically over-report their own confidence. This helper
downgrades a reported "high" confidence to "mid" when the scorer's anchor
hit-rate — the fraction of high-confidence anchor judgments that were actually
correct — falls below the calibration threshold. It never upgrades a low
confidence. The calibrated level then feeds the §5.4 三路径分流 so that an
overconfident-but-inaccurate scorer is routed to human review instead of the
automatic revision loop.

Usage (CLI):
  python -m shenbi.skill_utils.calibration --high-confidence 0.6 --threshold 0.8 --reported high
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass


@dataclass(frozen=True)
class HitRate:
    high_confidence: float  # fraction of high-confidence anchor judgments that were correct
    threshold: float = 0.8


def calibrate_confidence(reported: str, hr: HitRate) -> str:
    """LLM scorers are overconfident. Downgrade 'high' -> 'mid' when anchor
    hit-rate < threshold. Never upgrade. (spec §8.2 置信度校准)
    """
    if reported == "high" and hr.high_confidence < hr.threshold:
        return "mid"
    return reported


def main() -> None:
    """CLI: print the calibrated confidence level as JSON."""
    parser = argparse.ArgumentParser(
        prog="confidence",
        description="Calibrate a scorer's reported confidence by anchor hit-rate (spec §8.2).",
    )
    parser.add_argument(
        "--reported",
        required=True,
        help="Reported confidence level (high/mid/low).",
    )
    parser.add_argument(
        "--high-confidence",
        type=float,
        required=True,
        help="Fraction of high-confidence anchor judgments that were correct.",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.8,
        help="Hit-rate below which a 'high' report is downgraded to 'mid' (default 0.8).",
    )
    args = parser.parse_args()

    calibrated = calibrate_confidence(
        args.reported,
        HitRate(high_confidence=args.high_confidence, threshold=args.threshold),
    )
    output = {
        "reported": args.reported,
        "high_confidence": args.high_confidence,
        "threshold": args.threshold,
        "calibrated": calibrated,
        "downgraded": calibrated != args.reported,
    }
    sys.stdout.write(json.dumps(output, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
