#!/usr/bin/env python3
"""Enforce per-module coverage floors (spec #53 C15 T3).

Reads a coverage.py JSON report and compares each floored module against
tools/module-coverage-floors.json. Exit 1 with per-module detail on breach.
The floor table's data source is the pytest --cov JSON itself — no third
hand-maintained registry (C22 lesson).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def main() -> int:
    """Compare per-module coverage against the floor table."""
    report = Path(sys.argv[1] if len(sys.argv) > 1 else REPO / "coverage.json")
    floors = json.loads((REPO / "tools" / "module-coverage-floors.json").read_text("utf-8"))
    data = json.loads(report.read_text("utf-8"))
    breaches: list[str] = []
    for path, floor in sorted(floors.items()):
        if path.startswith("_"):
            continue
        entry = data["files"].get(path)
        pct = entry["summary"]["percent_covered"] if entry else 0.0
        if pct < floor:
            breaches.append(f"{path}: {pct:.2f}% < floor {floor}")
    if breaches:
        print("module coverage floor breaches:", file=sys.stderr)
        for b in breaches:
            print(f"  {b}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
