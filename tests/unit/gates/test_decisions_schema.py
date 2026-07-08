"""Unit tests for decisions schema v1 + P2.5 rationale rules."""

from __future__ import annotations

import pytest

from shenbi.gates.g4._decisions_schema import (
    DECISIONS_SCHEMA_VERSION,
    ROUTINE_BASIS,
    VALID_BASIS,
    VALID_SEVERITY,
    validate_adjustment_rationale,
    validate_selection_rationale,
)


@pytest.mark.unit
class TestSchemaConstants:
    def test_schema_version(self) -> None:
        assert DECISIONS_SCHEMA_VERSION == "shenbi-decisions-v1"

    def test_valid_basis_contains_routine_and_anomaly(self) -> None:
        assert "adjacent_to_target_chapter" in VALID_BASIS
        assert "arc_relevance" in VALID_BASIS
        assert "volume_scope" in VALID_BASIS
        assert "manual_override" in VALID_BASIS

    def test_routine_basis_excludes_manual_override(self) -> None:
        assert "manual_override" not in ROUTINE_BASIS

    def test_valid_severity_has_low_and_high(self) -> None:
        assert "low" in VALID_SEVERITY
        assert "high" in VALID_SEVERITY


@pytest.mark.unit
class TestP25RationaleRules:
    def test_routine_low_severity_with_rationale_fails(self) -> None:
        """P2.5: routine basis + low severity → rationale FORBIDDEN."""
        errors = validate_selection_rationale(
            basis="arc_relevance", severity="low", rationale="some explanation"
        )
        assert len(errors) == 1
        assert "FORBIDDEN" in errors[0] or "forbidden" in errors[0].lower()

    def test_routine_low_severity_without_rationale_passes(self) -> None:
        errors = validate_selection_rationale(basis="arc_relevance", severity="low", rationale=None)
        assert errors == []

    def test_routine_high_severity_without_rationale_fails(self) -> None:
        """P2.5 escape hatch: high-stakes routine → rationale REQUIRED."""
        errors = validate_selection_rationale(
            basis="arc_relevance", severity="high", rationale=None
        )
        assert len(errors) == 1
        assert "REQUIRED" in errors[0] or "required" in errors[0].lower()

    def test_routine_high_severity_with_rationale_passes(self) -> None:
        errors = validate_selection_rationale(
            basis="arc_relevance", severity="high", rationale="climax chapter, must deliver"
        )
        assert errors == []

    def test_manual_override_without_rationale_fails(self) -> None:
        errors = validate_selection_rationale(
            basis="manual_override", severity="low", rationale=None
        )
        assert len(errors) == 1

    def test_manual_override_with_rationale_passes(self) -> None:
        errors = validate_selection_rationale(
            basis="manual_override", severity="low", rationale="POV conflict"
        )
        assert errors == []

    def test_rationale_over_100_chars_fails(self) -> None:
        long_rationale = "x" * 101
        errors = validate_selection_rationale(
            basis="manual_override", severity="low", rationale=long_rationale
        )
        assert any("100" in e for e in errors)

    def test_invalid_basis_fails(self) -> None:
        errors = validate_selection_rationale(basis="invalid_basis", severity="low", rationale=None)
        assert any("basis" in e.lower() for e in errors)

    def test_adjustment_without_rationale_fails(self) -> None:
        errors = validate_adjustment_rationale(rationale=None)
        assert len(errors) == 1

    def test_adjustment_with_rationale_passes(self) -> None:
        errors = validate_adjustment_rationale(rationale="drift absorbed by pacing")
        assert errors == []
