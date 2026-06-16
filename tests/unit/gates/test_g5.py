"""Unit tests for G5: T2 phase check."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

from shenbi.gates.g5 import gate_G5


def _result_dict(result: str) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(result))


class TestG5PhaseCheck:
    def test_emits_valid_json_for_valid_args(self, tmp_path: Path) -> None:
        round_dir = tmp_path / "round"
        round_dir.mkdir()
        result_str = gate_G5("design", str(round_dir), str(tmp_path))
        parsed = json.loads(result_str)
        assert "status" in parsed

    def test_handles_none_arguments(self) -> None:
        result_str = gate_G5(None, None, None)
        parsed = json.loads(result_str)
        assert "status" in parsed

    def test_handles_missing_round_dir(self, tmp_path: Path) -> None:
        result_str = gate_G5("design", str(tmp_path / "nope"), None)
        parsed = json.loads(result_str)
        assert "status" in parsed

    def test_returns_str_for_any_phase_name(self, tmp_path: Path) -> None:
        """Even unknown phases return a parseable result."""
        round_dir = tmp_path / "round"
        round_dir.mkdir()
        result_str = gate_G5("nonexistent-phase", str(round_dir), None)
        assert isinstance(result_str, str)
        assert json.loads(result_str)
