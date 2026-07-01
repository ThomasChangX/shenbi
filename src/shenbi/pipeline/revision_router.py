"""Revision routing: reuse existing route_revision + delegate to specialist skills.

Spec §6.3. Wraps ``shenbi.skill_utils.revision_routing.route.route_revision``
and adds specialist skill delegation, a resonance threshold check, the full
§6.3 decision tree, escalation dispatch, and audit issue collection.

Decision tree (spec §6.3)::

    audit complete
      +-- no BLOCKING + resonance >= floor  -> pass
      +-- no BLOCKING + resonance borderline -> escalation checkpoint
      +-- no BLOCKING + resonance < floor    -> revision_routing
      +-- BLOCKING -> revision -> re-audit (max 3) -> 3 failures -> escalation
"""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Any

from shenbi.logging import get_logger
from shenbi.pipeline.dispatch_helper import dispatch_skill

log = get_logger(__name__)

#: Sub-directory under a project where audit reports are written.
AUDIT_DIR = "audits"


class RevisionRoute(StrEnum):
    """Concrete revision mode (delegates to existing ``RevisionMode``)."""

    SPOT_FIX = "spot-fix"
    REGENERATE = "regenerate"
    CONSTRAINED_REGENERATE = "constrained-regenerate"
    NO_REVISION = "no-revision"


class RevisionDecision(StrEnum):
    """Top-level §6.3 outcome — whether to revise at all."""

    PASS = "pass"
    REVISION = "revision"
    ESCALATION = "escalation"


# Specialist skill delegation (spec §6.3 revision_routing 委派边界).
# Maps diagnosis category -> specialist skill that handles it.
SPECIALIST_SKILLS: dict[str, str] = {
    "craft_expression": "shenbi-style-polishing",
    "ai_tell": "shenbi-anti-detect",
    "word_count": "shenbi-length-normalizing",
}

#: Skill for structure / plot revision (spec §6.3 revision_routing 分流).
CHAPTER_REVISION_SKILL = "shenbi-chapter-revision"

#: Skill dispatched when retries are exhausted or resonance is critically low.
ESCALATION_SKILL = "shenbi-escalation-review"

#: Default resonance global floor (spec §6.3, config.resonance_global_floor).
DEFAULT_RESONANCE_FLOOR = 50


def route_chapter_revision(issues: list[dict[str, Any]], blocking: bool) -> RevisionRoute:
    """Route revision based on audit issues.

    Reuses the existing ``route_revision`` logic from
    ``shenbi.skill_utils.revision_routing.route``. Returns
    :attr:`RevisionRoute.NO_REVISION` when *issues* is empty.
    """
    if not issues:
        return RevisionRoute.NO_REVISION
    from shenbi.skill_utils.revision_routing.route import RevisionMode, route_revision

    diagnosis = {"issues": issues}
    mode = route_revision(diagnosis)
    if mode == RevisionMode.SPOT_FIX:
        return RevisionRoute.SPOT_FIX
    if mode == RevisionMode.REGENERATE:
        return RevisionRoute.REGENERATE
    if mode == RevisionMode.CONSTRAINED_REGENERATE:
        return RevisionRoute.CONSTRAINED_REGENERATE
    return RevisionRoute.NO_REVISION


def check_resonance(resonance_score: int | None, floor: int = DEFAULT_RESONANCE_FLOOR) -> bool:
    """True if *resonance_score* meets or exceeds the global *floor*.

    A ``None`` score (not yet evaluated) is treated as passing so that the
    pipeline is not blocked by missing data.
    """
    if resonance_score is None:
        return True
    return resonance_score >= floor


def decide_revision(
    issues: list[dict[str, Any]],
    blocking: bool,
    resonance_score: int | None,
    resonance_floor: int = DEFAULT_RESONANCE_FLOOR,
) -> RevisionDecision:
    """Apply the full spec §6.3 decision tree.

    Order of checks:

    1. **BLOCKING** found -> :attr:`RevisionDecision.REVISION`
       (the caller re-audits up to ``max_audit_retries`` times; on exhaustion
       it calls :func:`dispatch_escalation`).
    2. **No BLOCKING** + resonance >= floor -> :attr:`RevisionDecision.PASS`
    3. **No BLOCKING** + resonance < floor -> :attr:`RevisionDecision.REVISION`
       (route via :func:`route_chapter_revision`).
    """
    if blocking:
        return RevisionDecision.REVISION
    if check_resonance(resonance_score, resonance_floor):
        return RevisionDecision.PASS
    return RevisionDecision.REVISION


def dispatch_escalation(project_dir: Path | str, chapter: int, context: str = "") -> bool:
    """Dispatch ``shenbi-escalation-review`` for *chapter* (spec §6.3).

    The escalation-review skill compiles resonance trends and audit scores
    into ``audits/escalation-N-report.md``. Returns ``True`` on successful
    dispatch, ``False`` otherwise.
    """
    prompt = (
        f"Escalation review for chapter {chapter}. "
        f"Compile resonance trends and audit scores into a decision report."
    )
    if context:
        prompt += f" Context: {context}"
    result = dispatch_skill(ESCALATION_SKILL, project_dir, prompt)
    if not result.success:
        log.error(
            "escalation_dispatch_failed",
            chapter=chapter,
            returncode=result.returncode,
            stderr=result.stderr,
        )
    else:
        log.info("escalation_dispatched", chapter=chapter)
    return result.success


def collect_audit_issues(
    project_dir: Path | str, chapter: int
) -> tuple[list[dict[str, Any]], bool]:
    """Scan audit reports for *chapter* and extract severity-tagged issues.

    Reads ``audits/chapter-N-*.md`` files and checks for ``BLOCKING`` /
    ``CRITICAL`` severity markers (consistent with
    :func:`shenbi.pipeline.audit_layer.run_audit_layer`). Returns a tuple
    of ``(issues, blocking_found)``.

    Each issue dict carries:

    * ``severity`` -- ``"BLOCKING"`` or ``"CRITICAL"``
    * ``file``     -- project-relative path of the audit report
    * ``category`` -- ``"unmet_goal"`` for BLOCKING (structural failure),
      ``"craft"`` for CRITICAL (surface-level quality)
    """
    project_dir = Path(project_dir)
    audit_dir = project_dir / AUDIT_DIR
    if not audit_dir.is_dir():
        return [], False

    issues: list[dict[str, Any]] = []
    blocking_found = False
    prefix = f"chapter-{chapter}-"

    for audit_file in sorted(audit_dir.glob(f"{prefix}*.md")):
        rel = f"{AUDIT_DIR}/{audit_file.name}"
        content = audit_file.read_text(encoding="utf-8")
        if "BLOCKING" in content:
            blocking_found = True
            issues.append({"severity": "BLOCKING", "category": "unmet_goal", "file": rel})
        elif "CRITICAL" in content:
            issues.append({"severity": "CRITICAL", "category": "craft", "file": rel})

    return issues, blocking_found
