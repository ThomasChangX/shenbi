"""route.py — diagnosis routing for revision mode selection (spec §5.2).

Classifies a structured diagnosis from the scoring subagent into one of
three revision modes. The routing is deterministic: BLOCKING unmet-goal
issues demand regeneration (the chapter failed its stated goals); craft-
only issues can be spot-fixed. When both are present, regeneration runs
under craft constraints so the rewrite does not reintroduce AI tells.

Diagnosis schema (spec §5.1):
    {"issues": [
        {"category": "unmet_goal" | "craft",
         "id": str,
         "evidence": str,
         "severity": "BLOCKING" | "CRITICAL" | "MINOR"}
    ]}

Usage (CLI):
  python -m shenbi.skill_utils.revision_routing --diagnosis '{"issues":[]}'
"""

from __future__ import annotations

from enum import StrEnum

from typing import Any


class RevisionMode(StrEnum):
    SPOT_FIX = "spot-fix"
    REGENERATE = "regenerate"
    CONSTRAINED_REGENERATE = "constrained-regenerate"


def route_revision(diagnosis: dict[str, Any]) -> str:
    """Classify diagnosis into revision mode (spec §5.2).

    Returns one of RevisionMode values as a plain string.
    """
    issues = diagnosis.get("issues", [])
    has_unmet_blocking = any(
        i.get("category") == "unmet_goal" and i.get("severity") == "BLOCKING" for i in issues
    )
    has_craft = any(i.get("category") == "craft" for i in issues)
    if has_unmet_blocking and has_craft:
        return RevisionMode.CONSTRAINED_REGENERATE
    if has_unmet_blocking:
        return RevisionMode.REGENERATE
    return RevisionMode.SPOT_FIX
