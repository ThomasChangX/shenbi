"""tests private-import baseline lint (spec #87 T5).

Current set of ``(file, symbol)`` pairs where tests import a private
(``_``-prefixed) member of ``shenbi.pipeline`` must stay a SUBSET of the
version-controlled baseline ``tests/private_imports_baseline.txt`` —
increment = zero (stop-the-bleed; legacy entries shrink as files are
touched). ``--update`` is for human-reviewed regeneration only.

Modes: ``--check`` (exit 1 on new pairs) / ``--update`` (rewrite baseline)
/ ``--report`` (print proposed baseline, write nothing).
"""

import argparse
import ast
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BASELINE = REPO_ROOT / "tests" / "private_imports_baseline.txt"
TESTS_ROOT = REPO_ROOT / "tests"


def collect_private_imports() -> set[tuple[str, str]]:
    """Scan tests/ for private shenbi.pipeline imports (AST, incl. aliased)."""
    pairs: set[tuple[str, str]] = set()
    for py in sorted(TESTS_ROOT.rglob("*.py")):
        try:
            tree = ast.parse(py.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        rel = str(py.relative_to(REPO_ROOT))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.ImportFrom)
                and node.module
                and node.module.startswith("shenbi.pipeline")
            ):
                for alias in node.names:
                    if alias.name.startswith("_") and not alias.name.startswith("__"):
                        pairs.add((rel, alias.name))
    return pairs


def load_baseline() -> set[tuple[str, str]]:
    """Parse the version-controlled baseline file into (file, symbol) pairs."""
    if not BASELINE.exists():
        return set()
    out: set[tuple[str, str]] = set()
    for raw in BASELINE.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        file, _, symbol = line.partition("::")
        if symbol:
            out.add((file, symbol))
    return out


def main() -> int:
    """CLI dispatch over the three modes."""
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="fail on pairs absent from baseline")
    mode.add_argument("--update", action="store_true", help="rewrite baseline (human review only)")
    mode.add_argument("--report", action="store_true", help="print proposed baseline")
    args = parser.parse_args()

    current = collect_private_imports()

    if args.update:
        lines = sorted(f"{f}::{s}" for f, s in current)
        BASELINE.write_text(
            "# tests private-import baseline (spec #87 T5) — subset invariant;\n"
            "# --update is human-reviewed only\n" + "\n".join(lines) + "\n",
            encoding="utf-8",
        )
        print(f"baseline rewritten: {len(lines)} entries")
        return 0

    if args.report:
        for line in sorted(f"{f}::{s}" for f, s in current):
            print(line)
        print(f"{len(current)} entries", file=sys.stderr)
        return 0

    baseline = load_baseline()
    added = current - baseline
    if added:
        print(f"NEW private imports (baseline subset violation): {sorted(added)}")
        print("Fix: import the public name, or human-review + `--update`.", file=sys.stderr)
        return 1
    print(f"private-import baseline OK ({len(current)} current <= {len(baseline)} baseline)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
