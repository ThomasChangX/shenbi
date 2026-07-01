"""Audit sub-orchestrator: genre circle activation + boundary circle triggers.

Spec section 6.2 — three-circle audit layer. The core circle (anti-ai,
continuity, character, pacing, foreshadowing, memo-compliance, pov) runs as
regular chapter_loop steps before this module is invoked. This module covers
the two dynamic circles that follow:

* **Genre circle** (gate-driven): ``genre-config.json``'s ``audit_dimensions``
  dict selects which genre-specific review skills to run. Only activates after
  the core circle fully passes (enforced by the chapter_loop caller).
* **Boundary circle** (deterministic): fires on chapter-number milestones
  (every 24th chapter for long-span, every 6th for chapter-pattern, etc.).

BLOCKING-severity findings short-circuit into revision; the caller checks
``AuditResult.blocking_found`` and routes accordingly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from collections.abc import Callable, Mapping

from shenbi.logging import get_logger
from shenbi.pipeline.dispatch_helper import dispatch_skill, run_gate_g4
from shenbi.status import GateStatus

log = get_logger(__name__)

#: Sub-directory under a project where audit reports are written.
AUDIT_DIR = "audits"

# ---------------------------------------------------------------------------
# Genre-circle activation matrix (spec section 6.2)
#
# Maps ``genre-config.json`` ``audit_dimensions`` keys to the review skill that
# implements that dimension. Values are full ``shenbi-*`` skill names so they
# can be dispatched directly.
# ---------------------------------------------------------------------------
GENRE_ACTIVATION_MATRIX: dict[str, str] = {
    "era": "shenbi-review-era",
    "fanfic": "shenbi-review-fanfic",
    "world_rules": "shenbi-review-world-rules",
    "sensitivity": "shenbi-review-sensitivity",
    "dialogue_focus": "shenbi-review-dialogue",
    "motivation_focus": "shenbi-review-motivation",
    "texture_focus": "shenbi-review-texture",
    "reader_pull_focus": "shenbi-review-reader-pull",
    "highpoint_focus": "shenbi-review-highpoint",
}


# ---------------------------------------------------------------------------
# Boundary-circle triggers (spec section 6.2)
#
# arc-payoff and spinoff are triggered by volume boundaries / user marks rather
# than chapter number, so they return False here and are activated elsewhere.
# ---------------------------------------------------------------------------
BOUNDARY_TRIGGERS: dict[str, Callable[[int], bool]] = {
    "shenbi-review-long-span": lambda ch: ch % 24 == 0,
    "shenbi-review-arc-payoff": lambda ch: False,
    "shenbi-review-spinoff": lambda ch: False,
    "shenbi-chapter-pattern": lambda ch: ch % 6 == 0,
}


@dataclass
class AuditResult:
    """Aggregated outcome of the genre + boundary audit circles."""

    blocking_found: bool = False
    critical_found: bool = False
    audit_reports: list[str] = field(default_factory=list)
    issues: list[dict[str, object]] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Activation helpers
# ---------------------------------------------------------------------------
def get_active_genre_audits(genre_config: Mapping[str, object]) -> list[str]:
    """Determine which genre-circle audits to run based on genre-config.json.

    Reads the ``audit_dimensions`` sub-dict; every key set to a truthy value
    maps (via :data:`GENRE_ACTIVATION_MATRIX`) to a review skill.
    """
    audit_dims = genre_config.get("audit_dimensions", {})
    if not isinstance(audit_dims, dict):
        return []
    return [
        skill
        for dim_key, skill in GENRE_ACTIVATION_MATRIX.items()
        if audit_dims.get(dim_key, False)
    ]


def get_active_boundary_audits(chapter: int) -> list[str]:
    """Determine which boundary-circle audits to run for *chapter*."""
    return [skill for skill, trigger in BOUNDARY_TRIGGERS.items() if trigger(chapter)]


# ---------------------------------------------------------------------------
# Path helper
# ---------------------------------------------------------------------------
def _audit_suffix(skill: str) -> str:
    """Strip the ``shenbi-`` / ``shenbi-review-`` prefix for file naming."""
    if skill.startswith("shenbi-review-"):
        return skill[len("shenbi-review-") :]
    if skill.startswith("shenbi-"):
        return skill[len("shenbi-") :]
    return skill


def audit_relative_path(chapter: int, skill: str) -> str:
    """Project-relative path of the audit report for *skill* on *chapter*.

    Mirrors the chapter_loop convention ``audits/chapter-N-{suffix}.md``.
    """
    return f"{AUDIT_DIR}/chapter-{chapter}-{_audit_suffix(skill)}.md"


def _gate_passed(result: dict[str, object]) -> bool:
    """True iff a gate result dict reports PASS (handles str and GateStatus)."""
    return str(result.get("status", "")) == GateStatus.PASS


# ---------------------------------------------------------------------------
# Sub-orchestrator
# ---------------------------------------------------------------------------
def run_audit_layer(
    project_dir: Path | str, chapter: int, genre_config: Mapping[str, object]
) -> AuditResult:
    """Run genre + boundary audits after the core circle passes.

    Dispatches each active audit skill via the dispatcher, validates the output
    with G4 (consistent with chapter_loop's per-step G4), and scans for
    ``BLOCKING`` / ``CRITICAL`` severity markers in the produced report.

    Returns an :class:`AuditResult`; the caller checks ``blocking_found`` to
    decide whether to enter revision.
    """
    project_dir = Path(project_dir)
    result = AuditResult()
    active = get_active_genre_audits(genre_config) + get_active_boundary_audits(chapter)

    for skill in active:
        rel_path = audit_relative_path(chapter, skill)
        log.info("audit_dispatch", skill=skill, chapter=chapter)

        disp = dispatch_skill(skill, project_dir, f"Execute {skill} audit for chapter {chapter}.")
        if not disp.success:
            log.error("audit_dispatch_failed", skill=skill, chapter=chapter)
            result.blocking_found = True
            result.issues.append(_issue(skill, chapter, "BLOCKING", "dispatch", rel_path))
            continue

        g4 = run_gate_g4(skill, [rel_path], project_dir)
        if not _gate_passed(g4):
            log.error("audit_g4_failed", skill=skill, chapter=chapter, g4=g4)
            result.blocking_found = True
            result.issues.append(_issue(skill, chapter, "BLOCKING", "g4", rel_path, detail=g4))
            continue

        audit_file = project_dir / rel_path
        result.audit_reports.append(rel_path)
        if audit_file.exists():
            content = audit_file.read_text(encoding="utf-8")
            if "BLOCKING" in content:
                result.blocking_found = True
                result.issues.append(_issue(skill, chapter, "BLOCKING", "content", rel_path))
            if "CRITICAL" in content:
                result.critical_found = True
                result.issues.append(_issue(skill, chapter, "CRITICAL", "content", rel_path))

    return result


def _issue(
    skill: str,
    chapter: int,
    severity: str,
    source: str,
    file: str,
    detail: object | None = None,
) -> dict[str, object]:
    """Build a structured issue record for the revision router (W3T5)."""
    issue: dict[str, object] = {
        "skill": skill,
        "chapter": chapter,
        "severity": severity,
        "source": source,
        "file": file,
    }
    if detail is not None:
        issue["detail"] = detail
    return issue
