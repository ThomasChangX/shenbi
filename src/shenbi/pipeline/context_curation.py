"""Deterministic context curation — replaces LLM-based context-composing.

Performs 9-section structuring of assembled context, ending diversity checks,
and hook debt briefing — all deterministic Python operations. Replaces the
``shenbi-context-composing`` LLM call with deterministic functions.

Spec: docs/superpowers/specs/2026-07-07-pipeline-performance-redesign.md Phase 2.1
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from shenbi.logging import get_logger

log = get_logger(__name__)

# ---------------------------------------------------------------------------
# Section dataclass
# ---------------------------------------------------------------------------

# Priority rank for reorder_to_layered_format (§2.1).
_PRIORITY_ORDER: dict[str, int] = {
    "chapter-plan": 1,
    "book_spine": 2,
    "book_strata": 3,
    "volume_summaries": 4,
    "arcs": 5,
    "chapter_summaries": 6,
    "world_rules": 7,
    "style_profile": 7,
    "audit_drift": 7,
}

# P1-P7 section labels in the final rendered document.
_P_TITLES: list[tuple[str, str]] = [
    ("P1", "章节备忘"),
    ("P2", "书脊（L5）"),
    ("P3", "当前大弧（L4）"),
    ("P4", "当前卷摘要（L3）"),
    ("P5", "当前弧段（L2）"),
    ("P6", "近章拍点（L1）"),
    ("P7", "世界铁律与文风"),
]

# Ending diversity classification patterns (§2.1).
_ENDING_PATTERNS: dict[str, str] = {
    "cliffhanger": r"(突然|猛然|就在此时|一声|眼前一|[？?]$)",
    "hook": r"(但|然而|却|不过|还[有存]|等待|尚未|不知)",
    "resolution": r"(终于|最后|就这样|[。！]$)",
    "reflection": r"(回想|想起|原来|或许|也许|大概)",
    "transition": r"(第二天|次日|翌日|接下来|之后|随后)",
}


@dataclass
class Section:
    """A single curated context section.

    Mirrors ``ContextSection`` from ``context_assemble`` but is independent
    so curation doesn't couple to assembly internals.
    """

    source: str
    priority: float
    text: str
    category: str = ""
    estimated_tokens: int = 0


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def curate_context(project_dir: Path, chapter: int) -> str:
    """Curate the assembled context into a structured 9-section format.

    Replaces the ``shenbi-context-composing`` LLM call with deterministic
    Python operations: section reordering, ending diversity check,
    hook debt briefing generation.

    Args:
        project_dir: Project root directory.
        chapter: Chapter number (1-indexed).

    Returns:
        A markdown string with 9 curated sections.
    """
    project_dir = Path(project_dir)

    # 1. Read assembled context
    ctx_path = project_dir / "context" / f"chapter-{chapter}-context.md"
    if not ctx_path.exists():
        log.info("context_curation_no_assembled_context", chapter=chapter)
        return _generate_minimal_context(project_dir, chapter)

    assembled = ctx_path.read_text(encoding="utf-8")

    # 2. Reorder flat sections into P1-P7 hierarchy
    sections = _reorder_to_layered_format(assembled, chapter, project_dir)

    # 3. Check ending diversity (deterministic regex)
    ending_table = _check_ending_diversity(project_dir, chapter)

    # 4. Build hook debt briefing (deterministic data aggregation)
    hook_briefing = _build_hook_debt_briefing(project_dir, chapter)

    # 5. Render 9-section output
    return _render_context_document(sections, ending_table, hook_briefing)


# ---------------------------------------------------------------------------
# Section reordering
# ---------------------------------------------------------------------------


def _reorder_to_layered_format(
    assembled: str,
    chapter: int,
    project_dir: Path,
) -> list[Section]:
    """Reorder flat Route A/B/C results into P1-P7 priority layers.

    Parses ``## route-X:entity`` sections from assembled context, sorts by
    priority, and prepends the chapter plan as P1 if available.
    """
    sections = _parse_assembled_sections(assembled)

    def _sort_key(s: Section) -> int:
        for prefix, prio in _PRIORITY_ORDER.items():
            if prefix in s.source.lower():
                return prio
        return 99  # unknown → bottom

    sections.sort(key=_sort_key)

    # Load the chapter plan as P1 if not already in assembled results.
    plan_path = project_dir / "plans" / f"chapter-{chapter}-plan.md"
    if plan_path.exists():
        plan_text = plan_path.read_text(encoding="utf-8")
        plan_section = Section(
            source="P1 章节备忘",
            priority=1.0,
            text=plan_text,
            category="plan",
            estimated_tokens=int(len(plan_text) * 1.5),
        )
        sections.insert(0, plan_section)

    return sections


def _parse_assembled_sections(assembled: str) -> list[Section]:
    """Parse flat Route A/B/C results from assembled context markdown.

    The assembled context is a flat series of ``## route-X:entity_id`` H2
    sections. Extracts each into a ``Section`` with source, text, category,
    and priority.
    """
    sections: list[Section] = []
    # Split on H2 headers that start with "## route-".
    parts = re.split(r"\n(?=## route-[abc]:)", assembled)
    for part in parts:
        header_match = re.match(r"## (route-[abc]):(.+)", part)
        if not header_match:
            # Could be a stray header or the first chunk before any route header.
            # Try to match anywhere in the part.
            inner = re.search(r"^## (route-[abc]):(.+)$", part, re.MULTILINE)
            if inner:
                header_match = inner
            else:
                continue

        category = header_match.group(1)
        source_id = header_match.group(2).strip()
        text = part[header_match.end() :].strip()
        sections.append(
            Section(
                source=f"{category}:{source_id}",
                priority={"route-a": 1.0, "route-b": 0.8, "route-c": 0.6}.get(
                    category, 0.5
                ),
                text=text,
                category=category,
                estimated_tokens=int(len(text) * 1.5),
            )
        )
    return sections


# ---------------------------------------------------------------------------
# Minimal context fallback
# ---------------------------------------------------------------------------


def _generate_minimal_context(project_dir: Path, chapter: int) -> str:
    """Fallback when assembled context is missing (early ramp-up chapters).

    Returns a minimal 9-section context with just the chapter plan as P1
    and placeholder text for all other sections.
    """
    plan_path = project_dir / "plans" / f"chapter-{chapter}-plan.md"
    plan_text = (
        plan_path.read_text(encoding="utf-8") if plan_path.exists() else "(no plan yet)"
    )
    return (
        f"## P1 章节备忘\n\n{plan_text}\n\n"
        f"## P2 书脊（L5）\n\n(未产出)\n\n"
        f"## P3 当前大弧（L4）\n\n(未产出)\n\n"
        f"## P4 当前卷摘要（L3）\n\n(未产出)\n\n"
        f"## P5 当前弧段（L2）\n\n(未产出)\n\n"
        f"## P6 近章拍点（L1）\n\n(未产出)\n\n"
        f"## P7 世界铁律与文风\n\n(未产出)\n\n"
        f"## 近章结尾多样性\n\n(不足3章)\n\n"
        f"## Hook 债务简报\n\n(无活跃伏笔)\n"
    )


# ---------------------------------------------------------------------------
# Ending diversity check
# ---------------------------------------------------------------------------


def _check_ending_diversity(project_dir: Path, chapter: int) -> str:
    """Check last 3 chapters' endings for consecutive same-type patterns.

    Reads actual chapter files (not summaries — SKILL.md 铁律 4).
    Classifies each ending's last paragraph against ``_ENDING_PATTERNS``
    and warns when 3+ consecutive chapters share the same type.

    Returns a markdown table string.
    """
    project_dir = Path(project_dir)
    if chapter < 4:
        return (
            "| 章节 | 结尾方式 | 末段首句（前 20 字） |\n"
            "|------|---------|-------------------|\n"
            "| (不足3章) | — | — |\n"
        )

    rows: list[str] = []
    ending_types: list[str] = []
    for offset in range(3, 0, -1):
        ch = chapter - offset
        ch_path = project_dir / "chapters" / f"chapter-{ch}.md"
        if not ch_path.exists():
            rows.append(f"| {ch} | (未产出) | — |")
            ending_types.append("missing")
            continue

        text = ch_path.read_text(encoding="utf-8")
        # Get last paragraph, skipping meta blocks and headers.
        paragraphs = [
            p.strip()
            for p in text.split("\n\n")
            if p.strip()
            and not p.strip().startswith("<!--")
            and not p.strip().startswith("## ")
        ]
        last_p = paragraphs[-1] if paragraphs else ""
        first_20 = last_p[:20].replace("\n", " ")

        # Classify ending type.
        etype = "other"
        for name, pattern in _ENDING_PATTERNS.items():
            if re.search(pattern, last_p):
                etype = name
                break

        ending_types.append(etype)
        rows.append(f"| {ch} | {etype} | {first_20} |")

    # Check for 3+ consecutive same type.
    warning = ""
    if len(ending_types) >= 3 and len(set(ending_types[-3:])) == 1:
        warning = (
            f"\n⚠️ 连续 3 章相同结尾方式 ({ending_types[-1]})，本章必须避免！\n"
        )

    # Monitor classifier health: if "other" rate exceeds 20%, patterns may have
    # drifted.
    non_missing = [t for t in ending_types if t != "missing"]
    if non_missing:
        other_rate = non_missing.count("other") / len(non_missing)
        if other_rate > 0.2:
            log.warning(
                "ending_classifier_drift",
                chapter=chapter,
                other_rate=f"{other_rate:.0%}",
            )

    header = (
        "| 章节 | 结尾方式 | 末段首句（前 20 字） |\n"
        "|------|---------|-------------------|\n"
    )
    return header + "\n".join(rows) + warning


# ---------------------------------------------------------------------------
# Hook debt briefing
# ---------------------------------------------------------------------------


def _build_hook_debt_briefing(project_dir: Path, chapter: int) -> str:
    r"""Generate MH*/H* two-tier hook debt briefing from truth files.

    Reads ``truth/pending_hooks.md`` (YAML frontmatter with ``hooks`` list)
    and ``truth/book_spine.md`` (for master hooks). Renders a two-tier table:

    * **MH\*** — master hooks from book_spine, with urgency warning when
      ``silence > max_distance * 0.7``.
    * **H\*** — arc-level hooks from pending_hooks that don't start with ``MH``.

    Args:
        project_dir: Project root directory.
        chapter: Current chapter number (used to calculate silence).

    Returns:
        A markdown string with the two-tier hook debt briefing table.
    """
    hooks = _read_pending_hooks(project_dir)
    spine_hooks = _read_spine_master_hooks(project_dir)

    # MH* — from book_spine master hooks.
    mh_rows: list[str] = []
    for h in spine_hooks:
        last_reinforced = h.get("last_reinforced", h.get("plant_chapter", 0))
        silence = chapter - last_reinforced if last_reinforced else 999
        max_dist = h.get("max_distance", 999)
        urgency = "URGENT" if max_dist > 0 and silence > max_dist * 0.7 else ""
        mh_rows.append(
            f"| {h['id']} | {h.get('content', '?')} | {h.get('state', '?')} | "
            f"{h.get('last_reinforced', '?')} | {silence} | {urgency or 'advance'} |"
        )

    # H* — from pending_hooks non-MH hooks.
    h_rows: list[str] = []
    for h in hooks:
        if h.get("id", "").startswith("MH"):
            continue
        last_reinforced = h.get("last_reinforced", h.get("plant_chapter", 0))
        silence = chapter - last_reinforced if last_reinforced else 999
        h_rows.append(
            f"| {h['id']} | {h.get('content', '?')} | {h.get('state', '?')} | "
            f"{h.get('last_reinforced', '?')} | {silence} | |"
        )

    briefing = "## Hook 债务简报\n\n"
    briefing += "### 主线钩子（MH*）\n\n"
    briefing += (
        "| Hook ID | 内容 | 状态 | 最后推进章 | 沉默章数 | 操作建议 |\n"
        "|---------|------|------|----------|---------|---------|\n"
    )
    briefing += (
        "\n".join(mh_rows) if mh_rows else "| (无) | — | — | — | — | — |\n"
    )

    briefing += "\n### 弧内钩子（H*）\n\n"
    briefing += (
        "| Hook ID | 内容 | 状态 | 最后推进章 | 沉默章数 |\n"
        "|---------|------|------|----------|---------|\n"
    )
    briefing += (
        "\n".join(h_rows) if h_rows else "| (无) | — | — | — | — |\n"
    )

    return briefing


def _read_pending_hooks(project_dir: Path) -> list[dict[str, Any]]:
    """Read the pending hooks list from ``truth/pending_hooks.md``.

    Parses YAML frontmatter. Returns an empty list when the file is missing,
    empty, or has unparseable frontmatter (ramp-up tolerance).
    """
    hooks_file = project_dir / "truth" / "pending_hooks.md"
    if not hooks_file.exists():
        log.info("pending_hooks_missing", path=str(hooks_file))
        return []

    text = hooks_file.read_text(encoding="utf-8")
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            try:
                fm = yaml.safe_load(parts[1]) or {}
                hooks = fm.get("hooks", [])
                if isinstance(hooks, list):
                    return hooks
            except Exception:
                log.warning("pending_hooks_yaml_parse_error", path=str(hooks_file))

    return []


def _read_spine_master_hooks(project_dir: Path) -> list[dict[str, Any]]:
    """Read master hooks from ``truth/book_spine.md``.

    Extracts MH* entries from the book spine YAML frontmatter (or inline
    ``hook_master_list``). Returns an empty list when the file is missing
    or unparseable (ramp-up tolerance).
    """
    spine_path = project_dir / "truth" / "book_spine.md"
    if not spine_path.exists():
        log.info("book_spine_missing", path=str(spine_path))
        return []

    text = spine_path.read_text(encoding="utf-8")

    # Try YAML frontmatter first.
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            try:
                fm = yaml.safe_load(parts[1]) or {}
                hooks = fm.get("hook_master_list", fm.get("master_hooks", []))
                if isinstance(hooks, list):
                    return hooks
            except Exception:
                log.warning("spine_yaml_parse_error", path=str(spine_path))

    # Fallback: scan for inline MH* entries in markdown tables.
    # Look for table rows that start with | MH
    mh_hooks: list[dict[str, Any]] = []
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped.startswith("| MH"):
            # Parse table row: | MH001 | content | state | chapter |
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            if len(cells) >= 2:
                hook: dict[str, Any] = {"id": cells[0].strip()}
                if len(cells) >= 2:
                    hook["content"] = cells[1].strip()
                if len(cells) >= 3:
                    hook["state"] = cells[2].strip()
                if len(cells) >= 4:
                    try:
                        hook["last_reinforced"] = int(cells[3].strip())
                    except (ValueError, TypeError):
                        pass
                mh_hooks.append(hook)

    return mh_hooks


# ---------------------------------------------------------------------------
# Document rendering
# ---------------------------------------------------------------------------


def _render_context_document(
    sections: list[Section],
    ending_table: str,
    hook_briefing: str,
) -> str:
    """Render the curated 9-section context document.

    Maps sections to P1-P7 titles based on source/priority, then appends
    the ending diversity table and hook debt briefing as sections 8 and 9.
    """
    # Group sections by P-tier.
    p_buckets: dict[int, list[Section]] = {i: [] for i in range(1, 8)}

    for s in sections:
        assigned = False
        for prefix, prio in _PRIORITY_ORDER.items():
            if prefix in s.source.lower():
                p_buckets.setdefault(prio, []).append(s)
                assigned = True
                break
        if not assigned:
            p_buckets.setdefault(7, []).append(s)

    parts: list[str] = []
    for idx, (p_label, p_title) in enumerate(_P_TITLES, start=1):
        parts.append(f"## {p_label} {p_title}\n")
        bucket = p_buckets.get(idx, [])
        if bucket:
            for s in bucket:
                parts.append(f"\n{s.text}\n")
        else:
            parts.append("\n(未产出)\n")
        parts.append("")

    # Section 8: Ending diversity.
    parts.append("## 近章结尾多样性\n")
    parts.append(ending_table)
    parts.append("")

    # Section 9: Hook debt briefing.
    parts.append(hook_briefing)

    return "\n".join(parts)


__all__ = [
    "Section",
    "curate_context",
    "_check_ending_diversity",
    "_build_hook_debt_briefing",
    "_reorder_to_layered_format",
    "_parse_assembled_sections",
    "_generate_minimal_context",
    "_read_pending_hooks",
    "_read_spine_master_hooks",
    "_render_context_document",
]
