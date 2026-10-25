"""spec #75 T1: checker skeleton + regression fixture provenance."""

from __future__ import annotations

from pathlib import Path

import pytest

from shenbi.gates.g4.cross_chapter import (
    CrossChapterContext,
    check_cross_chapter,
    g4_cross_chapter,
    load_memo_declarations,
    prev_chapter_path,
)

FIX = Path(__file__).resolve().parents[4] / "tests/fixtures/cross-chapter-regression"


@pytest.mark.unit
def test_fixture_provenance_real_output() -> None:
    from shenbi.gates.g0_purity import load_provenance

    for n in (7, 9):  # G0.19 variant-sibling 判据命中面
        p = load_provenance(FIX / "chapters" / f"chapter-{n}.md")
        assert p == "real-output", n


@pytest.mark.unit
def test_prev_chapter_n_minus_one() -> None:
    prev = prev_chapter_path(FIX / "chapters" / "chapter-2.md")
    assert prev is not None and prev.name == "chapter-1.md"
    assert prev_chapter_path(FIX / "chapters" / "chapter-1.md") is None  # 首章
    p5 = prev_chapter_path(FIX / "chapters" / "chapter-5.md")
    assert p5 is not None and p5.name == "chapter-4.md"


@pytest.mark.unit
def test_first_chapter_skips_seam_items() -> None:
    issues = check_cross_chapter(
        FIX / "chapters" / "chapter-1.md", None, None, CrossChapterContext()
    )
    assert issues == []


@pytest.mark.unit
def test_memo_declarations_parsed() -> None:
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        memo = Path(td) / "chapter-3-plan.md"
        memo.write_text(
            "### 场景预算与收束钩（#72 粒度契约）\n"
            "- 场景1: 1900字｜独立型｜收束钩：x\n"
            "- 时间锚: 腊月初十\n"
            "- 余额: 一百九十二文\n"
            "- POV: 他\n",
            encoding="utf-8",
        )
        decls = load_memo_declarations(memo)
        assert decls == {"时间锚": "腊月初十", "余额": "一百九十二文", "POV": "他"}
        # 回拨标记
        memo.write_text("- 时间锚: [回拨]腊月初五\n", encoding="utf-8")
        assert load_memo_declarations(memo)["时间锚"] == "[回拨]腊月初五"
        # 旧格式备忘 → 空 dict（legacy WARN 路径判据）
        memo.write_text("# 旧式备忘\n", encoding="utf-8")
        assert load_memo_declarations(memo) == {}


@pytest.mark.integration
def test_g4_entry_reports_wound1() -> None:
    """T2 onwards: ch2-vs-ch1 must surface the POV break."""
    result = g4_cross_chapter([str(FIX / "chapters" / "chapter-2.md")], rd=str(FIX / "chapters"))
    assert "POV" in result


@pytest.mark.unit
def test_registry_absence_degrades_to_warn() -> None:
    """#75: registry tables absent → cross-check layer WARN (visible, not fatal)."""
    import json as _json
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        # chapters/ exists (ch2 vs ch1 clean pair), truth/ has NO registry tables
        ch_dir = Path(td) / "chapters"
        ch_dir.mkdir()
        filler = "他" * 4 + "数了一遍。" * 30
        (ch_dir / "chapter-1.md").write_text(
            "---\nprovenance: real-output\n---\n\n他推门。腊月初一。" + filler, encoding="utf-8"
        )
        (ch_dir / "chapter-2.md").write_text(
            "---\nprovenance: real-output\n---\n\n他出门。腊月初二。" + filler, encoding="utf-8"
        )
        result = _json.loads(
            g4_cross_chapter(
                [str(ch_dir / "chapter-2.md")],
                rd=str(ch_dir),
                project_dir=td,
            )
        )
        warns = [c for c in result["checks"] if c["id"] == "XC.registry" and c["s"] == "WARN"]
        assert len(warns) == 3, f"expected 3 registry WARNs, got {result['checks']}"
        assert result["status"] == "PASS", "registry absence must degrade (WARN), not FAIL"
