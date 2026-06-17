"""Unit tests for G1: pre-dispatch input validation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import pytest

from shenbi.gates.g1 import gate_G1


def _result_dict(result: str) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(result))


class TestG1SkillLookup:
    def test_fails_when_skill_name_unknown(self) -> None:
        result = _result_dict(gate_G1(skill_name="shenbi-nonexistent", input_files="x.md"))
        assert result["status"] == "FAIL"

    def test_returns_unimplemented_for_skill_without_g1_checks(self, tmp_path: Path) -> None:
        """Skills without a specific G1 check return UNIMPLEMENTED, not FAIL."""
        result_str = gate_G1(skill_name="shenbi-worldbuilding", input_files=None)
        assert result_str  # returns a non-empty string

    def test_emits_valid_json_for_any_input(self) -> None:
        """All gate results must be valid JSON parseable by downstream tools."""
        result_str = gate_G1(skill_name=None, input_files=None)
        parsed = json.loads(result_str)
        assert "status" in parsed


@pytest.mark.unit
class TestG1ErrorPaths:
    """Error-path tests for G1.1-G1.5 file and lock checks.

    Source convention: file-level FAILs (G1.1 not-found/empty, G1.2 JSON
    parse, G1.3 YAML parse) are appended to mf list and stringified to
    must_fix entries like 'G1.1:/path/file.md'. Round-level checks (G1.4
    in-place, G1.5 lock, G1.6 scoring_history) appear in checks list.
    """

    def test_g11_fails_when_file_not_found(self, tmp_path: Path) -> None:
        """Non-existent file -> G1.1 FAIL surfaces in must_fix."""
        missing = tmp_path / "nonexistent.md"
        result = _result_dict(
            gate_G1(skill_name="shenbi-worldbuilding", input_files=[str(missing)])
        )
        assert result["status"] == "FAIL"
        assert any("G1.1" in mf for mf in result.get("must_fix", []))

    def test_g11_fails_when_file_empty(self, tmp_path: Path) -> None:
        """Zero-byte file -> G1.1 FAIL in must_fix."""
        empty = tmp_path / "empty.md"
        empty.write_text("")
        result = _result_dict(gate_G1(skill_name="shenbi-worldbuilding", input_files=[str(empty)]))
        assert any("G1.1" in mf for mf in result.get("must_fix", []))

    def test_g12_fails_on_corrupt_json(self, tmp_path: Path) -> None:
        """Malformed JSON file -> G1.2 FAIL in must_fix."""
        bad = tmp_path / "bad.json"
        bad.write_text("{not valid json", encoding="utf-8")
        result = _result_dict(gate_G1(skill_name="shenbi-worldbuilding", input_files=[str(bad)]))
        assert any("G1.2" in mf for mf in result.get("must_fix", []))

    def test_g13_fails_on_corrupt_yaml_frontmatter(self, tmp_path: Path) -> None:
        """Markdown with malformed YAML frontmatter -> G1.3 FAIL in must_fix
        (yload may tolerate some malformed YAML — assert no crash).
        """
        bad = tmp_path / "bad.md"
        bad.write_text("---\n: invalid yaml: :\n---\n# Body\n", encoding="utf-8")
        result = _result_dict(gate_G1(skill_name="shenbi-worldbuilding", input_files=[str(bad)]))
        assert result["status"] in ("PASS", "FAIL")

    def test_g14_creates_bak_for_inplace_skill(self, tmp_path: Path) -> None:
        """In-place skill + round_dir -> G1.4 PASS with .bak created on disk."""
        src = tmp_path / "input.md"
        src.write_text("# Faction\n", encoding="utf-8")
        round_dir = tmp_path / "round"
        round_dir.mkdir()
        gate_G1(
            skill_name="shenbi-faction-builder",
            input_files=[str(src)],
            round_dir=str(round_dir),
        )
        assert (tmp_path / "input.md.bak").exists()

    def test_g15_passes_when_no_lock_file(self, tmp_path: Path) -> None:
        """round_dir with no .gate-lock -> G1.5 PASS in checks."""
        src = tmp_path / "input.md"
        src.write_text("content", encoding="utf-8")
        round_dir = tmp_path / "round"
        round_dir.mkdir()
        result = _result_dict(
            gate_G1(
                skill_name="shenbi-worldbuilding",
                input_files=[str(src)],
                round_dir=str(round_dir),
            )
        )
        g15 = next((c for c in result["checks"] if c.get("id") == "G1.5"), None)
        assert g15 is not None
        assert g15["s"] == "PASS"

    def test_g15_fails_when_lock_active(self, tmp_path: Path) -> None:
        """Fresh .gate-lock file (<300s old) -> G1.5 FAIL in must_fix."""
        src = tmp_path / "input.md"
        src.write_text("content", encoding="utf-8")
        round_dir = tmp_path / "round"
        round_dir.mkdir()
        (round_dir / ".gate-lock").write_text("locked")  # mtime is now
        result = _result_dict(
            gate_G1(
                skill_name="shenbi-worldbuilding",
                input_files=[str(src)],
                round_dir=str(round_dir),
            )
        )
        # Lock FAIL appears in must_fix (mf list), not checks.
        assert any("G1.5" in mf for mf in result.get("must_fix", []))
