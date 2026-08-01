"""Unit tests for plugins/generate.py happy paths."""

from __future__ import annotations

from pathlib import Path

import pytest

from shenbi.plugins.generate import (
    _common_header,
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


# ---------------------------------------------------------------------------
# load_master validation + generate_all/main branch coverage (PR-56 fill)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_load_master_raises_on_non_dict_master(tmp_path: Path, monkeypatch) -> None:
    """master.json that parses to a non-object -> ValueError (expected JSON object)."""
    from shenbi.plugins import generate as gen_mod

    fake = tmp_path / "master.json"
    fake.write_text("[1, 2, 3]", encoding="utf-8")
    monkeypatch.setattr(gen_mod, "MASTER_PATH", fake)
    with pytest.raises(ValueError, match="expected JSON object"):
        gen_mod.load_master()


@pytest.mark.unit
def test_load_master_raises_on_missing_required_fields(tmp_path: Path, monkeypatch) -> None:
    """master.json missing required fields -> ValueError listing them."""
    import json as _json

    from shenbi.plugins import generate as gen_mod

    fake = tmp_path / "master.json"
    fake.write_text(_json.dumps({"name": "x"}), encoding="utf-8")  # missing most fields
    monkeypatch.setattr(gen_mod, "MASTER_PATH", fake)
    with pytest.raises(ValueError, match="missing required fields"):
        gen_mod.load_master()


@pytest.mark.unit
def test_generate_all_writes_all_platform_manifests(tmp_path: Path, monkeypatch) -> None:
    """generate_all writes each platform manifest under REPO_ROOT/config.output.

    Covers generate.py:103-126 (the full generation loop, json write branch)
    across the codex generator.
    """
    import json as _json

    from shenbi.plugins import generate as gen_mod

    master_data = {
        "name": "t",
        "version": "0.1.0",
        "description": "d",
        "author": "a",
        "skills": ["s1"],
        "platforms": {
            "codex-cli": {
                "format": "codex-cli",
                "output": ".codex-plugin/plugin.json",
                "fields": {"marketplace": "mp", "type": "skill"},
            },
        },
    }
    fake = tmp_path / "master.json"
    fake.write_text(_json.dumps(master_data), encoding="utf-8")
    monkeypatch.setattr(gen_mod, "MASTER_PATH", fake)
    monkeypatch.setattr(gen_mod, "REPO_ROOT", tmp_path)
    assert gen_mod.generate_all() == 0
    assert (tmp_path / ".codex-plugin" / "plugin.json").exists()


@pytest.mark.unit
def test_generate_all_unknown_format_returns_1(tmp_path: Path, monkeypatch) -> None:
    """An unrecognized platform format -> generate_all returns 1 (covers 110-112)."""
    import json as _json

    from shenbi.plugins import generate as gen_mod

    master_data = {
        "name": "t",
        "version": "0.1.0",
        "description": "d",
        "author": "a",
        "skills": [],
        "platforms": {"weird": {"format": "no-such-format", "output": "x/y.json"}},
    }
    fake = tmp_path / "master.json"
    fake.write_text(_json.dumps(master_data), encoding="utf-8")
    monkeypatch.setattr(gen_mod, "MASTER_PATH", fake)
    monkeypatch.setattr(gen_mod, "REPO_ROOT", tmp_path)
    assert gen_mod.generate_all() == 1


@pytest.mark.unit
def test_main_delegates_to_generate_all(monkeypatch) -> None:
    """main() returns whatever generate_all returns (covers generate.py:130)."""
    from shenbi.plugins import generate as gen_mod

    monkeypatch.setattr(gen_mod, "generate_all", lambda: 42)
    assert gen_mod.main() == 42
