"""Deterministic pre-revision audit aggregation (spec #4 F10 / §5.1a).

Merges the raw per-auditor reports ``audits/chapter-N-*.md`` into a single
deduplicated ``audits/chapter-N.aggregate.md`` before chapter revision is
dispatched. Zero LLM calls: pure parsing + rendering, idempotent.

Design invariants (spec §5.1a):
- the aggregate filename uses a DOT separator so it never matches the
  ``chapter-N-*.md`` glob consumed by revision_router / drift-guidance;
- the file never starts with ``---`` (G1.3 frontmatter parsing);
- lossless: every ANCHORED severity-bearing finding unit (BLOCKING/CRITICAL/
  MINOR/WARNING/ERROR as bracket/bold/cell/inline-key marker) from the raw
  reports is present in the aggregate, merged only on exact (severity, text)
  key; the consolidator's own review-summary is excluded (downstream echo);
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

#: Severity vocabulary shared by every anchored marker form. MINOR joined
#: when the 21 review templates migrated to the enums vocabulary
#: (BLOCKING/CRITICAL/MINOR brackets — commit b748f048).
_SEV_WORDS = r"BLOCKING|CRITICAL|MINOR|WARNING|ERROR"
#: Anchored finding markers (fixcheck ch2: the former bare ``\bWORD\b``
#: IGNORECASE sensor counted the review-summary's counter lines
#: (``- **BLOCKING Issues**: 2``), its per-report echoes, severity LABEL
#: lines (``- **严重度**: CRITICAL``), a lowercase PASS row
#: (``…，blocking）：…PASS。``), and fix-suggestion prose mentioning
#: "CRITICAL 1" — aggregate said BLOCKING Findings(6) while the truth was
#: 2). A finding entry line must carry one of these MARKER shapes; a bare
#: severity word in prose is never a finding.
_BRACKET_RE = re.compile(rf"^\s*-\s*\[({_SEV_WORDS})\]")
_BOLD_RE = re.compile(rf"\*\*({_SEV_WORDS})\*\*")
#: Table-cell value (``| ERROR |``; case-insensitive for the legacy
#: lowercase ``| warning |`` production form — a cell is pipe-delimited,
#: prose parentheticals are not).
_CELL_RE = re.compile(rf"(?:^|\|)\s*({_SEV_WORDS})\s*(?:\||$)", re.IGNORECASE)
#: Inline severity key with leading content (``…：severity: CRITICAL``).
# probe6 ch1: a FORMAT DOCUMENTATION legend (``4. **严重度**：BLOCKING /
# CRITICAL / MINOR``, numbered list so _LABEL_ONLY_RE does not catch it) is
# not a finding — reject values that continue an enum list (same guard as
# revision_router / parallel_dispatch severity sensors).
_ENUM_TAIL = r"(?!\s*[/／、,，]\s*(?:BLOCKING|CRITICAL|MINOR|WARNING|ERROR)\b)"
_KEY_RE = re.compile(
    rf"(?:\*\*)?\s*(?:severity|严重度)\s*(?:\*\*)?\s*[：:]\s*({_SEV_WORDS})\b{_ENUM_TAIL}",
    re.IGNORECASE,
)
#: Severity LABEL lines carry nothing but the key (``- **严重度**: CRITICAL``)
#: — metadata of the finding stated on the line above, never a finding.
_LABEL_ONLY_RE = re.compile(
    r"^[\s\-*|]*(?:\*\*)?\s*(?:severity|严重度)\s*(?:\*\*)?\s*[：:]", re.IGNORECASE
)
#: Non-entry lines (headings, prose) that merely MENTION a severity word
#: degrade to verbatim context — lossless preservation, never a unit.
_BARE_SEV_RE = re.compile(rf"\b({_SEV_WORDS})\b")
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
#: The consolidator's own summary is downstream of the same raw reports in
#: the glob — including it double-counts every finding via its counter and
#: echo lines (fixcheck ch2: 3 of the 6 phantom BLOCKING units came from it).
_SUMMARY_NAME_RE = re.compile(r"^chapter-\d+-review-summary\.md$")


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


def _severity_of(line: str) -> tuple[str, re.Pattern[str]] | None:
    """First anchored marker match on *line*: (severity, matched pattern)."""
    for pat in (_BRACKET_RE, _BOLD_RE, _CELL_RE, _KEY_RE):
        m = pat.search(line)
        if m:
            return m.group(1).upper(), pat
    return None


def extract_finding_units(report_name: str, content: str) -> tuple[list[FindingUnit], list[str]]:
    """Split *content* into finding units and preserved context lines.

    A finding unit is a markdown list item or table row that carries an
    ANCHORED severity marker: bracket (``- [BLOCKING] …``), bold-wrapped
    word (``**CRITICAL**``), pipe-delimited table cell (``| ERROR |``), or
    an inline severity key with leading content (``- P5 对白信息倾倒: severity: CRITICAL``).
    A severity LABEL line (``- **严重度**: CRITICAL`` — metadata of the
    finding stated above it) degrades to context. Placeholder rows (all
    em-dashes) never produce units. Non-entry lines that merely mention a
    severity word (headings, prose) degrade to verbatim context —
    conservative preservation, never silent loss.
    """
    units: list[FindingUnit] = []
    context: list[str] = []
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped or _PLACEHOLDER_ROW_RE.match(stripped):
            continue
        if _CONTEXT_RE.match(stripped) or _METADATA_LEAD_RE.match(stripped):
            context.append(stripped)
            continue
        hit = _severity_of(stripped) if stripped.startswith(("- ", "* ", "|")) else None
        if hit is not None:
            sev, pat = hit
            if pat is _KEY_RE and _LABEL_ONLY_RE.match(stripped):
                context.append(stripped)
                continue
            text = _normalize(pat.sub("", stripped, count=1).strip("-*| "))
            if text:
                units.append(FindingUnit(sev, text, (report_name,)))
            else:
                context.append(stripped)
        elif _BARE_SEV_RE.search(stripped):
            # Severity mentioned but not an anchored entry — keep verbatim
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
    for sev in ("BLOCKING", "CRITICAL", "MINOR", "WARNING", "ERROR"):
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
    if context:
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
        if _SUMMARY_NAME_RE.match(report.name):
            continue  # downstream of the same raw reports — double counts
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
