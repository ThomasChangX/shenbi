"""pending_hooks.md canonical dual-source writer (SDD #11 R5 / F637).

Canonical three-part format, same shape as the real fixture
``tests/fixtures/truth-pending_hooks.md``:
  1. YAML frontmatter ``hooks`` list — read by pipeline/context_curation.py,
     pipeline/review_checklist.py, chapter_loop._count_triggered_hooks;
  2. ``## hooks`` YAML body block — read by records/parser.parse_records
     (authority per spec New-F), audit/write_audit.py;
  3. ``## 活跃伏笔`` markdown table — read by records/drift.parse_markdown_table.

Table and YAML block are generated from ONE record set, so
detect_cross_section_drift is empty by construction. Migration
(collect_records) is a union over all legacy shapes — frontmatter-only,
body-YAML-block, and body free-text (the production state per
truth_index.py) — with field-level merge and first-appearance ordering;
serialization is deterministic, so migration is idempotent.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from shenbi.records.drift import MD_HEADER_TO_KEY, parse_markdown_table
from shenbi.records.parser import parse_records, serialize_records
from shenbi.safe_write import safe_write

# Same pattern as pipeline/truth_index.py _HOOK_ID_RE (body free-text IDs).
_HOOK_ID_RE = re.compile(r"(?:[HM]\d+|P\d*-\d+)")

# 8 canonical table columns, sourced from the drift checker's header map.
TABLE_COLUMNS: list[str] = list(MD_HEADER_TO_KEY.values())
_KEY_TO_HEADER: dict[str, str] = {v: k for k, v in MD_HEADER_TO_KEY.items()}

_FM_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?", re.DOTALL)


def _split_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    m = _FM_RE.match(text)
    if m is None:
        return {}, text
    try:
        fm = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError:
        return {}, text
    return fm if isinstance(fm, dict) else {}, text[m.end() :]


def normalize_record(rec: dict[str, Any]) -> dict[str, Any]:
    """Pad every record to the 8-column set; ID-only records get PENDING.

    _values_equal(None, "") is False, so a missing column would fabricate
    drift against the generated table's empty cell.
    """
    out = dict(rec)
    has_state = bool(str(out.get("state") or "").strip())
    for col in TABLE_COLUMNS:
        if col == "state":
            if not has_state:
                out["state"] = "PENDING"
        elif out.get(col) is None:
            out[col] = ""
    return out


def collect_records(text: str) -> list[dict[str, Any]]:
    """Union-migrate all record sources in ``text`` into normalized records.

    Value precedence per key (field-level merge, first non-empty wins):
    body-YAML > frontmatter > markdown table > ID-only. Appearance order
    (output list order): frontmatter order first, then first appearance in
    body sources — stable across round-trips.
    """
    fm, body = _split_frontmatter(text)

    raw_fm = fm.get("hooks")
    fm_records: list[dict[str, Any]] = (
        [h for h in raw_fm if isinstance(h, dict) and h.get("id")]
        if isinstance(raw_fm, list)
        else []
    )
    body_block = parse_records(text)
    table_rows = parse_markdown_table(text)
    free_ids = _HOOK_ID_RE.findall(body)

    # Appearance order: frontmatter first, then body block, then remaining
    # table-only / free-text IDs in scan order.
    order: list[str] = []
    for rec in fm_records + body_block:
        rid = str(rec.get("id"))
        if rid not in order:
            order.append(rid)
    for rid in [*table_rows, *free_ids]:
        if rid not in order:
            order.append(rid)

    # Value precedence: apply lowest-priority sources first, then overwrite.
    layered: list[list[dict[str, Any]]] = [
        [{"id": hid} for hid in free_ids],
        [{"id": rid, **row} for rid, row in table_rows.items()],
        fm_records,
        body_block,  # authoritative — applied last
    ]
    merged: dict[str, dict[str, Any]] = {}
    for source in layered:
        for rec in source:
            rid = str(rec.get("id") or "")
            if not rid:
                continue
            target = merged.setdefault(rid, {})
            for k, v in rec.items():
                if v is None or (isinstance(v, str) and not v.strip()):
                    continue  # empty values never overwrite richer ones
                target[k] = v

    return [normalize_record(merged[rid]) for rid in order]


def _render_table(records: list[dict[str, Any]]) -> str:
    header = "| " + " | ".join(_KEY_TO_HEADER[c] for c in TABLE_COLUMNS) + " |"
    sep = "|" + "|".join("---" for _ in TABLE_COLUMNS) + "|"
    lines = [header, sep]
    for rec in records:
        cells = [str(rec.get(c, "")) for c in TABLE_COLUMNS]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def render_pending_hooks(
    records: list[dict[str, Any]], *, preserve_frontmatter: dict[str, Any] | None = None
) -> str:
    """Render the canonical three-part document from one record set.

    ``preserve_frontmatter`` carries non-hooks frontmatter keys (project /
    last_updated / ...) from the file being rewritten so they survive.
    """
    fm: dict[str, Any] = dict(preserve_frontmatter or {})
    fm["hooks"] = records
    frontmatter = yaml.safe_dump(fm, sort_keys=True, allow_unicode=True, default_flow_style=False)
    return (
        "---\n"
        + frontmatter
        + "---\n\n"
        + "## hooks\n\n"
        + serialize_records(records)
        + "\n\n## 活跃伏笔\n\n"
        + _render_table(records)
        + "\n"
    )


def preserve_keys(text: str) -> dict[str, Any]:
    """Non-hooks frontmatter keys of ``text`` (to survive a canonical rewrite)."""
    fm, _ = _split_frontmatter(text)
    return {k: v for k, v in fm.items() if k != "hooks"}


def write_pending_hooks(
    project_dir: Path,
    records: list[dict[str, Any]],
    preserve_frontmatter: dict[str, Any] | None = None,
) -> None:
    """Public write API mirroring parser.parse_records/serialize_records.

    Currently no in-repo production caller (hook_planting inlines the render
    so it can log its own append event and handle mid-file migration); kept
    as the module's write-side entry point for future writers of
    ``truth/pending_hooks.md``.
    """
    safe_write(
        project_dir / "truth" / "pending_hooks.md",
        render_pending_hooks(records, preserve_frontmatter=preserve_frontmatter),
    )


__all__ = [
    "TABLE_COLUMNS",
    "collect_records",
    "normalize_record",
    "preserve_keys",
    "render_pending_hooks",
    "write_pending_hooks",
]
