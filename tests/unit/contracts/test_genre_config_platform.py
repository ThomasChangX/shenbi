"""spec #72 T1: primary_platform optional top-level key + fanqie_update sub-block.

Four-station closed-keyset sync (ownership.GENRE_KEYS / Pydantic model /
genre-config SKILL template / project config) — this file pins stations 1-2.
"""

from __future__ import annotations

import pytest

from shenbi.contracts.ownership import GENRE_KEYS
from shenbi.contracts.skills.genre_config import GenreConfig


def _base() -> dict[str, object]:
    return {
        "approval": {"decision": "approved"},
        # validator bounds: chapterTypes 6-10 / auditDimensions 5-10 (genre_config.py:106-118)
        "auditDimensions": {f"d{i}": True for i in range(5)},
        "chapterTypes": {f"t{i}": True for i in range(6)},
        "customRules": [],
        "fatigueWords": {"禁用": []},
        "pacing": {},
        "updated": "",
        "version": "1",
        "chapter_word": {
            "default": 3200,
            "min": 2800,
            "max": 4000,
            "fanqie_update": {"min": 1800, "max": 2800},
        },
    }


@pytest.mark.unit
def test_primary_platform_in_genre_keys() -> None:
    assert "primary_platform" in GENRE_KEYS
    assert len(GENRE_KEYS) == 11


@pytest.mark.unit
def test_optional_key_absent_still_valid() -> None:
    cfg = GenreConfig.model_validate(_base())
    assert cfg.primary_platform == ""


@pytest.mark.unit
def test_primary_platform_enum() -> None:
    data = _base() | {"primary_platform": "qidian"}
    assert GenreConfig.model_validate(data).primary_platform == "qidian"
    with pytest.raises(Exception, match="primary_platform"):
        GenreConfig.model_validate(_base() | {"primary_platform": "zongheng"})


@pytest.mark.unit
def test_fanqie_update_subkey_passes() -> None:
    # chapter_word 子键不受顶层闭键集约束（spec 施工面 1）
    GenreConfig.model_validate(_base())


@pytest.mark.unit
def test_unknown_top_level_key_rejected() -> None:
    with pytest.raises(Exception, match="unknown top-level key"):
        GenreConfig.model_validate(_base() | {"platforms": {}})


@pytest.mark.unit
def test_required_keys_still_eight() -> None:
    from shenbi.contracts.skills.genre_config import _REQUIRED_TOP_KEYS

    assert len(_REQUIRED_TOP_KEYS) == 8
    assert "primary_platform" not in _REQUIRED_TOP_KEYS
