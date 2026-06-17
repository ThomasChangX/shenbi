"""Bespoke error-path tests for g4_genre_config.

genre_config resolves project_dir = fps[0].parent.parent, so fps[0] lives
at <project_dir>/<sub>/<file>.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from shenbi.gates.g4.genre_config import g4_genre_config


def _result(s: str) -> dict[str, Any]:
    return json.loads(s)


def _setup(tmp_path: Path) -> tuple[Path, Path]:
    project_dir = tmp_path / "project"
    sub_dir = project_dir / "skill-output"
    sub_dir.mkdir(parents=True)
    marker = sub_dir / "out.md"
    marker.write_text("x", encoding="utf-8")
    return project_dir, marker


def _genre(project_dir: Path, content: object) -> None:
    (project_dir / "genre-config.json").write_text(json.dumps(content), encoding="utf-8")


@pytest.mark.unit
def test_fails_when_chapter_word_below_floor(tmp_path: Path) -> None:
    """chapter_word.default < 1000 -> FAIL with G4.gc.chapter_word:{n}<1000."""
    project_dir, marker = _setup(tmp_path)
    _genre(
        project_dir,
        {
            "chapter_word": {"default": 500},
            "fatigue_words": ["突然"],
            "audit_dimensions": {"a": 1, "b": 2, "c": 3, "d": 4, "e": 5},
        },
    )

    result = _result(g4_genre_config([str(marker)]))
    assert result["status"] == "FAIL"
    assert any(mf == "G4.gc.chapter_word:500<1000" for mf in result["must_fix"])


@pytest.mark.unit
def test_fails_when_fatigue_words_absent(tmp_path: Path) -> None:
    """No fatigue_words field -> FAIL.

    The checker defaults missing fatigue_words to {} (an empty dict), which
    trips the dict branch's has_words=False guard. pins current behavior:
    missing collapses to G4.gc.fatigue_words:empty, never :missing.
    """
    project_dir, marker = _setup(tmp_path)
    _genre(
        project_dir,
        {
            "chapter_word": {"default": 3000},
            "audit_dimensions": {"a": 1, "b": 2, "c": 3, "d": 4, "e": 5},
        },
    )

    result = _result(g4_genre_config([str(marker)]))
    assert result["status"] == "FAIL"
    assert any(mf == "G4.gc.fatigue_words:empty" for mf in result["must_fix"])


@pytest.mark.unit
def test_fails_when_fatigue_words_is_string_not_list(tmp_path: Path) -> None:
    """fatigue_words given as a scalar string -> FAIL with G4.gc.fatigue_words:missing.

    The checker accepts dict-of-lists or non-empty list; a bare string is
    neither and falls through to the missing branch.
    """
    project_dir, marker = _setup(tmp_path)
    _genre(
        project_dir,
        {
            "chapter_word": {"default": 3000},
            "fatigue_words": "突然, 瞬间",
            "audit_dimensions": {"a": 1, "b": 2, "c": 3, "d": 4, "e": 5},
        },
    )

    result = _result(g4_genre_config([str(marker)]))
    assert result["status"] == "FAIL"
    assert any(mf == "G4.gc.fatigue_words:missing" for mf in result["must_fix"])


@pytest.mark.unit
def test_fails_when_fatigue_words_dict_has_no_populated_lists(tmp_path: Path) -> None:
    """fatigue_words as a dict whose values are all empty lists -> G4.gc.fatigue_words:empty."""
    project_dir, marker = _setup(tmp_path)
    _genre(
        project_dir,
        {
            "chapter_word": {"default": 3000},
            "fatigue_words": {"level1": [], "level2": []},
            "audit_dimensions": {"a": 1, "b": 2, "c": 3, "d": 4, "e": 5},
        },
    )

    result = _result(g4_genre_config([str(marker)]))
    assert result["status"] == "FAIL"
    assert any(mf == "G4.gc.fatigue_words:empty" for mf in result["must_fix"])


@pytest.mark.unit
def test_fails_when_audit_dimensions_below_five(tmp_path: Path) -> None:
    """audit_dimensions with < 5 entries -> FAIL with G4.gc.audit_dimensions:{n}<5."""
    project_dir, marker = _setup(tmp_path)
    _genre(
        project_dir,
        {
            "chapter_word": {"default": 3000},
            "fatigue_words": ["突然"],
            "audit_dimensions": {"a": 1, "b": 2},
        },
    )

    result = _result(g4_genre_config([str(marker)]))
    assert result["status"] == "FAIL"
    assert any(mf == "G4.gc.audit_dimensions:2<5" for mf in result["must_fix"])


@pytest.mark.unit
def test_fails_when_genre_config_not_found(tmp_path: Path) -> None:
    """No genre-config.json -> FAIL with G4.gc.not_found."""
    project_dir, marker = _setup(tmp_path)

    result = _result(g4_genre_config([str(marker)]))
    assert result["status"] == "FAIL"
    assert any(mf == "G4.gc.not_found" for mf in result["must_fix"])
