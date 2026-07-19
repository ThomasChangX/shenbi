"""Tests for the single-source-of-truth quality thresholds module."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from shenbi.config.thresholds import (
    AUDIT_SAFETY_MATRIX,
    DEFAULT_THRESHOLDS,
    QualityThresholds,
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
