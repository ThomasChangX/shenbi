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

import re
from enum import StrEnum
from pathlib import Path
from typing import Any

from shenbi.contracts.paths import PathContext
from shenbi.logging import get_logger
from shenbi.pipeline.dispatch_helper import dispatch_skill

log = get_logger(__name__)

#: Sub-directory under a project where audit reports are written.
from shenbi.contracts.enums import RevisionMode

#: Sub-directory under a project where audit reports are written.
AUDIT_DIR = "audits"


# spec #34 T910: single domain shenbi.contracts.enums.RevisionMode — the
# local 4-value twin class is collapsed to an alias (callers keep the name).
RevisionRoute = RevisionMode


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

#: Revision-loop cap (spec #33 T1b): migrated from the deleted dead model
#: (routing model formerly in skill_utils/review_resonance, deleted by spec #33 T1b) — same chapter may not exceed
#: this many cumulative revisions (any cause) before escalation.
MAX_AUTO_REVISIONS = 2


def revision_cap_exceeded(revision_count: int) -> bool:
    """True when the chapter's cumulative revision count exceeds the cap."""
    return revision_count > MAX_AUTO_REVISIONS


#: Default resonance global floor (spec §6.3, config.resonance_global_floor).
DEFAULT_RESONANCE_FLOOR = 50

