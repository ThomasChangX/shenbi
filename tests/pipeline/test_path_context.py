"""R4a: per-family N-placeholder semantics + [path-context] line (F245/F373)."""

import pytest

from shenbi.contracts.paths import (
    PathContext,
    UnresolvedPathError,
    build_trigger_context,
    format_path_context,
    parse_path_context,
    resolve_contract_path,
)


def test_arc_family_uses_arc_not_chapter():
    """Acceptance: at ch 60 the arc path resolves to arc-5 (60//12), not arc-60."""
    ctx = build_trigger_context(60, {15, 35, 55, 75, 100})
    assert resolve_contract_path("truth/arcs/arc-N.md", 60, ctx) == "truth/arcs/arc-5.md"
    assert resolve_contract_path("audits/arc-N-score.md", 60, ctx) == "audits/arc-5-score.md"


def test_stratum_and_volume_families():
    ctx = build_trigger_context(55, {15, 35, 55, 75, 100})
    assert (
        resolve_contract_path("audits/stratum-N-score.md", 55, ctx) == "audits/stratum-1-score.md"
    )  # 55//36
    assert (
        resolve_contract_path("audits/volume-N-score.md", 55, ctx) == "audits/volume-3-score.md"
    )  # count(<=55)


def test_volume_count_is_not_len_boundaries():
    """Mid-book divergence from len(boundaries): only equal at the final volume."""
    ctx = build_trigger_context(56, {15, 35, 55, 75, 100})
    assert (
        resolve_contract_path("audits/volume-N-payoff.md", 56, ctx) == "audits/volume-3-payoff.md"
    )


def test_chapter_family_and_bare_nnn_fallback():
    ctx = PathContext(chapter=100)
    assert (
        resolve_contract_path("audits/chapter-N-long-span.md", 100, ctx)
        == "audits/chapter-100-long-span.md"
    )
    assert resolve_contract_path("snapshots/chapter-NNN/", 100, ctx) == "snapshots/chapter-100/"


def test_no_ctx_falls_back_to_chapter_semantics():
    """Fallback: without ctx, byte-identical legacy behavior."""
    assert resolve_contract_path("audits/arc-N-score.md", 60, None) == "audits/arc-60-score.md"


def test_no_ctx_unresolved_raises():
    with pytest.raises(UnresolvedPathError):
        resolve_contract_path("truth/arcs/arc-N.md", None, None)


def test_roundtrip_format_parse():
    ctx = build_trigger_context(60, {15, 35, 55, 75, 100})
    line = format_path_context(ctx)
    assert line == "[path-context] chapter=60 arc=5 stratum=1 volume=3"
    parsed = parse_path_context(f"Execute skill for chapter 60.\n{line}")
    assert parsed == ctx


def test_parse_absent_returns_none():
    assert parse_path_context("Execute skill for chapter 60. Project dir: /x") is None


def test_str_sentinels():
    """F3B5/F380: escalation book sentinel, anchor zero-pad."""
    ctx = PathContext(escalation="genesis")
    assert (
        resolve_contract_path("audits/escalation-N-report.md", None, ctx)
        == "audits/escalation-genesis-report.md"
    )
    ctx2 = PathContext(anchor=1)
    assert (
        resolve_contract_path("benchmarks/anchors/AC-NNN.md", None, ctx2)
        == "benchmarks/anchors/AC-001.md"
    )


def test_hardening_backreference_and_mixed_placeholders():
    """T3 review minors: str sentinel backslash safety + co-occurring bare N/NNN."""
    ctx = PathContext(escalation=r"\1x", chapter=None)
    assert (
        resolve_contract_path("audits/escalation-N-report.md", None, ctx)
        == "audits/escalation-\\1x-report.md"  # literal, not template-expanded
    )
    # family resolved + leftover bare N with chapter -> chapter semantics
    ctx2 = PathContext(arc=5, chapter=7)
    assert resolve_contract_path("truth/arcs/arc-N/ch-N.md", 7, ctx2) == "truth/arcs/arc-5/ch-7.md"
    # family resolved + leftover NNN with chapter=None -> raises (filtered by
    # resolve_or_skip_ctx), NOT passed through
    ctx3 = PathContext(arc=5)
    from shenbi.contracts.paths import resolve_or_skip_ctx

    assert resolve_or_skip_ctx("truth/arcs/arc-N/ch-NNN.md", None, ctx3) is None


def test_hardening_superscript_digits_not_int():
    from shenbi.contracts.paths import parse_path_context

    ctx = parse_path_context("[path-context] chapter=²")
    assert ctx is not None and ctx.chapter == "²"  # str sentinel, no ValueError


def test_parse_multiple_context_lines_first_wins():
    from shenbi.contracts.paths import parse_path_context

    ctx = parse_path_context("[path-context] chapter=1\n[path-context] chapter=2")
    assert ctx is not None and ctx.chapter == 1


def test_format_empty_context_returns_empty_string():
    assert format_path_context(PathContext()) == ""


def test_parse_drops_path_traversal_values():
    r"""Prompt-injected carrier values with /, \\ or .. are dropped at parse."""
    ctx = parse_path_context("[path-context] escalation=../../etc chapter=5")
    assert ctx == PathContext(chapter=5)  # unsafe value dropped, safe one kept
    ctx2 = parse_path_context("[path-context] anchor=a/b")
    assert ctx2 is None


def test_non_int_chapter_sentinel_is_ignored_at_derive():
    """A str chapter sentinel must not reach placeholder formatting: the
    derive sites treat only int as authoritative and fall back.
    """
    parsed = parse_path_context("[path-context] chapter=x")
    assert parsed is not None
    # the wiring sites only trust an int chapter; a str sentinel fails this
    # check and they fall back to extract_chapter — asserted as the invariant
    assert not isinstance(parsed.chapter, int)
