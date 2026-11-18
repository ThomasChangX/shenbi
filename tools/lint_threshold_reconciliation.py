#!/usr/bin/env python3
"""Allowlist-driven threshold reconciliation lint (spec #35 T5, re-anchored #93 T1b).

Scans SKILL.md numeric ranges near an anchored pattern and reads the checker's
own hard band constant (CONSTELLATION_HARD_BAND); containment test (SKILL range
must sit inside the hard band); keyword is mandatory (an entry without keyword
validates the wrong column). WARN-only in the first cycle (exit 0 always) so CI
is never blocked by a documentation drift; flipping to FAIL is a deliberate
later step once the allowlist has stabilized.

Allowlist format (tools/threshold_allowlist.json):
    {"entries": [{"skill", "pattern", "keyword", "file", "checker"}]}
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from shenbi.contracts.skills.pacing_design import CONSTELLATION_HARD_BAND

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ALLOWLIST = REPO_ROOT / "tools" / "threshold_allowlist.json"
RANGE_RE = re.compile(r"(\d+)\s*[-\u2013]\s*(\d+)\s*%?")  # hyphen or EN dash


def _scan_entry(entry: dict[str, Any]) -> str | None:
    """Return a WARN line for a drifted/missing entry, else None.

    ``pattern`` selects the line(s); ``keyword`` (mandatory) narrows the scan
    to the text after its occurrence on that line — table rows pack several
    ranges per line (QUEST/FIRE/CONSTELLATION), so the keyword keeps the
    comparison anchored to the column the checker actually enforces; an
    entry without one would validate the wrong column, so it is rejected up
    front (``keyword_missing``). A keyword that vanishes from its line is
    itself drift (same label), never a silent fallback to the whole line.
    Comparison reads the checker's hard band constant
    (CONSTELLATION_HARD_BAND) as the single source — the SKILL range must
    sit fully inside that band (containment, not mere overlap); per-volume
    drift inside that band needs a machine-readable per-volume source and
    is out of scope for this lint.
    """
    file_path = REPO_ROOT / entry["file"]
    checker_path = REPO_ROOT / entry["checker"]
    for label, path in (("file", file_path), ("checker", checker_path)):
        if not path.is_file():
            return (
                f"WARN threshold_entry {label}_missing skill={entry['skill']} "
                f"{label}={entry[label]}"
            )
    keyword = entry.get("keyword", "")
    if not keyword:
        return f"WARN threshold_entry keyword_missing skill={entry['skill']} file={entry['file']}"
    lines = file_path.read_text(encoding="utf-8").splitlines()
    lo, hi = CONSTELLATION_HARD_BAND
    found_any = False
    for line in lines:
        if entry["pattern"] not in line:
            continue
        if keyword not in line:
            return (
                f"WARN threshold_entry keyword_missing skill={entry['skill']} "
                f"keyword={keyword} file={entry['file']}"
            )
        scope = line[line.index(keyword) + len(keyword) :]
        match = RANGE_RE.search(scope)
        if match is None:
            continue
        found_any = True
        d_lo, d_hi = int(match.group(1)), int(match.group(2))
        if not (d_lo >= lo and d_hi <= hi):
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
    return 0  # WARN-only: never blocks CI (--strict FAIL mode lands in spec #93 T1c)


if __name__ == "__main__":
    sys.exit(main())
