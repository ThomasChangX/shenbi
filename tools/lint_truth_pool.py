"""Pool two-table reconciliation lint (GO①, phase3 终报条件①).

``truth/pending_hooks.md`` carries TWO representations of every hook — the
总览 table row and the ``### <id>`` detail section — with independent
writer disciplines and (before the derivation-on-write fix) no invariant
enforcement: the phase3 overview silently froze ch15-36 while details kept
advancing, and the drift was only discovered by hand at book closure
(ch118, debt overstated 1.8×).

Checks (findings print as a table; exit 1 when any remain):
- ``section_without_row``  — detail section with no 总览 row (repairable)
- ``row_state_mismatch``   — 总览 当前生命周期/种植章/兑现章 disagrees with the
                             detail section's fields (repairable)
- ``row_without_section``  — 总览 row with no detail section (report-only)
- ``planted_with_resolve`` — lifecycle PLANTED but 兑现章 non-empty: a
                             contradiction needing evidence-based disposition,
                             NOT auto-repair (the CP-006/MH10 shape)
- ``tombstone_has_row``    — archived tombstone section still holds a live row

``--repair`` runs :func:`shenbi.pipeline.truth_io.sync_pool_overview_rows`
(the same derivation the merge layer now applies on every hook-section
landing) over the whole file, fixing the repairable classes.

CLI: ``uv run python tools/lint_truth_pool.py <project_dir> [--repair]``
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from shenbi.pipeline.truth_io import canon_hook_id, sync_pool_overview_rows

_HOOK_ID_RE = re.compile(r"(?<![A-Za-z0-9-])(MH|CP)-?(\d{1,4})(?!\d)")
_FIELD_RE = re.compile(
    r"^-\s+(lifecycle_state|plant_chapter|resolve_chapter|archived_to)\s*[:：]\s*(.*)$"
)

#: Overview column indices (genesis EXACT-table contract): 1=当前生命周期,
#: 3=兑现章（卷）.
_COL_LIFECYCLE = 1
_COL_RESOLVE = 3


@dataclass(frozen=True)
class Finding:
    """One lint hit: check name, hook id, human-readable message."""

    check: str
    hook: str
    message: str


def _cells(line: str) -> list[str]:
    """Split a markdown table row into stripped cells."""
    return [c.strip() for c in line.strip().strip("|").split("|")]


def _section_map(text: str) -> dict[str, dict[str, str]]:
    """hook_id → parsed stable fields of its ``###`` detail section."""
    sections: dict[str, dict[str, str]] = {}
    current: str | None = None
    for line in text.splitlines():
        hm = re.match(r"^#{2,6}\s+((?:MH|H|CP)-?\d{1,4})\b", line.strip())
        if hm:
            current = canon_hook_id(hm.group(1))
            sections.setdefault(current, {})
            continue
        if current is None:
            continue
        fm = _FIELD_RE.match(line.strip())
        if fm:
            sections[current].setdefault(fm.group(1), fm.group(2).strip())
    return sections


def _row_map(text: str) -> dict[str, list[str]]:
    """hook_id → overview row cells (first table after ``## 总览``)."""
    rows: dict[str, list[str]] = {}
    m_ov = re.search(r"^##\s*总览\s*$", text, re.MULTILINE)
    if m_ov is None:
        return rows
    rest = text[m_ov.end() :]
    m_next = re.search(r"^##\s+\S", rest, re.MULTILINE)
    body = rest[: m_next.start()] if m_next is not None else rest
    for line in body.splitlines():
        s = line.strip()
        if not s.startswith("|"):
            continue
        cells = _cells(s)
        if len(cells) <= _COL_LIFECYCLE or cells[0].startswith("Hook"):
            continue
        idm = _HOOK_ID_RE.search(cells[0])
        if idm is not None:
            rows.setdefault(canon_hook_id(f"{idm.group(1)}{idm.group(2)}"), cells)
    return rows


def lint_pool(text: str) -> list[Finding]:
    """Reconcile the pool's two representations; returns the finding list."""
    findings: list[Finding] = []
    sections = _section_map(text)
    rows = _row_map(text)

    for hid, fields in sections.items():
        if "archived_to" in fields:
            if hid in rows:
                findings.append(
                    Finding("tombstone_has_row", hid, "archived tombstone still holds a 总览 row")
                )
            continue
        if hid not in rows:
            findings.append(Finding("section_without_row", hid, "detail section has no 总览 row"))
            continue
        cells = rows[hid]
        state = fields.get("lifecycle_state")
        if state and cells[_COL_LIFECYCLE] and cells[_COL_LIFECYCLE] != state:
            findings.append(
                Finding(
                    "row_state_mismatch",
                    hid,
                    f"当前生命周期 row={cells[_COL_LIFECYCLE]!r} vs section={state!r}",
                )
            )
        rc = fields.get("resolve_chapter", "")
        sec_rc = rc.split("（", 1)[0].split("(", 1)[0].strip()
        row_rc = (
            cells[_COL_RESOLVE].split("（", 1)[0].split("(", 1)[0].strip()
            if len(cells) > _COL_RESOLVE
            else ""
        )
        if sec_rc and row_rc and row_rc != sec_rc:
            findings.append(
                Finding(
                    "row_state_mismatch",
                    hid,
                    f"兑现章 row={cells[_COL_RESOLVE]!r} vs section={rc!r}",
                )
            )

    for hid, cells in rows.items():
        if hid not in sections:
            findings.append(Finding("row_without_section", hid, "总览 row has no detail section"))
        elif (
            cells[_COL_LIFECYCLE] == "PLANTED"
            and len(cells) > _COL_RESOLVE
            and cells[_COL_RESOLVE].strip() not in ("", "-")
        ):
            findings.append(
                Finding(
                    "planted_with_resolve",
                    hid,
                    f"lifecycle PLANTED but 兑现章={cells[_COL_RESOLVE]!r}"
                    " — needs evidence-based disposition",
                )
            )
    return findings


def main(argv: list[str] | None = None) -> int:
    """CLI entry: lint (and optionally repair) a project's pool."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("project_dir", type=str)
    parser.add_argument(
        "--repair", action="store_true", help="derive stale/missing rows from sections"
    )
    args = parser.parse_args(argv)

    pool_path = Path(args.project_dir) / "truth" / "pending_hooks.md"
    if not pool_path.is_file():
        sys.stdout.write(f"FAIL: {pool_path} not found\n")
        return 2
    text = pool_path.read_text(encoding="utf-8")

    findings = lint_pool(text)
    if findings and args.repair:
        repaired = sync_pool_overview_rows(text)
        if repaired != text:
            pool_path.write_text(repaired, encoding="utf-8")
            sys.stdout.write("repaired: overview rows re-derived from sections\n")
        findings = lint_pool(repaired)

    if not findings:
        sys.stdout.write("OK: pool two-table reconciliation clean\n")
        return 0
    for f in findings:
        sys.stdout.write(f"FAIL [{f.check}] {f.hook}: {f.message}\n")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
