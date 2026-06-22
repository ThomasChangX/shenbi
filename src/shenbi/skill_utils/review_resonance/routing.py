"""routing.py — three-path block routing + 2-revision cap (spec §5.4 三路径分流).

After a block (story section) is reviewed and scored, this helper decides the
next step:

  * **clear pass** (overall >= threshold and every dimension floor met) -> the
    block is accepted as-is.
  * **clear fail** (overall more than 5 below threshold, high confidence, under
    the revision cap, *high* calibrated confidence) -> route to automatic
    revision for another draft.
  * **borderline / uncertain** (within ±5 of threshold, a breached floor that is
    itself near threshold, or non-high scorer confidence) -> escalate to human
    review.

To avoid an infinite revision loop, after ``MAX_AUTO_REVISIONS`` (2) automatic
revisions a clear fail is no longer retried automatically — it escalates to
human review instead.

The calibrated confidence level (see ``skill_utils.calibration``) should be
passed in as ``confidence`` so that an overconfident-but-inaccurate scorer is
routed to a human rather than burning revision cycles.

Usage (CLI)::

    python -m shenbi.skill_utils.review_resonance \
        --overall 40 --threshold 75 --confidence high --prior-revisions 0
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum

# Half-width of the ±5 "borderline" band around the pass threshold (spec §5.4).
BORDERLINE_BAND: float = 5.0


class Routing(StrEnum):
    PASS = "pass"
    AUTO_REVISE = "auto_revise"
    HUMAN_REVIEW = "human_review"


MAX_AUTO_REVISIONS = 2


@dataclass(frozen=True)
class RevisionLoop:
    """Outcome of routing one reviewed block.

    ``path`` is the authoritative decision; the remaining fields are the
    diagnostic context that produced it, useful for the audit trail and the CLI.
    """

    path: Routing
    overall: float
    threshold: float
    confidence: str
    prior_revisions: int
    floor_ok: bool
    near_threshold: bool
    reason: str


def _decide(
    overall: float,
    threshold: float,
    floor_ok: bool,
    confidence: str,
    prior_revisions: int,
) -> tuple[Routing, str]:
    """Pure branching logic shared by :func:`route_block`. Returns (path, reason)."""
    if overall >= threshold and floor_ok:
        return Routing.PASS, "overall >= threshold and all floors met"

    near_threshold = abs(overall - threshold) <= BORDERLINE_BAND
    # A borderline score (within ±5) or any non-high (calibrated) confidence
    # cannot be trusted with an automatic revision, so a human must adjudicate.
    # Spec §5.4: 明确失败 → auto-revise requires *high* confidence; a scorer
    # calibrated down to "mid" (overconfident-but-inaccurate) loses that privilege.
    if near_threshold:
        return Routing.HUMAN_REVIEW, "overall within ±5 of threshold (borderline)"
    if confidence == "low":
        return Routing.HUMAN_REVIEW, "low scorer confidence"
    if confidence != "high":
        return (
            Routing.HUMAN_REVIEW,
            "calibrated confidence not high (overconfident/uncertain scorer)",
        )

    # High confidence and clearly below threshold (>5 under). Auto-revise unless
    # the 2-revision cap has been reached, in which case escalate to a human.
    if prior_revisions >= MAX_AUTO_REVISIONS:
        return Routing.HUMAN_REVIEW, "revision cap reached (no auto-revisions left)"
    return Routing.AUTO_REVISE, "clear fail, high confidence, under revision cap"


def route_block(
    overall: float,
    threshold: float,
    floors: Mapping[str, tuple[float, float]],
    confidence: str,
    prior_revisions: int,
) -> RevisionLoop:
    """Route one reviewed block to its next step (spec §5.4).

    Args:
        overall: The block's overall resonance score (0-100).
        threshold: The pass threshold for ``overall``.
        floors: Mapping of dimension name to ``(score, floor)``. Every ``score``
            must be ``>=`` its ``floor`` for a clear pass.
        confidence: Calibrated scorer confidence (``high`` / ``mid`` / ``low``).
            Only ``high`` qualifies a clear fail for automatic revision; ``mid``
            (e.g. a scorer calibrated down from an overconfident ``high``) and
            ``low`` both escalate to human review.
        prior_revisions: How many auto-revisions this block has already gone
            through. At/above ``MAX_AUTO_REVISIONS`` a clear fail escalates.

    Returns:
        A :class:`RevisionLoop` whose ``.path`` is the routing decision.
    """
    floor_ok = all(score >= floor for score, floor in floors.values())
    near_threshold = abs(overall - threshold) <= BORDERLINE_BAND
    path, reason = _decide(overall, threshold, floor_ok, confidence, prior_revisions)
    return RevisionLoop(
        path=path,
        overall=overall,
        threshold=threshold,
        confidence=confidence,
        prior_revisions=prior_revisions,
        floor_ok=floor_ok,
        near_threshold=near_threshold,
        reason=reason,
    )


def main() -> None:
    """CLI: route a single block and print the decision as JSON."""
    parser = argparse.ArgumentParser(
        prog="routing",
        description="Three-path block routing + 2-revision cap (spec §5.4).",
    )
    parser.add_argument(
        "--overall",
        type=float,
        required=True,
        help="Block overall score (0-100).",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        required=True,
        help="Pass threshold for the overall score.",
    )
    parser.add_argument(
        "--confidence",
        required=True,
        help="Calibrated scorer confidence (high/mid/low).",
    )
    parser.add_argument(
        "--prior-revisions",
        type=int,
        default=0,
        help="Auto-revisions already spent on this block (default 0).",
    )
    parser.add_argument(
        "--floor",
        action="append",
        default=[],
        metavar="DIM=SCORE:FLOOR",
        help="Dimension floor, e.g. '情感落地=22:20'. Repeatable.",
    )
    args = parser.parse_args()

    floors: dict[str, tuple[float, float]] = {}
    for spec in args.floor:
        name, values = spec.split("=", 1)
        score_s, floor_s = values.split(":", 1)
        floors[name] = (float(score_s), float(floor_s))

    result = route_block(
        overall=args.overall,
        threshold=args.threshold,
        floors=floors,
        confidence=args.confidence,
        prior_revisions=args.prior_revisions,
    )
    output = {
        "path": result.path.value,
        "overall": result.overall,
        "threshold": result.threshold,
        "confidence": result.confidence,
        "prior_revisions": result.prior_revisions,
        "floor_ok": result.floor_ok,
        "near_threshold": result.near_threshold,
        "reason": result.reason,
    }
    sys.stdout.write(json.dumps(output, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
