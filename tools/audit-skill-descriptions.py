#!/usr/bin/env python3
"""Audit skill descriptions for AGENTS.md compliance (spec §3.4).

Report (and exit non-zero on):
  - description longer than 500 chars
  - description that reads as behavioral ('This skill does X') rather than
    trigger-only ('Use when Y')

Reuses the G0.skill_contract helpers so there is one source of truth for the
rules. Run:  python tools/audit-skill-descriptions.py [--skills-dir skills]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Allow running from repo root without install.
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "src"))

from shenbi.gates.g0_skill_contract import (  # noqa: E402
    DESCRIPTION_MAX_CHARS,
    _desc_has_behavioral_text,
    _parse_frontmatter,
)


def audit(skills_dir: Path) -> list[tuple[str, str]]:
    """Return [(skill_name, issue)] for every description violation."""
    violations: list[tuple[str, str]] = []
    for skill_md in sorted(skills_dir.glob("*/SKILL.md")):
        name = skill_md.parent.name
        fm = _parse_frontmatter(skill_md)
        if fm is None:
            continue
        desc = str(fm.get("description", ""))
        if len(desc) > DESCRIPTION_MAX_CHARS:
            violations.append((name, f"desc_too_long:{len(desc)}"))
        if desc and _desc_has_behavioral_text(desc):
            violations.append((name, "desc_has_behavior"))
    return violations


def main() -> int:
    """Parse args, run audit, print report.

    Returns exit code (0=pass, 1=violations, 2=error).
    """
    ap = argparse.ArgumentParser(description="Audit skill descriptions for compliance.")
    ap.add_argument(
        "--skills-dir",
        type=Path,
        default=_REPO_ROOT / "skills",
        help="Directory of skill subdirs (default: repo skills/)",
    )
    args = ap.parse_args()

    if not args.skills_dir.is_dir():
        print(f"error: skills dir not found: {args.skills_dir}", file=sys.stderr)
        return 2

    violations = audit(args.skills_dir)
    if not violations:
        print(f"OK: all descriptions compliant in {args.skills_dir}")
        return 0

    print(f"# Skill Description Audit — {len(violations)} violation(s)\n")
    for name, issue in violations:
        print(f"- {name}: {issue}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
