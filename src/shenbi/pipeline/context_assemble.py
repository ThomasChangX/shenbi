"""Context assembly: three-route retrieval + deterministic rerank (spec §7.1-7.4).

Integrates the three retrieval routes into a curated context package:
    - Route A: entity index (deterministic, weight 1.0 for P1 direct involvement)
    - Route B: embedding search (bge-large-zh, weight = cosine_similarity * 0.8)
    - Route C: fixed rule routing (deterministic, weight 0.6)

Candidate entries are reranked by weight (descending), deduplicated by content
hash (keeping the highest-weight copy per §7.1 "多路命中取最高权重"), and trimmed
to the chapter_role token budget (§7.2). The resulting ContextPackage is
materialized to ``context/chapter-N-context.md`` (§7.1 [I1]).

Route B degrades gracefully (§7.3): when the embedding model is unavailable,
the ``route_b_degraded`` flag is set and Routes A+C continue.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from shenbi.logging import get_logger
from shenbi.pipeline.truth_index import (
    build_index,
    extract_entities_from_plan,
    query_index,
)
from shenbi.safe_write import safe_write

log = get_logger(__name__)

# Token budget per chapter_role (spec §7.2). 1 Chinese char ≈ 1.5 tokens.
BUDGET_BY_ROLE: dict[str, int] = {
    "高潮/兑现": 18000,
    "推进/转折": 12000,
    "过渡/铺垫": 8000,
}
DEFAULT_BUDGET = 12000
TOKEN_FACTOR = 1.5

# Bridge activation window: chapters before activation to start surfacing bridges.
_BRIDGE_ACTIVATION_WINDOW = 3

# Route C: always-loaded fixed context files (§7.1 "规则路由").
# volume_map.md is also injected at runtime via _load_volume_context()
# when outline/volume_map.md exists and the chapter falls within a known volume.
_ROUTE_C_FILES: list[tuple[str, str]] = [
    ("truth/book_spine.md", "book_spine"),
    ("truth/audit_drift.md", "audit_drift"),
    ("style/style_profile.md", "style_profile"),
]

# Cap Route C file reads so a runaway audit_drift can't blow the budget alone.
_ROUTE_C_MAX_CHARS = 2000

# Query embedding uses the first N chars of the plan (keeps encode latency bounded).
_PLAN_QUERY_CHARS = 500

_ROLE_RE = re.compile(r"chapter_role:\s*(.+)")


@dataclass
class ContextSection:
    """A single context fragment selected for inclusion.

    Attributes:
        source: Origin route and entity id, e.g. ``route-a:Hero``.
        priority: Rerank weight (1.0 for Route A P1, sim*0.8 for Route B, 0.6 for C).
        text: The fragment's prose content.
        category: Route name (``route-a``, ``route-b``, ``route-c``).
        estimated_tokens: Token estimate: ``int(len(text) * 1.5)`` (§7.2).
    """

    source: str
    priority: float
    text: str
    category: str = ""
    estimated_tokens: int = 0


@dataclass
class ContextPackage:
    """The curated context assembled for one chapter.

    Attributes:
        chapter_role: Role parsed from the plan (determines token budget).
        sections: Ordered list of context fragments after rerank + budget trim.
        total_tokens: Sum of section token estimates.
        route_b_degraded: True when Route B was skipped (§7.3 degradation).
    """

    chapter_role: str | None = None
    sections: list[ContextSection] = field(default_factory=list)
    total_tokens: int = 0
    route_b_degraded: bool = False

    def to_markdown(self) -> str:
        """Render sections as a markdown document with per-section headers."""
        return "\n\n".join(f"## {s.source}\n\n{s.text}\n" for s in self.sections)


def _content_hash(text: str) -> str:
    """Deterministic hash for content-based deduplication."""
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def _parse_chapter_role(plan_text: str) -> str | None:
    """Extract the ``chapter_role:`` value from a chapter plan."""
    m = _ROLE_RE.search(plan_text)
    return m.group(1).strip() if m else None


def _route_a(index: Any, plan_text: str) -> list[dict[str, Any]]:
    """Route A: entity index lookup via known-name matching (weight 1.0)."""
    entities = extract_entities_from_plan(index, plan_text)
    entries = query_index(index, **entities)
    results: list[dict[str, Any]] = []
    for e in entries:
        results.append(
            {
                "source": f"route-a:{e.entity_id}",
                "weight": 1.0,
                "text": f"[{e.category}] {e.entity_id} from {e.file}",
                "id": e.entity_id,
            }
        )
    return results


def _route_b(project_dir: Path, plan_text: str) -> tuple[list[dict[str, Any]], bool]:
    """Route B: embedding cosine search. Returns (results, degraded_flag).

    Embeds the plan text (first 500 chars) and searches the project's
    embedding DB. Degradation (``True``) is returned only when the model is
    unavailable or encoding/search fails (§7.3). When the model works but no
    DB exists or search returns no hits, ``([], False)`` is returned.
    """
    try:
        import importlib

        from shenbi.pipeline.truth_embed import EmbeddingStore, is_embed_available

        if not is_embed_available():
            return [], True

        db_path = project_dir / "truth-embeddings.db"
        if not db_path.exists():
            # Model available but no embeddings indexed — not degradation.
            return [], False

        st = importlib.import_module("sentence_transformers")
        model = st.SentenceTransformer("bge-large-zh")
        query_vec = model.encode(plan_text[:_PLAN_QUERY_CHARS]).astype("<f4").tobytes()

        store = EmbeddingStore(db_path)
        results = store.search_cosine(query_vec, top_k=5)
        store.close()

        return (
            [
                {
                    "source": f"route-b:{r.chunk_id}",
                    "weight": float(r.similarity) * 0.8,
                    "text": r.text,
                    "id": r.chunk_id,
                }
                for r in results
            ],
            False,
        )
    except Exception as e:
        log.warning("route_b_degraded", error=str(e))
        return [], True


def _route_c(project_dir: Path) -> list[dict[str, Any]]:
    """Route C: always-load fixed context files (weight 0.6)."""
    results: list[dict[str, Any]] = []
    for fname, label in _ROUTE_C_FILES:
        p = project_dir / fname
        if p.exists():
            results.append(
                {
                    "source": f"route-c:{label}",
                    "weight": 0.6,
                    "text": p.read_text(encoding="utf-8")[:_ROUTE_C_MAX_CHARS],
                    "id": label,
                }
            )
    return results


# Volume boundaries are parsed at runtime from volume_map.md via
# triggers.py:read_volume_boundaries() -- NEVER hard-coded. Hard-coding
# ('Volume 1', (1, 15)) duplicates the map and will diverge.


def _resolve_volume_at_runtime(project_dir: Path, chapter: int) -> tuple[str, int, int] | None:
    """Resolve (volume_name, ch_start, ch_end) for a chapter at runtime.

    Parses volume_map.md via triggers.py:read_volume_boundaries() which
    returns a set of last-chapter numbers per volume. We build the
    (start, end) ranges from that set.
    """
    from shenbi.pipeline.triggers import read_volume_boundaries

    boundary_chapters = read_volume_boundaries(project_dir)
    if not boundary_chapters:
        return None

    boundaries_sorted = sorted(boundary_chapters)
    prev_end = 0
    for i, end in enumerate(boundaries_sorted, 1):
        ch_start = prev_end + 1
        if ch_start <= chapter <= end:
            return (f"Volume {i}", ch_start, end)
        prev_end = end
    return None


def _load_volume_context(project_dir: Path, chapter: int) -> str:
    """Extract current volume context from volume_map.md for the given chapter.

    Returns a markdown string containing:
    - Current volume Objective
    - Current chapter's node role and content description
    - Pending cross-volume bridges approaching activation
    """
    vm_path = project_dir / "outline" / "volume_map.md"
    if not vm_path.exists():
        return ""

    volume_map_text = vm_path.read_text(encoding="utf-8")

    # Determine current volume at runtime (NEVER hard-code boundaries)
    resolved = _resolve_volume_at_runtime(project_dir, chapter)
    if resolved is None:
        return ""
    current_volume = resolved[0]

    parts: list[str] = []
    parts.append("## Current Volume Context (from volume_map.md)\n")

    # Extract volume heading line (includes volume number and title)
    vol_heading_pattern = re.compile(
        rf"## ({re.escape(current_volume)}[^\n]*)\n",
    )
    vol_heading_match = vol_heading_pattern.search(volume_map_text)
    if vol_heading_match:
        parts.append(f"**Volume:** {vol_heading_match.group(1).strip()}\n")

    # Extract volume objective
    vol_pattern = re.compile(
        rf"## {re.escape(current_volume)}.*?\n\*\*Objective:\*\*\s*(.+?)(?=\n##|\n###|\Z)",
        re.DOTALL,
    )
    vol_match = vol_pattern.search(volume_map_text)
    if vol_match:
        parts.append(f"**Volume Objective:** {vol_match.group(1).strip()}\n")

    # Extract chapter node info
    chapter_node_pattern = re.compile(
        rf"\|\s*{chapter}\s*\|([^|]+)\|([^|]+)\|",
    )
    node_match = chapter_node_pattern.search(volume_map_text)
    if node_match:
        role = node_match.group(1).strip()
        content = node_match.group(2).strip()
        parts.append(f"**Chapter Role:** {role}")
        parts.append(f"**Expected Content:** {content}\n")

    # Extract pending cross-volume bridges
    bridge_section = volume_map_text.split("## Cross-Volume Bridges")
    if len(bridge_section) > 1:
        bridge_pattern = re.compile(
            r"\|\s*(V\d+-B\d+)\s*\|([^|]+)\|\s*(?:Ch\s*)?(\d+)\s*\|",
        )
        pending_bridges: list[str] = []
        for m in bridge_pattern.finditer(bridge_section[1]):
            bridge_id = m.group(1)
            bridge_content = m.group(2).strip()
            activation_ch = int(m.group(3))
            if chapter >= activation_ch - _BRIDGE_ACTIVATION_WINDOW:
                pending_bridges.append(
                    f"- **{bridge_id}** ({bridge_content}) activates Ch {activation_ch}"
                )
        if pending_bridges:
            parts.append("**Pending Cross-Volume Bridges:**")
            parts.extend(pending_bridges)
            parts.append("")

    return "\n".join(parts)


def rerank_results(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Deterministic rerank: sort by weight desc, dedup by content hash.

    Per §7.1, multi-route hits on the same fragment keep only the highest
    weight. Sorting is stable so equal-weight entries retain insertion order.
    """
    entries.sort(key=lambda e: e.get("weight", 0.0), reverse=True)
    seen_hashes: set[str] = set()
    deduped: list[dict[str, Any]] = []
    for e in entries:
        ch = _content_hash(str(e.get("text", "")))
        if ch in seen_hashes:
            continue
        seen_hashes.add(ch)
        deduped.append(e)
    return deduped


