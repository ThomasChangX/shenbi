"""Unit tests for G3: pre-scoring dependency check."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

from shenbi.gates.g3 import gate_G3


def _result_dict(result: str) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(result))


class TestG3DependencyCheck:
    def test_emits_valid_json_for_valid_args(self, tmp_path: Path) -> None:
        round_dir = tmp_path / "round"
        round_dir.mkdir()
        result_str = gate_G3("shenbi-worldbuilding", "generative", str(round_dir))
        parsed = json.loads(result_str)
        assert "status" in parsed

    def test_handles_none_arguments(self) -> None:
        """All-None args should not crash — gate reports cleanly."""
        result_str = gate_G3(None, None, None)
        parsed = json.loads(result_str)
        assert "status" in parsed

    def test_handles_missing_round_dir(self, tmp_path: Path) -> None:
        """A round_dir that doesn't exist should not crash G3."""
        result_str = gate_G3(
            "shenbi-x", "generative", str(tmp_path / "nonexistent-round")
        )
        parsed = json.loads(result_str)
        assert "status" in parsed

    def test_emits_valid_json_for_bug_hunt(self, tmp_path: Path) -> None:
        round_dir = tmp_path / "round"
        round_dir.mkdir()
        result_str = gate_G3("shenbi-worldbuilding", "bug-hunt", str(round_dir))
        parsed = json.loads(result_str)
        assert "status" in parsed
