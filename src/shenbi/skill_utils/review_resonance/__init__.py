"""review_resonance subpackage — three-path block routing + revision cap (spec §5.4).

Re-exports the public API for import via the package path.
"""

from shenbi.skill_utils.review_resonance.routing import (
    BORDERLINE_BAND,
    MAX_AUTO_REVISIONS,
    RevisionLoop,
    Routing,
    main,
    route_block,
)

__all__ = [
    "BORDERLINE_BAND",
    "MAX_AUTO_REVISIONS",
    "RevisionLoop",
    "Routing",
    "main",
    "route_block",
]
