"""Unit tests for G6: T3 pipeline check."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

from shenbi.gates.g6 import gate_G6


def _result_dict(result: str) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(result))


class TestG6PipelineCheck:
    def test_emits_valid_json_for_valid_args(self, tmp_path: Path) -> None:
        round_dir = tmp_path / "round"
        round_dir.mkdir()
        result_str = gate_G6("long-form", str(round_dir), str(tmp_path))
        parsed = json.loads(result_str)
        assert "status" in parsed

    def test_handles_none_arguments(self) -> None:
        result_str = gate_G6(None, None, None)
        parsed = json.loads(result_str)
        assert "status" in parsed

    def test_handles_unknown_pipeline(self, tmp_path: Path) -> None:
        round_dir = tmp_path / "round"
        round_dir.mkdir()
        result_str = gate_G6("nonexistent-pipeline", str(round_dir), None)
        parsed = json.loads(result_str)
        assert "status" in parsed

    def test_handles_missing_round_dir(self, tmp_path: Path) -> None:
        result_str = gate_G6("long-form", str(tmp_path / "nope"), None)
        parsed = json.loads(result_str)
        assert "status" in parsed
