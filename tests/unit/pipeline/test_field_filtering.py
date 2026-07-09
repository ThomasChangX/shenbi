"""Integration tests for Layer B field-level filtering through dispatch_helper.

Task 12 migrated dispatch_helper to import :func:`filter_to_fields` from
``shenbi.contracts.fields`` (returning a ``(filtered_text, matched_any)`` tuple).
These tests assert that the dispatch_helper read loop correctly delegates to
the shared filter — covering the markdown H2 extraction, JSON key projection,
and the escape-hatch (full text + WARN when nothing matches). The canonical
unit coverage of ``contracts.fields`` lives in ``tests/unit/contracts/test_fields.py``.
"""

from __future__ import annotations

import json

import pytest

from shenbi.contracts.fields import filter_to_fields


@pytest.mark.unit
class TestFilterToFieldsMarkdown:
    def test_markdown_filter_keeps_declared_sections(self) -> None:
        text = "## goal\ncontent"
        result, matched = filter_to_fields(text, ["goal"], "plans/chapter-1-plan.md")
        assert matched is True
        assert "goal" in result
        assert "content" in result

    def test_escape_hatch_returns_full_text_when_no_fields_match(self) -> None:
        """Escape hatch: no declared field found → matched=False, full text returned."""
        text = "## some_other_section\ncontent"
        result, matched = filter_to_fields(text, ["nonexistent_field"], "plans/chapter-1-plan.md")
        assert matched is False
        assert result == text  # fallback to full text


@pytest.mark.unit
class TestFilterToFieldsJson:
    def test_json_filter_projects_declared_keys(self) -> None:
        text = json.dumps({"a": 1, "b": 2})
        result, matched = filter_to_fields(text, ["a"], "genre-config.json")
        assert matched is True
        projected = json.loads(result)
        assert "a" in projected
        assert "b" not in projected

    def test_invalid_json_escape_hatch(self) -> None:
        """Escape hatch: invalid JSON → matched=False, original text returned."""
        result, matched = filter_to_fields("not json", ["a"], "genre-config.json")
        assert matched is False
        assert result == "not json"


@pytest.mark.unit
class TestFilterToFieldsPassthrough:
    def test_unknown_extension_no_filter(self) -> None:
        text = "some content"
        result, matched = filter_to_fields(text, ["field"], "file.txt")
        assert matched is True
        assert result == text  # safe default: no filtering

    def test_empty_fields_no_filter(self) -> None:
        text = "## goal\ncontent"
        result, matched = filter_to_fields(text, [], "plans/chapter-1-plan.md")
        assert matched is True
        assert result == text
