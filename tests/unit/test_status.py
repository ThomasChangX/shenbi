"""Typed status vocabulary — enums serialize to the existing wire values."""

from __future__ import annotations

import pytest

from shenbi.status import (
    STATUS_STRING_LITERALS,
    CommandStatus,
    GateResult,
    GateStatus,
    PhaseState,
    ScoreClassification,
    ScoringStatus,
)


@pytest.mark.unit
class TestGateStatusWireValues:
    def test_pass_serializes_to_uppercase_pass(self) -> None:
        assert GateStatus.PASS.value == "PASS"
        assert str(GateStatus.PASS) == "PASS"

    def test_exhaustive_set(self) -> None:
        assert {g.value for g in GateStatus} == {"PASS", "FAIL", "SKIP", "WARN"}


@pytest.mark.unit
class TestPhaseStateWireValues:
    def test_preserves_existing_lowercase_values(self) -> None:
        """State files already on disk use lowercase; serialization must match."""
        assert PhaseState.CREATED.value == "created"
        assert PhaseState.SKILLS_DONE.value == "skills_done"
        assert {p.value for p in PhaseState} == {
            "created",
            "started",
            "skills_done",
            "scored",
            "finalized",
        }


@pytest.mark.unit
class TestCommandStatusWireValues:
    def test_values(self) -> None:
        assert {c.value for c in CommandStatus} == {"ok", "blocked", "error"}


@pytest.mark.unit
class TestScoringAndClassification:
    def test_scoring_status_values(self) -> None:
        assert ScoringStatus.REJECT.value == "REJECT"
        assert ScoringStatus.MARKER_MISSING.value == "MARKER_MISSING"

    def test_classification_strings_match_classifier_output(self) -> None:
        assert ScoreClassification.PASS_EXCELLENT.value == "PASS (excellent)"
        assert ScoreClassification.CONDITIONAL.value == "CONDITIONAL"


@pytest.mark.unit
class TestStatusStringLiteralSet:
    def test_set_is_complete_vocab(self) -> None:
        # The lint (Task 3) forbids these bare strings outside status.py.
        assert "PASS" in STATUS_STRING_LITERALS
        assert "created" in STATUS_STRING_LITERALS
        assert "REJECT" in STATUS_STRING_LITERALS
        assert "PASS (excellent)" in STATUS_STRING_LITERALS


@pytest.mark.unit
class TestGateResultTyped:
    def test_status_field_is_gate_status_typed(self) -> None:
        # A GateResult's status field carries a GateStatus member, not a bare str.
        result: GateResult = {
            "gate": "G1",
            "status": GateStatus.PASS,
            "timestamp": "2026-06-21T00:00:00Z",
            "checks": [],
        }
        assert result["status"] is GateStatus.PASS


@pytest.mark.unit
class TestSharedHelpersUseEnums:
    def test_passed_result_has_gate_status_pass(self) -> None:
        import json

        from shenbi.gates.shared import passed

        result = json.loads(passed("G1", [{"id": "G1.1", "s": "PASS"}]))
        assert result["status"] == GateStatus.PASS.value

    def test_fail_result_has_gate_status_fail(self) -> None:
        import json

        from shenbi.gates.shared import fail

        result = json.loads(fail("G1", [], "scoring", ["G1.0:x"]))
        assert result["status"] == GateStatus.FAIL.value
        assert result["blocked_action"] == "scoring"

    def test_unimplemented_result_status(self) -> None:
        import json

        from shenbi.gates.shared import unimplemented

        result = json.loads(unimplemented("G9"))
        assert result["status"] == ScoringStatus.UNIMPLEMENTED.value
