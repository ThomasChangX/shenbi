"""Unit tests for G7: round close validation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

from shenbi.gates.g7 import gate_G7


def _result_dict(result: str) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(result))


class TestG7RoundClose:
    def test_emits_valid_json_for_empty_round(self, tmp_path: Path) -> None:
        """G7 must return a parseable result for any round_dir, even empty."""
        round_dir = tmp_path / "round"
        round_dir.mkdir()
        result_str = gate_G7(str(round_dir))
        parsed = json.loads(result_str)
        assert "status" in parsed

    def test_returns_str_result(self, tmp_path: Path) -> None:
        round_dir = tmp_path / "round"
        round_dir.mkdir()
        result_str = gate_G7(str(round_dir))
        assert isinstance(result_str, str)
        assert json.loads(result_str)

    def test_handles_round_dir_with_partial_state(self, tmp_path: Path) -> None:
        """A round in progress (markers, partial summaries) should not crash."""
        round_dir = tmp_path / "round"
        (round_dir / "gate-markers").mkdir(parents=True)
        (round_dir / "gate-markers" / "G0-seed-generative.json").write_text(
            json.dumps({"status": "PASS"}), encoding="utf-8"
        )
        result_str = gate_G7(str(round_dir))
        parsed = json.loads(result_str)
        assert "status" in parsed
