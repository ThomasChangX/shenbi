from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from shenbi.contracts.skills.genre_config import GenreConfig

# Base valid config (minimal structure that passes all validators)
_BASE = {
    "approval": {"decision": "approved", "reviewer": "test", "date": "2026-01-01"},
    "auditDimensions": {f"dim{i}": True for i in range(5)},
    "chapterTypes": {f"ch{i}": {"maxConsecutive": 3} for i in range(8)},
    "customRules": [],
    "fatigueWords": {
        "禁用": ["word1"],
        "慎用": ["word2"],
        "替换建议": {"word1": ["alt1"], "word2": ["alt2"]},
    },
    "pacing": {},
    "updated": "2026-01-01",
    "version": "1.0",
}


def test_valid_config_passes() -> None:
    GenreConfig.model_validate(_BASE)


def test_invalid_approval_decision() -> None:
    bad = json.loads(json.dumps(_BASE))
    bad["approval"]["decision"] = "maybe"
    with pytest.raises(ValidationError, match="approved"):
        GenreConfig.model_validate(bad)


def test_too_many_banned_words() -> None:
    bad = json.loads(json.dumps(_BASE))
    bad["fatigueWords"]["禁用"] = [f"w{i}" for i in range(51)]
    with pytest.raises(ValidationError, match="> 50"):
        GenreConfig.model_validate(bad)


def test_banned_word_without_replacement() -> None:
    bad = json.loads(json.dumps(_BASE))
    bad["fatigueWords"]["禁用"].append("noreplacement")
    with pytest.raises(ValidationError, match="noreplacement"):
        GenreConfig.model_validate(bad)


def test_cautioned_word_without_replacement() -> None:
    bad = json.loads(json.dumps(_BASE))
    bad["fatigueWords"]["慎用"].append("noreplacement")
    with pytest.raises(ValidationError, match="noreplacement"):
        GenreConfig.model_validate(bad)


def test_too_few_chapter_types() -> None:
    bad = json.loads(json.dumps(_BASE))
    bad["chapterTypes"] = {f"ch{i}": {} for i in range(5)}
    with pytest.raises(ValidationError, match="chapterTypes"):
        GenreConfig.model_validate(bad)


def test_too_many_chapter_types() -> None:
    bad = json.loads(json.dumps(_BASE))
    bad["chapterTypes"] = {f"ch{i}": {} for i in range(11)}
    with pytest.raises(ValidationError, match="chapterTypes"):
        GenreConfig.model_validate(bad)


def test_too_few_audit_dimensions() -> None:
    bad = json.loads(json.dumps(_BASE))
    bad["auditDimensions"] = {f"d{i}": True for i in range(4)}
    with pytest.raises(ValidationError, match="auditDimensions"):
        GenreConfig.model_validate(bad)


def test_registry_includes_genre_config() -> None:
    from shenbi.contracts.registry import REGISTRY

    assert "shenbi-genre-config" in REGISTRY
