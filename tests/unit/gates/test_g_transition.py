"""Unit tests for G_TRANSITION: phase transition gate.

G_TRANSITION signature: gate_G_TRANSITION(from_phase, to_phase, round_dir).
Gate reads `progress.get(f"remaining_{from_phase}", [])` from progress.json
in round_dir. PASS when that list is empty.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from shenbi.gates.g_transition import gate_G_TRANSITION


def _result_dict(result_str: str) -> dict[str, Any]:
    return json.loads(result_str)


@pytest.mark.unit
def test_g_transition_passes_when_remaining_queue_empty(make_project) -> None:
    """remaining_drafting = [] -> PASS transition drafting -> review."""
    _, round_dir = make_project(progress={"remaining_drafting": []})
    result = _result_dict(gate_G_TRANSITION("drafting", "review", str(round_dir)))
    assert result["status"] == "PASS"


@pytest.mark.unit
def test_g_transition_fails_when_remaining_queue_not_empty(make_project) -> None:
    """remaining_drafting non-empty -> FAIL with GT.1 reason."""
    _, round_dir = make_project(progress={"remaining_drafting": ["shenbi-chapter-drafting"]})
    result = _result_dict(gate_G_TRANSITION("drafting", "review", str(round_dir)))
    assert result["status"] == "FAIL"
    assert any("GT.1" in mf for mf in result.get("must_fix", []))


@pytest.mark.unit
def test_g_transition_fails_when_progress_missing(tmp_path: Path) -> None:
    """Missing progress.json -> FAIL with GT.0:no_progress_file."""
    result = _result_dict(gate_G_TRANSITION("drafting", "review", str(tmp_path / "empty")))
    assert result["status"] == "FAIL"
    assert any("GT.0" in mf for mf in result["must_fix"])


@pytest.mark.unit
def test_g_transition_returns_gate_field(make_project) -> None:
    """Every response (PASS or FAIL) includes gate == 'G_TRANSITION'."""
    _, round_dir = make_project(progress={"remaining_drafting": []})
    result = _result_dict(gate_G_TRANSITION("drafting", "review", str(round_dir)))
    assert result["gate"] == "G_TRANSITION"
