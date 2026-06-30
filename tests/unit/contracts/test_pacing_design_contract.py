"""Tests for pacing-design contract model validators."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from shenbi.contracts.skills.pacing_design import PacingDesign

_BASE = {
    "beats": {"铺垫": 25.0, "升级": 30.0, "爆发": 25.0, "余波": 20.0},
    "line_ratios": {"QUEST": 40.0, "FIRE": 35.0, "CONSTELLATION": 25.0},
    "scene_types": [f"s{i}" for i in range(8)],
    "chapter_sequence": [],
}


def test_valid_config_passes() -> None:
    PacingDesign.model_validate(_BASE)


def test_missing_beat_fails() -> None:
    bad = dict(_BASE)
    bad["beats"] = {"铺垫": 50, "升级": 50}
    with pytest.raises(ValidationError, match="missing beats"):
        PacingDesign.model_validate(bad)


def test_beat_sum_not_100_fails() -> None:
    bad = dict(_BASE)
    bad["beats"] = {"铺垫": 25, "升级": 25, "爆发": 25, "余波": 50}
    with pytest.raises(ValidationError, match="100"):
        PacingDesign.model_validate(bad)


def test_missing_line_fails() -> None:
    bad = dict(_BASE)
    bad["line_ratios"] = {"QUEST": 50, "FIRE": 50}
    with pytest.raises(ValidationError, match="CONSTELLATION"):
        PacingDesign.model_validate(bad)


def test_constellation_out_of_range_fails() -> None:
    bad = dict(_BASE)
    bad["line_ratios"] = {"QUEST": 50, "FIRE": 35, "CONSTELLATION": 15}
    with pytest.raises(ValidationError, match="CONSTELLATION"):
        PacingDesign.model_validate(bad)


def test_wrong_scene_type_count_fails() -> None:
    bad = dict(_BASE)
    bad["scene_types"] = [f"s{i}" for i in range(6)]
    with pytest.raises(ValidationError, match="8 scene types"):
        PacingDesign.model_validate(bad)


def test_three_consecutive_same_fails() -> None:
    bad = dict(_BASE)
    bad["chapter_sequence"] = ["battle", "battle", "battle", "dialogue"]
    with pytest.raises(ValidationError, match="3 consecutive"):
        PacingDesign.model_validate(bad)


def test_from_markdown_parses_beats() -> None:
    md = "铺垫 25% 升级 30% 爆发 25% 余波 20%\nQUEST 40% FIRE 35% CONSTELLATION 25%\n战斗 对话 日常 探索 修炼 阴谋 逃亡 揭示"
    m = PacingDesign.from_markdown(md)
    assert m.beats["铺垫"] == 25.0
    assert m.line_ratios["CONSTELLATION"] == 25.0


def test_registry_includes_pacing_design() -> None:
    from shenbi.contracts.registry import REGISTRY

    assert "shenbi-pacing-design" in REGISTRY
