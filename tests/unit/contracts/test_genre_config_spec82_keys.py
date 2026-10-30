"""spec #82 Task 3: market_params new keys (three-source landing) + emotion_band retirement.

Validator domains for the nine new keys; emotion_band leaves the required
tuple (legacy configs carrying it still PASS — subkey extras are tolerated;
configs without it must PASS too — the `eb = v["emotion_band"]` direct access
was a KeyError waiting to happen once retirement began).
"""

from __future__ import annotations

from typing import Any

import pytest

from shenbi.contracts.skills.genre_config import GenreConfig

BASE: dict[str, Any] = {
    "approval": {"decision": "approved"},
    "auditDimensions": {f"d{i}": True for i in range(5)},
    "chapterTypes": {f"t{i}": True for i in range(6)},
    "customRules": [],
    "fatigueWords": {"禁用": []},
    "pacing": {},
    "updated": "",
    "version": "1",
    "market_params": {
        "payoff_density": {"window": 3, "min": 1},
        "hook_grading": {"max_consecutive_micro": 2},
    },
}


def _cfg(
    extra_market: dict[str, dict[str, Any]] | None = None, *, drop_emotion_band: bool = False
) -> dict[str, Any]:
    cfg = dict(BASE)
    mp: dict[str, Any] = dict(cfg["market_params"])
    if not drop_emotion_band:
        mp["emotion_band"] = {"window": 1, "min": 1}
    if extra_market:
        mp.update(extra_market)
    cfg["market_params"] = mp
    return cfg


NEW_KEYS_FULL: dict[str, dict[str, Any]] = {
    "cold_streak_cap": {"max": 3, "shadow": True},
    "hot_hook_floor": {"window": 10, "min": 1, "shadow": True},
    "payoff_magnitude_floor": {"window": 6, "min": "中", "shadow": True},
    "temperature_profile": {"window": 10, "hot_ratio_min": 0.2},
    "hook_max_age": {"max": 8, "shadow": True},
    "hook_rotation": {"shadow": True},
    "quote_anchor": {"shadow": True},
    "retention_anchor": {"from_ch": 1, "to_ch": None, "shadow": True},
    "hook_defer_budget": {"per_volume": 3},
}


@pytest.mark.unit
def test_new_nine_keys_accepted() -> None:
    GenreConfig.model_validate(_cfg(NEW_KEYS_FULL))


@pytest.mark.unit
def test_emotion_band_retired_but_tolerated() -> None:
    """Legacy configs carrying emotion_band still PASS (characterization)."""
    GenreConfig.model_validate(_cfg())  # carries emotion_band


@pytest.mark.unit
def test_config_without_emotion_band_passes() -> None:
    """audit-T2-class guard: retirement must not KeyError on absence."""
    GenreConfig.model_validate(_cfg(drop_emotion_band=True))


@pytest.mark.unit
def test_toch_none_tolerated() -> None:
    GenreConfig.model_validate(_cfg({"retention_anchor": {"from_ch": 1, "to_ch": None}}))


@pytest.mark.unit
def test_payoff_min_string_tolerated() -> None:
    GenreConfig.model_validate(_cfg({"payoff_magnitude_floor": {"window": 6, "min": "中"}}))


@pytest.mark.unit
def test_cold_streak_cap_domain() -> None:
    with pytest.raises(ValueError, match="cold_streak_cap"):
        GenreConfig.model_validate(_cfg({"cold_streak_cap": {"max": 0}}))
    with pytest.raises(ValueError, match="cold_streak_cap"):
        GenreConfig.model_validate(_cfg({"cold_streak_cap": {"max": 13}}))
