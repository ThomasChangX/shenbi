#!/usr/bin/env python3
"""Allowlist-driven threshold reconciliation lint (spec #35 T5).

Scans SKILL.md numeric ranges near an anchored pattern and compares them
against the checker's declared hard bounds. WARN-only in the first cycle
(exit 0 always) so CI is never blocked by a documentation drift; flipping
to FAIL is a deliberate later step once the allowlist has stabilized.

Allowlist format (tools/threshold_allowlist.json):
    {"entries": [{"skill", "pattern", "file", "checker", "bounds": [lo, hi]}]}
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ALLOWLIST = REPO_ROOT / "tools" / "threshold_allowlist.json"
RANGE_RE = re.compile(r"(\d+)\s*[-\u2013]\s*(\d+)\s*%?")  # hyphen or EN dash
WINDOW = 3  # lines around the anchored pattern


def _scan_entry(entry: dict) -> str | None:
    """Return a WARN line for a drifted/missing entry, else None.

    ``pattern`` selects the line(s); ``keyword`` (optional) narrows the scan
    to the text after its occurrence on that line — table rows pack several
    ranges per line (QUEST/FIRE/CONSTELLATION), so the keyword keeps the
    comparison anchored to the column the checker actually enforces.
    """
    file_path = REPO_ROOT / entry["file"]
    checker_path = REPO_ROOT / entry["checker"]
    if not file_path.is_file():
        return f"WARN threshold_entry file_missing skill={entry['skill']} file={entry['file']}"
    if not checker_path.is_file():
        return (
            f"WARN threshold_entry checker_missing skill={entry['skill']}"
            f" checker={entry['checker']}"
        )
    lines = file_path.read_text(encoding="utf-8").splitlines()
    lo, hi = entry["bounds"]
    keyword = entry.get("keyword", "")
    found_any = False
    for line in lines:
        if entry["pattern"] not in line:
            continue
        scope = line[line.index(keyword) + len(keyword) :] if keyword and keyword in line else line
        match = RANGE_RE.search(scope)
        if match is None:
            continue
        found_any = True
        d_lo, d_hi = int(match.group(1)), int(match.group(2))
        if d_hi < lo or d_lo > hi:
            return (
                f"WARN threshold_drift skill={entry['skill']} "
                f"file={entry['file']} found={d_lo}-{d_hi} expected=[{lo}, {hi}]"
            )
    if not found_any:
        return (
            f"WARN threshold_entry no_range_found skill={entry['skill']} "
            f"pattern={entry['pattern']} file={entry['file']}"
        )
    return None


def main(argv: list[str] | None = None) -> int:
    """Entry point: always exits 0 (WARN-only lint)."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--allowlist",
        default=str(DEFAULT_ALLOWLIST),
        help="path to the allowlist JSON (default: tools/threshold_allowlist.json)",
    )
    args = parser.parse_args(argv)

    allow_path = Path(args.allowlist)
    if not allow_path.is_file():
        print(f"WARN allowlist_missing path={allow_path}")
        return 0
    entries = json.loads(allow_path.read_text(encoding="utf-8")).get("entries", [])
    for entry in entries:
        warn = _scan_entry(entry)
        if warn:
            print(warn)
    return 0  # WARN-only: never blocks CI in the first cycle


if __name__ == "__main__":
    sys.exit(main())
