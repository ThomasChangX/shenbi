#!/usr/bin/env python3
"""lint_bare_subprocess_json: bare json.loads-on-subprocess-stdout inventory (spec #38 T6).

Scans src/shenbi/ for json.loads calls whose argument involves subprocess
output (stdout / proc_result / r.stdout shapes). Every hit must either live
in process_guard.py (the sanctioned guard primitive) or carry an exemption
comment ``# bare-json-exempt: <reason>`` on the same line.

Lower bound by construction (regex over code lines); the exemption mechanism
backstops the residue.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

SRC = Path("src/shenbi")

PATTERN = re.compile(r"json\.loads\([^)]*(?:stdout|output\)|proc_result)")
EXEMPT = "# bare-json-exempt"
GUARD_FILE = "process_guard.py"

SKIP_SUFFIXES = (".md", ".json", ".yaml", ".txt")


def main() -> int:
    """Entry point: 0 = clean, 1 = violations."""
    violations: list[str] = []
    hits = 0
    for py in sorted(SRC.rglob("*.py")):
        rel = py.relative_to(SRC)
        if str(rel) == GUARD_FILE:
            continue
        for i, line in enumerate(py.read_text(encoding="utf-8").splitlines(), 1):
            if PATTERN.search(line):
                hits += 1
                if EXEMPT in line:
                    continue
                violations.append(
                    f"{rel}:{i}: bare json.loads on subprocess output: {line.strip()}"
                )
    for v in violations:
        print(v)
    print(f"[lint_bare_subprocess_json] hits={hits} violations={len(violations)}")
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
