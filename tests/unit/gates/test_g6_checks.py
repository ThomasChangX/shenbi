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


# ---------------------------------------------------------------------------
# Error-path tests (PR-52 Step 6) — extracted-check level
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_check_continuity_timeline_regression_detected(tmp_path: Path) -> None:
    """A day count that goes backward across chapters -> G6.4 timeline_regression."""
    ch1 = tmp_path / "chapter-001.md"
    ch2 = tmp_path / "chapter-002.md"
    ch1.write_text("第5天，故事开始。\n", encoding="utf-8")
    ch2.write_text("第3天，回溯。\n", encoding="utf-8")
    checks, mf = check_continuity([ch1, ch2])
    assert any(e.startswith("G6.4:timeline_regression") for e in mf)


@pytest.mark.unit
def test_check_continuity_future_knowledge_not_detected_pins_inert_behavior(tmp_path: Path) -> None:
    r"""Future-knowledge check: pins current (inert) behavior.

    The check appends a future_knowledge violation only when
    `intro_map[re_ent] > cn`. intro_map is populated in ascending chapter
    order with first-occurrence values, so intro_map[ent] is always <= cn
    and the `> cn` guard can never be true. No future_knowledge violation
    is ever emitted. This test pins that inert behavior (Non-Goal #3:
    do not modify source).
    """
    ch1 = tmp_path / "chapter-001.md"
    ch2 = tmp_path / "chapter-002.md"
    ch1.write_text("主角意识到灵能乙的存在。\n", encoding="utf-8")
    ch2.write_text("灵能乙首次出现。\n", encoding="utf-8")
    checks, mf = check_continuity([ch1, ch2])
    # pins current behavior: future_knowledge is never flagged (dead guard).
    assert not any(e.startswith("G6.4:future_knowledge") for e in mf)


@pytest.mark.unit
def test_check_pacing_four_consecutive_same_type(tmp_path: Path) -> None:
    """Four consecutive chapters classified as the same type -> G6.5 4_consecutive."""
    chapters = []
    for i in range(1, 5):
        ch = tmp_path / f"chapter-{i:03d}.md"
        # Pure introspection-heavy text -> 'introspection' classification.
        ch.write_text("心想暗想心说默念内心。" * 30, encoding="utf-8")
        chapters.append(ch)
    checks, mf = check_pacing(chapters)
    assert any(e.startswith("G6.5:4_consecutive") for e in mf)


@pytest.mark.unit
def test_check_pacing_no_action_peaks_when_all_quiet(tmp_path: Path) -> None:
    """8+ chapters with zero action density peaks -> G6.5:no_action_peaks."""
    chapters = []
    for i in range(1, 9):
        ch = tmp_path / f"chapter-{i:03d}.md"
        # Introspection text only — no action vocabulary, low dialogue.
        ch.write_text("心想暗想心说默念内心。" * 20, encoding="utf-8")
        chapters.append(ch)
    checks, mf = check_pacing(chapters)
    assert any("no_action_peaks" in e for e in mf)


@pytest.mark.unit
def test_check_style_consistency_sentence_out_of_range(tmp_path: Path) -> None:
    """A chapter with sentences far longer than the style range ->
    G6.10:sentence outlier in mf.
    """
    style = tmp_path / "style_profile.md"
    style.write_text("# Style\n\n句长：5-8\n", encoding="utf-8")
    ch = tmp_path / "chapter-001.md"
    # Very few sentence terminators relative to CJK chars -> huge avg sentence.
    ch.write_text(
        "这是一段非常非常长的没有任何句号分隔的连续中文正文内容文字" * 5, encoding="utf-8"
    )
    checks, mf = check_style_consistency(style, [ch])
    assert any(e.startswith("G6.10:sentence") for e in mf)


@pytest.mark.unit
def test_check_style_consistency_paragraph_out_of_range(tmp_path: Path) -> None:
    """A chapter with one giant paragraph -> paragraph avg outside range -> mf."""
    style = tmp_path / "style_profile.md"
    style.write_text("# Style\n\n段长：80-120\n", encoding="utf-8")
    ch = tmp_path / "chapter-001.md"
    # Single paragraph (no blank lines) -> para avg = all CJK chars, very large.
    ch.write_text(("这是一段正文。" * 60), encoding="utf-8")
    checks, mf = check_style_consistency(style, [ch])
    assert any(e.startswith("G6.10:paragraph") for e in mf)


@pytest.mark.unit
def test_check_style_consistency_dialogue_out_of_range(tmp_path: Path) -> None:
    """Zero dialogue in a chapter whose style profile requires >= some % -> mf."""
    style = tmp_path / "style_profile.md"
    style.write_text("# Style\n\n对白占比：30-50\n", encoding="utf-8")
    ch = tmp_path / "chapter-001.md"
    # Pure narrative, no 「」 or "" dialogue markers.
    ch.write_text("主角走在路上。天气很好。他继续前行。" * 15, encoding="utf-8")
    checks, mf = check_style_consistency(style, [ch])
    assert any(e.startswith("G6.10:dialogue") for e in mf)


@pytest.mark.unit
def test_check_style_consistency_skips_when_ranges_unparseable(tmp_path: Path) -> None:
    """A style_profile.md with no recognizable ranges AND no table -> SKIP."""
    style = tmp_path / "style_profile.md"
    style.write_text("# Style\n\n这是无法解析的描述性文字，没有任何数字范围。\n", encoding="utf-8")
    ch = tmp_path / "chapter-001.md"
    ch.write_text("正文内容。\n", encoding="utf-8")
    checks, mf = check_style_consistency(style, [ch])
    assert any(c.get("id") == "G6.10" and c.get("s") == "SKIP" for c in checks)
    assert mf == []
