"""spec #75 T2: POV consistency + protagonist naming three-signal binding."""

from __future__ import annotations

from pathlib import Path

import pytest

from shenbi.gates.g4.cross_chapter import (
    CrossChapterContext,
    check_cross_chapter,
    derive_pov_mode,
    protagonist_binding_hits,
)

FIX = Path(__file__).resolve().parents[4] / "tests/fixtures/cross-chapter-regression"


@pytest.mark.unit
def test_pov_derivation_first_vs_third() -> None:
    assert derive_pov_mode("我趴在长案上。我的手很冷。") == "我"
    assert derive_pov_mode("他蹲过去问。他把手放下。") == "他"


@pytest.mark.integration
def test_wound1_pov_break_fixture() -> None:
    """Wound 1: ch1 first-person vs ch2 third-person (true positive)."""
    issues = check_cross_chapter(
        FIX / "chapters" / "chapter-2.md",
        FIX / "chapters" / "chapter-1.md",
        None,
        CrossChapterContext(),
    )
    assert any("POV 人称断裂" in i for i in issues)


@pytest.mark.integration
def test_wound2_lamp_binding_fixture() -> None:
    """Wound 2: ch4 protagonist called 灯, three-signal bound (true positive)."""
    issues = check_cross_chapter(
        FIX / "chapters" / "chapter-4.md",
        FIX / "chapters" / "chapter-3.md",
        None,
        CrossChapterContext(),
    )
    assert any("称谓违例" in i and "灯" in i for i in issues)


@pytest.mark.unit
def test_inner_verb_binding_signal() -> None:
    hits = protagonist_binding_hits("灯在心里过了一遍米数。", "灯", ("临", "他"))
    assert hits  # 内汲动词 + 主语位双信号


@pytest.mark.unit
def test_whitelisted_name_passes() -> None:
    assert protagonist_binding_hits("临在心里过了一遍。", "临", ("临", "他")) == []


@pytest.mark.unit
def test_clean_adjacent_no_false_positive() -> None:
    """True negative: whitelisted naming + consistent POV."""
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        (d / "chapter-1.md").write_text(
            "他推门进来。临把手里的册子合上。他在心里数了三遍。", encoding="utf-8"
        )
        (d / "chapter-2.md").write_text(
            "他抬起头。临把灯芯拨亮了一点。他转身出去。", encoding="utf-8"
        )
        issues = check_cross_chapter(
            d / "chapter-2.md", d / "chapter-1.md", None, CrossChapterContext()
        )
        assert issues == []
