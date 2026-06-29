"""calibration subpackage — confidence calibration by anchor hit-rate (spec §8.2).

Re-exports the public API for import via the package path.
"""

from shenbi.skill_utils.calibration.confidence import (
    HitRate,
    calibrate_confidence,
    main,
)

__all__ = [
    "HitRate",
    "calibrate_confidence",
    "main",
]
