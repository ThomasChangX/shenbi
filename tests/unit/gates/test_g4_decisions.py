"""Unit tests for G4 decisions schema validation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from shenbi.gates.g4.decisions_validator import g4_decisions


@pytest.mark.unit
class TestG4DecisionsValidation:
    def test_valid_decisions_passes(self, tmp_path: Path) -> None:
        decisions = {
            "$schema": "shenbi-decisions-v1",
            "skill": "shenbi-context-composing",
            "chapter": 5,
            "produced_at": "2026-07-07T12:00:00Z",
            "selections": [
                {
                    "target": "truth/audit_drift.md",
                    "selected": ["drift_1"],
                    "basis": "adjacent_to_target_chapter",
                    "severity": "low",
                    "omitted": [],
                }
            ],
        }
        fp = tmp_path / "chapter-5-context-decisions.json"
        fp.write_text(json.dumps(decisions), encoding="utf-8")
        result = g4_decisions([str(fp)])
        data = json.loads(result)
        assert data["status"] == "PASS"

    def test_routine_low_severity_with_rationale_fails(self, tmp_path: Path) -> None:
        decisions = {
            "$schema": "shenbi-decisions-v1",
            "skill": "shenbi-context-composing",
            "chapter": 5,
            "produced_at": "2026-07-07T12:00:00Z",
            "selections": [
                {
                    "target": "truth/audit_drift.md",
                    "selected": ["drift_1"],
                    "basis": "arc_relevance",
                    "severity": "low",
                    "omitted": [],
                    "rationale": "should not be here",
                }
            ],
        }
        fp = tmp_path / "chapter-5-context-decisions.json"
        fp.write_text(json.dumps(decisions), encoding="utf-8")
        result = g4_decisions([str(fp)])
        data = json.loads(result)
        assert data["status"] == "FAIL"

    def test_manual_override_without_rationale_fails(self, tmp_path: Path) -> None:
        decisions = {
            "$schema": "shenbi-decisions-v1",
            "skill": "shenbi-context-composing",
            "chapter": 5,
            "produced_at": "2026-07-07T12:00:00Z",
            "selections": [
                {
                    "target": "world/rules.md",
                    "selected": ["rule_1"],
                    "basis": "manual_override",
                    "severity": "low",
                    "omitted": ["rule_2"],
                }
            ],
        }
        fp = tmp_path / "chapter-5-context-decisions.json"
        fp.write_text(json.dumps(decisions), encoding="utf-8")
        result = g4_decisions([str(fp)])
        data = json.loads(result)
        assert data["status"] == "FAIL"

    def test_high_severity_without_rationale_fails(self, tmp_path: Path) -> None:
        decisions = {
            "$schema": "shenbi-decisions-v1",
            "skill": "shenbi-context-composing",
            "chapter": 5,
            "produced_at": "2026-07-07T12:00:00Z",
            "selections": [
                {
                    "target": "truth/arcs/arc-N.md",
                    "selected": ["climax"],
                    "basis": "arc_relevance",
                    "severity": "high",
                    "omitted": [],
                }
            ],
        }
        fp = tmp_path / "chapter-5-context-decisions.json"
        fp.write_text(json.dumps(decisions), encoding="utf-8")
        result = g4_decisions([str(fp)])
        data = json.loads(result)
        assert data["status"] == "FAIL"

    def test_adjustment_without_rationale_fails(self, tmp_path: Path) -> None:
        decisions = {
            "$schema": "shenbi-decisions-v1",
            "skill": "shenbi-context-composing",
            "chapter": 5,
            "produced_at": "2026-07-07T12:00:00Z",
            "selections": [],
            "adjustments": [
                {"issue_id": "drift_1", "severity": "medium", "handling": "compensate_via_pacing"}
            ],
        }
        fp = tmp_path / "chapter-5-context-decisions.json"
        fp.write_text(json.dumps(decisions), encoding="utf-8")
        result = g4_decisions([str(fp)])
        data = json.loads(result)
        assert data["status"] == "FAIL"


@pytest.mark.unit
class TestG4DecisionsNonJsonSkip:
    """Critical: g4_decisions MUST skip non-JSON files.

    Composite checkers pass ALL skill outputs (including .md artifacts).
    Without the .json guard, json.loads() on markdown crashes.
    """

    def test_skips_markdown_files_without_crash(self, tmp_path: Path) -> None:
        """A .md file with markdown content must not crash g4_decisions."""
        md_fp = tmp_path / "chapter-5-context.md"
        md_fp.write_text("# Chapter 5 Context\n\nThis is markdown, not JSON.", encoding="utf-8")
        # Should not raise; non-JSON file is silently skipped
        result = g4_decisions([str(md_fp)])
        data = json.loads(result)
        # Skipped file → no checks recorded as PASS, no must_fix
        assert data["status"] == "PASS"

    def test_mixed_json_and_markdown_processes_only_json(self, tmp_path: Path) -> None:
        """Composite scenario: main .md artifact + sidecar .json decisions."""
        md_fp = tmp_path / "chapter-5-context.md"
        md_fp.write_text("# Not JSON at all { broken", encoding="utf-8")

        decisions = {
            "$schema": "shenbi-decisions-v1",
            "skill": "shenbi-context-composing",
            "chapter": 5,
            "produced_at": "2026-07-07T12:00:00Z",
            "selections": [],
        }
        json_fp = tmp_path / "chapter-5-context-decisions.json"
        json_fp.write_text(json.dumps(decisions), encoding="utf-8")

        result = g4_decisions([str(md_fp), str(json_fp)])
        data = json.loads(result)
        # JSON file is valid → PASS; md file is skipped (not a failure)
        assert data["status"] == "PASS"


@pytest.mark.unit
class TestG4CompositeChecker:
    """Critical: make_composite_checker reads 'must_fix' key (not 'failures').

    fail() in shared.py emits 'must_fix'. The composite must aggregate both
    checkers' must_fix lists and FAIL if either is non-empty.
    """

    def test_composite_passes_when_both_pass(self, tmp_path: Path) -> None:
        from shenbi.gates.g4.decisions_validator import make_composite_checker
        from shenbi.gates.shared import passed

        def passing_checker(fps: list[str], rd: str | None = None) -> str:
            return passed("G4-fake", [{"id": "G4.fake", "s": "PASS"}])

        composite = make_composite_checker(passing_checker, passing_checker)
        result = json.loads(composite([], None))
        assert result["status"] == "PASS"

    def test_composite_fails_when_first_fails(self) -> None:
        from shenbi.gates.g4.decisions_validator import make_composite_checker
        from shenbi.gates.shared import fail, passed

        def failing_checker(fps: list[str], rd: str | None = None) -> str:
            return fail("G4-fail", [], "scoring", ["G4.fail:broken"])

        def passing_checker(fps: list[str], rd: str | None = None) -> str:
            return passed("G4-ok", [{"id": "G4.ok", "s": "PASS"}])

        composite = make_composite_checker(failing_checker, passing_checker)
        result = json.loads(composite([], None))
        assert result["status"] == "FAIL"
        # must_fix from first checker is preserved (key is "must_fix", not "failures")
        assert "G4.fail:broken" in result["must_fix"]

    def test_composite_fails_when_second_fails(self) -> None:
        from shenbi.gates.g4.decisions_validator import make_composite_checker
        from shenbi.gates.shared import fail, passed

        def passing_checker(fps: list[str], rd: str | None = None) -> str:
            return passed("G4-ok", [{"id": "G4.ok", "s": "PASS"}])

        def failing_checker(fps: list[str], rd: str | None = None) -> str:
            return fail("G4-fail", [], "scoring", ["G4.dec:broken"])

        composite = make_composite_checker(passing_checker, failing_checker)
        result = json.loads(composite([], None))
        assert result["status"] == "FAIL"
        assert "G4.dec:broken" in result["must_fix"]

    def test_composite_aggregates_must_fix_from_both(self) -> None:
        from shenbi.gates.g4.decisions_validator import make_composite_checker
        from shenbi.gates.shared import fail

        def fail_a(fps: list[str], rd: str | None = None) -> str:
            return fail("G4-a", [], "scoring", ["err_a"])

        def fail_b(fps: list[str], rd: str | None = None) -> str:
            return fail("G4-b", [], "scoring", ["err_b"])

        composite = make_composite_checker(fail_a, fail_b)
        result = json.loads(composite([], None))
        assert result["status"] == "FAIL"
        assert "err_a" in result["must_fix"]
        assert "err_b" in result["must_fix"]
