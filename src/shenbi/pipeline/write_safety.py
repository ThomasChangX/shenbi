"""Write-safety classification for concurrent dispatch (spec §3.1, §3.4).

The parallel dispatch path (ThreadPoolExecutor) is safe ONLY for read-only
audit skills today. This module makes that boundary explicit and enforced:
any skill not classified READ_ONLY_AUDIT must run serially, so a future
expansion (e.g. Spec 6) cannot silently place a write-capable skill on the
concurrent path and race on truth files / shared state (spec §2.1-2.3).
"""

from __future__ import annotations

from enum import StrEnum


class WriteSafety(StrEnum):
    READ_ONLY_AUDIT = "read_only_audit"
    WRITE_ISOLATED = "write_isolated"  # disjoint files — safe with file locking
    WRITE_SHARED = "write_shared"  # shared truth/hooks — must serialize


# Skills known to write to SHARED mutable files (truth/*.md, pending_hooks.md).
# These MUST NOT be parallelized (spec §3.1 "Write-shared").
# These are write-capable skills from CHAPTER_STEPS. Only shenbi-state-settling
# and shenbi-foreshadowing-track are currently on the concurrent path; the others
# are listed for completeness as they may be parallelized in future.
_WRITE_SHARED_SKILLS = frozenset(
    {
        "shenbi-state-settling",
        "shenbi-foreshadowing-track",
        "shenbi-foreshadowing-plant",
        "shenbi-chapter-drafting",
        "shenbi-chapter-revision",
        "shenbi-intent-management",
    }
)


def classify_skill_write_safety(skill: str) -> WriteSafety:
    """Classify a skill's write safety for concurrent dispatch.

    Conservative default: an unknown skill is WRITE_SHARED (must serialize),
    so new skills cannot accidentally land on the parallel path until they
    are explicitly classified READ_ONLY_AUDIT.
    """
    if skill.startswith("shenbi-review-"):
        return WriteSafety.READ_ONLY_AUDIT
    if skill in _WRITE_SHARED_SKILLS:
        return WriteSafety.WRITE_SHARED
    # Everything else (including unknown skills) is treated conservatively.
    return WriteSafety.WRITE_SHARED
