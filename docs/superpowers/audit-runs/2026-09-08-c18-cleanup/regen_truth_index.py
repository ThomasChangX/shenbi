#!/usr/bin/env python
"""One-off (SDD #56 C18 T6): regenerate truth-index.json (F1168).

The manual-era index stalls at genesis state (3 top keys / 19 entities) while
``truth/`` holds 13 files. This tool mechanically registers every truth file
into the index — content summaries are NOT regenerated (that would need LLM
dispatch, forbidden by F947); each entry records file presence + mtime
provenance ``c18-regen 2026-09-08``.

Usage:
  uv run python docs/superpowers/audit-runs/2026-09-08-c18-cleanup/\
    regen_truth_index.py <project_dir> [--apply]
"""

from __future__ import annotations

import argparse
import datetime
import json
from pathlib import Path


def main() -> None:
    """CLI entry (dry-run by default)."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("project_dir", type=Path)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    idx_file = args.project_dir / "truth-index.json"
    idx = json.loads(idx_file.read_text(encoding="utf-8"))
    truth_dir = args.project_dir / "truth"

    registered = 0
    for p in sorted(truth_dir.glob("*.md")):
        key = p.stem
        if key in idx.get("files", {}):
            continue
        mtime = datetime.datetime.fromtimestamp(p.stat().st_mtime, tz=datetime.UTC).isoformat()
        idx.setdefault("files", {})[key] = {
            "path": f"truth/{p.name}",
            "bytes": p.stat().st_size,
            "mtime": mtime,
            "provenance": (
                "c18-regen 2026-09-08 (presence registration only; content not re-summarized, F947)"
            ),
        }
        registered += 1

    if args.apply:
        idx_file.write_text(json.dumps(idx, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"APPLIED: {registered} truth files registered")
    else:
        print(f"dry-run: {registered} unregistered truth files")


if __name__ == "__main__":
    main()
