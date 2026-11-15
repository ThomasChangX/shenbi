"""Spec #105 T4b: aggregate parser dual-format tolerance (new item-level severity)."""

from __future__ import annotations

from tools.report_longitudinal import _parse_aggregate_sections

_NEW = """# Chapter 9 — Audit Aggregate

## MINOR Findings (2)

- **MINOR** · 措辞建议甲
  - 报告方: r1
- **MINOR** · 措辞建议乙
  - 报告方: r2

## BLOCKING Findings (1)

- **BLOCKING** · 结构缺陷丙
  - 报告方: r3

## Resonance 报告（逐字保留）

### chapter-9-resonance.md
- [WARNING] 伪条目（正文引用，不得成 unit）

## WARNING Findings (1)

- [WARNING] 终止后伪节也不得成 unit
"""

_OLD = """# Chapter 9 — Audit Aggregate

## BLOCKING Findings (1)

- 旧格式条目（无前缀）
  - 报告方: r1

## WARNING Findings (1)

- 旧格式告警
  - 报告方: r2
"""


def test_new_format_prefix_stripped() -> None:
    units = _parse_aggregate_sections(_NEW)
    triples = [(u.severity, u.text) for u in units]
    assert triples == [
        ("MINOR", "措辞建议甲"),
        ("MINOR", "措辞建议乙"),
        ("BLOCKING", "结构缺陷丙"),
    ]


def test_old_format_still_parsed() -> None:
    units = _parse_aggregate_sections(_OLD)
    triples = [(u.severity, u.text) for u in units]
    assert triples == [
        ("BLOCKING", "旧格式条目（无前缀）"),
        ("WARNING", "旧格式告警"),
    ]


def test_minor_section_no_longer_breaks_parsing() -> None:
    """T1b behavior change holds: the MINOR section no longer breaks parsing."""
    units = _parse_aggregate_sections(_NEW)
    assert any(u.severity == "BLOCKING" for u in units)


def test_resonance_section_still_terminates() -> None:
    units = _parse_aggregate_sections(_NEW)
    assert all("正文" not in u.text for u in units)


def test_item_level_severity_wins_over_section_header() -> None:
    """Plan Step 3: 节头与条目级不一致时条目级胜出。"""
    content = """# Chapter 9 — Audit Aggregate

## BLOCKING Findings (1)

- **MINOR** · 实为建议
"""
    units = _parse_aggregate_sections(content)
    assert [(u.severity, u.text) for u in units] == [("MINOR", "实为建议")]


def test_render_parse_round_trip() -> None:
    """Render and parse are one contract: round-trip sets must match."""
    from shenbi.pipeline.audit_aggregate import FindingUnit, render_aggregate

    units = [
        FindingUnit("BLOCKING", "结构缺陷甲", ("r1",)),
        FindingUnit("MINOR", "措辞乙", ("r2",)),
        FindingUnit("WARNING", "告警丙", ("r3",)),
    ]
    out = render_aggregate(7, units, {})
    parsed = _parse_aggregate_sections(out)
    assert {(u.severity, u.text) for u in parsed} == {(u.severity, u.text) for u in units}
