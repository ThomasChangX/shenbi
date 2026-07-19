"""Tests for the automatic recovery strategy definitions."""

from __future__ import annotations

from shenbi.recovery import (
    RECOVERY_STRATEGIES,
    RecoveryStrategy,
)


class TestRecoveryStrategy:
    def test_enum_has_four_members(self):
        """RecoveryStrategy must have exactly four members."""
        assert len(RecoveryStrategy) == 4

    def test_none_is_string_none(self):
        assert RecoveryStrategy.NONE.value == "none"

    def test_auto_retry_is_string_auto_retry(self):
        assert RecoveryStrategy.AUTO_RETRY.value == "auto_retry"

    def test_auto_rebuild_is_string_auto_rebuild(self):
        assert RecoveryStrategy.AUTO_REBUILD.value == "auto_rebuild"

    def test_halt_is_string_halt(self):
        assert RecoveryStrategy.HALT.value == "halt"

    def test_enum_is_iterable(self):
        """RecoveryStrategy enum is iterable."""
        members = list(RecoveryStrategy)
        assert len(members) == 4
        assert RecoveryStrategy.NONE in members


class TestRecoveryStrategies:
    def test_registry_stale_triggers_auto_rebuild(self):
        assert RECOVERY_STRATEGIES["RegistryStaleError"] == RecoveryStrategy.AUTO_REBUILD

    def test_registry_missing_triggers_auto_rebuild(self):
        assert RECOVERY_STRATEGIES["RegistryMissingError"] == RecoveryStrategy.AUTO_REBUILD

    def test_gate_marker_missing_triggers_none(self):
        assert RECOVERY_STRATEGIES["GateMarkerMissingError"] == RecoveryStrategy.NONE

    def test_schema_validation_triggers_none(self):
        assert RECOVERY_STRATEGIES["SchemaValidationError"] == RecoveryStrategy.NONE

    def test_subagent_timeout_triggers_auto_retry(self):
        assert RECOVERY_STRATEGIES["SubAgentTimeoutError"] == RecoveryStrategy.AUTO_RETRY

    def test_tool_tamper_triggers_halt(self):
        assert RECOVERY_STRATEGIES["ToolTamperError"] == RecoveryStrategy.HALT

    def test_all_known_errors_have_strategy(self):
        """All six known error types must have a recovery strategy."""
        expected_errors = {
            "RegistryStaleError",
            "RegistryMissingError",
            "GateMarkerMissingError",
            "SchemaValidationError",
            "SubAgentTimeoutError",
            "ToolTamperError",
        }
        assert set(RECOVERY_STRATEGIES.keys()) == expected_errors

    def test_all_strategies_are_valid_enum_values(self):
        """Every strategy value must be a RecoveryStrategy enum member."""
        for error_name, strategy in RECOVERY_STRATEGIES.items():
            assert isinstance(strategy, RecoveryStrategy), (
                f"{error_name} has invalid strategy {strategy}"
            )

    def test_auto_retry_is_not_halt(self):
        """Auto retry and halt are distinct strategies."""
        assert RecoveryStrategy.AUTO_RETRY != RecoveryStrategy.HALT
