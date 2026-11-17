"""Spec #109 T4 (I2): the tool's families/anchor are single-sourced from src."""

from __future__ import annotations


def test_tool_families_single_source_with_src() -> None:
    import tools.audit_starve_baseline as tool
    from shenbi.pipeline.audit_starve_family import NARROW6, T4_VARIANTS, VERDICT_LINE_RE

    assert tool.NARROW6 == NARROW6
    assert tool.T4_VARIANTS == T4_VARIANTS
    assert tool.VERDICT_LINE.pattern == VERDICT_LINE_RE.pattern


def test_tool_family_regexes_built_from_imported_constants() -> None:
    import tools.audit_starve_baseline as tool
    from shenbi.pipeline.audit_starve_family import NARROW6, WIDE12

    assert tool.FAMILY["narrow6"].pattern == "|".join(NARROW6)
    assert tool.FAMILY["wide12"].pattern == "|".join(WIDE12)
