"""Unit tests for G_DISPATCH, G_RECONCILE, G_TRANSITION gates."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

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
