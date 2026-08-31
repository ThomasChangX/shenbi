#!/usr/bin/env python3
"""Lint: SKILL.md must reference helper precompute output, not recompute by hand.

Anti-recurrence guard for spec #33 (T1442): whenever a deterministic helper
already covers a statistic, SKILL.md bodies must point the LLM at the
framework-injected precompute block (or the framework's post-dispatch
enforcement) instead of instructing the LLM to compute/count it — on the API
dispatch route those ``python -m`` instructions are dead code anyway.

Capability list is the five-helper surface only (compute_stats /
compute_pattern / calibration / review_resonance / transition counting).
Out-of-scope dead instructions (e.g. drift-guidance's ``python -m
drift_detection``) are deliberately not listed — they are recorded as T5
follow-up candidates in the spec.

Exit 0 = clean (or only ALLOWED exemptions); exit 1 = WARN findings.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

#: (skill, line-number-1-based) pairs adjudicated as exempt.
ALLOWED: dict[str, list[int]] = {}

CAPABILITY_PATTERNS = [
    re.compile(p)
    for p in (
        r"python -m shenbi\.skill_utils\."
        r"(style_learning|chapter_pattern|calibration|review_resonance)",
        r"运行 `compute_stats\.py`",
        r"自行(计算|统计|计数).{0,12}(转折词|变异系数|CV|熵)",
        r"手算(校准|降级)",
    )
]


def lint_skill(skill_md: Path) -> list[str]:
    """Return WARN findings (file:line) for one SKILL.md."""
    findings: list[str] = []
    text = skill_md.read_text(encoding="utf-8")
    exempt_lines = set(ALLOWED.get(skill_md.parent.name, []))
    for lineno, line in enumerate(text.splitlines(), start=1):
        if lineno in exempt_lines:
            continue
        for pat in CAPABILITY_PATTERNS:
            if pat.search(line):
                findings.append(
                    f"{skill_md.parent.name}/SKILL.md:{lineno}: "
                    f"{pat.pattern} -> {line.strip()[:80]}"
                )
                break
    return findings


def main() -> int:
    """Lint all skills; exit 1 on unexempted findings."""
    findings: list[str] = []
    for skill_md in sorted(REPO.glob("skills/*/SKILL.md")):
        findings.extend(lint_skill(skill_md))
    if findings:
        print(
            f"lint_helper_usage: {len(findings)} finding(s) — "
            "point the LLM at the helper precompute instead:"
        )
        for f in findings:
            print(f"  WARN {f}")
        return 1
    print("lint_helper_usage: clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
