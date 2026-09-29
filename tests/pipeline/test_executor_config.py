"""Tests for executor_config.toml overrides (spec §2.1, §2.2)."""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

_PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _load_config() -> dict[str, Any]:
    config_path = _PROJECT_ROOT / "executor_config.toml"
    with open(config_path, "rb") as f:
        return tomllib.load(f)


def test_drafting_max_tokens_raised():
    """Drafting max_tokens must be >16384 (was 16384 = no-op override, spec §2.2)."""
    config = _load_config()
    drafting = config["overrides"]["shenbi-chapter-drafting"]
    assert drafting["max_tokens"] > 16384, (
        f"drafting max_tokens={drafting['max_tokens']} should be raised "
        f"above default 16384 to prevent truncation (spec §2.2: AVG output 96% of cap)"
    )


def test_faction_builder_has_headroom():
    """Faction-builder's single create_or_overwrite file rides the output cap
    (fixcheck 2026-09-29 escalation #2: 3 cycles pinned at 32766-32767; probe
    2026-09-28 squeaked through at 30516). Override must clear the raised cap.
    """
    config = _load_config()
    faction = config["overrides"].get("shenbi-faction-builder", {})
    assert faction.get("max_tokens", 0) > 32768, (
        "shenbi-faction-builder needs max_tokens headroom above the 32768 "
        "runtime raise (persistent length truncation, 3 dispatch failures)"
    )


def test_score_skills_have_low_temperature():
    """All 3 score-* skills must have temperature ≤0.2 (spec §2.1 P0)."""
    config = _load_config()
    overrides = config.get("overrides", {})
    for skill in ("shenbi-score-arc", "shenbi-score-stratum", "shenbi-score-volume"):
        assert skill in overrides, f"{skill} missing temperature override"
        temp = overrides[skill]["temperature"]
        assert temp <= 0.2, f"{skill} temperature={temp} should be ≤0.2"


def test_discriminative_review_queue_has_low_temperature():
    """9 discriminative review skills must have temperature ≤0.2 (spec §2.1 P0)."""
    config = _load_config()
    overrides = config.get("overrides", {})
    discriminative = [
        "shenbi-review-memo-compliance",
        "shenbi-review-world-rules",
        "shenbi-review-arc-payoff",
        "shenbi-review-pov",
        "shenbi-review-era",
        "shenbi-review-fanfic",
        "shenbi-review-sensitivity",
        "shenbi-review-spinoff",
        "shenbi-review-dialogue",
    ]
    for skill in discriminative:
        assert skill in overrides, f"{skill} missing temperature override"
        temp = overrides[skill]["temperature"]
        assert temp <= 0.2, f"{skill} temperature={temp} should be ≤0.2"


def test_state_settling_has_headroom():
    """Fixcheck ch1 (2026-09-29): the full six-file staging write set with a
    live-base character_matrix rebuild pins the 32768 raise (completion 32771)
    — the settle redo needs the same headroom tier as lifecycle.
    """
    config = _load_config()
    settle = config["overrides"].get("shenbi-state-settling", {})
    assert settle.get("max_tokens", 0) > 32768, (
        "shenbi-state-settling needs max_tokens headroom above the 32768 "
        "runtime raise (persistent length truncation on full rebuild)"
    )
