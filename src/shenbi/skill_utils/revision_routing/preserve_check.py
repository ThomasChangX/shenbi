"""preserve_check.py — regeneration preservation verification (spec §5.3, §11.5).

After a chapter is regenerated (not spot-fixed), the regenerated version
must retain every key outcome the original already achieved: advanced/
resolved hooks, realized §6 changes, and character state changes. This
function compares the original-item dict (assembled before regeneration)
against the regenerated dict (from rerun state-settling) and reports
violations.

Dict schema (spec §11.5):
    {"chapter": int,
     "hooks_advanced": [str],       # hook_ids advanced/resolved in original
     "changes_realized": [str],     # §6 changes that occurred in original
     "state_changes": [str]}        # character matrix deltas in original

Usage (CLI):
  python -m shenbi.skill_utils.revision_routing.preserve_check \
      --original '{"hooks_advanced":["H01"],"changes_realized":[],"state_changes":[]}' \
      --regenerated '{"hooks_advanced":[],"changes_realized":[],"state_changes":[]}'
"""

from __future__ import annotations

from typing import Any


def verify_preservation(
    original: dict[str, Any], regenerated: dict[str, Any]
) -> tuple[bool, list[str]]:
    """Verify regenerated chapter retains all original key outcomes.

    Returns (all_preserved, violations). A violation is a human-readable
    string naming what was lost.
    """
    violations: list[str] = []

    original_hooks = set(original.get("hooks_advanced", []))
    regen_hooks = set(regenerated.get("hooks_advanced", []))
    for hook_id in original_hooks - regen_hooks:
        violations.append(f"hook {hook_id} advanced in original but lost in regeneration")

    original_changes = original.get("changes_realized", [])
    regen_changes = set(regenerated.get("changes_realized", []))
    for change in original_changes:
        if change not in regen_changes:
            violations.append(f"§6 change lost: {change}")

    original_states = original.get("state_changes", [])
    regen_states = set(regenerated.get("state_changes", []))
    for state in original_states:
        if state not in regen_states:
            violations.append(f"state change reverted: {state}")

    return (len(violations) == 0, violations)
