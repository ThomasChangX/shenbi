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


@pytest.mark.unit
class TestG4CompositeFilePartitioning:
    """C2: composite checker must partition fps by extension.

    Structural checkers (e.g. g4_context_composing) parse ALL files as markdown
    and have NO .json guard — feeding them a decisions.json fails (no expected
    P1-P7 sections in JSON). The composite must route .md to the structural
    checker and .json to the decisions checker.
    """

    @staticmethod
    def _valid_context_md() -> str:
        """A context-composing .md with all required P1-P7 sections populated."""
        return (
            "# Chapter 5 Context\n\n"
            "## P1 章节备忘\nchapter memo content\n\n"
            "## P2 书脊\nbook spine content\n\n"
            "## P3 当前大弧\narc content\n\n"
            "## P4 当前卷摘要\nvolume summary\n\n"
            "## P5 当前弧段\narc segment\n\n"
            "## P6 近章拍点\nbeat points\n\n"
            "## P7 世界铁律与文风\nrules and style\n\n"
            "## 近章结尾多样性\nending variety\n\n"
            "## Hook 债务简报\nhook debt\n"
        )

    @staticmethod
    def _valid_decisions() -> dict[str, object]:
        return {
            "$schema": "shenbi-decisions-v1",
            "skill": "shenbi-context-composing",
            "chapter": 5,
            "produced_at": "2026-07-07T12:00:00Z",
            "selections": [],
        }

    def test_composite_passes_with_mixed_md_and_json(self, tmp_path: Path) -> None:
        """Valid .md + valid .json to a composite checker -> PASS.

        Regression for C2: before partitioning, the .json was fed to
        g4_context_composing which failed (no P1-P7 sections in JSON).
        """
        from shenbi.gates.g4.context_composing import g4_context_composing
        from shenbi.gates.g4.decisions_validator import g4_decisions, make_composite_checker

        md_fp = tmp_path / "chapter-5-context.md"
        md_fp.write_text(self._valid_context_md(), encoding="utf-8")
        json_fp = tmp_path / "chapter-5-context-decisions.json"
        json_fp.write_text(json.dumps(self._valid_decisions()), encoding="utf-8")

        composite = make_composite_checker(g4_context_composing, g4_decisions)
        result = json.loads(composite([str(md_fp), str(json_fp)], str(tmp_path)))
        assert result["status"] == "PASS", f"composite failed: {result.get('must_fix', [])}"

    def test_composite_partitions_json_away_from_structural_checker(self, tmp_path: Path) -> None:
        """The structural checker must NEVER see the .json file.

        Uses a spy structural checker that records the fps it received, then
        asserts no .json path was passed to it.
        """
        from shenbi.gates.g4.decisions_validator import g4_decisions, make_composite_checker
        from shenbi.gates.shared import passed

        seen: list[list[str]] = []

        def spy_structural(fps: list[str], rd: str | None = None) -> str:
            seen.append(list(fps))
            return passed("G4-spy", [{"id": "G4.spy", "s": "PASS"}])

        md_fp = tmp_path / "chapter-5-context.md"
        md_fp.write_text(self._valid_context_md(), encoding="utf-8")
        json_fp = tmp_path / "chapter-5-context-decisions.json"
        json_fp.write_text(json.dumps(self._valid_decisions()), encoding="utf-8")

        composite = make_composite_checker(spy_structural, g4_decisions)
        composite([str(md_fp), str(json_fp)], str(tmp_path))

        assert len(seen) == 1
        received = seen[0]
        assert str(md_fp) in received, ".md must go to the structural checker"
        assert not any(fp.endswith(".json") for fp in received), (
            f".json leaked to structural checker: {received}"
        )
