"""Tests for the genre-config update helper with mandatory rationale."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from shenbi.config.config_coherence import (
    AUDIT_TRAIL_NAME,
    ConfigError,
    govern_genre_config_change,
    update_genre_config,
)


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


_LONG = "x" * 55  # >= RATIONALE_MIN_CHARS


def _real_config(tmp_path):
    """Copy of the real genre-config fixture (G0.9: no hand-crafted mocks)."""
    src = Path(__file__).parents[2] / "fixtures" / "genre-config-example.json"
    cfg = json.loads(src.read_text(encoding="utf-8"))
    (tmp_path / "genre-config.json").write_text(json.dumps(cfg), encoding="utf-8")
    return cfg


class TestRule1BypassVectors:
    def test_whole_key_object_overwrite_blocked(self, tmp_path):
        _real_config(tmp_path)
        victim = dict.fromkeys(("texture", "antiAi", "continuity"), False)
        with pytest.raises(ConfigError):
            update_genre_config(tmp_path, {"auditDimensions": victim}, rationale="none")

    def test_falsy_zero_blocked(self, tmp_path):
        # antiAi is True in the real fixture (texture is already false there)
        _real_config(tmp_path)
        with pytest.raises(ConfigError):
            update_genre_config(tmp_path, {"auditDimensions.antiAi": 0}, rationale="none")

    def test_snake_case_key_blocked(self, tmp_path):
        # Strip camelCase first: with camel present, the snake write is a
        # camel-wins no-op (declared merge semantics), not a bypass.
        cfg = _real_config(tmp_path)
        del cfg["auditDimensions"]
        (tmp_path / "genre-config.json").write_text(json.dumps(cfg), encoding="utf-8")
        with pytest.raises(ConfigError):
            update_genre_config(tmp_path, {"audit_dimensions.antiAi": False}, rationale="none")

    def test_malformed_scalar_change_blocked(self, tmp_path):
        _real_config(tmp_path)
        with pytest.raises(ConfigError):
            update_genre_config(tmp_path, {"auditDimensions": False}, rationale=_LONG)

    def test_valid_disable_with_rationale_passes(self, tmp_path):
        _real_config(tmp_path)
        update_genre_config(tmp_path, {"auditDimensions.texture": False}, rationale=_LONG)
        trail = (tmp_path / AUDIT_TRAIL_NAME).read_text(encoding="utf-8")
        assert '"key": "auditDimensions.texture"' in trail


class TestRule2TypeGuard:
    def test_float_below_trigger_blocked(self, tmp_path):
        _real_config(tmp_path)
        with pytest.raises(ConfigError):
            update_genre_config(tmp_path, {"resonance_global_floor": 59.5}, rationale=_LONG)

    def test_string_floor_blocked(self, tmp_path):
        _real_config(tmp_path)
        with pytest.raises(ConfigError):
            update_genre_config(tmp_path, {"resonance_global_floor": "50"}, rationale=_LONG)

    def test_float_above_trigger_ok(self, tmp_path):
        _real_config(tmp_path)
        update_genre_config(tmp_path, {"resonance_global_floor": 60.0}, rationale=_LONG)


class TestTwoPhaseCommit:
    def test_mixed_batch_leaves_no_phantom_trail(self, tmp_path):
        _real_config(tmp_path)
        with pytest.raises(ConfigError):
            update_genre_config(
                tmp_path,
                {"auditDimensions.dialogue": False, "auditDimensions.antiAi": False},
                rationale="short",
            )
        assert not (tmp_path / AUDIT_TRAIL_NAME).exists()
        cfg = json.loads((tmp_path / "genre-config.json").read_text(encoding="utf-8"))
        assert cfg["auditDimensions"]["dialogue"] is True
        assert cfg["auditDimensions"]["antiAi"] is True


class TestDeltaSemantics:
    def test_whole_key_omitting_critical_blocked(self, tmp_path):
        """audit-T1 C1: omission-shape whole-key overwrite drops critical dims."""
        _real_config(tmp_path)
        with pytest.raises(ConfigError):
            update_genre_config(tmp_path, {"auditDimensions": {"dialogue": True}}, rationale="none")

    def test_benign_change_with_preexisting_disabled_critical_ok(self, tmp_path):
        """audit-T1 I1: pre-existing texture=false must not block dialogue change."""
        _real_config(tmp_path)  # fixture has texture: false
        update_genre_config(tmp_path, {"auditDimensions.dialogue": False}, rationale="none needed")

    def test_none_rationale_is_configerror_not_typeerror(self, tmp_path):
        _real_config(tmp_path)
        with pytest.raises(ConfigError):
            update_genre_config(tmp_path, {"auditDimensions.antiAi": False}, rationale=None)  # type: ignore[arg-type]


class TestAuditT1EdgeFixes:
    def test_nan_floor_blocked(self, tmp_path):
        _real_config(tmp_path)
        with pytest.raises(ConfigError):
            update_genre_config(tmp_path, {"resonance_global_floor": float("nan")}, rationale=_LONG)

    def test_inf_floor_blocked(self, tmp_path):
        _real_config(tmp_path)
        with pytest.raises(ConfigError):
            update_genre_config(tmp_path, {"resonance_global_floor": float("inf")}, rationale=_LONG)

    def test_scalar_intermediate_dotted_write_is_configerror(self, tmp_path):
        _real_config(tmp_path)
        (tmp_path / "genre-config.json").write_text(
            json.dumps({"auditDimensions": False}), encoding="utf-8"
        )
        with pytest.raises(ConfigError):
            update_genre_config(tmp_path, {"auditDimensions.texture": True}, rationale="none")

    def test_whitespace_only_rationale_blocked(self, tmp_path):
        _real_config(tmp_path)
        with pytest.raises(ConfigError):
            update_genre_config(tmp_path, {"auditDimensions.antiAi": False}, rationale=" " * 60)


class TestGovernGenreConfigChange:
    def _pair(self, tmp_path):
        cfg = _real_config(tmp_path)
        # 真实 fixture 的 texture 本为 false；治理测试需要 enabled→disabled 方向
        cfg["auditDimensions"]["texture"] = True
        (tmp_path / "genre-config.json").write_text(json.dumps(cfg), encoding="utf-8")
        return cfg, copy.deepcopy(cfg)

    def test_disable_critical_without_rationale_rejected(self, tmp_path):
        old, new = self._pair(tmp_path)
        new["auditDimensions"]["texture"] = False
        with pytest.raises(ConfigError):
            govern_genre_config_change(tmp_path, old, new, rationale="short")

    def test_delete_critical_key_rejected(self, tmp_path):
        old, new = self._pair(tmp_path)
        del new["auditDimensions"]["texture"]
        with pytest.raises(ConfigError):
            govern_genre_config_change(tmp_path, old, new, rationale="short")

    def test_old_missing_new_false_rejected(self, tmp_path):
        old, new = self._pair(tmp_path)
        del old["auditDimensions"]["antiAi"]
        new["auditDimensions"]["antiAi"] = False
        with pytest.raises(ConfigError):
            govern_genre_config_change(tmp_path, old, new, rationale="short")

    def test_rationale_over_500_rejected(self, tmp_path):
        old, new = self._pair(tmp_path)
        new["auditDimensions"]["texture"] = False
        with pytest.raises(ConfigError):
            govern_genre_config_change(tmp_path, old, new, rationale="y" * 501)

    def test_valid_change_appends_trail(self, tmp_path):
        old, new = self._pair(tmp_path)
        new["auditDimensions"]["texture"] = False
        govern_genre_config_change(tmp_path, old, new, rationale=_LONG)
        trail = (tmp_path / AUDIT_TRAIL_NAME).read_text(encoding="utf-8")
        assert '"key": "auditDimensions.texture"' in trail

    def test_no_dim_change_no_trail(self, tmp_path):
        old, new = self._pair(tmp_path)
        new["updated"] = "2026-08-30"
        govern_genre_config_change(tmp_path, old, new, rationale="routine date bump")
        assert not (tmp_path / AUDIT_TRAIL_NAME).exists()
