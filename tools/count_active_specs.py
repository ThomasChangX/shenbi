"""Active-spec count lint: INDEX header vs directory scan (spec #49 R4, C35 T1507).

Counts top-level spec .md files (excluding INDEX.md; archive/ is not matched
by the glob) and compares against the first integer after the 活跃 spec 数 header marker
in docs/superpowers/specs/INDEX.md. Any drift FAILs — eliminating the manual
66/68/63 count drift (T1507).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SPECS_DIR = REPO_ROOT / "docs" / "superpowers" / "specs"
INDEX = SPECS_DIR / "INDEX.md"


def count_active(specs_dir: Path) -> int:
    """File-count basis: top-level .md files excluding INDEX.md."""
    return sum(1 for p in specs_dir.glob("*.md") if p.name != "INDEX.md")


def declared_count(index_text: str) -> int | None:
    """First integer after the 活跃 spec 数 header marker, before any prose."""
    m = re.search(r"活跃 spec 数\*\*\uff1a\s*(\d+)", index_text)
    return int(m.group(1)) if m else None


def main() -> int:
    """CLI entry: exit 1 on count drift or missing marker."""
    active = count_active(SPECS_DIR)
    declared = declared_count(INDEX.read_text(encoding="utf-8"))
    if declared is None:
        print("FAIL: INDEX.md lacks 活跃 spec 数 header count")
        return 1
    if declared != active:
        print(f"FAIL: INDEX header 活跃 spec 数={declared} vs directory scan {active}")
        return 1
    print(f"PASS active specs: {active} (INDEX header consistent)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
