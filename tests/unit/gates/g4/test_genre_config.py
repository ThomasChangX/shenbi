"""Tests for g4_genre_config (rewritten: structured Pydantic validation).

The new checker reads fps[0] as the genre-config.json path directly.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from shenbi.gates.g4.genre_config import g4_genre_config


def _result(s: str) -> dict[str, Any]:
    return json.loads(s)


_VALID = {
    "approval": {"decision": "approved"},
    "auditDimensions": {f"d{i}": True for i in range(5)},
    "chapterTypes": {f"c{i}": {} for i in range(8)},
    "customRules": [],
    "fatigueWords": {"禁用": ["w1"], "慎用": ["w2"], "替换建议": {"w1": ["a1"], "w2": ["a2"]}},
    "pacing": {},
    "updated": "2026-01-01",
    "version": "1.0",
}


def _write_gc(tmp_path: Path, data: object) -> str:
    p = tmp_path / "genre-config.json"
    p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return str(p)


@pytest.mark.unit
def test_passes_on_valid_config(tmp_path: Path) -> None:
    gc = _write_gc(tmp_path, _VALID)
    r = _result(g4_genre_config([gc]))
    assert r["status"] == "PASS"


@pytest.mark.unit
def test_fails_when_not_found(tmp_path: Path) -> None:
    r = _result(g4_genre_config([str(tmp_path / "nonexistent.json")]))
    assert r["status"] == "FAIL"
    assert any("invalid_json" in m or "no_input" in m for m in r.get("must_fix", []))


@pytest.mark.unit
def test_fails_when_audit_dimensions_below_five(tmp_path: Path) -> None:
    bad = json.loads(json.dumps(_VALID))
    bad["auditDimensions"] = {"d0": True, "d1": True}
    gc = _write_gc(tmp_path, bad)
    r = _result(g4_genre_config([gc]))
    assert r["status"] == "FAIL"
    assert any("auditDimensions" in m for m in r.get("must_fix", []))


@pytest.mark.unit
def test_fails_when_chapter_types_out_of_range(tmp_path: Path) -> None:
    bad = json.loads(json.dumps(_VALID))
    bad["chapterTypes"] = {f"c{i}": {} for i in range(4)}
    gc = _write_gc(tmp_path, bad)
    r = _result(g4_genre_config([gc]))
    assert r["status"] == "FAIL"


@pytest.mark.unit
def test_fails_on_invalid_approval(tmp_path: Path) -> None:
    bad = json.loads(json.dumps(_VALID))
    bad["approval"]["decision"] = "maybe"
    gc = _write_gc(tmp_path, bad)
    r = _result(g4_genre_config([gc]))
    assert r["status"] == "FAIL"


@pytest.mark.unit
def test_fails_on_banned_word_without_replacement(tmp_path: Path) -> None:
    bad = json.loads(json.dumps(_VALID))
    bad["fatigueWords"]["禁用"].append("noreplace")
    gc = _write_gc(tmp_path, bad)
    r = _result(g4_genre_config([gc]))
    assert r["status"] == "FAIL"


# --- Spec #35 (F232/F214): approval required + keyset bound ----------------
_FIXTURE = Path("tests/fixtures/genre-config-example.json")


def _real_config() -> dict[str, Any]:
    return json.loads(_FIXTURE.read_text(encoding="utf-8"))


@pytest.mark.unit
def test_fails_when_approval_missing(tmp_path: Path) -> None:
    bad = _real_config()
    bad.pop("approval")
    gc = _write_gc(tmp_path, bad)
    r = _result(g4_genre_config([gc]))
    assert r["status"] == "FAIL"
    assert any("approval" in m for m in r.get("must_fix", []))


@pytest.mark.unit
def test_fails_when_approval_empty(tmp_path: Path) -> None:
    bad = _real_config()
    bad["approval"] = {}
    gc = _write_gc(tmp_path, bad)
    r = _result(g4_genre_config([gc]))
    assert r["status"] == "FAIL"
    assert any("approval" in m for m in r.get("must_fix", []))


@pytest.mark.unit
def test_fails_on_unknown_top_level_key(tmp_path: Path) -> None:
    bad = _real_config()
    bad["rogueKey"] = 1
    gc = _write_gc(tmp_path, bad)
    r = _result(g4_genre_config([gc]))
    assert r["status"] == "FAIL"
    assert any("rogueKey" in m for m in r.get("must_fix", []))


@pytest.mark.unit
def test_fails_when_required_key_missing(tmp_path: Path) -> None:
    bad = _real_config()
    bad.pop("pacing")
    gc = _write_gc(tmp_path, bad)
    r = _result(g4_genre_config([gc]))
    assert r["status"] == "FAIL"


@pytest.mark.unit
def test_trope_inventory_optional(tmp_path: Path) -> None:
    cfg = _real_config()
    cfg.pop("tropeInventory")
    gc = _write_gc(tmp_path, cfg)
    r = _result(g4_genre_config([gc]))
    assert r["status"] == "PASS"


@pytest.mark.unit
def test_real_fixture_still_valid(tmp_path: Path) -> None:
    gc = _write_gc(tmp_path, _real_config())
    r = _result(g4_genre_config([gc]))
    assert r["status"] == "PASS"


@pytest.mark.unit
def test_keyset_authority_is_ownership() -> None:
    from shenbi.contracts.ownership import GENRE_KEYS
    from shenbi.contracts.skills.genre_config import _REQUIRED_TOP_KEYS

    assert set(_REQUIRED_TOP_KEYS) == GENRE_KEYS - {"tropeInventory"}
