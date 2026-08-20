"""Write-safety classification for concurrent dispatch (spec §3.1, §3.4).

The parallel dispatch path (ThreadPoolExecutor) is safe ONLY for read-only
audit skills today. This module makes that boundary explicit and enforced:
any skill not classified READ_ONLY_AUDIT must run serially, so a future
expansion (e.g. Spec 6) cannot silently place a write-capable skill on the
concurrent path and race on truth files / shared state (spec §2.1-2.3).

Classification reads the skill's own contract (SKILL.md frontmatter
writes/updates), not the skill-name prefix (F532, C32 R4): a
``shenbi-review-*`` name alone no longer grants READ_ONLY_AUDIT.
review-resonance / review-arc-payoff declare ``updates: truth/audit_drift.md``
plus trend truth files and are therefore WRITE_SHARED (must serialize), while
review skills writing only their own ``audits/`` report remain on the
concurrent path.
"""

from __future__ import annotations

from enum import StrEnum

from shenbi.contracts import ContractError, load_contract


class WriteSafety(StrEnum):
    READ_ONLY_AUDIT = "read_only_audit"
    WRITE_ISOLATED = "write_isolated"  # disjoint files — safe with file locking
    WRITE_SHARED = "write_shared"  # shared truth/hooks — must serialize


def _is_shared_truth_path(path: str) -> bool:
    """Declared output path targets a SHARED mutable file: truth/*.md, hooks."""
    return path == "pending_hooks.md" or path.startswith("truth/")


def _contract_write_surface(skill: str) -> list[str] | None:
    """Return the contract writes+updates; None when the contract is unloadable."""
    try:
        c = load_contract(skill)
    except ContractError:
        return None
    return [*c["writes"], *c["updates"]]


def classify_skill_write_safety(skill: str) -> WriteSafety:
    """Classify a skill's write safety for concurrent dispatch.

    The verdict is derived from the skill contract (SKILL.md frontmatter
    writes/updates), not from the name prefix (F532, C32 R4):

    - contract unloadable -> write surface unverifiable -> conservative
      WRITE_SHARED (the review- prefix no longer grants a pass);
    - contract declares a write into the shared truth namespace
      (truth/*, pending_hooks.md) -> WRITE_SHARED;
    - contract declares no persisted writes, or every declared write is the
      skill's own audits/ report (disjoint watch surfaces; spec §3.1
      "read-only audit = review producing audits/") -> READ_ONLY_AUDIT;
    - anything else (chapters/ and other non-isolated outputs, unknown
      shapes) -> conservative WRITE_SHARED.

    Conservative default: an unknown or non-audit skill is WRITE_SHARED (must
    serialize), so new skills cannot accidentally land on the parallel path
    until their contract proves an isolated read-only write surface.
    """
    outputs = _contract_write_surface(skill)
    if outputs is None:
        return WriteSafety.WRITE_SHARED
    if any(_is_shared_truth_path(p) for p in outputs):
        # F532: review-resonance / review-arc-payoff contract updates write
        # truth/audit_drift.md + truth/resonance_trend.md (and the arc-payoff
        # trend file) -> must serialize, not ride the wave on their prefix.
        return WriteSafety.WRITE_SHARED
    if not outputs:
        return WriteSafety.READ_ONLY_AUDIT  # no persisted writes
    if all(p.startswith("audits/") for p in outputs):
        return WriteSafety.READ_ONLY_AUDIT  # own audit report only
    # Everything else (including unknown output shapes) is treated conservatively.
    return WriteSafety.WRITE_SHARED
