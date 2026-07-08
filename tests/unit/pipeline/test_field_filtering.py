"""Unit tests for Layer B field-level filtering (B.1)."""

from __future__ import annotations

import json

import pytest

from shenbi.pipeline.dispatch_helper import (
    _extract_h2_sections,
    _filter_to_fields,
    _project_json_keys,
)


@pytest.mark.unit
class TestExtractH2Sections:
    def test_extracts_declared_h2_sections(self) -> None:
        text = """# File

## chapter_goal
Do the thing.

## beats
Beat 1, Beat 2.

## unused_section
Should not appear.
"""
        result = _extract_h2_sections(text, ["chapter_goal", "beats"])
        assert "chapter_goal" in result
        assert "Do the thing" in result
        assert "beats" in result
        assert "Beat 1" in result
        assert "unused_section" not in result

    def test_returns_full_text_when_no_fields_match(self) -> None:
        """Escape hatch: no declared field found → return full text."""
        text = "## some_other_section\ncontent"
        result = _extract_h2_sections(text, ["nonexistent_field"])
        assert result == text  # fallback to full text

    def test_empty_fields_returns_full_text(self) -> None:
        text = "## anything\ncontent"
        result = _extract_h2_sections(text, [])
        assert result == text

    def test_chinese_headings_exact_match_no_lowercase(self) -> None:
        """Real truth files use Chinese headings — no lowercasing/normalization."""
        text = "## 主角状态\n主角信息\n\n## 剧情节点\n节点1\n"
        result = _extract_h2_sections(text, ["主角状态"])
        assert "主角状态" in result
        assert "主角信息" in result
        assert "剧情节点" not in result

    def test_no_h2_headings_returns_full_text(self) -> None:
        """Plain text with no H2 headings → escape hatch."""
        text = "just some plain content\nwithout headings"
        result = _extract_h2_sections(text, ["anything"])
        assert result == text


@pytest.mark.unit
class TestProjectJsonKeys:
    def test_projects_declared_keys(self) -> None:
        data = {"a": 1, "b": 2, "c": 3}
        text = json.dumps(data)
        result = _project_json_keys(text, ["a", "c"])
        projected = json.loads(result)
        assert projected == {"a": 1, "c": 3}
        assert "b" not in projected

    def test_returns_full_text_when_no_keys_match(self) -> None:
        """Escape hatch: no declared key found → return full text."""
        data = {"x": 1}
        text = json.dumps(data)
        result = _project_json_keys(text, ["nonexistent"])
        assert result == text  # fallback

    def test_invalid_json_returns_full_text(self) -> None:
        """Escape hatch: invalid JSON → return original text."""
        result = _project_json_keys("not json", ["a"])
        assert result == "not json"

    def test_empty_fields_returns_full_text(self) -> None:
        data = {"a": 1}
        text = json.dumps(data)
        result = _project_json_keys(text, [])
        assert result == text

    def test_json_array_returns_full_text(self) -> None:
        """Non-dict JSON (array) → no projection, return full text."""
        text = json.dumps([1, 2, 3])
        result = _project_json_keys(text, ["a"])
        assert result == text


@pytest.mark.unit
class TestFilterToFields:
    def test_markdown_filter(self) -> None:
        text = "## goal\ncontent"
        result = _filter_to_fields(text, ["goal"], "plans/chapter-1-plan.md")
        assert "goal" in result

    def test_json_filter(self) -> None:
        text = json.dumps({"a": 1, "b": 2})
        result = _filter_to_fields(text, ["a"], "genre-config.json")
        projected = json.loads(result)
        assert "a" in projected
        assert "b" not in projected

    def test_unknown_extension_no_filter(self) -> None:
        text = "some content"
        result = _filter_to_fields(text, ["field"], "file.txt")
        assert result == text  # safe default: no filtering

    def test_empty_fields_no_filter(self) -> None:
        text = "## goal\ncontent"
        result = _filter_to_fields(text, [], "plans/chapter-1-plan.md")
        assert result == text
