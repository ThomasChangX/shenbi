from __future__ import annotations

from shenbi.gates.shared import PROJECT
from shenbi.records.parser import (
    extract_yaml_block,
    is_idempotent,
    parse_records,
    serialize_records,
)

FIXTURE = PROJECT / "tests" / "fixtures" / "truth-pending_hooks.md"
INIT_FIXTURE = PROJECT / "tests" / "fixtures" / "pending-hooks-init.md"


def test_extract_stops_before_next_header() -> None:
    """关键：只截 ## hooks 到下一个 ## 标题；含入后续 markdown 表会令 YAML 崩溃。"""
    body = extract_yaml_block(FIXTURE.read_text(encoding="utf-8"))
    assert "伏笔统计" not in body  # 未越界进入下一段
    assert body != ""


def test_parse_real_fixture_three_records() -> None:
    recs = parse_records(FIXTURE.read_text(encoding="utf-8"))
    assert len(recs) == 3
    assert [r["id"] for r in recs] == ["hook-ch1-001", "hook-ch1-002", "hook-ch1-003"]
    assert recs[0]["state"] == "PLANTED"  # 非 status


def test_parse_empty_init_fixture() -> None:
    assert parse_records(INIT_FIXTURE.read_text(encoding="utf-8")) == []


def test_union_record_keys_are_sixteen() -> None:
    """Fixture ## hooks 16 键（spec New-A/B；亲手核对）。"""
    recs = parse_records(FIXTURE.read_text(encoding="utf-8"))
    keys: set[str] = set()
    for r in recs:
        keys |= set(r.keys())
    assert keys == {
        "id",
        "state",
        "operation",
        "type",
        "dimension",
        "content",
        "subtlety",
        "plant_chapter",
        "cultivation_interval",
        "last_reinforced",
        "max_distance",
        "escalation_curve",
        "depends_on",
        "core_hook",
        "promoted",
        "notes",
    }


def test_semantic_round_trip_on_fixture() -> None:
    """判据 12：parse(serialize(parse(x))) == parse(x)。"""
    text = FIXTURE.read_text(encoding="utf-8")
    assert is_idempotent(text)
    once = parse_records(text)
    twice = parse_records("## hooks\n" + serialize_records(once))
    assert once == twice


def test_serialize_preserves_depends_on_list() -> None:
    recs = parse_records(FIXTURE.read_text(encoding="utf-8"))
    out = parse_records("## hooks\n" + serialize_records(recs))
    assert out[0]["depends_on"] == []  # list 不丢
