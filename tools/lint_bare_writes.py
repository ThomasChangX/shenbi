#!/usr/bin/env python3
"""lint_bare_writes: bare-write inventory with exemption annotations (spec #37 AC2).

Scans src/shenbi/ for write-shaped file mutations (open in write/append
mode, mkstemp, os.fdopen-w, Path.write_text, shutil.move/copy) that are NOT
in the purity lint's allowlists. Every hit must carry an exemption comment
``# write-audit-exempt: <reason>`` on the same line or the line above.

This is a LOWER BOUND by construction (regex over code lines, comment and
def lines excluded); the exemption mechanism backstops the residue.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

SRC = Path("src/shenbi")

# Mirror of lint_no_fs_mutation allowlists — those files are the sanctioned
# write primitives and are checked by that lint instead.
ALLOWED_FILES = {
    "safe_write.py",
    "append_helper.py",
    "trace/writer.py",
    "config/config_coherence.py",
    "trace/compaction.py",
    "pipeline/checkpoint.py",
}

# Write-shaped patterns (lower bound; see module docstring).
PATTERNS = re.compile(
    r"open\([^)]*['\"](a|w|ab|wb|w\+|r\+)['\"]"
    r"|mkstemp"
    r"|os\.fdopen\([^)]*['\"]w"
    r"|\.write_text\("
    r"|shutil\.(move|copy)"
    r"|_shutil\.(move|copy)"
)
EXEMPT_MARK = "# write-audit-exempt:"
DEF_LINE = re.compile(r"^\s*(async\s+)?def\s")


def lint(root: Path) -> list[str]:
    """Return bare-write violations under *root* (no exemption annotations)."""
    violations: list[str] = []
    for path in sorted(root.rglob("*.py")):
        rel = path.relative_to(root).as_posix()
        if rel in ALLOWED_FILES:
            continue
        lines = path.read_text(encoding="utf-8").splitlines()
        for i, line in enumerate(lines):
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or DEF_LINE.match(line):
                continue
            if not PATTERNS.search(stripped):
                continue
            if EXEMPT_MARK in line or (i > 0 and EXEMPT_MARK in lines[i - 1]):
                continue
            violations.append(f"{rel}:{i + 1}: bare write without exemption: {stripped[:90]}")
    return violations


def main() -> int:
    """CLI entry: print violations, exit 1 if any."""
    violations = lint(SRC)
    for v in violations:
        print(v)
    if violations:
        print(f"\n{len(violations)} bare write(s) lack '# write-audit-exempt:' annotations.")
        return 1
    print("lint_bare_writes: clean (all bare writes exempt or migrated)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
