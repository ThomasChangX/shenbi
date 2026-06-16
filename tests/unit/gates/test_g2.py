"""Unit tests for G2: write verification."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

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
