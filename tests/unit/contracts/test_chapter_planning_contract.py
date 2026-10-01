"""chapter-planning contract reads (probe4 finding: P0/B-line per-chapter
progression constraints could not reach the memo because the contract never
declared ``outline/thread_map.md``).

The memo model only sees files the contract declares (Layer B field-level
filtering), so a missing read is a structural blind spot, not a prompt
quality issue (adjudication probe4-003 §九.3).
"""

from __future__ import annotations

from shenbi.contracts.fields import filter_to_fields
from shenbi.contracts.loader import load_contract

THREAD_MAP_FIELDS = ["章节线索推进表", "线索详情"]


def test_chapter_planning_reads_thread_map_field_level() -> None:
    contract = load_contract("shenbi-chapter-planning")
    assert "outline/thread_map.md" in contract["reads"]
    assert contract["read_fields"]["outline/thread_map.md"] == THREAD_MAP_FIELDS


def test_thread_map_fields_match_producer_skeleton() -> None:
    """The declared field names must match the H2 sections the producer
    (shenbi-plot-thread-weaver) pins in its output skeleton — a mismatch
    would fire the any-missing escape hatch and silently widen the read
    back to the full file.
    """
    skeleton = (
        "# 线索地图\n\n"
        "## 线索总览表\n\n总览内容\n\n"
        "## 线索详情\n\n### A1: 示例线索\n- **推进点**: 第1章首次露面\n\n"
        "## 章节线索推进表\n\n| 章节 | 主推 | 副推 |\n\n"
        "## 约束检查表\n\n检查内容\n"
    )
    result, matched = filter_to_fields(skeleton, THREAD_MAP_FIELDS, "outline/thread_map.md")
    assert matched is True
    assert "推进点" in result
    assert "总览内容" not in result
    assert "检查内容" not in result
