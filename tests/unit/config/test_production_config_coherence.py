"""Guard the production novel-output config against coherence regressions."""

from __future__ import annotations

import json
from pathlib import Path

from shenbi.config.thresholds import DEFAULT_THRESHOLDS
from shenbi.gates.g0_config_coherence import check_config_coherence

# 生产树 novel-output/xinghuo-ranqiong 已出库（spec #63 T1504）；此为出库前
# verbatim 副本（G0.9 真实产物，provenance：原产树 xinghuo-ranqiong，2026-09-13）。
PRODUCTION_DIR = Path(__file__).resolve().parents[3] / "tests/fixtures/production-config"


def test_production_texture_is_enabled():
    cfg = json.loads((PRODUCTION_DIR / "genre-config.json").read_text(encoding="utf-8"))
    assert cfg["auditDimensions"]["texture"] is True, (
        "production texture audit must stay enabled (E34 root cause)"
    )


def test_production_resonance_floor_matches_default():
    state = json.loads((PRODUCTION_DIR / "pipeline-state.json").read_text(encoding="utf-8"))
    # The floor is serialized at top-level of the config sub-object.
    config = state.get("config", state)
    assert config["resonance_global_floor"] == DEFAULT_THRESHOLDS.resonance_global_floor


def test_production_passes_coherence_check():
    state = json.loads((PRODUCTION_DIR / "pipeline-state.json").read_text(encoding="utf-8"))
    config = state.get("config", state)
    issues = check_config_coherence(
        PRODUCTION_DIR, resonance_global_floor=config["resonance_global_floor"]
    )
    assert issues == [], "production config has coherence issues: " + "; ".join(issues)
