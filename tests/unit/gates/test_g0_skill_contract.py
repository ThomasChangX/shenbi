"""Tests for G0.skill_contract check (spec §3.1)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from shenbi.gates.g0_skill_contract import (
    DESCRIPTION_MAX_CHARS,
    _desc_has_behavioral_text,
    check_skill_contracts,
)


def _make_skill(tmp_path: Path, name: str, body: dict[str, Any]) -> Path:
    """Write a synthetic skills/<name>/SKILL.md and return the skills dir."""
    skill_dir = tmp_path / name
    skill_dir.mkdir(parents=True)
    fm = "---\n" + yaml.safe_dump(body, sort_keys=False) + "---\n\n# body\n"
    (skill_dir / "SKILL.md").write_text(fm, encoding="utf-8")
    return tmp_path


class TestDescriptionLength:
    def test_max_chars_is_500(self):
        assert DESCRIPTION_MAX_CHARS == 500

    def test_too_long_description_flagged(self, tmp_path: Path):
        skills_dir = _make_skill(
            tmp_path,
            "shenbi-x",
            {"name": "shenbi-x", "description": "x" * 501, "contract": {"kind": "ephemeral"}},
        )
        issues = check_skill_contracts(skills_dir)
        assert any("desc_too_long" in i for i in issues)

    def test_exactly_500_passes(self, tmp_path: Path):
        skills_dir = _make_skill(
            tmp_path,
            "shenbi-x",
            {"name": "shenbi-x", "description": "x" * 500, "contract": {"kind": "ephemeral"}},
        )
        issues = check_skill_contracts(skills_dir)
        assert not any("desc_too_long" in i for i in issues)


class TestBehavioralText:
    def test_trigger_only_passes(self):
        assert not _desc_has_behavioral_text("Use when a chapter fails the audit gate.")

    def test_behavioral_flagged(self):
        assert _desc_has_behavioral_text("This skill rewrites the chapter prose.")

    def test_generates_flagged(self):
        assert _desc_has_behavioral_text("Generates a new plot outline.")


class TestWriteUpdateOverlap:
    def test_overlap_flagged(self, tmp_path: Path):
        skills_dir = _make_skill(
            tmp_path,
            "shenbi-x",
            {
                "name": "shenbi-x",
                "description": "Use when y",
                "contract": {
                    "kind": "artifact",
                    "writes": ["chapters/chapter-N.md"],
                    "updates": ["chapters/chapter-N.md"],
                },
            },
        )
        issues = check_skill_contracts(skills_dir)
        assert any("write_update_overlap" in i for i in issues)

    def test_disjoint_passes(self, tmp_path: Path):
        skills_dir = _make_skill(
            tmp_path,
            "shenbi-x",
            {
                "name": "shenbi-x",
                "description": "Use when y",
                "contract": {
                    "kind": "artifact",
                    "writes": ["chapters/chapter-N-decisions.json"],
                    "updates": ["chapters/chapter-N.md"],
                },
            },
        )
        issues = check_skill_contracts(skills_dir)
        assert not any("write_update_overlap" in i for i in issues)


class TestMissingWriteSemantics:
    def test_update_without_mode_flagged(self, tmp_path: Path):
        skills_dir = _make_skill(
            tmp_path,
            "shenbi-x",
            {
                "name": "shenbi-x",
                "description": "Use when y",
                "contract": {
                    "kind": "artifact",
                    "updates": [{"file": "chapters/chapter-N.md"}],  # no mode
                },
            },
        )
        issues = check_skill_contracts(skills_dir)
        assert any("missing_write_semantics" in i for i in issues)

    def test_update_with_mode_passes(self, tmp_path: Path):
        skills_dir = _make_skill(
            tmp_path,
            "shenbi-x",
            {
                "name": "shenbi-x",
                "description": "Use when y",
                "contract": {
                    "kind": "artifact",
                    "updates": [{"file": "chapters/chapter-N.md", "mode": "merge_prose"}],
                },
            },
        )
        issues = check_skill_contracts(skills_dir)
        assert not any("missing_write_semantics" in i for i in issues)


class TestEmptyIssuesOnCleanContract:
    def test_clean_contract_no_issues(self, tmp_path: Path):
        skills_dir = _make_skill(
            tmp_path,
            "shenbi-x",
            {
                "name": "shenbi-x",
                "description": "Use when the chapter needs revision after audit",
                "contract": {
                    "kind": "artifact",
                    "reads": ["audits/chapter-N-*.md"],
                    "writes": [
                        {
                            "file": "chapters/chapter-N-revision-decisions.json",
                            "mode": "create_or_overwrite",
                        }
                    ],
                    "updates": [
                        {
                            "file": "chapters/chapter-N.md",
                            "mode": "merge_prose",
                            "no_op_behavior": "skip_write",
                        }
                    ],
                },
            },
        )
        assert check_skill_contracts(skills_dir) == []


class TestRealSkillsTree:
    def test_all_real_skills_pass_contract_check(self):
        """Every skill in the real skills/ tree passes G0.16.

        This is the regression gate: after frontmatter is updated to declare
        write semantics, the whole tree must be clean.
        """
        from shenbi.gates.shared import SKILLS

        issues = check_skill_contracts(SKILLS)
        # If this fails, the failing skill needs its writes/updates given a
        # 'mode:' (and the description shortened/triggerified if flagged).
        assert issues == [], "G0.16 contract violations in real skills tree:\n  " + "\n  ".join(
            issues
        )
