"""Tests for the single-source-of-truth quality thresholds module."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from shenbi.config.thresholds import (
    AUDIT_SAFETY_MATRIX,
    DEFAULT_THRESHOLDS,
    QualityThresholds,
    is_critical_audit_dimension,
)


class TestQualityThresholds:
    def test_default_resonance_floor_is_65(self):
        assert DEFAULT_THRESHOLDS.resonance_global_floor == 65

    def test_quality_thresholds_is_frozen(self):
        with pytest.raises(FrozenInstanceError):
            DEFAULT_THRESHOLDS.resonance_global_floor = 50  # type: ignore[misc]

    def test_can_construct_custom_thresholds(self):
        custom = QualityThresholds(resonance_global_floor=70)
        assert custom.resonance_global_floor == 70
        # Other fields keep their defaults.
        assert custom.word_count_floor == 3000

    def test_all_default_field_values_match_spec(self):
        """Verify every default field matches the documented spec values."""
        t = DEFAULT_THRESHOLDS
        assert t.resonance_global_floor == 65
        assert t.resonance_revision_trigger == 60
        assert t.word_count_floor == 3000
        assert t.protagonist_mention_floor == 3
        assert t.system_term_density_warn == 30
        assert t.system_term_density_hard == 50

    def test_custom_thresholds_override_all_fields_independently(self):
        """Each field can be overridden without affecting others."""
        custom = QualityThresholds(
            resonance_global_floor=70,
            resonance_revision_trigger=55,
            word_count_floor=5000,
            protagonist_mention_floor=5,
            system_term_density_warn=25,
            system_term_density_hard=45,
        )
        assert custom.resonance_global_floor == 70
        assert custom.resonance_revision_trigger == 55
        assert custom.word_count_floor == 5000
        assert custom.protagonist_mention_floor == 5
        assert custom.system_term_density_warn == 25
        assert custom.system_term_density_hard == 45

    def test_density_warn_is_below_density_hard(self):
        """System term density warn must be lower than hard cutoff."""
        assert (
            DEFAULT_THRESHOLDS.system_term_density_warn
            < DEFAULT_THRESHOLDS.system_term_density_hard
        )

    def test_revision_trigger_below_global_floor(self):
        """Revision trigger must be below the global floor — it triggers before failing."""
        assert (
            DEFAULT_THRESHOLDS.resonance_revision_trigger
            < DEFAULT_THRESHOLDS.resonance_global_floor
        )


class TestAuditSafetyMatrix:
    def test_texture_is_critical(self):
        assert AUDIT_SAFETY_MATRIX["texture"]["critical"] is True

    def test_antiAi_is_critical(self):
        assert AUDIT_SAFETY_MATRIX["antiAi"]["critical"] is True

    def test_continuity_is_critical(self):
        assert AUDIT_SAFETY_MATRIX["continuity"]["critical"] is True

    def test_dialogue_is_not_critical(self):
        assert AUDIT_SAFETY_MATRIX["dialogue"]["critical"] is False

    @pytest.mark.parametrize("dim", ["texture", "antiAi", "continuity"])
    def test_critical_dimensions_declare_detection_target(self, dim):
        entry = AUDIT_SAFETY_MATRIX[dim]
        assert entry.get("detects")
        assert entry.get("cannot_disable_without")

    @pytest.mark.parametrize("dim", ["dialogue", "character", "pacing"])
    def test_non_critical_dimensions_allow_disable(self, dim):
        """Non-critical dimensions explicitly declare can_disable=True."""
        entry = AUDIT_SAFETY_MATRIX[dim]
        assert entry.get("critical") is False
        assert entry.get("can_disable") is True

    def test_all_matrix_entries_have_required_keys(self):
        """Every entry must declare critical and detects at minimum."""
        for dim, entry in AUDIT_SAFETY_MATRIX.items():
            assert "critical" in entry, f"{dim} missing 'critical'"
            assert "detects" in entry, f"{dim} missing 'detects'"

    def test_matrix_contains_all_six_dimensions(self):
        """All six known audit dimensions are present in the matrix."""
        assert set(AUDIT_SAFETY_MATRIX.keys()) == {
            "texture",
            "antiAi",
            "continuity",
            "dialogue",
            "character",
            "pacing",
        }


class TestIsCriticalAuditDimension:
    @pytest.mark.parametrize("dim", ["texture", "antiAi", "continuity"])
    def test_known_critical_returns_true(self, dim):
        assert is_critical_audit_dimension(dim) is True

    @pytest.mark.parametrize("dim", ["dialogue", "character", "pacing"])
    def test_known_non_critical_returns_false(self, dim):
        assert is_critical_audit_dimension(dim) is False

    def test_unknown_dimension_returns_false(self):
        """A dimension not in the matrix is treated as non-critical (safe default)."""
        assert is_critical_audit_dimension("nonexistent_dimension") is False

    def test_empty_string_returns_false(self):
        assert is_critical_audit_dimension("") is False
