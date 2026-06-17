"""Bespoke error-path tests for g4_worldbuilding.

worldbuilding resolves project_dir = fps[0].parent.parent, so each test
places files at <project_dir>/<sub>/<file> and passes <sub>/<file> as
fps[0] so the checker reads <project_dir>/<file>.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from shenbi.gates.g4.worldbuilding import g4_worldbuilding


def _result(s: str) -> dict[str, Any]:
    return json.loads(s)


def _setup(tmp_path: Path) -> tuple[Path, Path]:
    """Build a <project>/<sub>/ tree; return (project_dir, marker file).

    fps[0] lives at <project>/<sub>/<file> so fps[0].parent.parent == project_dir.
    """
    project_dir = tmp_path / "project"
    sub_dir = project_dir / "skill-output"
    sub_dir.mkdir(parents=True)
    marker = sub_dir / "out.md"
    marker.write_text("x", encoding="utf-8")
    return project_dir, marker


def _novel(project_dir: Path, **overrides: object) -> None:
    data: dict[str, object] = {
        "title": "T",
        "genre": ["x"],
        "language": "zh",
        "target_words": 100000,
    }
    data.update(overrides)
    (project_dir / "novel.json").write_text(json.dumps(data), encoding="utf-8")


@pytest.mark.unit
def test_fails_when_novel_json_missing_required_field(tmp_path: Path) -> None:
    """novel.json missing a required field (title) -> FAIL with G4.novel.missing_title."""
    project_dir, marker = _setup(tmp_path)
    _novel(project_dir, title=None)
    (project_dir / "genre-config.json").write_text(
        json.dumps({"chapter_word": {"default": 3000}}), encoding="utf-8"
    )

    result = _result(g4_worldbuilding([str(marker)]))
    assert result["status"] == "FAIL"
    assert any("G4.novel.missing_title" in mf for mf in result["must_fix"])


@pytest.mark.unit
def test_fails_when_novel_json_not_found(tmp_path: Path) -> None:
    """No novel.json at all -> FAIL with G4.novel.not_found."""
    project_dir, marker = _setup(tmp_path)

    result = _result(g4_worldbuilding([str(marker)]))
    assert result["status"] == "FAIL"
    assert any(mf == "G4.novel.not_found" for mf in result["must_fix"])


@pytest.mark.unit
def test_fails_when_genre_config_not_found(tmp_path: Path) -> None:
    """No genre-config.json -> FAIL with G4.genre_config.not_found."""
    project_dir, marker = _setup(tmp_path)
    _novel(project_dir)

    result = _result(g4_worldbuilding([str(marker)]))
    assert result["status"] == "FAIL"
    assert any(mf == "G4.genre_config.not_found" for mf in result["must_fix"])


@pytest.mark.unit
def test_fails_when_story_bible_has_too_few_sections(tmp_path: Path) -> None:
    """story_bible.md with < 4 '## ' headings -> FAIL with G4.sb.sections."""
    project_dir, marker = _setup(tmp_path)
    _novel(project_dir)
    (project_dir / "genre-config.json").write_text(
        json.dumps({"chapter_word": {"default": 3000}}), encoding="utf-8"
    )
    world = project_dir / "world"
    world.mkdir()
    (world / "story_bible.md").write_text(
        "# Bible\n\n## One\n\n## Two\n\n",
        encoding="utf-8",
    )

    result = _result(g4_worldbuilding([str(marker)]))
    assert result["status"] == "FAIL"
    assert any("G4.sb.sections:found_2_need_4" in mf for mf in result["must_fix"])


@pytest.mark.unit
def test_fails_when_story_bible_bullet_density_above_threshold(tmp_path: Path) -> None:
    """story_bible.md dominated by bullet lines (>5%) -> FAIL with G4.sb.bullet_density."""
    project_dir, marker = _setup(tmp_path)
    _novel(project_dir)
    (project_dir / "genre-config.json").write_text(
        json.dumps({"chapter_word": {"default": 3000}}), encoding="utf-8"
    )
    world = project_dir / "world"
    world.mkdir()
    body = (
        "# Bible\n\n## One\n- a\n- b\n- c\n\n"
        "## Two\n- d\n- e\n- f\n\n"
        "## Three\n- g\n- h\n\n"
        "## Four\n- i\n- j\n"
    )
    (world / "story_bible.md").write_text(body, encoding="utf-8")

    result = _result(g4_worldbuilding([str(marker)]))
    assert result["status"] == "FAIL"
    assert any("G4.sb.bullet_density:" in mf for mf in result["must_fix"])
