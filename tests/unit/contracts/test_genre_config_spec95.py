"""Spec #95 T2 (阶段8 M2): volume_opening_protocol schema validation faces."""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from shenbi.contracts.skills.genre_config import GenreConfig


def _base() -> dict[str, object]:
    with open("tests/fixtures/genre-config-example.json", encoding="utf-8") as f:
        cfg = dict(json.load(f))
    cfg["market_params"] = {
        "payoff_density": {"window": 3, "min": 1},
        "hook_grading": {"max_consecutive_micro": 2},
    }
    return cfg


def test_valid_subkey_passes() -> None:
    cfg = _base()
    cfg["market_params"]["volume_opening_protocol"] = {  # type: ignore[index]
        "热开篇": "危机开场",
        "shadow": True,
    }
    GenreConfig.model_validate(cfg)


def test_empty_block_rejected() -> None:
    cfg = _base()
    cfg["market_params"]["volume_opening_protocol"] = {}  # type: ignore[index]
    with pytest.raises(ValidationError, match="非空"):
        GenreConfig.model_validate(cfg)


def test_empty_key_rejected() -> None:
    cfg = _base()
    cfg["market_params"]["volume_opening_protocol"] = {"": "v"}  # type: ignore[index]
    with pytest.raises(ValidationError, match="键须非空"):
        GenreConfig.model_validate(cfg)
