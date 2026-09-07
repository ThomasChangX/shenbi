"""Carryover list generator for cross-round audit continuity (spec #49 R2, C35).

Extracts status ∈ {verified, open} entries (all severities) from a previous
run's findings-ledger.md into <prev-run>/carryover.md, one entry per line:

    <ID> <severity> <status> <title>

lint_audit_run.py --verify-carryover diffs this list against the next run's
ledger: an entry whose ID never appears in the next run is a broken-carryover
FAIL (the F1177 failure mode).

CLI: uv run python tools/generate_carryover.py <prev-run-dir>
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tools.lint_audit_run import EXPECTED_BODY_COLUMNS, _parse_rows

CARRIED_STATUSES = {"verified", "open"}


def generate_carryover(prev_ledger: Path, out: Path) -> int:
    """Write carryover list for <prev_ledger>; return number of carried entries."""
    rows = _parse_rows(prev_ledger.parent)
    lines: list[str] = [
        "# 承接清单 — 未关闭 verified/open 条目（全 severity，spec #49 R2）",  # noqa: RUF001
        "",
    ]
    count = 0
    for _lineno, _raw, cells in rows:
        if len(cells) < EXPECTED_BODY_COLUMNS:
            continue
        if any(c.lstrip().startswith("→") for c in cells[EXPECTED_BODY_COLUMNS:]):
            continue  # closure annotation present: entry is closed/merged
        status = cells[10].strip()
        if status not in CARRIED_STATUSES:
            continue
        lines.append(f"{cells[0]} {cells[3]} {status} {cells[1]}")
        count += 1
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return count


def main(argv: list[str] | None = None) -> int:
    """CLI entry: generate carryover.md inside the given previous run dir."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("prev_run_dir", type=Path, help="previous audit run directory")
    args = parser.parse_args(argv)
    if not (args.prev_run_dir / "findings-ledger.md").exists():
        print(f"FAIL {args.prev_run_dir}: findings-ledger.md not found")
        return 1
    out = args.prev_run_dir / "carryover.md"
    count = generate_carryover(args.prev_run_dir / "findings-ledger.md", out)
    print(f"PASS carryover: {count} entries -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
