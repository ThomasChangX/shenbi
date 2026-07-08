"""Decisions schema v1 — enums + P2.5 rationale validation rules.

P2.5 rule (spec A.3):
- basis in ROUTINE_BASIS and severity != "high" → rationale FORBIDDEN
- basis == "manual_override" → rationale REQUIRED (severity ignored)
- severity == "high" (any basis) → rationale REQUIRED
- adjustments[] → rationale ALWAYS REQUIRED (anomalous by definition)
- rationale (when present) must be ≤100 chars
"""

from __future__ import annotations

DECISIONS_SCHEMA_VERSION = "shenbi-decisions-v1"

VALID_BASIS = {
    "adjacent_to_target_chapter",  # routine: chapters near target
    "arc_relevance",  # routine: related to current arc
    "volume_scope",  # routine: within current volume
    "manual_override",  # anomaly: human/skill explicitly overrode routine
}

VALID_SEVERITY = {
    "low",  # default for routine decisions — rationale forbidden
    "high",  # high-stakes routine decision — rationale required (P2.5 escape hatch)
}

VALID_HANDLING = {
    "compensate_via_pacing",
    "explicit_callout",
    "defer_to_next_chapter",
    "ignore",
}

VALID_TRIM = {"none", "oldest_first", "lowest_relevance", "manual"}

ROUTINE_BASIS = VALID_BASIS - {"manual_override"}

_RATIONALE_MAX_CHARS = 100


def validate_selection_rationale(basis: str, severity: str, rationale: str | None) -> list[str]:
    """Validate P2.5 rationale rules for a selections[] entry.

    Returns list of error strings (empty = valid).
    """
    errors: list[str] = []

    if basis not in VALID_BASIS:
        errors.append(f"invalid basis: {basis!r}, allowed: {sorted(VALID_BASIS)}")
        return errors

    if severity not in VALID_SEVERITY:
        errors.append(f"invalid severity: {severity!r}, allowed: {sorted(VALID_SEVERITY)}")
        return errors

    needs_rationale = basis == "manual_override" or severity == "high"
    is_routine_low = basis in ROUTINE_BASIS and severity != "high"

    if is_routine_low and rationale is not None:
        errors.append(f"rationale FORBIDDEN for routine basis {basis!r} with severity {severity!r}")
    elif needs_rationale and not rationale:
        errors.append(f"rationale REQUIRED for basis {basis!r} with severity {severity!r}")

    if rationale and len(rationale) > _RATIONALE_MAX_CHARS:
        errors.append(f"rationale exceeds {_RATIONALE_MAX_CHARS} chars (got {len(rationale)})")

    return errors


def validate_adjustment_rationale(rationale: str | None) -> list[str]:
    """Validate that adjustments[] always have rationale (anomalous by definition)."""
    if not rationale:
        return ["rationale REQUIRED for adjustments (anomalous by definition)"]
    if len(rationale) > _RATIONALE_MAX_CHARS:
        return [f"rationale exceeds {_RATIONALE_MAX_CHARS} chars (got {len(rationale)})"]
    return []
