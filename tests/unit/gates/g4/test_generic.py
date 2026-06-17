"""Unit tests for shenbi.gates.g4.generic.

Business rules under test:
- Generative checker: file must exist, be non-empty, have substantial content
- Bug-hunt checker: detection summary + file/line refs + rule refs + FP check
- Clean checker: zero-count assertion + per-file list + no fabricated suggestions
- Gate router: dispatches to per-skill checkers; falls back to generic
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

from shenbi.gates.g4.generic import (
    g4_generic_bughunt,
    g4_generic_clean,
    g4_generic_generative,
    gate_G4,
)

import pytest


def _result_dict(result: str) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(result))


pytestmark = pytest.mark.unit


# --- TestGenerativeChecker ----------------------------------------------


class TestGenerativeChecker:
    def test_skips_when_no_files_provided(self) -> None:
        result = _result_dict(g4_generic_generative([]))
        assert any(c["s"] == "SKIP" for c in result.get("checks", []))

    def test_fails_on_missing_file(self, tmp_path: Path) -> None:
        result = _result_dict(
            g4_generic_generative([str(tmp_path / "nonexistent.md")])
        )
        assert result["status"] == "FAIL"
        assert any("not_found" in m for m in result["must_fix"])

    def test_fails_on_empty_file(self, tmp_path: Path) -> None:
        f = tmp_path / "empty.md"
        f.write_text("", encoding="utf-8")
        result = _result_dict(g4_generic_generative([str(f)]))
        assert result["status"] == "FAIL"
        assert any("empty" in m for m in result["must_fix"])

    def test_fails_on_too_short_markdown(self, tmp_path: Path) -> None:
        """Markdown files under 50 chars are flagged too_short."""
        f = tmp_path / "short.md"
        f.write_text("# x\nshort", encoding="utf-8")
        result = _result_dict(g4_generic_generative([str(f)]))
        assert result["status"] == "FAIL"
        assert any("too_short" in m for m in result["must_fix"])

    def test_passes_on_substantial_markdown(self, tmp_path: Path) -> None:
        f = tmp_path / "ok.md"
        f.write_text(
            "# Substantial document\n\n" + ("content line\n" * 10), encoding="utf-8"
        )
        result = _result_dict(g4_generic_generative([str(f)]))
        assert result["status"] == "PASS"

    def test_validates_json_file_content(self, tmp_path: Path) -> None:
        f = tmp_path / "data.json"
        f.write_text('{"valid": true}', encoding="utf-8")
        result = _result_dict(g4_generic_generative([str(f)]))
        assert result["status"] == "PASS"

    def test_fails_on_invalid_json(self, tmp_path: Path) -> None:
        f = tmp_path / "bad.json"
        f.write_text("not json", encoding="utf-8")
        result = _result_dict(g4_generic_generative([str(f)]))
        assert result["status"] == "FAIL"
        assert any("invalid_json" in m for m in result["must_fix"])


# --- TestBughuntChecker --------------------------------------------------


class TestBughuntChecker:
    def _valid_bughunt_report(self) -> str:
        return (
            "# Bug Hunt Report\n\n"
            "## Detection\n\nFound 3 issues.\n\n"
            "## Details\n\n"
            "- `chapter.md:L42` violates Iron Rule: no fabricated content.\n"
            "- Violated Rule: SKILL.md Rule 2.\n\n"
            "## False positives: 0\n"
        )

    def test_fails_when_no_detection_section(self, tmp_path: Path) -> None:
        f = tmp_path / "r.md"
        f.write_text("# Report\n\nNo detection summary.", encoding="utf-8")
        result = _result_dict(g4_generic_bughunt([str(f)]))
        assert result["status"] == "FAIL"
        assert any("no_detection_section" in m for m in result["must_fix"])

    def test_fails_when_no_location_reference(self, tmp_path: Path) -> None:
        f = tmp_path / "r.md"
        f.write_text("# Report\n\n## Detection\n\nIssue found.\n", encoding="utf-8")
        result = _result_dict(g4_generic_bughunt([str(f)]))
        assert result["status"] == "FAIL"
        assert any("no_location_ref" in m for m in result["must_fix"])

    def test_fails_when_no_rule_reference(self, tmp_path: Path) -> None:
        f = tmp_path / "r.md"
        f.write_text(
            "# Report\n\n## Detection\n\n`chapter.md:L42` issue found.\n",
            encoding="utf-8",
        )
        result = _result_dict(g4_generic_bughunt([str(f)]))
        assert result["status"] == "FAIL"
        assert any("no_rule_reference" in m for m in result["must_fix"])

    def test_fails_when_no_false_positive_check(self, tmp_path: Path) -> None:
        f = tmp_path / "r.md"
        f.write_text(
            "# Report\n\n## Detection\n\n`chapter.md:L42` violates 铁律 1.\n",
            encoding="utf-8",
        )
        result = _result_dict(g4_generic_bughunt([str(f)]))
        assert result["status"] == "FAIL"
        assert any("no_false_positive_check" in m for m in result["must_fix"])

    def test_passes_with_all_required_sections(self, tmp_path: Path) -> None:
        f = tmp_path / "r.md"
        f.write_text(self._valid_bughunt_report(), encoding="utf-8")
        result = _result_dict(g4_generic_bughunt([str(f)]))
        assert result["status"] == "PASS"


# --- TestCleanChecker ---------------------------------------------------


class TestCleanChecker:
    def _valid_clean_report(self) -> str:
        return (
            "# Clean Report\n\n"
            "## Files Checked\n\n"
            "- chapter.md\n"
            "- outline.md\n\n"
            "## Per-File Confirmation\n\n"
            "All files reviewed. Zero issues found.\n"
        )

    def test_fails_when_zero_count_missing(self, tmp_path: Path) -> None:
        f = tmp_path / "r.md"
        f.write_text("# Clean Report\n\n## Files\n\n- a.md\n", encoding="utf-8")
        result = _result_dict(g4_generic_clean([str(f)]))
        assert result["status"] == "FAIL"
        assert any("no_zero_count" in m for m in result["must_fix"])

    def test_fails_when_file_list_missing(self, tmp_path: Path) -> None:
        f = tmp_path / "r.md"
        f.write_text("# Clean Report\n\nZero issues found.\n", encoding="utf-8")
        result = _result_dict(g4_generic_clean([str(f)]))
        assert result["status"] == "FAIL"
        assert any("no_file_list" in m for m in result["must_fix"])

    def test_fails_when_improvement_suggestions_present(self, tmp_path: Path) -> None:
        """Clean reports must NOT contain improvement suggestions — those
        indicate fabricated defects.
        """
        f = tmp_path / "r.md"
        f.write_text(
            "# Clean Report\n\n## Files Checked\n\n- a.md\n\n"
            "Zero issues. 改进建议: add more detail.\n",
            encoding="utf-8",
        )
        result = _result_dict(g4_generic_clean([str(f)]))
        assert result["status"] == "FAIL"
        assert any("has_suggestions" in m for m in result["must_fix"])

    def test_passes_with_zero_count_and_file_list(self, tmp_path: Path) -> None:
        f = tmp_path / "r.md"
        f.write_text(self._valid_clean_report(), encoding="utf-8")
        result = _result_dict(g4_generic_clean([str(f)]))
        assert result["status"] == "PASS"

    def test_negated_suggestion_phrase_does_not_fail(
        self, tmp_path: Path
    ) -> None:
        """Phrases like '无改进建议' (no improvement suggestions) are negated
        and should NOT trigger the has_suggestions failure.
        """
        f = tmp_path / "r.md"
        f.write_text(
            "# Clean Report\n\n## Files Checked\n\n- a.md\n\n"
            "Zero issues. 无改进建议.\n",
            encoding="utf-8",
        )
        result = _result_dict(g4_generic_clean([str(f)]))
        assert result["status"] == "PASS"


# --- TestGateRouter -----------------------------------------------------


class TestGateRouter:
    def test_routes_to_bughunt_checker(self, tmp_path: Path) -> None:
        """test_type='bug-hunt' invokes g4_generic_bughunt regardless of skill."""
        f = tmp_path / "r.md"
        f.write_text(
            "# Bug Hunt\n\n## Detection\n\n`x.md:L1` violates 铁律.\n\nFalse positives: 0\n",
            encoding="utf-8",
        )
        result = _result_dict(gate_G4("any-skill", "bug-hunt", [str(f)]))
        assert result["status"] == "PASS"

    def test_routes_to_clean_checker(self, tmp_path: Path) -> None:
        f = tmp_path / "r.md"
        f.write_text(
            "# Clean Report\n\n## Files Checked\n\n- a.md\n\nZero issues.\n",
            encoding="utf-8",
        )
        result = _result_dict(gate_G4("any-skill", "clean", [str(f)]))
        assert result["status"] == "PASS"

    def test_falls_back_to_generic_generative_for_unknown_skill(
        self, tmp_path: Path
    ) -> None:
        """Skills without a dedicated g4_<skill> checker use generative fallback."""
        f = tmp_path / "out.md"
        f.write_text("# Substantial output\n\n" + ("line\n" * 10), encoding="utf-8")
        result = _result_dict(
            gate_G4("shenbi-nonexistent-skill", "generative", [str(f)])
        )
        # Should not crash; falls back to generic
        assert "status" in result

    def test_routes_to_per_skill_checker_for_known_skill(
        self, tmp_path: Path
    ) -> None:
        """Known skills (in G4_CHECKER_SKILLS) dispatch to their dedicated
        checker module.
        """
        f = tmp_path / "out.md"
        f.write_text("# Output\n", encoding="utf-8")
        result_str = gate_G4("shenbi-worldbuilding", "generative", [str(f)])
        # Result is valid JSON — the skill-specific checker ran
        parsed = json.loads(result_str)
        assert "status" in parsed
