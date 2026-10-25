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
        (d / "chapter-2.md").write_text("他把红纸包塞给了老妇。", encoding="utf-8")
        (d / "truth").mkdir()
        (d / "truth" / "prop_registry.md").write_text(
            "| 实体 | owner |\n| 红纸包 | 小满→我(ch1) |\n", encoding="utf-8"
        )
        memo = d / "chapter-2-plan.md"
        memo.write_text(
            "### 场景预算与收束钩\n- 时间锚: 腊月初十\n- 余额: 十文\n- POV: 他\n",
            encoding="utf-8",
        )
        issues = check_cross_chapter(
            d / "chapter-2.md",
            d / "chapter-1.md",
            memo,
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
    # keyed by the card's name: frontmatter (the prose name), not the stem
    assert "小满" in cards
    assert cards["小满"]["性别代词"] == "他"
    assert cards["小满"]["机构"] == "星象局"


@pytest.mark.unit
def test_handled_prop_passes() -> None:
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        (d / "chapter-1.md").write_text("他把红纸包收进袖子。", encoding="utf-8")
        (d / "chapter-2.md").write_text("红纸包在怀里焐着。", encoding="utf-8")
        memo = d / "chapter-2-plan.md"
        memo.write_text(
            "- 物象: 红纸包|小满→我\n- 时间锚: 腊月十五\n- 余额: 12文\n- POV: 他\n"
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


@pytest.mark.unit
def test_plain_mention_with_registry_is_legal(tmp_path: Path) -> None:
    """Round-2 review: unchanged-owner mention (no hand-off) is LEGAL per
    spec invariant 4's 或-rule — the deterministic re-dispatch loop the
    reviewer demonstrated (every recurring-prop chapter failing from batch
    2 onward) must not exist.
    """
    d = tmp_path
    (d / "chapter-1.md").write_text("他把红纸包收进袖子。", encoding="utf-8")
    (d / "chapter-2.md").write_text("红纸包在怀里焐着。", encoding="utf-8")
    (d / "truth").mkdir()
    (d / "truth" / "prop_registry.md").write_text(
        "| 实体 | owner |\n| 红纸包 | 我 |\n", encoding="utf-8"
    )
    memo = d / "chapter-2-plan.md"
    memo.write_text(
        "### 场景预算与收束钩\n- 时间锚: 腊月初十\n- 余额: 十文\n- POV: 他\n",
        encoding="utf-8",
    )
    issues = check_cross_chapter(
        d / "chapter-2.md",
        d / "chapter-1.md",
        memo,
        CrossChapterContext(project_dir=d, registry_dir=d / "truth"),
    )
    assert issues == [], issues


@pytest.mark.unit
@pytest.mark.parametrize(
    "body",
    [
        "红纸包还在怀里焐着。",
        "红纸包还在桌上。",
        "他怀里还有红纸包。",
        "骨哨还没响，红纸包收着。",
        "怀表还走着，红纸包完好。",
    ],
)
def test_adverb_hai_plain_mentions_legal(tmp_path: Path, body: str) -> None:
    """Round-3 review: the adverb 还 (still) is not the verb 还 (return) —
    «X还在/还有X» is top-frequency carrying prose, never a hand-off.
    """
    d = tmp_path
    (d / "chapter-1.md").write_text("他收下红纸包。", encoding="utf-8")
    (d / "chapter-2.md").write_text(body, encoding="utf-8")
    (d / "truth").mkdir()
    (d / "truth" / "prop_registry.md").write_text(
        "| 实体 | owner |\n| 红纸包 | 我 |\n", encoding="utf-8"
    )
    memo = d / "chapter-2-plan.md"
    memo.write_text(
        "### 场景预算与收束钩\n- 时间锚: 腊月初十\n- 余额: 十文\n- POV: 他\n",
        encoding="utf-8",
    )
    issues = check_cross_chapter(
        d / "chapter-2.md",
        d / "chapter-1.md",
        memo,
        CrossChapterContext(project_dir=d, registry_dir=d / "truth"),
    )
    assert issues == [], issues


@pytest.mark.unit
def test_declaration_origin_cross_checked(tmp_path: Path) -> None:
    """Round-3 review: a declaration is not free text — its stated hand-off
    origin must sit inside the registry's recorded owner cell.
    """
    d = tmp_path
    (d / "chapter-1.md").write_text("他收下红纸包。", encoding="utf-8")
    (d / "chapter-2.md").write_text("红纸包在怀里。", encoding="utf-8")
    (d / "truth").mkdir()
    (d / "truth" / "prop_registry.md").write_text(
        "| 实体 | owner |\n| 红纸包 | 我 |\n", encoding="utf-8"
    )
    memo = d / "chapter-2-plan.md"
    memo.write_text(
        "### 场景预算与收束钩\n- 时间锚: 腊月初十\n- 余额: 十文\n- POV: 他\n"
        "- 物象: 红纸包|萤→老妇\n",
        encoding="utf-8",
    )
    issues = check_cross_chapter(
        d / "chapter-2.md",
        d / "chapter-1.md",
        memo,
        CrossChapterContext(project_dir=d, registry_dir=d / "truth"),
    )
    assert any("经手起点" in i and "registry owner" in i for i in issues), issues


@pytest.mark.unit
def test_transfer_declaration_exempts(tmp_path: Path) -> None:
    d = tmp_path
    (d / "chapter-1.md").write_text("他把红纸包收进袖子。", encoding="utf-8")
    (d / "chapter-2.md").write_text("他把红纸包塞给了老妇。", encoding="utf-8")
    (d / "truth").mkdir()
    (d / "truth" / "prop_registry.md").write_text(
        "| 实体 | owner |\n| 红纸包 | 我 |\n", encoding="utf-8"
    )
    memo = d / "chapter-2-plan.md"
    memo.write_text(
        "### 场景预算与收束钩\n- 时间锚: 腊月初十\n- 余额: 十文\n- POV: 他\n"
        "- 物象: 红纸包|我→老妇\n",
        encoding="utf-8",
    )
    issues = check_cross_chapter(
        d / "chapter-2.md",
        d / "chapter-1.md",
        memo,
        CrossChapterContext(project_dir=d, registry_dir=d / "truth"),
    )
    assert issues == [], issues


@pytest.mark.unit
def test_legacy_memo_exempts_prop_check(tmp_path: Path) -> None:
    """Legacy memo (no scene-budget block): declaration cross-check exempt —
    G4.cp already WARNs on the legacy shape.
    """
    d = tmp_path
    (d / "chapter-1.md").write_text("他把红纸包收进袖子。", encoding="utf-8")
    (d / "chapter-2.md").write_text("他把红纸包塞给了老妇。", encoding="utf-8")
    (d / "truth").mkdir()
    (d / "truth" / "prop_registry.md").write_text(
        "| 实体 | owner |\n| 红纸包 | 我 |\n", encoding="utf-8"
    )
    memo = d / "chapter-2-plan.md"
    memo.write_text("# 旧式备忘\n", encoding="utf-8")
    issues = check_cross_chapter(
        d / "chapter-2.md",
        d / "chapter-1.md",
        memo,
        CrossChapterContext(project_dir=d, registry_dir=d / "truth"),
    )
    assert issues == [], issues
