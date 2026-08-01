#!/usr/bin/env python3
"""Pre-commit guard: fixture mirrors must match source hashes (G0.11 local).

Single source of truth: shenbi.gates.g0.MIRROR_MAP (spec Task 2.3),
avoiding drift between the gate and a second definition here.
"""

import hashlib
import sys
from pathlib import Path

from shenbi.gates.g0 import MIRROR_MAP  # Task 2.3 提模块级后生效

ROOT = Path(__file__).resolve().parent.parent


def _sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    """Check every fixture mirror against its source; exit non-zero on drift."""
    drift: list[tuple[str, str]] = []
    for fixture_rel, source_rel in MIRROR_MAP.items():
        fp, sp = ROOT / fixture_rel, ROOT / source_rel
        if not sp.exists():
            # source absent: not an error (may be uncreated); log for debug
            print(f"fixture mirror: source {source_rel} absent, skip", file=sys.stderr)
            continue
        if not fp.exists() or _sha256(fp) != _sha256(sp):
            drift.append((fixture_rel, source_rel))
    if drift:
        for f, s in drift:
            print(
                f"fixture mirror drift: {f} != {s}\n  fix: cp {s} {f}",
                file=sys.stderr,
            )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
