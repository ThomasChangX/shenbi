"""spec #75 T4: prop owner chain + card attribute consistency."""

from __future__ import annotations

from pathlib import Path

import pytest

from shenbi.gates.g4.cross_chapter import (
    CrossChapterContext,
    check_cross_chapter,
    load_card_attributes,
)

FIX = Path(__file__).resolve().parents[4] / "tests/fixtures/cross-chapter-regression"


@pytest.mark.integration
def test_wound4_prop_chain_fixture() -> None:
    """Wound true-positive over regression fixture."""
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        (d / "chapter-1.md").write_text("他把红纸包收进袖子。", encoding="utf-8")
        (d / "chapter-2.md").write_text("红纸包在怀里焐着。", encoding="utf-8")
        (d / "truth").mkdir()
        (d / "truth" / "prop_registry.md").write_text(
            "| 实体 | owner |\n| 红纸包 | 小满→我(ch1) |\n", encoding="utf-8"
        )
        issues = check_cross_chapter(
            d / "chapter-2.md",
            d / "chapter-1.md",
            None,
            CrossChapterContext(project_dir=d, registry_dir=d / "truth"),
        )
        assert any("红纸包" in i and "经手" in i for i in issues)


@pytest.mark.integration
def test_wound5_card_gender_org_fixture() -> None:
    """Wound true-positive over regression fixture."""
    issues = check_cross_chapter(
        FIX / "chapters" / "chapter-1.md",
        None,  # card check runs on the first chapter too
        None,
        CrossChapterContext(project_dir=FIX),
    )
    assert any("小满" in i for i in issues), issues
    assert any("机构" in i or "星象局" in i for i in issues), issues


@pytest.mark.unit
def test_card_attributes_parsed() -> None:
    cards = load_card_attributes(FIX / "characters" / "major")
    assert "xiao-man" in cards
    assert cards["xiao-man"]["性别代词"] == "他"
    assert cards["xiao-man"]["机构"] == "星象局"


@pytest.mark.unit
def test_handled_prop_passes() -> None:
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        (d / "chapter-1.md").write_text("他把红纸包收进袖子。", encoding="utf-8")
        (d / "chapter-2.md").write_text("红纸包在怀里焐着。", encoding="utf-8")
        memo = d / "chapter-2-plan.md"
        memo.write_text(
            "- 物象: 红纸包|萤→我\n- 时间锚: 腊月十五\n- 余额: 12文\n- POV: 他\n"
            "- 场景1: 1900字｜独立型｜收束钩：x\n",
            encoding="utf-8",
        )
        (d / "truth").mkdir()
        (d / "truth" / "prop_registry.md").write_text(
            "| 实体 | owner |\n| 红纸包 | 小满→我(ch1) |\n", encoding="utf-8"
        )
        issues = check_cross_chapter(
            d / "chapter-2.md",
            d / "chapter-1.md",
            memo,
            CrossChapterContext(project_dir=d, registry_dir=d / "truth"),
        )
        assert not any("经手" in i for i in issues)
