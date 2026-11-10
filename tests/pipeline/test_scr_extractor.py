"""recent_location_terms: the surviving world-freshness face of the old SCR.

spec #86 T1: the 17-field StructuredChapterRepresentation had exactly one
live consumer (world freshness reading world_refs[category=="location"]);
everything else was dead weight. This module now exposes a single function.
"""

from __future__ import annotations

from pathlib import Path

from shenbi.pipeline.scr_extractor import recent_location_terms


def _write_chapter(project_dir: Path, n: int, body: str) -> None:
    # 双剥离钉（plan r3 审查 M1）：标题内置「镇」、META 块内置「林/谷」——三者
    # 均不在任何期望集：META 剥离失效→林/谷泄漏红；H1 剥离失效→镇泄漏红。
    chapters = project_dir / "chapters"
    chapters.mkdir(parents=True, exist_ok=True)
    (chapters / f"chapter-{n}.md").write_text(
        f"# 第{n}章 镇志\n\n{body}\n\n"
        "<!--META-BEGIN-->林 # 非散文 META 行\n第二行谷<!--META-END-->\n",
        encoding="utf-8",
    )


def test_collects_location_terms_across_window(tmp_path: Path) -> None:
    _write_chapter(tmp_path, 3, "他走进山口，望见远处的城。")
    assert recent_location_terms(tmp_path, 4) == {"山", "城"}


def test_window_excludes_current_chapter(tmp_path: Path) -> None:
    _write_chapter(tmp_path, 3, "旧章的山")
    _write_chapter(tmp_path, 4, "本章的河")
    assert recent_location_terms(tmp_path, 4) == {"山"}


def test_lookback_bounds_at_chapter_one(tmp_path: Path) -> None:
    _write_chapter(tmp_path, 1, "第一章的林")
    assert recent_location_terms(tmp_path, 5) == {"林"}


def test_missing_chapter_tolerated(tmp_path: Path) -> None:
    _write_chapter(tmp_path, 2, "存在的海")  # chapter 1 absent
    assert recent_location_terms(tmp_path, 3) == {"海"}


def test_non_location_categories_ignored(tmp_path: Path) -> None:
    # 灵石=cultivation、金币=currency 必须被过滤；山/河=location 保留
    _write_chapter(tmp_path, 2, "他掏出灵石和金币，翻过山，渡过河。")
    assert recent_location_terms(tmp_path, 3) == {"山", "河"}


def test_empty_project_returns_empty(tmp_path: Path) -> None:
    assert recent_location_terms(tmp_path, 10) == set()
