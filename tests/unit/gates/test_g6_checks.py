"""Unit tests for g6_checks: G6.4 continuity, G6.5 pacing, G6.10 style."""

from __future__ import annotations

from pathlib import Path

import pytest

from shenbi.gates.g6_checks import (
    check_continuity,
    check_pacing,
    check_style_consistency,
)


@pytest.mark.unit
def test_check_continuity_passes_on_monotonic_timeline(tmp_path: Path) -> None:
    """Chapters with monotonically increasing days PASS."""
    chapters = []
    for i, day in enumerate([1, 2, 3, 4], 1):
        ch = tmp_path / f"chapter-{i:03d}.md"
        ch.write_text(f"第{day}天，主角出发。\n", encoding="utf-8")
        chapters.append(ch)
    checks, mf = check_continuity(chapters)
    assert mf == []
    assert any(c["id"] == "G6.4" and c["s"] == "PASS" for c in checks)


@pytest.mark.unit
def test_check_continuity_skips_when_no_chapters() -> None:
    """Empty chapters list returns SKIP."""
    checks, mf = check_continuity([])
    assert any(c["s"] == "SKIP" for c in checks)
    assert mf == []


@pytest.mark.unit
def test_check_pacing_returns_action_dialogue_introspection_mix(tmp_path: Path) -> None:
    """Diverse chapter types produce a G6.5 check (PASS or with warnings)."""
    chapters = []
    contents = [
        "「对话。」" * 50,
        "爆炸！战斗！攻击！" * 10,
        "心想，暗想，默念。" * 20,
    ]
    for i, content in enumerate(contents, 1):
        ch = tmp_path / f"chapter-{i:03d}.md"
        ch.write_text(content, encoding="utf-8")
        chapters.append(ch)
    checks, mf = check_pacing(chapters)
    assert any(c["id"] == "G6.5" for c in checks)


@pytest.mark.unit
def test_check_pacing_skips_when_no_chapters() -> None:
    checks, mf = check_pacing([])
    assert any(c["s"] == "SKIP" for c in checks)


@pytest.mark.unit
def test_check_style_consistency_skips_when_no_style_profile(tmp_path: Path) -> None:
    checks, mf = check_style_consistency(tmp_path / "missing.md", [])
    assert any(c["s"] == "SKIP" for c in checks)


@pytest.mark.unit
def test_check_style_consistency_passes_within_ranges(tmp_path: Path) -> None:
    """Chapters fed through style_profile.md ranges produce a G6.10 outcome.

    Source returns ([], [outliers]) when ranges are extracted but chapters
    fall outside them, and ([{G6.10 PASS}], []) when within. Either is valid;
    we assert the function actually ran (i.e., did not SKIP).
    """
    style = tmp_path / "style_profile.md"
    style.write_text(
        "# Style\n\n句长：15-25\n段长：80-150\n对白占比：20-40\n",
        encoding="utf-8",
    )
    chapters = []
    for i in range(1, 4):
        ch = tmp_path / f"chapter-{i:03d}.md"
        ch.write_text(("正文内容。" * 20 + "\n\n") * 5, encoding="utf-8")
        chapters.append(ch)
    checks, mf = check_style_consistency(style, chapters)
    g610_in_checks = any(c["id"] == "G6.10" for c in checks)
    g610_in_mf = any(entry.startswith("G6.10:") for entry in mf)
    assert g610_in_checks or g610_in_mf
    assert not any(c["s"] == "SKIP" for c in checks)


@pytest.mark.unit
def test_check_style_consistency_extracts_ranges_from_table(tmp_path: Path) -> None:
    """Fallback table parsing extracts avg_sent/avg_para when ranges absent.

    Same SKIP-vs-ran reasoning as the ranges test: we verify extraction
    succeeded (no SKIP) rather than locking in PASS/FAIL.
    """
    style = tmp_path / "style_profile.md"
    style.write_text(
        "# Style\n| 章节 | 总句 | 总段 | 总字 | 平均句长 | 平均段长 |\n"
        "|---|---|---|---|---|---|\n| 第1章 | 100 | 10 | 2000 | 20.0 | 200.0 |\n",
        encoding="utf-8",
    )
    chapters = [tmp_path / "chapter-001.md"]
    chapters[0].write_text("正文内容。\n", encoding="utf-8")
    checks, mf = check_style_consistency(style, chapters)
    g610_in_checks = any(c["id"] == "G6.10" for c in checks)
    g610_in_mf = any(entry.startswith("G6.10:") for entry in mf)
    assert g610_in_checks or g610_in_mf
    assert not any(c["s"] == "SKIP" for c in checks)