def assemble_context(project_dir: Path | str, chapter_plan_path: str) -> ContextPackage:
    """Assemble a curated context package for one chapter.

    Reads the chapter plan, runs all three retrieval routes, reranks and
    deduplicates, then trims to the chapter_role token budget. Missing source
    files are treated as empty (early-stage projects still yield a package).
    """
    project_dir = Path(project_dir)
    plan_text = (project_dir / chapter_plan_path).read_text(encoding="utf-8")
    chapter_role = _parse_chapter_role(plan_text)

    index = build_index(project_dir)
    route_a = _route_a(index, plan_text)
    route_b, degraded = _route_b(project_dir, plan_text)
    route_c = _route_c(project_dir)

    # Inject volume map context into Route C assembly. Route entries are dicts
    # (source/weight/text/id); rerank_results + the section-building loop convert
    # them to ContextSection(source/priority/text/category/estimated_tokens).
    _chapter_match = re.search(r"chapter-(\d+)", chapter_plan_path)
    _chapter_num = int(_chapter_match.group(1)) if _chapter_match else 0
    volume_ctx = _load_volume_context(project_dir, _chapter_num)
    if volume_ctx:
        route_c.append(
            {
                "source": "route-c:volume_map",
                "weight": 0.6,
                "text": volume_ctx,
                "id": "volume_map",
            }
        )

    ranked = rerank_results(route_a + route_b + route_c)
    budget = BUDGET_BY_ROLE.get(chapter_role or "", DEFAULT_BUDGET)

    sections: list[ContextSection] = []
    total = 0
    for entry in ranked:
        text = str(entry.get("text", ""))
        tokens = int(len(text) * TOKEN_FACTOR)
        if total + tokens > budget:
            break
        source = str(entry.get("source", ""))
        sections.append(
            ContextSection(
                source=source,
                priority=float(entry.get("weight", 0.0)),
                text=text,
                category=source.split(":", maxsplit=1)[0],
                estimated_tokens=tokens,
            )
        )
        total += tokens

    log.info(
        "context_assembled",
        chapter_role=chapter_role,
        sections=len(sections),
        total_tokens=total,
        budget=budget,
        route_b_degraded=degraded,
    )
    return ContextPackage(
        chapter_role=chapter_role,
        sections=sections,
        total_tokens=total,
        route_b_degraded=degraded,
    )


