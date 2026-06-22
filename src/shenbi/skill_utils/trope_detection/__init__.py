"""trope_detection subpackage — deterministic trope-matching helpers.

Re-exports the public API for import via the package path.
"""

from shenbi.skill_utils.trope_detection.match_tropes import (
    Trope,
    count_trope_hits,
    load_trope_inventory,
    main,
    trope_overuse,
)

__all__ = [
    "Trope",
    "count_trope_hits",
    "load_trope_inventory",
    "main",
    "trope_overuse",
]
