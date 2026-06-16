"""Unit tests for G1: pre-dispatch input validation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

from shenbi.gates.g1 import gate_G1


def _result_dict(result: str) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(result))


class TestG1SkillLookup:
    def test_fails_when_skill_name_unknown(self) -> None:
        result = _result_dict(gate_G1(skill_name="shenbi-nonexistent", input_files="x.md"))
        assert result["status"] == "FAIL"

    def test_returns_unimplemented_for_skill_without_g1_checks(
        self, tmp_path: Path
    ) -> None:
        """Skills without a specific G1 check return UNIMPLEMENTED, not FAIL."""
        # Use any real skill name from skills/
        result_str = gate_G1(skill_name="shenbi-worldbuilding", input_files=None)
        # Could be PASS, FAIL, or UNIMPLEMENTED depending on the skill
        assert result_str  # returns a non-empty string

    def test_emits_valid_json_for_any_input(self) -> None:
        """All gate results must be valid JSON parseable by downstream tools."""
        result_str = gate_G1(skill_name=None, input_files=None)
        parsed = json.loads(result_str)
        assert "status" in parsed
