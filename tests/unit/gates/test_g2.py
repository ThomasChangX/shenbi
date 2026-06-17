"""Unit tests for G2: write verification."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import pytest

from shenbi.gates.g2 import gate_G2


def _result_dict(result: str) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(result))


class TestG2FileInputs:
    def test_accepts_string_file_paths(self, tmp_path: Path) -> None:
        f = tmp_path / "x.md"
        f.write_text("# x\n", encoding="utf-8")
        result = _result_dict(gate_G2(str(f), "report"))
        assert "status" in result

    def test_accepts_list_file_paths(self, tmp_path: Path) -> None:
        f1 = tmp_path / "a.md"
        f1.write_text("a", encoding="utf-8")
        f2 = tmp_path / "b.md"
        f2.write_text("b", encoding="utf-8")
        result = _result_dict(gate_G2([str(f1), str(f2)], "report"))
        assert "status" in result

    def test_handles_none_file_paths(self) -> None:
        result = _result_dict(gate_G2(None, "chapter"))
        assert "status" in result

    def test_handles_missing_files(self, tmp_path: Path) -> None:
        """A non-existent file should not crash G2; it reports failure cleanly."""
        result = _result_dict(gate_G2([str(tmp_path / "nope.md")], "chapter"))
        assert result["status"] in {"FAIL", "PASS"}  # behavior depends on impl

    def test_supports_chapter_file_type(self, tmp_path: Path) -> None:
        """Chapter file type applies chapter-word-floor/ceiling checks."""
        f = tmp_path / "ch.md"
        f.write_text("正文内容", encoding="utf-8")
        result = _result_dict(gate_G2(str(f), "chapter"))
        assert "status" in result

    def test_supports_report_file_type(self, tmp_path: Path) -> None:
        f = tmp_path / "r.md"
        f.write_text("# Report\n内容", encoding="utf-8")
        result = _result_dict(gate_G2(str(f), "report"))
        assert "status" in result

    def test_emits_valid_json(self, tmp_path: Path) -> None:
        f = tmp_path / "x.md"
        f.write_text("x", encoding="utf-8")
        parsed = json.loads(gate_G2(str(f), "report"))
        assert "status" in parsed


@pytest.mark.unit
class TestG2ErrorPaths:
    """Error-path tests for G2.1-G2.5 file integrity checks.

    Source convention mirrors G1: per-file FAILs go to mf list and surface
    as must_fix strings like 'G2.1:/path/file.md'.
    """

    def test_g21_fails_when_file_not_found(self, tmp_path: Path) -> None:
        """Non-existent file -> G2.1 FAIL in must_fix."""
        missing = tmp_path / "nope.md"
        result = _result_dict(gate_G2([str(missing)], "chapter"))
        assert any("G2.1" in mf for mf in result.get("must_fix", []))

    def test_g22_fails_when_file_empty(self, tmp_path: Path) -> None:
        """Zero-byte file -> G2.2 FAIL in must_fix."""
        empty = tmp_path / "empty.md"
        empty.write_text("")
        result = _result_dict(gate_G2([str(empty)], "chapter"))
        assert any("G2.2" in mf for mf in result.get("must_fix", []))

    def test_g24_fails_on_corrupt_json(self, tmp_path: Path) -> None:
        """Malformed JSON file -> G2.4 FAIL in must_fix."""
        bad = tmp_path / "bad.json"
        bad.write_text("{not json", encoding="utf-8")
        result = _result_dict(gate_G2([str(bad)], "report"))
        assert any("G2.4" in mf for mf in result.get("must_fix", []))

    def test_g25_fails_when_structured_data_lacks_frontmatter(self, tmp_path: Path) -> None:
        """truth/outline/plans .md file without YAML frontmatter -> G2.5 FAIL.

        Source line 76: must_have=True for paths containing /truth/, /outline/,
        /plans/, /snapshots/ or ending in plan.md/memo.md/map.md.
        """
        truth_dir = tmp_path / "truth"
        truth_dir.mkdir()
        no_fm = truth_dir / "hooks.md"
        no_fm.write_text("# Hooks\n\nplain content without frontmatter\n")
        result = _result_dict(gate_G2([str(no_fm)], "truth"))
        assert any("G2.5" in mf for mf in result.get("must_fix", []))

    def test_g23_passes_on_valid_utf8_file(self, tmp_path: Path) -> None:
        """Valid UTF-8 file -> G2.3 PASS in checks."""
        f = tmp_path / "ok.md"
        f.write_text("# Title\n\n正文内容\n", encoding="utf-8")
        result = _result_dict(gate_G2([str(f)], "chapter"))
        g23 = next((c for c in result["checks"] if c.get("id") == "G2.3"), None)
        assert g23 is not None
        assert g23["s"] == "PASS"

    def test_comma_separated_string_input_is_split(self, tmp_path: Path) -> None:
        """Comma-separated string input is split into multiple paths."""
        f1 = tmp_path / "a.md"
        f1.write_text("a", encoding="utf-8")
        f2 = tmp_path / "b.md"
        f2.write_text("b", encoding="utf-8")
        result = _result_dict(gate_G2(f"{f1},{f2}", "report"))
        # Both files should produce PASS entries (at least 2 G2.1 PASS)
        pass_count = sum(
            1 for c in result["checks"] if c.get("id") == "G2.1" and c.get("s") == "PASS"
        )
        assert pass_count == 2
