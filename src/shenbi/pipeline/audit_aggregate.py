"""Deterministic pre-revision audit aggregation (spec #4 F10 / §5.1a).

Merges the raw per-auditor reports ``audits/chapter-N-*.md`` into a single
deduplicated ``audits/chapter-N.aggregate.md`` before chapter revision is
dispatched. Zero LLM calls: pure parsing + rendering, idempotent.

Design invariants (spec §5.1a):
- the aggregate filename uses a DOT separator so it never matches the
  ``chapter-N-*.md`` glob consumed by revision_router / drift-guidance;
- the file never starts with ``---`` (G1.3 frontmatter parsing);
- lossless: every severity-bearing finding unit (BLOCKING/CRITICAL/WARNING/
  ERROR in any surface form) from the raw reports is present in the
  aggregate, merged only on exact (severity, text) key;
- resonance reports (chapter-N-resonance.md) are preserved verbatim in
  full — their dedicated read is deleted from the revision contract, so
  the aggregate is their only path into the revision skill.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from shenbi.logging import get_logger
from shenbi.pipeline.revision_router import AUDIT_DIR
from shenbi.safe_write import safe_write

log = get_logger(__name__)

AGGREGATE_SUFFIX = ".aggregate.md"

#: Severity value matched anywhere in a finding entry line (bolded marker
#: ``**BLOCKING**``, bracketed ``**[WARNING]**``, severity-key form, or a
#: bare table-cell value like ``| warning |`` — the real production form in
#: tests/fixtures/audit-report-example.md). Single capture group.
_SEVERITY_RE = re.compile(r"\b(BLOCKING|CRITICAL|WARNING|ERROR)\b", re.IGNORECASE)
#: Table rows filled with em-dashes are empty placeholders, not findings.
_PLACEHOLDER_ROW_RE = re.compile(r"^\|[\s—\-|]*\|$")
#: Context lines worth preserving verbatim (result / score / target headers).
_CONTEXT_RE = re.compile(r"^(\*\*(结果|审计目标文件|章节)\*\*|###\s*评分)", re.IGNORECASE)
#: Metadata-leading lines (``**结果**…`` or ``| 结果 | …``) are context even
#: when they mention a severity word in passing — they must not inflate the
#: finding count nor lose their verbatim context slot.
_METADATA_LEAD_RE = re.compile(r"^\|?\s*\**\s*(结果|评分)", re.IGNORECASE)
#: Resonance reports are preserved verbatim in full (spec §5.1a).
_RESONANCE_NAME_RE = re.compile(r"^chapter-\d+-resonance\.md$")


@dataclass(frozen=True)
class FindingUnit:
    """One severity-bearing finding, merged across reporters on its key."""

    severity: str
    text: str
    reporters: tuple[str, ...]


def aggregate_path(project_dir: Path, chapter: int) -> Path:
    return project_dir / AUDIT_DIR / f"chapter-{chapter}{AGGREGATE_SUFFIX}"


def _normalize(line: str) -> str:
    return re.sub(r"\s+", " ", line.strip())


def _severity_of(line: str) -> str | None:
    m = _SEVERITY_RE.search(line)
    return m.group(1).upper() if m else None


def extract_finding_units(report_name: str, content: str) -> tuple[list[FindingUnit], list[str]]:
    """Split *content* into finding units and preserved context lines.

    A finding unit is a markdown list item or table row that carries a
    BLOCKING/CRITICAL/WARNING/ERROR severity value (any surface form).
    Placeholder rows (all em-dashes) never produce units. Lines that carry
    a severity word but are NOT entries (headings, prose paragraphs), or
    that lead with metadata (结果/评分), degrade to verbatim context —
    conservative preservation, never silent loss.
    """
    units: list[FindingUnit] = []
    context: list[str] = []
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped or _PLACEHOLDER_ROW_RE.match(stripped):
            continue
        sev = _severity_of(stripped)
        if _CONTEXT_RE.match(stripped) or _METADATA_LEAD_RE.match(stripped):
            context.append(stripped)
        elif stripped.startswith(("- ", "* ", "|")) and sev:
            text = _normalize(_SEVERITY_RE.sub("", stripped).strip("-*| "))
            units.append(FindingUnit(sev, text, (report_name,)))
        elif sev:
            # Severity-bearing but not a list/table entry — keep verbatim
            # rather than dropping (lossless invariant over tidy output).
            context.append(stripped)
    return units, context


def render_aggregate(
    chapter: int,
    units: list[FindingUnit],
    context: dict[str, list[str]],
    resonance_bodies: dict[str, str] | None = None,
) -> str:
    parts = [f"# Chapter {chapter} — Audit Aggregate", ""]
    parts.append(f"- **来源报告数**: {len(context) + len(resonance_bodies or {})}")
    parts.append(f"- **去重后缺陷条目**: {len(units)}")
    parts.append("")
    for sev in ("BLOCKING", "CRITICAL", "WARNING", "ERROR"):
        sev_units = [u for u in units if u.severity == sev]
        if not sev_units:
            continue
        parts.append(f"## {sev} Findings ({len(sev_units)})")
        parts.append("")
        for u in sev_units:
            parts.append(f"- {u.text}")
            parts.append(f"  - 报告方: {', '.join(u.reporters)}")
        parts.append("")
    if resonance_bodies:
        parts.append("## Resonance 报告（逐字保留）")
        parts.append("")
        for name, body in sorted(resonance_bodies.items()):
            parts.append(f"### {name}")
            parts.append("")
            parts.append(body.rstrip())
            parts.append("")
    parts.append("## 报告上下文")
    parts.append("")
    for name, lines in sorted(context.items()):
        parts.append(f"### {name}")
        parts.extend(lines)
        parts.append("")
    return "\n".join(parts).rstrip() + "\n"


def write_audit_aggregate(project_dir: Path | str, chapter: int) -> Path | None:
    """Aggregate raw audits for *chapter*; returns the aggregate path.

    Returns ``None`` when there are no raw reports (nothing to aggregate —
    the dispatcher fallback then injects whatever exists).
    """
    project_dir = Path(project_dir)
    audit_dir = project_dir / AUDIT_DIR
    if not audit_dir.is_dir():
        return None
    raw = sorted(audit_dir.glob(f"chapter-{chapter}-*.md"))
    if not raw:
        return None

    merged: dict[tuple[str, str], FindingUnit] = {}
    context: dict[str, list[str]] = {}
    resonance_bodies: dict[str, str] = {}
    for report in raw:
        content = report.read_text(encoding="utf-8")
        if _RESONANCE_NAME_RE.match(report.name):
            resonance_bodies[report.name] = content
            continue
        units, ctx = extract_finding_units(report.name, content)
        context[report.name] = ctx
        for u in units:
            key = (u.severity, u.text)
            if key in merged:
                prev = merged[key]
                merged[key] = FindingUnit(
                    u.severity, u.text, tuple(dict.fromkeys([*prev.reporters, *u.reporters]))
                )
            else:
                merged[key] = u

    out = aggregate_path(project_dir, chapter)
    rendered = render_aggregate(chapter, list(merged.values()), context, resonance_bodies)
    safe_write(out, rendered)
    log.info(
        "audit_aggregate_written",
        chapter=chapter,
        reports=len(raw),
        findings=len(merged),
        resonance=len(resonance_bodies),
        bytes=len(rendered),
    )
    return out
