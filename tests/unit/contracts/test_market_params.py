"""spec #73 T1: market_params three-state validation + four-station key count."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from shenbi.contracts.ownership import GENRE_KEYS
from shenbi.contracts.skills.genre_config import GenreConfig
from tests.unit.contracts.test_genre_config_platform import _base

_FULL = {
    "payoff_density": {"window": 3, "min": 1},
    "emotion_band": {"window": 1, "min": 1},
    "hook_grading": {"max_consecutive_micro": 2},
    "voice_density_min": {"min_per_chapter": 2},
    "meme_quota": {"per_volume": 3},
}


@pytest.mark.unit
def test_genre_keys_twelve() -> None:
    assert "market_params" in GENRE_KEYS
    assert len(GENRE_KEYS) == 12


@pytest.mark.unit
def test_absent_block_passes() -> None:
    GenreConfig.model_validate(_base())  # 顶层缺块 PASS（可选——存量 fixture 全兼容）


@pytest.mark.unit
def test_full_block_passes() -> None:
    cfg = GenreConfig.model_validate(_base() | {"market_params": _FULL})
    assert cfg.market_params["payoff_density"]["window"] == 3


@pytest.mark.unit
def test_missing_subkey_fails() -> None:
    partial = {k: v for k, v in _FULL.items() if k != "payoff_density"}
    with pytest.raises(Exception, match="payoff_density"):
        GenreConfig.model_validate(_base() | {"market_params": partial})


@pytest.mark.unit
def test_out_of_range_fails() -> None:
    with pytest.raises(Exception, match="window"):
        GenreConfig.model_validate(
            _base() | {"market_params": _FULL | {"payoff_density": {"window": 99, "min": 1}}}
        )
    with pytest.raises(Exception, match="max_consecutive_micro"):
        GenreConfig.model_validate(
            _base() | {"market_params": _FULL | {"hook_grading": {"max_consecutive_micro": 9}}}
        )


@pytest.mark.unit
def test_g4_three_state_via_real_checker(tmp_path: Path) -> None:
    """G4 genre_config three states: absent PASS / full PASS / out-of-range FAIL."""
    from shenbi.gates.g4.genre_config import g4_genre_config

    base_ok = tmp_path / "genre-config.json"
    base_ok.write_text(
        json.dumps(_base() | {"market_params": _FULL}, ensure_ascii=False), encoding="utf-8"
    )
    r = g4_genre_config([str(base_ok)], rd=str(tmp_path))
    assert "window" not in r and "market_params:" not in r

    absent = tmp_path / "genre-config-absent.json"
    absent.write_text(json.dumps(_base(), ensure_ascii=False), encoding="utf-8")
    assert "market_params" not in g4_genre_config([str(absent)], rd=str(tmp_path))

    bad = tmp_path / "genre-config-bad.json"
    bad.write_text(
        json.dumps(
            _base() | {"market_params": _FULL | {"payoff_density": {"window": 99, "min": 1}}},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    r2 = g4_genre_config([str(bad)], rd=str(tmp_path))
    assert "window" in r2 or "market_params" in r2
