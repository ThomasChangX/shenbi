"""Tests for typed exception hierarchy."""

import pytest

from shenbi.exceptions import (
    FrameworkError,
    GateError,
    GateMarkerMissingError,
    RegistryError,
    RegistryStaleError,
    ShenbiError,
)

pytestmark = pytest.mark.unit


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
        assert "1 source file changed" in s


class TestRegistryStaleTruncation:
    def test_truncates_to_5(self) -> None:
        mismatches = [(f"path{i}", "exp", "act") for i in range(100)]
        err = RegistryStaleError(
            mismatches=mismatches,
            lockfile_generated_at="2026-06-14T00:00:00Z",
        )
        assert len(err.context["mismatches"]) == 5
        assert err.context["total_mismatches"] == 100
