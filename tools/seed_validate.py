#!/usr/bin/env python3
"""Structural validation for seed outlines (T2: AI-tool-edit guard).

Usage: uv run python tools/seed_validate.py <seed-path>

Exit 0 + "seed OK" when the outline carries every required section, an H1
title, and parseable Basic Info key:value items. Exit 1 with the full
problem list otherwise. Run this after ANY AI-tool rewrite of
outline-example.md, before `just pipeline-init`.
"""

from __future__ import annotations

import sys

from shenbi.pipeline.seed_parser import validate_seed


def main(argv: list[str]) -> int:
    """Validate a seed outline and print the verdict."""
    seed = argv[1] if len(argv) > 1 else "outline-example.md"
    errors = validate_seed(seed)
    if errors:
        print("SEED INVALID:")
        for err in errors:
            print(f" - {err}")
        return 1
    print("seed OK: 9 sections + H1 + key:value all present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
