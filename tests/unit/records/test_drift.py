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
