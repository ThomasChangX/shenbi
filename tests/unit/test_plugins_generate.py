"""Unit tests for plugins/generate.py happy paths."""

from __future__ import annotations

import pytest

from shenbi.plugins.generate import (
    _common_header,
    _js_string,
    gen_claude,
    gen_codex,
    load_master,
)


@pytest.mark.unit
def test_load_master_returns_dict_with_required_fields() -> None:
    master = load_master()
    assert isinstance(master, dict)
    for field in ("name", "version", "description", "author", "skills", "platforms"):
        assert field in master, f"missing required field: {field}"


@pytest.mark.unit
def test_common_header_returns_canonical_key_order() -> None:
    master = {
        "name": "test",
        "version": "0.1.0",
        "description": "d",
        "author": "a",
        "skills": [],
    }
    header = _common_header(master)
    assert list(header.keys()) == ["name", "version", "description", "author"]


@pytest.mark.unit
def test_gen_claude_returns_dict_with_skills() -> None:
    master = {
        "name": "test",
        "version": "0.1.0",
        "description": "d",
        "author": "a",
        "skills": [{"name": "skill-x"}],
    }
    result = gen_claude(master, {})
    assert result["skills"] == master["skills"]
    assert "name" in result


@pytest.mark.unit
def test_gen_codex_adds_marketplace_and_type() -> None:
    master = {
        "name": "test",
        "version": "0.1.0",
        "description": "d",
        "author": "a",
        "skills": [],
    }
    config = {"fields": {"marketplace": "mp", "type": "skill"}}
    result = gen_codex(master, config)
    assert result["marketplace"] == "mp"
    assert result["type"] == "skill"


@pytest.mark.unit
def test_js_string_escapes_apostrophe_and_backslash() -> None:
    assert _js_string("it's") == "it\\'s"
    assert _js_string("a\\b") == "a\\\\b"
    assert _js_string("plain") == "plain"
