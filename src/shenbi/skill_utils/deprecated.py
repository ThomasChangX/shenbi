"""Single source for DEPRECATED-skill detection (spec #59 T1/T3).

Two banner forms exist in the wild (verified 2026-09-12):
``# DEPRECATED: ...`` and ``<!-- DEPRECATED: ... -->``.
"""

from __future__ import annotations

import re
from pathlib import Path

_BANNER_RE = re.compile(r"^\s*(?:#\s*|<!--\s*)DEPRECATED[:\s]", re.MULTILINE)


def is_deprecated_skill(skills_dir: Path, skill_name: str) -> bool:
    """True iff the skill's SKILL.md carries a DEPRECATED banner."""
    skill_md = skills_dir / skill_name / "SKILL.md"
    if not skill_md.exists():
        return False
    return bool(_BANNER_RE.search(skill_md.read_text(encoding="utf-8")))


def deprecated_skill_names(skills_dir: Path) -> frozenset[str]:
    """All DEPRECATED-marked skill dir names under *skills_dir*."""
    return frozenset(
        p.parent.name
        for p in skills_dir.glob("*/SKILL.md")
        if _BANNER_RE.search(p.read_text(encoding="utf-8"))
    )
