"""Hash-level duplicate detection over tests/fixtures (spec #54 C16 AC3).

Byte-identical groups are legal only when registered in MIRROR_MAP (sync
guard owns their equality). Any unregistered duplicate group is reported
and fails the run. Carrier files (provenance sidecars, baseline) are not
fixtures and are excluded.

Usage: uv run python tools/check_fixture_duplicates.py
"""

import hashlib
import sys
from collections import defaultdict
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
FIXTURES = PROJECT / "tests" / "fixtures"

sys.path.insert(0, str(PROJECT / "src"))

from shenbi.gates.g0 import MIRROR_MAP  # noqa: E402

_EXEMPT_NAMES = {".gitkeep", "provenance-baseline.json"}
_EXEMPT_SUFFIX = ".provenance.json"
_MIN_GROUP = 2


def main() -> int:
    """Scan fixtures for byte-identical groups and fail on unregistered ones."""
    registered = {frozenset(pair) for pair in MIRROR_MAP.items()}
    by_hash: dict[str, list[str]] = defaultdict(list)
    for p in sorted(FIXTURES.rglob("*")):
        if not p.is_file() or p.name in _EXEMPT_NAMES or p.name.endswith(_EXEMPT_SUFFIX):
            continue
        rel = "tests/fixtures/" + p.relative_to(FIXTURES).as_posix()
        by_hash[hashlib.sha256(p.read_bytes()).hexdigest()].append(rel)
    illegal = 0
    for group in by_hash.values():
        if len(group) < _MIN_GROUP:
            continue
        if any(frozenset((a, b)) in registered for a in group for b in group if a != b):
            continue
        illegal += 1
        print(f"UNREGISTERED DUPLICATE GROUP: {group}")
    print(f"{illegal} unregistered duplicate groups")
    return 1 if illegal else 0


if __name__ == "__main__":
    raise SystemExit(main())
