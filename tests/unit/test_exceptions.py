"""Tests for typed exception hierarchy."""

from tests.error_guidance import get_guidance
from tests.exceptions import (
    FrameworkError,
    GateError,
    GateMarkerMissingError,
    RegistryError,
    RegistryStaleError,
    ShenbiError,
)
from tests.recovery import RECOVERY_STRATEGIES, RecoveryStrategy


class TestHierarchy:
    def test_registry_stale_is_registry_error(self) -> None:
        err = RegistryStaleError(
            mismatches=[("a", "exp", "act")],
            lockfile_generated_at="2026-06-14T00:00:00Z",
        )
        assert isinstance(err, RegistryError)
        assert isinstance(err, FrameworkError)
        assert isinstance(err, ShenbiError)

    def test_gate_marker_missing_is_gate_error(self) -> None:
        err = GateMarkerMissingError(
            gate="G4",
            missing_markers=["G4-shenbi-worldbuilding"],
        )
        assert isinstance(err, GateError)


class TestSerialization:
    def test_to_dict_includes_error_class(self) -> None:
        err = RegistryStaleError(
            mismatches=[("a", "exp", "act")],
            lockfile_generated_at="2026-06-14T00:00:00Z",
        )
        d = err.to_dict()
        assert d["error_class"] == "RegistryStaleError"

    def test_to_dict_includes_context(self) -> None:
        err = RegistryStaleError(
            mismatches=[("a", "exp", "act")],
            lockfile_generated_at="2026-06-14T00:00:00Z",
        )
        d = err.to_dict()
        assert "mismatches" in d["context"]
        assert d["context"]["lockfile_generated_at"] == "2026-06-14T00:00:00Z"

    def test_str_includes_context(self) -> None:
        err = RegistryStaleError(
            mismatches=[("a", "exp", "act")],
            lockfile_generated_at="2026-06-14T00:00:00Z",
        )
        s = str(err)
        assert "1 source files changed" in s


class TestRegistryStaleTruncation:
    def test_truncates_to_5(self) -> None:
        mismatches = [(f"path{i}", "exp", "act") for i in range(100)]
        err = RegistryStaleError(
            mismatches=mismatches,
            lockfile_generated_at="2026-06-14T00:00:00Z",
        )
        assert len(err.context["mismatches"]) == 5
        assert err.context["total_mismatches"] == 100


class TestErrorGuidance:
    def test_get_guidance_returns_entry(self) -> None:
        err = RegistryStaleError([("a", "b", "c")], "2026-06-14")
        guidance = get_guidance(err)
        assert guidance is not None
        assert "build_registry" in guidance.action

    def test_get_guidance_unknown_error_returns_none(self) -> None:
        err = ValueError("test")
        assert get_guidance(err) is None


class TestRecoveryStrategies:
    def test_registry_stale_auto_rebuild(self) -> None:
        assert RECOVERY_STRATEGIES["RegistryStaleError"] == RecoveryStrategy.AUTO_REBUILD

    def test_tool_tamper_halt(self) -> None:
        assert RECOVERY_STRATEGIES["ToolTamperError"] == RecoveryStrategy.HALT
