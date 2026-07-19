"""Tests for the G0 configuration-coherence sub-check."""

from __future__ import annotations

import json
from pathlib import Path

from shenbi.gates.g0_config_coherence import check_config_coherence


def _write_genre_config(project_dir: Path, audit_dims: dict[str, bool]) -> None:
    cfg = {"auditDimensions": audit_dims}
    (project_dir / "genre-config.json").write_text(
        json.dumps(cfg, ensure_ascii=False), encoding="utf-8"
    )


class TestCheckConfigCoherence:
    def test_clean_config_returns_no_issues(self, tmp_path):
        _write_genre_config(
            tmp_path,
            {"texture": True, "antiAi": True, "continuity": True, "dialogue": True},
        )
        assert check_config_coherence(tmp_path, resonance_global_floor=65) == []

    def test_disabled_critical_dimension_flags_issue(self, tmp_path):
        _write_genre_config(
            tmp_path,
            {"texture": False, "antiAi": True, "continuity": True},
        )
        issues = check_config_coherence(tmp_path, resonance_global_floor=65)
        assert len(issues) == 1
        assert "G0.cc.critical_audit_disabled:texture" in issues[0]

    def test_threshold_mismatch_flags_issue(self, tmp_path):
        _write_genre_config(
            tmp_path,
            {"texture": True, "antiAi": True, "continuity": True},
        )
        # state floor 50 < default 65
        issues = check_config_coherence(tmp_path, resonance_global_floor=50)
        assert any("G0.cc.threshold_mismatch" in i for i in issues)

    def test_floor_too_low_flags_issue(self, tmp_path):
        _write_genre_config(
            tmp_path,
            {"texture": True, "antiAi": True, "continuity": True},
        )
        issues = check_config_coherence(tmp_path, resonance_global_floor=50)
        assert any("G0.cc.floor_too_low" in i for i in issues)

    def test_missing_genre_config_is_silent(self, tmp_path):
        # No genre-config.json — checker must not crash, returns [] for the
        # audit-dim check (the floor checks still run if a floor is passed).
        assert check_config_coherence(tmp_path, resonance_global_floor=65) == []

    def test_floor_at_default_no_mismatch(self, tmp_path):
        _write_genre_config(
            tmp_path,
            {"texture": True, "antiAi": True, "continuity": True},
        )
        issues = check_config_coherence(tmp_path, resonance_global_floor=65)
        assert not any("threshold_mismatch" in i for i in issues)