def write_context_file(project_dir: Path | str, chapter: int, pkg: ContextPackage) -> Path:
    """Materialize the context package to ``context/chapter-N-context.md``.

    Uses :func:`safe_write` for atomic, locked persistence (§7.1 [I1]).
    """
    project_dir = Path(project_dir)
    out = project_dir / "context" / f"chapter-{chapter}-context.md"
    safe_write(out, pkg.to_markdown())
    return out


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for ``pipeline-context-assemble``."""
    import argparse

    from shenbi.cli_utils import emit_json
    from shenbi.logging import configure_logging
    from shenbi.status import CommandStatus

    configure_logging()
    parser = argparse.ArgumentParser(prog="pipeline-context-assemble")
    parser.add_argument("build", choices=["build"])
    parser.add_argument("--project-dir", required=True)
    parser.add_argument("--chapter", type=int, required=True)
    args = parser.parse_args(argv)

    plan_path = f"plans/chapter-{args.chapter}-plan.md"
    pkg = assemble_context(args.project_dir, plan_path)
    out = write_context_file(args.project_dir, args.chapter, pkg)

    emit_json(
        {
            "status": CommandStatus.OK,
            "chapter": args.chapter,
            "chapter_role": pkg.chapter_role,
            "sections": len(pkg.sections),
            "total_tokens": pkg.total_tokens,
            "route_b_degraded": pkg.route_b_degraded,
            "output": str(out),
        }
    )
    return 0


__all__ = [
    "BUDGET_BY_ROLE",
    "DEFAULT_BUDGET",
    "TOKEN_FACTOR",
    "ContextPackage",
    "ContextSection",
    "_load_volume_context",
    "assemble_context",
    "main",
    "rerank_results",
    "write_context_file",
]
