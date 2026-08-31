from __future__ import annotations

from shenbi.gates.shared import PROJECT
from shenbi.records.drift import detect_cross_section_drift, parse_markdown_table
from shenbi.records.parser import parse_records

FIXTURE = PROJECT / "tests" / "fixtures" / "truth-pending_hooks.md"


def test_parse_markdown_table_three_rows() -> None:
    rows = parse_markdown_table(FIXTURE.read_text(encoding="utf-8"))
    assert set(rows) == {"hook-ch1-001", "hook-ch1-002", "hook-ch1-003"}
    assert rows["hook-ch1-001"]["state"] == "PLANTED"
    assert rows["hook-ch1-001"]["type"] == "GENUINE"


def test_no_drift_on_consistent_fixture() -> None:
    text = FIXTURE.read_text(encoding="utf-8")
    recs = parse_records(text)
    md = parse_markdown_table(text)
    assert detect_cross_section_drift(recs, md) == []


def test_drift_detected_when_table_value_mismatches_yaml() -> None:
    text = FIXTURE.read_text(encoding="utf-8")
    recs = parse_records(text)
    md = parse_markdown_table(text)
    md["hook-ch1-001"]["state"] = "RESOLVED"  # YAML 仍是 PLANTED
    issues = detect_cross_section_drift(recs, md)
    assert any("hook-ch1-001" in i and "state" in i for i in issues)


def test_drift_detected_when_table_id_missing_in_yaml() -> None:
    text = FIXTURE.read_text(encoding="utf-8")
    recs = parse_records(text)
    md = parse_markdown_table(text)
    md["hook-ghost"] = {"id": "hook-ghost", "state": "PLANTED"}
    issues = detect_cross_section_drift(recs, md)
    assert any("hook-ghost" in i for i in issues)


def test_no_drift_when_no_active_table() -> None:
    """Init fixture 无活跃表 → drift=[]（md_rows={}）。"""
    init = (PROJECT / "tests" / "fixtures" / "pending-hooks-init.md").read_text(encoding="utf-8")
    assert detect_cross_section_drift(parse_records(init), parse_markdown_table(init)) == []


def test_no_false_drift_on_float_formatting() -> None:
    """Pin the float-format case: YAML 0.8 vs markdown '0.80' must NOT drift."""
    recs = [{"id": "h", "subtlety": 0.8}]  # YAML parses to float 0.8
    md = {"h": {"id": "h", "subtlety": "0.80"}}  # markdown table text "0.80"
    assert detect_cross_section_drift(recs, md) == []


class TestSpec16:
    def test_duplicate_id_first_wins(self):
        """F658: a repeated table id keeps the FIRST row, not a silent overwrite."""
        from shenbi.records.drift import parse_markdown_table

        md = "## 活跃伏笔\n\n| id | title |\n|---|---|\n| F1 | first |\n| F1 | second |\n"
        table = parse_markdown_table(md)
        assert table["F1"]["title"] == "first"


class TestSpec32F649:
    """Short/overflow rows in parse_markdown_table must be handled and disclosed.

    Old behavior: a row with fewer cells than the header kept a *partial* row
    (missing keys silently absent), and overflow cells were silently dropped —
    neither was disclosed. F649: short rows are padded with empty cells (so
    downstream ``_values_equal`` sees an explicit "" and reports real drift),
    and overflow cells are dropped but counted in ``stats["discarded_cells"]``.
    """

    def test_short_row_padded_with_empty_cells(self):
        from shenbi.records.drift import parse_markdown_table

        md = (
            "## 活跃伏笔\n\n"
            "| Hook ID | 类型 | 状态 |\n"
            "|---|---|---|\n"
            "| h1 | GENUINE |\n"  # 状态 cell missing
        )
        table = parse_markdown_table(md)
        assert table["h1"] == {"id": "h1", "type": "GENUINE", "state": ""}

    def test_short_row_empty_cell_surfaces_as_drift(self):
        """The padded "" must not silently equal a real YAML value."""
        from shenbi.records.drift import detect_cross_section_drift, parse_markdown_table

        md = "## 活跃伏笔\n\n| Hook ID | 类型 | 状态 |\n|---|---|---|\n| h1 | GENUINE |\n"
        rows = parse_markdown_table(md)
        recs = [{"id": "h1", "type": "GENUINE", "state": "PLANTED"}]
        issues = detect_cross_section_drift(recs, rows)
        assert any("state" in i for i in issues)

    def test_overflow_cells_dropped_and_counted(self):
        from shenbi.records.drift import parse_markdown_table

        md = (
            "## 活跃伏笔\n\n"
            "| Hook ID | 类型 | 状态 |\n"
            "|---|---|---|\n"
            "| h1 | GENUINE | PLANTED | EXTRA1 | EXTRA2 |\n"
        )
        stats: dict[str, int] = {}
        table = parse_markdown_table(md, stats=stats)
        assert table["h1"] == {"id": "h1", "type": "GENUINE", "state": "PLANTED"}
        assert stats["discarded_cells"] == 2

    def test_well_formed_row_no_discards(self):
        from shenbi.records.drift import parse_markdown_table

        text = FIXTURE.read_text(encoding="utf-8")
        stats: dict[str, int] = {}
        parse_markdown_table(text, stats=stats)
        assert stats["discarded_cells"] == 0
