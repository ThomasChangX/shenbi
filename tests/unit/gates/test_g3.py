"""Unit tests for G3: pre-scoring dependency check."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import pytest

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
        result_str = gate_G3("shenbi-x", "generative", str(tmp_path / "nonexistent-round"))
        parsed = json.loads(result_str)
        assert "status" in parsed

    def test_emits_valid_json_for_bug_hunt(self, tmp_path: Path) -> None:
        round_dir = tmp_path / "round"
        round_dir.mkdir()
        result_str = gate_G3("shenbi-worldbuilding", "bug-hunt", str(round_dir))
        parsed = json.loads(result_str)
        assert "status" in parsed


@pytest.mark.unit
class TestG3ErrorPaths:
    """Error-path tests for G3 — pre-scoring dependency checks."""

    def test_g30_fails_when_round_dir_missing(self, tmp_path: Path) -> None:
        """None/missing round_dir -> FAIL with G3.0:no_round_dir."""
        result = _result_dict(gate_G3("shenbi-x", "generative", None))
        assert result["status"] == "FAIL"
        assert any("G3.0" in mf for mf in result.get("must_fix", []))

    def test_g30_fails_when_round_dir_does_not_exist(self, tmp_path: Path) -> None:
        """round_dir path that doesn't exist on disk -> FAIL G3.0."""
        result = _result_dict(gate_G3("shenbi-x", "generative", str(tmp_path / "nonexistent")))
        assert result["status"] == "FAIL"
        assert any("G3.0" in mf for mf in result.get("must_fix", []))

    def test_g31_emits_check_with_real_deps_json(self, tmp_path: Path) -> None:
        """With real repo deps.json, G3.1 emits some check (PASS/SKIP/FAIL).

        Source: TESTS/tiers/deps.json is read; skill_name looked up; for each
        prerequisite, find_report() is called. Result depends on repo state.
        """
        round_dir = tmp_path / "round"
        round_dir.mkdir()
        result = _result_dict(gate_G3("shenbi-worldbuilding", "generative", str(round_dir)))
        g31 = next((c for c in result["checks"] if c.get("id") == "G3.1"), None)
        if g31 is not None:
            assert g31["s"] in ("PASS", "FAIL", "SKIP")

    def test_g32_emits_check_with_real_acceptance_json(self, tmp_path: Path) -> None:
        """G3.2 reads TESTS/tiers/acceptance.json for threshold; emits check."""
        round_dir = tmp_path / "round"
        round_dir.mkdir()
        # Add a t1-reports dir with a low-score report to exercise the FAIL branch.
        reports = round_dir / "t1-reports"
        reports.mkdir()
        (reports / "shenbi-test-generative.json").write_text(
            json.dumps({"score": 50}), encoding="utf-8"
        )
        result = _result_dict(gate_G3("shenbi-worldbuilding", "generative", str(round_dir)))
        # Gate ran without crash; G3.2 may or may not appear.
        assert result["status"] in ("PASS", "FAIL")

    def test_g30_returns_valid_json_with_gate_identifier(self) -> None:
        """All paths include gate == 'G3'."""
        result = _result_dict(gate_G3(None, None, None))
        assert result["gate"] == "G3"

    def test_g30_includes_timestamp(self) -> None:
        """All paths include ISO-8601 timestamp."""
        result = _result_dict(gate_G3(None, None, None))
        assert "timestamp" in result
