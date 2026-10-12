#!/usr/bin/env python3
"""Regenerate the tests/fixtures outline mirror from the root seed.

Usage: uv run python tools/seed_sync.py

The fixture is the root outline-example.md payload plus a 5-line provenance
frontmatter (byte-identical payload — the G0.11 mirror guard in
tools/check_fixture_mirror.py enforces the pair). Run after editing the root
seed, then `just check` stays green.
"""

from __future__ import annotations

from pathlib import Path

FRONTMATTER = (
    "---\n"
    "provenance: synthetic-sample\n"
    "source: outline-example.md (repo root, payload byte-identical mirror)\n"
    "---\n"
    "\n"
)


def main() -> int:
    """Regenerate the fixture mirror from the root seed."""
    root = Path("outline-example.md")
    fixture = Path("tests/fixtures/outline-example.md")
    if not root.exists():
        print(f"root seed missing: {root}")
        return 1
    fixture.write_text(FRONTMATTER + root.read_text(encoding="utf-8"), encoding="utf-8")
    print("fixture mirror regenerated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
