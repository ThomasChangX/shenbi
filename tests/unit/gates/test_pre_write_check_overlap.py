"""Audit: which NL-artifact skills have embedded PRE_WRITE_CHECK/POST_WRITE_SELF_CHECK?

This test documents the overlap between existing embedded intent mechanisms
and the proposed decisions.json sidecar (Layer A). It must pass before Task 10
proceeds — the results inform whether decisions.json is redundant or complementary.

Audit outcome (recorded 2026-07-07, Task 9):

    shenbi-chapter-drafting : exists=True  PRE_WRITE_CHECK=True   POST_WRITE_SELF_CHECK=True
    shenbi-chapter-planning : exists=True  PRE_WRITE_CHECK=False  POST_WRITE_SELF_CHECK=False
    shenbi-chapter-revision : exists=True  PRE_WRITE_CHECK=False  POST_WRITE_SELF_CHECK=False
    shenbi-state-settling   : exists=True  PRE_WRITE_CHECK=False  POST_WRITE_SELF_CHECK=False
    shenbi-short-drafting   : exists=True  PRE_WRITE_CHECK=False  POST_WRITE_SELF_CHECK=False

Only chapter-drafting has an embedded PRE_WRITE_CHECK / POST_WRITE_SELF_CHECK.
For the other 4 skills, decisions.json is the ONLY intent channel → definitely
complementary (not redundant). For chapter-drafting, decisions.json is
COMPLEMENTARY too: PRE_WRITE_CHECK records per-chapter task/foreshadow/taboo
(a pre-flight self-check, human-approved before prose), while decisions.json
records plan-vs-prose deviations (pacing, opening strategy, beat selection).
Different scope, different lifecycle, different consumers. Proceed with all 5.
See spec Open Question #4 for the full decision record.
"""

from __future__ import annotations

from pathlib import Path

import pytest

SKILLS_DIR = Path(__file__).resolve().parents[3] / "skills"

NL_ARTIFACT_SKILLS = [
    "shenbi-chapter-drafting",
    "shenbi-chapter-planning",
    "shenbi-chapter-revision",
    "shenbi-state-settling",
    "shenbi-short-drafting",
]


@pytest.mark.unit
class TestPreWriteCheckOverlap:
    def test_audit_embedded_mechanisms(self) -> None:
        """Document which skills have PRE_WRITE_CHECK / POST_WRITE_SELF_CHECK.

        This test PASSES by documenting the current state — it's an audit, not
        a pass/fail gate on the presence of mechanisms.
        """
        results: dict[str, dict[str, bool]] = {}
        for skill in NL_ARTIFACT_SKILLS:
            skill_md = SKILLS_DIR / skill / "SKILL.md"
            if not skill_md.exists():
                results[skill] = {
                    "exists": False,
                    "pre_write_check": False,
                    "post_write_self_check": False,
                }
                continue
            content = skill_md.read_text(encoding="utf-8")
            results[skill] = {
                "exists": True,
                "pre_write_check": "PRE_WRITE_CHECK" in content,
                "post_write_self_check": "POST_WRITE_SELF_CHECK" in content,
            }

        # Document findings — this test always passes, it's an audit record.
        # The implementer must review the results and decide for each skill:
        # - If PRE_WRITE_CHECK captures the SAME intent as decisions.json → redundant, consider conditional
        # - If decisions.json captures DIFFERENT intent (pacing, foreshadowing) → complementary, proceed
        print("\n=== PRE_WRITE_CHECK Overlap Audit ===")
        for skill, findings in results.items():
            print(f"  {skill}: {findings}")
        assert len(results) == len(NL_ARTIFACT_SKILLS)
