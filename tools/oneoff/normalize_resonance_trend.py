#!/usr/bin/env python
"""One-off migration (SDD #21 R1): normalize legacy resonance_trend.md rows.

Legacy framework rows are 7-column with a ``Ch{N}`` key:
    | Ch55 | - | - | - | - | - | 70 |
Skill-contract rows are 9-column with a bare ``{N}`` key:
    | 55 | 推进/转折 | 18 | 12 | 23 | 17 | 70 | mid |  |

Because truth_io key comparison is whole-cell, a legacy ``Ch55`` row and a
new ``55`` row are two distinct rows for the same chapter. This tool rewrites
every legacy row into the 9-column contract layout, dropping it when a
9-column row for the same chapter already exists (the rich row wins).

Idempotent: a second run finds no legacy rows and changes nothing.
Usage: uv run python tools/oneoff/normalize_resonance_trend.py <project_dir> [--apply]
Default is dry-run (prints what would change).
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from shenbi.pipeline.truth_io import split_table_cells
from shenbi.safe_write import safe_write

#: Legacy framework rows are exactly 7 columns (key + 5 placeholders + overall).
_LEGACY_COLUMN_COUNT = 7

_LEGACY_ROW_RE = re.compile(r"^\s*\|\s*Ch(\d+)\s*\|")


def _normalize_text(text: str) -> tuple[str, int, int]:
    """Return (new_text, migrated_count, dropped_count)."""
    # chapter keys already present as 9-column-style bare keys
    rich_keys: set[str] = set()
    for line in text.split("\n"):
        cells = split_table_cells(line)
        if cells is None:
            continue
        key = cells[0]
        if key.isdigit():
            rich_keys.add(key)

    out_lines: list[str] = []
    migrated = dropped = 0
    for line in text.split("\n"):
        m = _LEGACY_ROW_RE.match(line)
        if m is None:
            out_lines.append(line)
            continue
        cells = split_table_cells(line)
        if cells is None or len(cells) != _LEGACY_COLUMN_COUNT:
            out_lines.append(line)
            continue
        chapter = m.group(1)
        overall = cells[6].strip()
        if chapter in rich_keys:
            dropped += 1
            continue
        out_lines.append(f"| {chapter} | - | - | - | - | - | {overall} | - |  |")
        migrated += 1
    return "\n".join(out_lines), migrated, dropped


def main(argv: list[str] | None = None) -> int:
    """CLI entry: normalize one project's resonance_trend.md (dry-run by default)."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project_dir", type=Path)
    parser.add_argument("--apply", action="store_true", help="write changes (default: dry-run)")
    args = parser.parse_args(argv)

    path = args.project_dir / "truth" / "resonance_trend.md"
    if not path.exists():
        print(f"not found: {path}")
        return 1
    new_text, migrated, dropped = _normalize_text(path.read_text(encoding="utf-8"))
    print(f"rows migrated: {migrated}, dropped (rich row exists): {dropped}")
    if args.apply:
        safe_write(path, new_text.encode("utf-8"))
        print(f"written: {path}")
    else:
        print("dry-run; pass --apply to write")
    return 0


if __name__ == "__main__":
    sys.exit(main())
