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

    # --- New edge case tests ---

    def test_multiple_critical_dimensions_disabled(self, tmp_path):
        """Disabling multiple critical dimensions flags all of them."""
        _write_genre_config(
            tmp_path,
            {"texture": False, "antiAi": False, "continuity": True},
        )
        issues = check_config_coherence(tmp_path, resonance_global_floor=65)
        assert len(issues) == 2
        assert any("texture" in i for i in issues)
        assert any("antiAi" in i for i in issues)

    def test_non_critical_dimension_disabled_silent(self, tmp_path):
        """Disabling a non-critical dimension (dialogue) does not flag."""
        _write_genre_config(
            tmp_path,
            {"texture": True, "antiAi": True, "continuity": True, "dialogue": False},
        )
        issues = check_config_coherence(tmp_path, resonance_global_floor=65)
        # dialogue is not critical — no issue
        assert not any("dialogue" in i for i in issues)

    def test_floor_none_skips_floor_checks(self, tmp_path):
        """When resonance_global_floor is None, floor checks are skipped entirely."""
        _write_genre_config(
            tmp_path,
            {"texture": True, "antiAi": True, "continuity": True},
        )
        # floor=None means no mismatch check, no too-low check
        issues = check_config_coherence(tmp_path, resonance_global_floor=None)
        assert not any("threshold_mismatch" in i for i in issues)
        assert not any("floor_too_low" in i for i in issues)

    def test_floor_at_exact_revision_trigger_not_too_low(self, tmp_path):
        """Floor at exactly 60 (the revision trigger) is NOT too low."""
        _write_genre_config(
            tmp_path,
            {"texture": True, "antiAi": True, "continuity": True},
        )
        issues = check_config_coherence(tmp_path, resonance_global_floor=60)
        # 60 is not below 60, so floor_too_low should NOT fire
        assert not any("floor_too_low" in i for i in issues)

    def test_floor_just_below_revision_trigger_flags(self, tmp_path):
        """Floor at 59 (below 60 revision trigger) flags floor_too_low."""
        _write_genre_config(
            tmp_path,
            {"texture": True, "antiAi": True, "continuity": True},
        )
        issues = check_config_coherence(tmp_path, resonance_global_floor=59)
        assert any("G0.cc.floor_too_low" in i for i in issues)

    def test_floor_above_default_flags_mismatch(self, tmp_path):
        """Floor above the default (e.g. 70 vs 65) also flags mismatch."""
        _write_genre_config(
            tmp_path,
            {"texture": True, "antiAi": True, "continuity": True},
        )
        issues = check_config_coherence(tmp_path, resonance_global_floor=70)
        assert any("G0.cc.threshold_mismatch" in i for i in issues)

    def test_all_three_issue_types_simultaneously(self, tmp_path):
        """Floor mismatch, too-low, and critical disabled can all fire at once."""
        _write_genre_config(
            tmp_path,
            {"texture": False, "antiAi": True, "continuity": True},
        )
        issues = check_config_coherence(tmp_path, resonance_global_floor=50)
        # Should have: threshold_mismatch, floor_too_low, critical_audit_disabled
        assert len(issues) == 3
        assert any("threshold_mismatch" in i for i in issues)
        assert any("floor_too_low" in i for i in issues)
        assert any("critical_audit_disabled" in i for i in issues)

    def test_corrupt_json_config_treated_as_empty(self, tmp_path):
        """A corrupt genre-config.json is treated as empty (no crash, no audit issues)."""
        (tmp_path / "genre-config.json").write_text("{not valid json!!!}", encoding="utf-8")
        issues = check_config_coherence(tmp_path, resonance_global_floor=65)
        # No audit-dim issues (treated as {}), no floor issues (floor matches default)
        assert issues == []

    def test_config_without_audit_dimensions_key(self, tmp_path):
        """genre-config.json without auditDimensions key is treated as all-enabled."""
        (tmp_path / "genre-config.json").write_text(
            json.dumps({"otherKey": "value"}), encoding="utf-8"
        )
        issues = check_config_coherence(tmp_path, resonance_global_floor=65)
        # No critical dims disabled (default True for absent keys)
        assert not any("critical_audit_disabled" in i for i in issues)


class TestG0Integration:
    def test_gate_g0_surfaces_disabled_texture(self, tmp_path, monkeypatch):
        """End-to-end: gate_G0 scans PROJECT / "novel-output" / "*" for
        genre-config.json and surfaces a G0.cc.critical_audit_disabled check
        when a production project has texture disabled.
        """
        # Production layout: genre-config.json lives under
        # novel-output/<project>/, NOT at the repo root. Mirror that here.
        project_dir = tmp_path / "novel-output" / "xinghuo-ranqiong"
        project_dir.mkdir(parents=True)
        _write_genre_config(
            project_dir,
            {"texture": False, "antiAi": True, "continuity": True},
        )

        # --- Build a minimal project skeleton inside tmp_path so every G0
        # sub-check passes (or skips cleanly) and we reach the G0.cc block. ---
        import hashlib

        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        fixtures_dir = tests_dir / "fixtures"
        fixtures_dir.mkdir()
        (tests_dir / "tiers").mkdir()
        deps = {"_calibration_hashes": {"combined": hashlib.sha256(b"").hexdigest()}}
        (tests_dir / "tiers" / "deps.json").write_text(json.dumps(deps), encoding="utf-8")

        from shenbi.gates import g0 as g0mod

        monkeypatch.setattr(g0mod, "PROJECT", tmp_path)
        monkeypatch.setattr(g0mod, "SKILLS", skills_dir)
        monkeypatch.setattr(g0mod, "TESTS", tests_dir)
        monkeypatch.setattr(g0mod, "FIXTURES", fixtures_dir)
        monkeypatch.setattr(g0mod, "ALL_SKILLS", [])
        monkeypatch.setattr(g0mod, "G4_CHECKER_SKILLS", set())

        # Run with a seed file so gate_G0 does not short-circuit at G0.1.
        seed = tmp_path / "seed.md"
        seed.write_text("目标字数：300000\n", encoding="utf-8")
        result = g0mod.gate_G0(seed_file=str(seed))
        assert "G0.cc.critical_audit_disabled:texture" in result
