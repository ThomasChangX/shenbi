"""Unit tests for G_DISPATCH, G_RECONCILE, G_TRANSITION gates."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import pytest

from shenbi.gates.g_dispatch import gate_G_DISPATCH
from shenbi.gates.g_reconcile import gate_G_RECONCILE
from shenbi.gates.g_transition import gate_G_TRANSITION


def _result_dict(result: str) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(result))


class TestGDispatch:
    def test_emits_valid_json_for_valid_args(self, tmp_path: Path) -> None:
        round_dir = tmp_path / "round"
        round_dir.mkdir()
        result_str = gate_G_DISPATCH("design", str(round_dir))
        parsed = json.loads(result_str)
        assert "status" in parsed

    def test_handles_empty_round_dir(self, tmp_path: Path) -> None:
        round_dir = tmp_path / "round"
        round_dir.mkdir()
        result_str = gate_G_DISPATCH("design", str(round_dir))
        assert isinstance(result_str, str)


class TestGReconcile:
    def test_emits_valid_json_with_no_args(self) -> None:
        result_str = gate_G_RECONCILE(round_dir=None)
        parsed = json.loads(result_str)
        assert "status" in parsed

    def test_emits_valid_json_with_round_dir(self, tmp_path: Path) -> None:
        round_dir = tmp_path / "round"
        round_dir.mkdir()
        result_str = gate_G_RECONCILE(str(round_dir))
        parsed = json.loads(result_str)
        assert "status" in parsed


class TestGTransition:
    def test_emits_valid_json_for_valid_args(self, tmp_path: Path) -> None:
        round_dir = tmp_path / "round"
        round_dir.mkdir()
        result_str = gate_G_TRANSITION("design", "build", str(round_dir))
        parsed = json.loads(result_str)
        assert "status" in parsed

    def test_returns_str_result(self, tmp_path: Path) -> None:
        round_dir = tmp_path / "round"
        round_dir.mkdir()
        result_str = gate_G_TRANSITION("a", "b", str(round_dir))
        assert isinstance(result_str, str)
        assert json.loads(result_str)


@pytest.mark.unit
def test_g_dispatch_passes_when_all_skills_completed(make_project) -> None:
    """GD.1 PASS when completed_skill_names ⊇ ALL_SKILLS."""
    from shenbi.gates.shared import ALL_SKILLS

    _, round_dir = make_project(progress={"completed_skill_names": sorted(ALL_SKILLS)})
    result = _result_dict(gate_G_DISPATCH("drafting", str(round_dir)))
    assert result["status"] == "PASS"


@pytest.mark.unit
def test_g_dispatch_fails_when_progress_missing(tmp_path: Path) -> None:
    """Missing progress.json -> FAIL with GD.0:no_progress in must_fix."""
    result = _result_dict(gate_G_DISPATCH("drafting", str(tmp_path / "empty")))
    assert result["status"] == "FAIL"
    assert any("GD.0" in mf for mf in result.get("must_fix", []))


@pytest.mark.unit
def test_g_dispatch_fails_when_skills_incomplete(make_project) -> None:
    """completed_skill_names missing some -> FAIL with GD.1 listing missing."""
    _, round_dir = make_project(progress={"completed_skill_names": []})
    result = _result_dict(gate_G_DISPATCH("drafting", str(round_dir)))
    assert result["status"] == "FAIL"
    assert any("GD.1" in mf for mf in result.get("must_fix", []))
