"""drift_detection subpackage — smoothing + chapter/volume drift triggers.

Re-exports the public API for import via the package path.
"""

from shenbi.skill_utils.drift_detection.compute_drift import (
    ARC_PAYOFF_DIMS,
    RESONANCE_DIMS,
    DriftFinding,
    DriftKind,
    detect_chapter_drift,
    detect_volume_drift,
    main,
    parse_trend,
    smooth,
)

__all__ = [
    "ARC_PAYOFF_DIMS",
    "RESONANCE_DIMS",
    "DriftFinding",
    "DriftKind",
    "detect_chapter_drift",
    "detect_volume_drift",
    "main",
    "parse_trend",
    "smooth",
]
