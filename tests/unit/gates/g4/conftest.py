"""Fixtures for G4 checker tests."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def sample_skill_output(tmp_path: Path) -> Path:
    """Minimal skill-output directory with novel.json + genre-config.json."""
    (tmp_path / "novel.json").write_text(
        '{"title": "Test", "genre": ["test"], "language": "zh", "target_words": 100000}',
        encoding="utf-8",
    )
    (tmp_path / "genre-config.json").write_text(
        '{"chapter_word": {"default": 3000}, "fatigue_words": []}',
        encoding="utf-8",
    )
    return tmp_path


@pytest.fixture
def empty_skill_output(tmp_path: Path) -> Path:
    """Empty directory — checkers should return FAIL, not crash."""
    return tmp_path
