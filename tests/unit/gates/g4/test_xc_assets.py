"""spec #75 T5: asset continuity (memo balance + event lines)."""

from __future__ import annotations

from pathlib import Path

import pytest

from shenbi.gates.g4.cross_chapter import (
    CrossChapterContext,
    _cn_amount,
    check_cross_chapter,
)


@pytest.mark.unit
def test_cn_amount() -> None:
    assert _cn_amount("一百九十二") == 192
    assert _cn_amount("十二") == 12
    assert _cn_amount("300") == 300
    assert _cn_amount("十") == 10


@pytest.mark.unit
def test_balance_jump_without_event_fails() -> None:
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        (d / "chapter-1.md").write_text("他把钱袋数了一遍。", encoding="utf-8")
        (d / "chapter-2.md").write_text("钱袋轻了。", encoding="utf-8")
        (d / "plans").mkdir()
        (d / "plans" / "chapter-1-plan.md").write_text("- 余额: 一百九十二文\n", encoding="utf-8")
        memo2 = d / "chapter-2-plan.md"
        memo2.write_text(
            "- 余额: 十二文\n- 时间锚: 腊月十五\n- POV: 他\n- 场景1: 1900字｜独立型｜收束钩：x\n",
            encoding="utf-8",
        )
        issues = check_cross_chapter(
            d / "chapter-2.md",
            d / "chapter-1.md",
            memo2,
            CrossChapterContext(project_dir=d),
        )
        assert any("余额跳变" in i for i in issues)


@pytest.mark.unit
def test_balance_jump_with_event_passes() -> None:
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        (d / "chapter-1.md").write_text("他把钱袋数了一遍。", encoding="utf-8")
        (d / "chapter-2.md").write_text("钱袋轻了。", encoding="utf-8")
        (d / "plans").mkdir()
        (d / "plans" / "chapter-1-plan.md").write_text("- 余额: 一百九十二文\n", encoding="utf-8")
        memo2 = d / "chapter-2-plan.md"
        memo2.write_text(
            "- 余额: 十二文\n- 事件: 支出|一百八十文|还债\n"
            "- 时间锚: 腊月十五\n- POV: 他\n- 场景1: 1900字｜独立型｜收束钩：x\n",
            encoding="utf-8",
        )
        issues = check_cross_chapter(
            d / "chapter-2.md",
            d / "chapter-1.md",
            memo2,
            CrossChapterContext(project_dir=d),
        )
        assert not any("余额跳变" in i for i in issues)


@pytest.mark.unit
def test_small_delta_passes() -> None:
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        (d / "chapter-1.md").write_text("他把钱袋数了一遍。", encoding="utf-8")
        (d / "chapter-2.md").write_text("钱袋差不多。", encoding="utf-8")
        memo2 = d / "chapter-2-plan.md"
        memo2.write_text(
            "- 余额: 一百八十五文\n- 时间锚: 腊月十五\n- POV: 他\n"
            "- 场景1: 1900字｜独立型｜收束钩：x\n",
            encoding="utf-8",
        )
        issues = check_cross_chapter(
            d / "chapter-2.md",
            d / "chapter-1.md",
            memo2,
            CrossChapterContext(project_dir=d),
        )
        assert not any("余额跳变" in i for i in issues)