# Severity markers (spec §6.3). Match BLOCKING/CRITICAL as a severity value
# rather than a bare substring, so prose like "No BLOCKING issues detected"
# does not register as a false positive. Accepts the bolded marker form
# (``**BLOCKING**``), the English severity-key form (``severity: BLOCKING``,
# ``**Severity**: BLOCKING``), and the CJK production form that all audit
# skills actually emit (``**严重度**: BLOCKING``, ``严重度: BLOCKING``).
# probe6 ch1 (2026-10-01): the value position alone is not enough — an
# audit's FORMAT DOCUMENTATION legend (``4. **严重度**：BLOCKING / CRITICAL /
# MINOR``, verbatim from a production sensitivity report) matched the key
# form and routed a phantom regenerate. A value inside an ENUM LIST is never
# a finding: the negative lookahead rejects it when further severity words
# are enumerated after it.
_SEV_ENUM_TAIL = r"(?!\s*[/／、,，]\s*(?:BLOCKING|CRITICAL|MINOR|WARNING|ERROR)\b)"
_SEVERITY_BLOCKING_RE = re.compile(
    r"\*\*BLOCKING\*\*"  # bolded marker: **BLOCKING**
    # severity key (English "severity" or CJK "严重度"): "severity: BLOCKING",
    # "**严重度**: BLOCKING". The optional \*{0,2} lets the key itself be bolded.
    rf"|(?:severity|严重度)\*{{0,2}}\W{{0,6}}BLOCKING\b{_SEV_ENUM_TAIL}",
    re.IGNORECASE,
)
_SEVERITY_CRITICAL_RE = re.compile(
    rf"\*\*CRITICAL\*\*"
    rf"|(?:severity|严重度)\*{{0,2}}\W{{0,6}}CRITICAL\b{_SEV_ENUM_TAIL}",
    re.IGNORECASE,
)


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
    pipeline is not blocked by missing data (fail-open), but the gap is
    disclosed via a ``resonance_unscored`` structlog event — an unscored
    chapter must never pass silently (spec #32 F304 disclosure rule).
    """
    if resonance_score is None:
        log.warning("resonance_unscored", floor=floor)
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


def dispatch_escalation(
    project_dir: Path | str,
    chapter: int | None,
    context: str = "",
    details: str | None = None,
    failing_skill: str | None = None,
) -> bool:
    """Dispatch ``shenbi-escalation-review`` for *chapter* (spec §6.3).

    The escalation-review skill compiles resonance trends and audit scores
    into ``audits/escalation-N-report.md``. Returns ``True`` on successful
    dispatch, ``False`` otherwise.

    *chapter* may be ``None`` during genesis when there is no chapter context
    (N-placeholder paths are filtered by the executor).

    *details* carries the concrete per-attempt failure record (the enriched
    G4 must-fix feedback from retry state). Canary/probe defect: the reviewer
    subagent reported "gate 失败明细未随调用传入" while the details sat unused
    in retry_feedback. When the dispatch fails OR leaves the report artifact
    stale (canary defect 升级报告未覆写: a second escalation kept the prior
    report's analysis), a minimal machine-generated report carrying *details*
    is written so the checkpoint reviewer never reads a stale analysis.
    """
    chapter_label = f"chapter {chapter}" if chapter is not None else "genesis (no chapter)"
    prompt = (
        f"Escalation review for {chapter_label}. "
        f"Compile resonance trends and audit scores into a decision report."
    )
    if context:
        prompt += f" Context: {context}"
    if failing_skill:
        # Probe2: both genesis escalation reports rendered THIS report
        # skill's own reads (trend files, N/A at genesis) in the 升级上下文
        # reads table instead of the FAILING skill's contract reads —
        # adjudicators had to correct the table by hand. Provide the
        # failing skill's contract reads WITH availability so the report
        # renders machine-truth, not its own context.
        from shenbi.contracts import ContractError, load_contract

        try:
            contract = load_contract(failing_skill)
            lines = []
            for rel in contract.get("reads", []):
                resolved = str(rel).replace("chapter-N", "N") if chapter is None else str(rel)
                probe = Path(project_dir) / resolved
                lines.append(f"- {resolved} — {'AVAILABLE' if probe.exists() else 'MISSING'}")
            if lines:
                prompt += (
                    "\n\n## FAILING SKILL CONTRACT READS (machine-provided — the "
                    "升级上下文 reads table MUST render THIS list with these "
                    "availability states, NOT this report skill's own reads)\n" + "\n".join(lines)
                )
        except ContractError:
            log.warning("escalation_failing_skill_contract_unavailable", skill=failing_skill)
    if details:
        prompt += f"\n\n## FAILURE DETAILS (per-attempt gate record from retry state)\n{details}"
    path_ctx = None
    _pd = Path(project_dir)
    artifact = (
        _pd / "audits" / "escalation-genesis-report.md"
        if chapter is None
        else _pd / "audits" / f"escalation-{chapter}-report.md"
    )
    pre_mtime = artifact.stat().st_mtime if artifact.exists() else None
    if chapter is None:
        # Genesis escalation (spec #6 F3B5): book-level sentinel resolves
        # audits/escalation-N-report.md to the genesis artifact name.
        path_ctx = PathContext(escalation="genesis")
    result = dispatch_skill(ESCALATION_SKILL, project_dir, prompt, path_context=path_ctx)
    if not result.success:
        log.error(
            "escalation_dispatch_failed",
            chapter=chapter,
            returncode=result.returncode,
            stderr=result.stderr,
        )
    else:
        log.info("escalation_dispatched", chapter=chapter)
    # Freshness guarantee: a successful dispatch that did not refresh the
    # artifact (skill write skipped / stale echo) is indistinguishable from
    # a failed one for the human reviewer — fall back to a machine report.
    post_mtime = artifact.stat().st_mtime if artifact.exists() else None
    if post_mtime is None or post_mtime == pre_mtime:
        log.warning(
            "escalation_report_stale_machine_fallback",
            chapter=chapter,
            artifact=str(artifact),
        )
        try:
            from datetime import UTC, datetime

            from shenbi.safe_write import safe_write

            artifact.parent.mkdir(parents=True, exist_ok=True)
            safe_write(
                artifact,
                (
                    f"# 升级审查报告（机器兜底生成）\n\n"
                    f"**触发上下文**: {context or 'n/a'}\n"
                    f"**生成时间**: {datetime.now(UTC).isoformat()}\n\n"
                    f"## 失败明细（来自重试状态的逐次 gate 记录）\n\n"
                    f"{details or '（无明细传入——见 pipeline 日志）'}\n\n"
                    f"> 注：escalation-review 技能派发"
                    f"{'失败' if not result.success else '未刷新报告'}，"
                    f"本报告为框架兜底，供检查点裁决使用；技能成功重跑后将覆写。\n"
                ).encode(),
                allowed_roots=(_pd,),
            )
        except OSError as exc:
            log.error("escalation_fallback_report_failed", chapter=chapter, error=str(exc))
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
        if _SEVERITY_BLOCKING_RE.search(content):
            blocking_found = True
            issues.append({"severity": "BLOCKING", "category": "unmet_goal", "file": rel})
        elif _SEVERITY_CRITICAL_RE.search(content):
            issues.append({"severity": "CRITICAL", "category": "craft", "file": rel})

    return issues, blocking_found
