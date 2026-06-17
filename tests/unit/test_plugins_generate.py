"""Unit tests for plugins/generate.py happy paths."""

from __future__ import annotations

import pytest

from shenbi.plugins.generate import (
    _common_header,
    _js_string,
    gen_claude,
    gen_codex,
    gen_cursor,
    gen_opencode,
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


@pytest.mark.unit
def test_gen_cursor_adds_plugin_root_and_hooks() -> None:
    """gen_cursor returns dict with pluginRoot and hooks."""
    master = {"name": "t", "version": "0.1.0", "description": "d", "author": "a", "skills": []}
    config = {"fields": {"pluginRoot": ".codex", "hooks": {"onStart": "run.sh"}}}
    result = gen_cursor(master, config)
    assert result["pluginRoot"] == ".codex"
    assert result["hooks"] == config["fields"]["hooks"]


@pytest.mark.unit
def test_gen_opencode_returns_valid_es_module() -> None:
    """gen_opencode returns a JS module with name, version, description, author, skills."""
    master = {"name": "t", "version": "0.1.0", "description": "d", "author": "a", "skills": ["s1"]}
    result = gen_opencode(master, {})
    assert "export default" in result
    assert "name: 't'" in result
    assert "skills:" in result
    assert "'s1'" in result


@pytest.mark.unit
def test_gen_opencode_escapes_special_chars() -> None:
    """gen_opencode properly escapes apostrophes and backslashes."""
    master = {"name": "it's", "version": "0.1.0", "description": "a\\b", "author": "a", "skills": []}
    result = gen_opencode(master, {})
    assert "it\\'s" in result
    assert "a\\\\b" in result
    assert result.endswith("\n")


@pytest.mark.unit
def test_load_master_with_valid_master_fails_on_bad_data(tmp_path: Path) -> None:
    """load_master raises FileNotFoundError on missing file, ValueError on invalid data.

    monkeypatch the MASTER_PATH to simulate errors.
    """
    import pytest
    from shenbi.plugins import generate as gen_mod
    from shenbi.plugins.generate import load_master
    original = gen_mod.MASTER_PATH
    # Test with non-existent path
    gen_mod.MASTER_PATH = tmp_path / "nonexistent.json"
    with pytest.raises(FileNotFoundError):
        load_master()
    gen_mod.MASTER_PATH = original  # restore
