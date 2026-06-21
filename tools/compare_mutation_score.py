#!/usr/bin/env python3
"""Compare current mutation score to baseline.

Exits 1 if current score drops more than 5% from baseline.
Used by CI in PR-35 (Cluster 05).
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path


def parse_score(baseline_text: str) -> dict[str, float]:
    """Parse baseline file to extract per-module scores."""
    scores: dict[str, float] = {}
    for line in baseline_text.splitlines():
        m = re.match(r"^(src/shenbi/\S+)\s+\d+\s+\d+\s+\d+\s+\d+\s+([\d.]+)", line)
        if m:
            scores[m.group(1)] = float(m.group(2))
    return scores


def main() -> int:
    """Run mutmut and compare to baseline; exit 1 if any module drops > threshold."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", required=True, type=Path)
    parser.add_argument(
        "--threshold",
        type=float,
        default=5.0,
        help="Allowed drop in percentage points (default: 5)",
    )
    args = parser.parse_args()

    if not args.baseline.exists():
        print(f"Baseline file not found: {args.baseline}", file=sys.stderr)
        return 2

    baseline_scores = parse_score(args.baseline.read_text())
    if not baseline_scores:
        print("Baseline file has no parseable scores", file=sys.stderr)
        return 2

    result = subprocess.run(
        ["uv", "run", "mutmut", "results"], check=False, capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"mutmut results failed: {result.stderr}", file=sys.stderr)
        return 2

    current_scores = parse_score(result.stdout)

    failed = False
    for module, baseline_score in baseline_scores.items():
        current = current_scores.get(module, 0.0)
        drop = baseline_score - current
        if drop > args.threshold:
            print(
                f"REGRESSION: {module} dropped {drop:.1f}% "
                f"(baseline {baseline_score}, current {current})"
            )
            failed = True
        else:
            print(f"OK: {module} drop {drop:.1f}% (within {args.threshold}% threshold)")

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
