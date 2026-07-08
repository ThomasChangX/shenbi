"""Unit tests for G1 field-existence soft check (B.4)."""

from __future__ import annotations

from pathlib import Path

import pytest

from shenbi.gates.g1 import check_fields_exist


@pytest.mark.unit
class TestCheckFieldsExist:
    def test_warns_when_declared_field_missing_from_markdown(self, tmp_path: Path) -> None:
        fp = tmp_path / "plan.md"
        fp.write_text("## chapter_goal\ndo the thing\n", encoding="utf-8")
        warnings = check_fields_exist(
            "shenbi-chapter-drafting",
            [str(fp)],
            {str(fp): ["chapter_goal", "nonexistent_field"]},
        )
        assert len(warnings) == 1
        assert "nonexistent_field" in warnings[0]

    def test_no_warning_when_all_fields_present(self, tmp_path: Path) -> None:
        fp = tmp_path / "plan.md"
        fp.write_text("## chapter_goal\ndo the thing\n## beats\nbeat1\n", encoding="utf-8")
        warnings = check_fields_exist(
            "shenbi-chapter-drafting",
            [str(fp)],
            {str(fp): ["chapter_goal", "beats"]},
        )
        assert warnings == []

    def test_no_warning_when_no_fields_declared(self, tmp_path: Path) -> None:
        fp = tmp_path / "plan.md"
        fp.write_text("content", encoding="utf-8")
        warnings = check_fields_exist("shenbi-skill", [str(fp)], {})
        assert warnings == []

    def test_warns_when_json_key_missing(self, tmp_path: Path) -> None:
        import json

        fp = tmp_path / "config.json"
        fp.write_text(json.dumps({"a": 1}), encoding="utf-8")
        warnings = check_fields_exist("shenbi-skill", [str(fp)], {str(fp): ["a", "missing_key"]})
        assert len(warnings) == 1
        assert "missing_key" in warnings[0]
