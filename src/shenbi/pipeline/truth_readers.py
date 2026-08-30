"""Single-source table-aware readers for truth/pending_hooks.md (SDD #21 R2).

The production ``pending_hooks.md`` (written by shenbi-foreshadowing-track /
shenbi-state-settling) is a Chinese markdown TABLE format:

* ``### 文本强化确认`` presentation table — ``当前生命周期`` column carries
  transition+annotation strings (``RELEVANT→TRIGGERED(待track确认)``) — used
  only for CROSS-CHECKING, never as the authoritative state.
* ``### 本章操作`` lifecycle table — ``前状态/后状态`` columns; the 后状态
  (post-state) column is the AUTHORITATIVE state source.
* ``### 培育间隔检查`` interval table — ``last_reinforced推定`` column
  (``ch54(...)``) is the best available last_reinforced estimate.
* ``### 距离上限逼近`` distance table — ``种植章``/``max_distance(14)``
  columns; note the default max_distance is embedded in the HEADER cell name,
  rows may repeat it.

Field-mapping and arbitration rules (spec #21 R2, audit r1 C2 + r2 I-2/I-3):

* ``state`` — lifecycle-table 后状态 wins; presentation column is
  cross-check only. ``A→B(批注)`` normalizes to ``B`` (after the last arrow,
  parenthetical annotation stripped).
* ``last_reinforced`` — from the interval table's ``chN`` token, capped by
  the frontmatter ``last_chapter`` (UPPER bound — a hook cannot have been
  reinforced later than the last processed chapter; treating it as a lower
  bound would mask OVERDUE crises, the exact failure R2 fixes).
* ``plant_chapter`` / ``max_distance`` — from the distance table; the value
  embedded in the ``max_distance(N)`` header cell is the default when a row
  cell is not a bare integer. That table semantically lists only hooks NEAR
  their distance cap — a missing row means no data, NOT a default value.
* Any field that cannot be derived is ``None`` (never a fabricated default;
  consumers must ``isinstance(x, int)``-guard numeric use and log skips).

All downstream readers (context_curation, gates/g6 G6.7, truth_index body
source) MUST go through :func:`read_pending_hooks` — no second parser.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from shenbi.logging import get_logger

log = get_logger(__name__)

#: Hook ids as written in production tables: ``P0-4``, ``P0-9``, plus the
#: legacy canonical ``H01``/``MH02`` forms (mirrors truth_index._HOOK_ID_RE).
_HOOK_ID_RE = re.compile(r"(?:MH\d+|[HM]\d+|P\d*-\d+)")

_CH_RE = re.compile(r"ch\s*(\d+)", re.IGNORECASE)

#: State annotation forms: ``RELEVANT→TRIGGERED(待track确认)`` / ``A -> B``.
_STATE_ARROW_RE = re.compile(r"(?:→|->)")

_STATE_ENUM = {"PLANTED", "RELEVANT", "TRIGGERED", "RESOLVED"}


def _cells(line: str) -> list[str] | None:
    """Split a markdown table row into stripped cells, or None if not a row."""
    s = line.strip()
    if not (s.startswith("|") and s.endswith("|")) or len(s) < 2:
        return None
    return [c.strip() for c in s[1:-1].split("|")]


def _is_separator(cells: list[str]) -> bool:
    return bool(cells) and all(re.fullmatch(r":?-{3,}:?", c) for c in cells)


def _hook_id(cell: str) -> str | None:
    m = _HOOK_ID_RE.search(cell)
    return m.group(0) if m else None


def _norm_state(raw: str) -> str | None:
    """Normalize ``RELEVANT→TRIGGERED(待track确认)`` to ``TRIGGERED``.

    Takes the segment after the LAST arrow, strips parenthetical annotations,
    uppercases. Returns ``None`` when nothing parseable remains (missing data
    must stay ``None`` — no fabricated default).
    """
    seg = _STATE_ARROW_RE.split(raw.strip())[-1]
    seg = re.sub(r"（[^）]*）|\([^)]*\)", "", seg).strip().upper()
    return seg if seg in _STATE_ENUM else None


def _int_or_none(cell: str) -> int | None:
    s = cell.strip()
    return int(s) if s.isdigit() else None


def _split_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """Minimal frontmatter split (no yaml dependency for one scalar)."""
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    fm_line = re.search(r"^last_chapter:\s*(\d+)\s*$", parts[1], re.MULTILINE)
    body = parts[2]
    return ({"last_chapter": int(fm_line.group(1))} if fm_line else {}), body


def _parse_tables(body: str) -> dict[str, dict[str, Any]]:
    """Parse the four production tables into per-hook partial records."""
    hooks: dict[str, dict[str, Any]] = {}
    lines = body.split("\n")

    def _ensure(hid: str) -> dict[str, Any]:
        return hooks.setdefault(hid, {"id": hid})

    i = 0
    while i < len(lines):
        cells = _cells(lines[i])
        if cells is None or _is_separator(cells):
            i += 1
            continue
        header = [c.lower() for c in cells]
        joined = "|".join(header)

        if "当前生命周期" in joined:
            # Presentation table — cross-check state source + content label.
            for j in range(i + 2, len(lines)):  # skip separator row
                row = _cells(lines[j])
                if row is None or _is_separator(row):
                    break
                if len(row) < 2:
                    continue
                hid = _hook_id(row[0])
                if hid is None:
                    continue
                rec = _ensure(hid)
                rec.setdefault("presentation_state", _norm_state(row[1]))
                paren = re.search(r"[（(]([^）)]*)[）)]", row[0])
                if paren and not rec.get("content"):
                    rec["content"] = paren.group(1).strip()
            i += 1
            continue

        if "后状态" in joined and "前状态" in joined:
            # Lifecycle table — AUTHORITATIVE state. Rows are ordered
            # Hook ID | 操作 | 前状态 | 后状态 | 文本位置; locate by header.
            op_idx = next((k for k, h in enumerate(header) if "操作" in h), None)
            post_idx = next((k for k, h in enumerate(header) if "后状态" in h), None)
            for j in range(i + 2, len(lines)):
                row = _cells(lines[j])
                if row is None or _is_separator(row):
                    break
                hid = _hook_id(row[0]) if row else None
                if hid is None or post_idx is None or post_idx >= len(row):
                    continue
                rec = _ensure(hid)
                state = _norm_state(row[post_idx])
                if state is not None:
                    rec["state"] = state
                if op_idx is not None and op_idx < len(row) and row[op_idx].strip() == "REINFORCE":
                    rec["reinforced_here"] = True
            i += 1
            continue

        if "last_reinforced" in joined or "间隔" in joined:
            # Interval table — Hook ID | last_reinforced推定 | 本章 | 间隔 | 状态.
            for j in range(i + 2, len(lines)):
                row = _cells(lines[j])
                if row is None or _is_separator(row):
                    break
                hid = _hook_id(row[0]) if row else None
                if hid is None or len(row) < 2:
                    continue
                m = _CH_RE.search(row[1])
                if m:
                    _ensure(hid)["last_reinforced"] = int(m.group(1))
                elif "本章" in row[1]:
                    # "ch56(本章…)" — reinforced in the current chapter; the
                    # chapter number comes from a later column or last_chapter.
                    cm = _CH_RE.search(" ".join(row[2:]))
                    if cm:
                        _ensure(hid)["last_reinforced"] = int(cm.group(1))
            i += 1
            continue

        if "max_distance" in joined:
            # Distance table — the default cap is embedded in the header cell
            # name ``max_distance(14)``; per-row cells may repeat it.
            md_idx = next((k for k, h in enumerate(header) if "max_distance" in h), None)
            plant_idx = next((k for k, h in enumerate(header) if "种植章" in h), None)
            header_md = None
            if md_idx is not None:
                m = re.search(r"max_distance\s*[（(]\s*(\d+)\s*[）)]", header[md_idx])
                if m:
                    header_md = int(m.group(1))
            for j in range(i + 2, len(lines)):
                row = _cells(lines[j])
                if row is None or _is_separator(row):
                    break
                hid = _hook_id(row[0]) if row else None
                if hid is None:
                    continue
                rec = _ensure(hid)
                if plant_idx is not None and plant_idx < len(row):
                    rec["plant_chapter"] = _int_or_none(row[plant_idx])
                if md_idx is not None and md_idx < len(row):
                    rec["max_distance"] = _int_or_none(row[md_idx])
                if rec.get("max_distance") is None:
                    rec["max_distance"] = header_md
                if rec["plant_chapter"] is None:
                    rec.pop("plant_chapter", None)
            i += 1
            continue

        i += 1

    return hooks


def read_pending_hooks(project_dir: Path) -> list[dict[str, Any]]:
    """Read hook records from ``truth/pending_hooks.md`` (single parser).

    Returns ``[]`` when the file is missing (ramp-up tolerance). Every field
    that cannot be derived from the real table format is ``None`` — callers
    must guard numeric use (``isinstance(x, int)``) and log skips instead of
    substituting defaults (no fabricated 0/999 silence values).
    """
    hooks_file = project_dir / "truth" / "pending_hooks.md"
    if not hooks_file.exists():
        log.info("pending_hooks_missing", path=str(hooks_file))
        return []

    text = hooks_file.read_text(encoding="utf-8")
    fm, body = _split_frontmatter(text)
    last_chapter = fm.get("last_chapter")

    hooks = _parse_tables(body)

    results: list[dict[str, Any]] = []
    for hid, rec in hooks.items():
        state = rec.get("state") or rec.get("presentation_state")
        last_reinforced = rec.get("last_reinforced")
        if last_reinforced is None and rec.get("reinforced_here") and isinstance(last_chapter, int):
            # A REINFORCE row in the latest chapter's lifecycle table pins
            # last_reinforced to that chapter.
            last_reinforced = last_chapter
        if isinstance(last_chapter, int) and isinstance(last_reinforced, int):
            # Upper bound: a hook cannot have been reinforced after the last
            # processed chapter (spec R2, audit r2 I-2).
            last_reinforced = min(last_reinforced, last_chapter)
        if state is None or last_reinforced is None or rec.get("plant_chapter") is None:
            log.info(
                "pending_hooks_field_unavailable",
                hook_id=hid,
                state=state,
                last_reinforced=last_reinforced,
                plant_chapter=rec.get("plant_chapter"),
            )
        results.append(
            {
                "id": hid,
                "state": state,
                "last_reinforced": last_reinforced,
                "plant_chapter": rec.get("plant_chapter"),
                "max_distance": rec.get("max_distance"),
                "content": rec.get("content"),
            }
        )
    if not results:
        log.warning("pending_hooks_no_records_parsed", path=str(hooks_file))
    return results
