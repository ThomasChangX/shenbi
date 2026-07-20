"""Tests for the user-facing error guidance catalog."""

from __future__ import annotations

import pytest

from shenbi.error_guidance import (
    ERROR_GUIDANCE,
    ErrorGuidance,
    get_guidance,
)


class TestErrorGuidanceCatalog:
    def test_catalog_is_non_empty(self):
        """The error guidance catalog must have entries."""
        assert len(ERROR_GUIDANCE) > 0

    def test_all_entries_are_error_guidance_instances(self):
        """Every entry is an ErrorGuidance NamedTuple."""
        for key, guidance in ERROR_GUIDANCE.items():
            assert isinstance(guidance, ErrorGuidance), f"{key} is not ErrorGuidance"

    def test_all_entries_have_explanation(self):
        """Every guidance entry must provide an explanation."""
        for key, guidance in ERROR_GUIDANCE.items():
            assert guidance.explanation, f"{key} missing explanation"

    def test_all_entries_have_action(self):
        """Every guidance entry must suggest an action."""
        for key, guidance in ERROR_GUIDANCE.items():
            assert guidance.action, f"{key} missing action"

    @pytest.mark.parametrize(
        "error_name",
        [
            "RegistryStaleError",
            "RegistryMissingError",
            "GateMarkerMissingError",
            "SchemaValidationError",
            "SubAgentTimeoutError",
            "ToolTamperError",
        ],
    )
    def test_known_errors_have_guidance(self, error_name):
        """All six known error types have guidance entries."""
        assert error_name in ERROR_GUIDANCE
        assert ERROR_GUIDANCE[error_name].explanation


class FakeError(Exception):
    """A fake exception type not in the guidance catalog."""


class TestGetGuidance:
    def test_returns_none_for_unknown_error(self):
        """get_guidance returns None for errors not in the catalog."""
        assert get_guidance(FakeError("test")) is None

    def test_returns_guidance_for_known_error(self):
        """get_guidance returns ErrorGuidance for registered error types."""
        err = type("RegistryStaleError", (Exception,), {})("stale")
        result = get_guidance(err)
        assert result is not None
        assert isinstance(result, ErrorGuidance)

    def test_returns_none_for_base_exception(self):
        """A plain Exception is not in the catalog."""
        assert get_guidance(Exception("generic")) is None

    def test_subclass_of_known_error_returns_none(self):
        """Subclasses of known errors are not matched (exact class name match)."""

        class RegistryStaleError(Exception):
            pass

        class SubRegistryStaleError(RegistryStaleError):
            pass

        result = get_guidance(SubRegistryStaleError("sub"))
        # SubRegistryStaleError is the class name, not in catalog
        assert result is None
