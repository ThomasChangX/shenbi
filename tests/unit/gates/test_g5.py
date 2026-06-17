"""Unit tests for G5: T2 phase check."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import pytest

from shenbi.gates.g5 import gate_G5


def _result_dict(result: str) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(result))


class TestG5PhaseCheck:
    def test_emits_valid_json_for_valid_args(self, tmp_path: Path) -> None:
        round_dir = tmp_path / "round"
        round_dir.mkdir()
        result_str = gate_G5("design", str(round_dir), str(tmp_path))
        parsed = json.loads(result_str)
        assert "status" in parsed

    def test_handles_none_arguments(self) -> None:
        result_str = gate_G5(None, None, None)
        parsed = json.loads(result_str)
        assert "status" in parsed

    def test_handles_missing_round_dir(self, tmp_path: Path) -> None:
        result_str = gate_G5("design", str(tmp_path / "nope"), None)
        parsed = json.loads(result_str)
        assert "status" in parsed

    def test_returns_str_for_any_phase_name(self, tmp_path: Path) -> None:
        """Even unknown phases return a parseable result."""
        round_dir = tmp_path / "round"
        round_dir.mkdir()
        result_str = gate_G5("nonexistent-phase", str(round_dir), None)
        assert isinstance(result_str, str)
        assert json.loads(result_str)


class TestG5ErrorPaths:
    """Error-path coverage for G5 phase boundary checks (PR-52 Step 5).

    Gate reads tests/tiers/deps.json for t2-phases definitions and
    tests/tiers/acceptance.json for the t2 score threshold. Phase names
    like "genesis"/"architecture"/"planning"/"drafting" have real
    prerequisite skill lists. All assertions check behavior (FAIL/PASS
    status + must_fix reasons), never structure.
    """

    @pytest.mark.unit
    def test_g5_unknown_phase_fails(self, tmp_path: Path) -> None:
        """An unknown phase name -> FAIL with 'unknown phase' reason."""
        round_dir = tmp_path / "round"
        round_dir.mkdir()
        result = _result_dict(gate_G5("not-a-real-phase", str(round_dir), None))
        assert result["status"] == "FAIL"
        assert any("unknown phase" in mf for mf in result["must_fix"])

    @pytest.mark.unit
    def test_g5_prereq_score_below_threshold_fails(self, tmp_path: Path) -> None:
        """A prerequisite with score < 94 threshold -> G5.1:score=... in must_fix."""
        round_dir = tmp_path / "round"
        round_dir.mkdir()
        # genesis's first prereq is shenbi-worldbuilding; report it below threshold.
        (round_dir / "t1-reports").mkdir()
        (round_dir / "t1-reports" / "shenbi-worldbuilding-generative-scores.json").write_text(
            json.dumps({"final_score": 80}), encoding="utf-8"
        )
        result = _result_dict(gate_G5("genesis", str(round_dir), None))
        assert result["status"] == "FAIL"
        assert any(mf.startswith("G5.1:") and "score=" in mf for mf in result["must_fix"])

    @pytest.mark.unit
    def test_g5_missing_prereq_report_fails(self, tmp_path: Path) -> None:
        """A prerequisite with no report and no summary entry -> G5.1:no_report."""
        round_dir = tmp_path / "round"
        round_dir.mkdir()
        result = _result_dict(gate_G5("genesis", str(round_dir), None))
        assert result["status"] == "FAIL"
        assert any(
            mf.startswith("G5.1:") and mf.endswith(":no_report") for mf in result["must_fix"]
        )

    @pytest.mark.unit
    def test_g5_handoff_mismatch_detected(self, tmp_path: Path) -> None:
        """If a downstream skill Reads something the upstream never Writes,
        G5.2 reports a handoff missing entry. We exercise the SKILL.md
        parsing path against the REAL skills/ dir for the planning phase
        (chapter-planning Reads plans/, foreshadowing-plant Reads truth/).
        The gate either finds a real mismatch or not; the structural
        contract is that G5.2 entries (if any) are well-formed. Here we
        force a mismatch by pointing at an empty project_dir so the gate
        runs the handoff loop on the real prereq skills.
        """
        round_dir = tmp_path / "round"
        round_dir.mkdir()
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        result = _result_dict(gate_G5("planning", str(round_dir), str(project_dir)))
        # planning's prereqs all have SKILL.md; the reviewer confirmed the gate
        # emits 2 real G5.2 handoff entries against an empty project_dir.
        g52 = [m for m in result["must_fix"] if m.startswith("G5.2:")]
        assert g52, "G5.2 handoff entries should be emitted"
        for mf in g52:
            assert "handoff:" in mf
        assert result["gate"] == "G5"

    @pytest.mark.unit
    def test_g5_cross_skill_char_role_conflict_detected(self, tmp_path: Path) -> None:
        """Two character files with the same name but different role ->
        G5.3:char_role_conflict in must_fix.
        """
        round_dir = tmp_path / "round"
        round_dir.mkdir()
        project_dir = tmp_path / "project"
        char_dir = project_dir / "characters"
        char_dir.mkdir(parents=True)
        (char_dir / "a.md").write_text("name: 林青\nrole: 剑客\n", encoding="utf-8")
        (char_dir / "b.md").write_text("name: 林青\nrole: 法师\n", encoding="utf-8")
        result = _result_dict(gate_G5("genesis", str(round_dir), str(project_dir)))
        assert result["status"] == "FAIL"
        assert any("G5.3:char_role_conflict:林青" in mf for mf in result["must_fix"])

    @pytest.mark.unit
    def test_g5_numeric_inconsistency_not_detected_pins_inert_behavior(
        self, tmp_path: Path
    ) -> None:
        r"""Numeric inconsistency detection: pins current behavior.

        The source num_pat regex is `(\d+)\s*(?:个|种|人|...)` — only ONE
        capture group. The loop body reads `m.group(2)` (the unit), which
        raises IndexError, caught by the per-file `except Exception: pass`.
        So the numeric registry never populates and G5.3:numeric conflicts
        are NEVER emitted. This test pins that inert behavior (Non-Goal #3:
        do not modify source). If the group-2 bug is later fixed, this test
        will flip and should assert G5.3:numeric IS flagged.
        """
        round_dir = tmp_path / "round"
        round_dir.mkdir()
        project_dir = tmp_path / "project"
        world_dir = project_dir / "world"
        world_dir.mkdir(parents=True)
        # Same CJK context words + same unit, different value -> conflict.
        # The gate regex matches Arabic digits only, not Chinese numerals.
        (world_dir / "factions.md").write_text("成员人数30000人。\n", encoding="utf-8")
        (world_dir / "history.md").write_text("成员人数50000人。\n", encoding="utf-8")
        result = _result_dict(gate_G5("genesis", str(round_dir), str(project_dir)))
        # pins current behavior: numeric conflict is NOT detected (source bug).
        assert not any(mf.startswith("G5.3:numeric") for mf in result.get("must_fix", []))

    @pytest.mark.unit
    def test_g5_terminology_drift_detected(self, tmp_path: Path) -> None:
        """Mixed use of paired term variants (灵能 vs 灵力, etc.) ->
        G5.3:term_mix in must_fix.
        """
        round_dir = tmp_path / "round"
        round_dir.mkdir()
        project_dir = tmp_path / "project"
        char_dir = project_dir / "characters"
        char_dir.mkdir(parents=True)
        # Use 灵能/灵力 heavily so c1+c2 > 3.
        body = "灵能灵能灵力灵力灵能灵力\n" * 1
        (char_dir / "hero.md").write_text("name: 主角\nrole: 剑客\n" + body, encoding="utf-8")
        result = _result_dict(gate_G5("genesis", str(round_dir), str(project_dir)))
        assert result["status"] == "FAIL"
        assert any(mf.startswith("G5.3:term_mix") for mf in result["must_fix"])

    @pytest.mark.unit
    def test_g5_conflict_detection_skips_without_project_dir(self, tmp_path: Path) -> None:
        """G5.3 SKIPs when project_dir is None -> PASS with SKIP check."""
        round_dir = tmp_path / "round"
        round_dir.mkdir()
        # genesis phase with report meeting threshold
        (round_dir / "t1-reports").mkdir()
        (round_dir / "t1-reports" / "shenbi-worldbuilding-generative-scores.json").write_text(
            json.dumps({"final_score": 100}), encoding="utf-8"
        )
        result = _result_dict(gate_G5("genesis", str(round_dir), None))
        g53 = next((c for c in result["checks"] if c.get("id") == "G5.3"), None)
        assert g53 is not None
        assert g53["s"] == "SKIP"

    @pytest.mark.unit
    def test_g5_glob_pattern_matching_passes(self, tmp_path: Path) -> None:
        """G5.4 glob pattern finding existing files -> PASS."""
        round_dir = tmp_path / "round"
        round_dir.mkdir()
        project_dir = tmp_path / "project"
        (project_dir / "outline").mkdir(parents=True)
        (project_dir / "outline" / "volume_map.md").write_text("# Volume\n", encoding="utf-8")
        (project_dir / "outline" / "story_frame.md").write_text("# Frame\n", encoding="utf-8")
        result = _result_dict(gate_G5("architecture", str(round_dir), str(project_dir)))
        g54 = [c for c in result["checks"] if c.get("id") == "G5.4"]
        assert g54, "G5.4 checks should exist"
        assert any(c["s"] == "PASS" for c in g54)
