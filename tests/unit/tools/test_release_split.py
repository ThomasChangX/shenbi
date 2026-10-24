"""spec #70 release-split unit tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from tools.release_split import (
    CHAPTER_FILE_RE,
    TIERS,
    ChapterInput,
    ReleaseSplitError,
    Tier,
    nonws,
    parse_chapter,
    select_chapter_files,
)

REPO = Path(__file__).resolve().parents[3]
FIX = REPO / "tests" / "fixtures" / "publish"

TITLES = {1: "明白纸", 2: "城破那日", 3: "两本册子", 4: "一升二合", 5: "例在，人在"}


@pytest.mark.unit
def test_tiers_pinned() -> None:
    assert TIERS["fanqie"] == Tier(floor=2000, target=2200, soft=2400)
    assert TIERS["qidian"] == Tier(floor=2000, target=2700, soft=3000)


@pytest.mark.unit
def test_chapter_file_regex() -> None:
    assert CHAPTER_FILE_RE.match("chapter-1.md")
    assert CHAPTER_FILE_RE.match("chapter-10.md")
    assert not CHAPTER_FILE_RE.match("chapter-1-pre-rev.md")
    assert not CHAPTER_FILE_RE.match("chapter-1-decisions.json")
    assert not CHAPTER_FILE_RE.match("chapter-1-revision-decisions.json")


@pytest.mark.unit
def test_select_orders_numerically_and_rejects_dup(tmp_path: Path) -> None:
    d = tmp_path / "chapters"
    d.mkdir()
    for name in ("chapter-10.md", "chapter-2.md", "chapter-1.md"):
        (d / name).write_text("# Chapter 1:\n\n# t\n\n正文", encoding="utf-8")
    files = select_chapter_files(d)
    assert [f.name for f in files] == ["chapter-1.md", "chapter-2.md", "chapter-10.md"]
    (d / "chapter-01.md").write_text("# Chapter 1:\n\n# t\n\n正文", encoding="utf-8")
    with pytest.raises(ReleaseSplitError, match="同章号"):
        select_chapter_files(d)


@pytest.mark.unit
def test_parse_real_fixtures() -> None:
    gates = {1: (8476, 14), 2: (8049, 15), 3: (7200, 15), 4: (7792, 15), 5: (6517, 22)}
    for n, (gate, h1n) in gates.items():
        ch = parse_chapter(FIX / f"chapter-{n}.md")
        assert isinstance(ch, ChapterInput)
        assert ch.number == n
        assert ch.title == TITLES[n]
        assert ch.gate_chars == gate
        assert ch.h1_nonws == h1n
        # identity: gate - h1 == sum of paragraph nonws
        assert ch.gate_chars - ch.h1_nonws == sum(nonws(p) for p in ch.paragraphs)
        # zero-nonws paragraphs dropped; every paragraph has content
        assert all(nonws(p) > 0 for p in ch.paragraphs)
        # no H1 lines, no META wrappers survive into paragraphs
        assert not any(p.startswith("# ") for p in ch.paragraphs)
        assert not any("META-BEGIN" in p or "PRE_WRITE_CHECK" in p for p in ch.paragraphs)


@pytest.mark.unit
def test_parse_ch5_duplicate_h1_outside_wrapper() -> None:
    ch = parse_chapter(FIX / "chapter-5.md")
    assert ch.title == "例在，人在"
    assert ch.h1_nonws == 22  # 三个 H1：# Chapter 5: + 章题 ×2（含 META 包装外重复行）


@pytest.mark.unit
def test_parse_zero_nonws_paragraph_dropped(tmp_path: Path) -> None:
    f = tmp_path / "chapter-1.md"
    f.write_text("# Chapter 1:\n\n# 题\n\n段一。\n\n　\n\n段二。", encoding="utf-8")
    # U+3000 独占段 = 零非空白字符段
    ch = parse_chapter(f)
    assert ch.paragraphs == ("段一。", "段二。")


@pytest.mark.unit
def test_parse_structural_errors(tmp_path: Path) -> None:
    no_h1 = tmp_path / "chapter-1.md"
    no_h1.write_text("# Chapter 1:\n\n正文一段。", encoding="utf-8")
    with pytest.raises(ReleaseSplitError, match="第二个 H1"):
        parse_chapter(no_h1)
    empty = tmp_path / "chapter-2.md"
    empty.write_text("", encoding="utf-8")
    with pytest.raises(ReleaseSplitError, match="空"):
        parse_chapter(empty)
    no_paras = tmp_path / "chapter-3.md"
    no_paras.write_text(
        "# Chapter 3:\n\n# 题\n\n<!--META-BEGIN-->\n## PRE_WRITE_CHECK\nx\n<!--META-END-->\n",
        encoding="utf-8",
    )
    with pytest.raises(ReleaseSplitError, match="正文段"):
        parse_chapter(no_paras)
