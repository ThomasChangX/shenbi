#!/usr/bin/env python
"""One-off (SDD #56 C18 T6): backfill F1165 missing audit reports.

Backfills 117 audit reports missing from pipeline-state.json chapter_states
(resonance 55 + review-summary 55 + ch56 whole chapter, empty container).

Deterministic: scans on-disk ``audits/chapter-*.md`` and appends missing
relative paths into ``chapter_states[N]["audit_results"]["audit_reports"]``.
Idempotent: a second run adds nothing.

Usage:
  uv run python docs/superpowers/audit-runs/2026-09-08-c18-cleanup/\
    backfill_audit_reports.py <project_dir> [--apply]
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

#: How many backfilled paths to preview per chapter in the log.
_PREVIEW_N = 2


def main() -> None:
    """CLI entry (dry-run by default)."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("project_dir", type=Path)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    state_file = args.project_dir / "pipeline-state.json"
    state = json.loads(state_file.read_text(encoding="utf-8"))
    states = state["chapter_loop"]["chapter_states"]

    on_disk: dict[str, set[str]] = {}
    for p in sorted((args.project_dir / "audits").glob("chapter-*.md")):
        m = re.match(r"chapter-(\d+)-", p.name)
        if m:
            on_disk.setdefault(m.group(1), set()).add(f"audits/{p.name}")

    missing_total = 0
    for ch, disk in sorted(on_disk.items()):
        ar = states.get(ch, {}).setdefault("audit_results", {})
        reports = ar.setdefault("audit_reports", [])
        known = set(reports)
        add = sorted(disk - known)
        if add:
            missing_total += len(add)
            preview = ", ".join(add[:2]) + ("..." if len(add) > _PREVIEW_N else "")
            print(f"ch{ch}: +{len(add)} {preview}")
            if args.apply:
                reports.extend(add)

    if args.apply:
        state_file.write_text(
            json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(f"APPLIED: {missing_total} paths backfilled")
    else:
        print(f"dry-run: {missing_total} paths missing")


if __name__ == "__main__":
    main()
