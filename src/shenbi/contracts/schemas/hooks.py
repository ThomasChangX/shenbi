"""Canonical hook lifecycle state enum (fixes D22).

The foreshadowing lifecycle has **6 canonical values** (phase-0:
foreshadowing-track/SKILL.md:72-73,120): PLANTED → RELEVANT → TRIGGERED →
RESOLVED, with ARCHIVED/EXPIRED as terminal exits. Skills also emit
non-canonical spellings (e.g. ``TRIGGER`` at SKILL.md:87), so
:func:`parse_hook_state` folds those + is case-insensitive.

This is deliberately a YAML-enum concern — NOT ``match_field`` (which is the
H2-heading matcher for markdown bodies, fixes D14/D17). YAML ``state`` values
are compared by enum identity, not by whitespace-folded heading text.
"""

from __future__ import annotations

from enum import StrEnum


class HookState(StrEnum):
    """The 6 canonical foreshadowing hook lifecycle states."""

    PLANTED = "PLANTED"
    RELEVANT = "RELEVANT"
    TRIGGERED = "TRIGGERED"
    RESOLVED = "RESOLVED"
    ARCHIVED = "ARCHIVED"  # phase-0: foreshadowing-track SKILL.md:72
    EXPIRED = "EXPIRED"  # phase-0: SKILL.md:73,120


# Non-canonical spellings emitted by skills, mapped to the canonical value.
# SKILL.md:87 uses the bare ``TRIGGER`` form; we normalize it so a hook is
# never missed just because the author abbreviated the state.
_NONCANONICAL: dict[str, HookState] = {
    "TRIGGER": HookState.TRIGGERED,
}


def parse_hook_state(raw: str) -> HookState | None:
    """Parse a raw ``state`` string into a canonical :class:`HookState`.

    Case-insensitive (``"triggered"``/``"Triggered"`` → ``TRIGGERED``) and maps
    known non-canonical spellings (``"TRIGGER"`` → ``TRIGGERED``). Returns
    ``None`` for empty/unknown input rather than raising, so callers can
    short-circuit ``state == TRIGGERED`` checks on malformed YAML without a
    try/except at every call site.
    """
    key = raw.strip()
    if not key:
        return None
    # Check both the raw spelling and its upper-case form against the
    # non-canonical map, so ``trigger``/``Trigger`` fold to TRIGGERED too.
    if key in _NONCANONICAL:
        return _NONCANONICAL[key]
    upper = key.upper()
    if upper in _NONCANONICAL:
        return _NONCANONICAL[upper]
    # Canonical lookup by value (membership avoids relying on Enum's ValueError).
    for state in HookState:
        if state.value == upper:
            return state
    return None
