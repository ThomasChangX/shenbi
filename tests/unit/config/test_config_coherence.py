"""Tests for the genre-config update helper with mandatory rationale."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from shenbi.config.config_coherence import ConfigError, update_genre_config


def _seed_genre_config(tmp_path: Path) -> Path:
    cfg = {
        "auditDimensions": {"texture": True, "dialogue": True, "antiAi": True},
        "resonance_global_floor": 65,
    }
    p = tmp_path / "genre-config.json"
    p.write_text(json.dumps(cfg, ensure_ascii=False), encoding="utf-8")
    return p


class TestUpdateGenreConfig:
    def test_non_critical_dim_can_be_disabled_without_rationale(self, tmp_path):
        _seed_genre_config(tmp_path)
        update_genre_config(tmp_path, {"auditDimensions.dialogue": False}, rationale="none needed")
        cfg = json.loads((tmp_path / "genre-config.json").read_text(encoding="utf-8"))
        assert cfg["auditDimensions"]["dialogue"] is False

    def test_critical_dim_requires_long_rationale(self, tmp_path):
        _seed_genre_config(tmp_path)
        with pytest.raises(ConfigError) as exc:
            update_genre_config(tmp_path, {"auditDimensions.texture": False}, rationale="too short")
        assert "texture" in str(exc.value)
        assert ">= 50 char" in str(exc.value)

    def test_critical_dim_accepts_long_rationale(self, tmp_path):
        _seed_genre_config(tmp_path)
        long_rationale = (
            "Disabled because we switched to the shenbi-review-sensory skill which "
            "covers the same sensory-detail detection surface (E34 mitigation)."
        )
        update_genre_config(tmp_path, {"auditDimensions.texture": False}, rationale=long_rationale)
        cfg = json.loads((tmp_path / "genre-config.json").read_text(encoding="utf-8"))
        assert cfg["auditDimensions"]["texture"] is False

    def test_audit_trail_entry_appended(self, tmp_path):
        _seed_genre_config(tmp_path)
        update_genre_config(tmp_path, {"resonance_global_floor": 70}, rationale="raising the bar")
        trail = (tmp_path / "config-change-log.jsonl").read_text(encoding="utf-8")
        entry = json.loads(trail.strip().splitlines()[-1])
        assert entry["key"] == "resonance_global_floor"
        assert entry["old"] == 65
        assert entry["new"] == 70
        assert entry["rationale"] == "raising the bar"
        assert "timestamp" in entry

    def test_floor_too_low_blocks_update(self, tmp_path):
        _seed_genre_config(tmp_path)
        with pytest.raises(ConfigError) as exc:
            update_genre_config(
                tmp_path, {"resonance_global_floor": 40}, rationale="lowering the bar"
            )
        assert "floor_too_low" in str(exc.value)
