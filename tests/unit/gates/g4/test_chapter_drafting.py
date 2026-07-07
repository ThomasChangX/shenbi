"""Bespoke error-path tests for g4_chapter_drafting.

The parametrized harness in test_all_skills_parametrized.py covers the COMMON
contract (empty input, missing file, gate field, etc.). This file covers the
checker-SPECIFIC business rules: content overlap, visual scene, chapter-end
hook, PRE/POST check blocks, transition-word density, and fatigue words.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from shenbi.gates.g4.chapter_drafting import g4_chapter_drafting


def _run(fps: list[str], rd: str | None = None) -> dict[str, Any]:
    return json.loads(g4_chapter_drafting(fps, rd))


def _must_fix(result: dict[str, Any]) -> list[str]:
    return result.get("must_fix", [])


# CJK paragraphs long enough (>=50 chars) to be fingerprinted for overlap.
_FP_PARA_A = "他沿着小路慢慢走着看着远方心中想着未来的种种可能不知道该如何是好。" * 2
_FP_PARA_B = "她站在窗前静静望着天空回想着过去发生的种种事情感到十分无奈。" * 2


@pytest.mark.unit
def test_fails_when_content_overlap_above_40_percent(tmp_path: Path) -> None:
    """Two near-identical chapters (>40% shared paragraphs) -> FAIL.

    The overlap check only runs when a round_dir is supplied and a sibling
    chapter exists under project-output/chapters.
    """
    rd = tmp_path / "round"
    chapters = rd / "project-output" / "chapters"
    chapters.mkdir(parents=True)
    body = f"{_FP_PARA_A}\n\n{_FP_PARA_B}\n"
    ch1 = chapters / "chapter-001.md"
    ch2 = chapters / "chapter-002.md"
    ch1.write_text(body, encoding="utf-8")
    ch2.write_text(body, encoding="utf-8")

    result = _run([str(ch1)], str(rd))
    mf = _must_fix(result)

    assert result["status"] == "FAIL"
    assert any("G4.cd.content_overlap" in m for m in mf)


@pytest.mark.unit
def test_fails_when_no_visual_scene(tmp_path: Path) -> None:
    """No paragraph with >=200 CJK chars of visual narrative -> FAIL."""
    ch = tmp_path / "chapter-001.md"
    ch.write_text("# 章节\n\n抽象的叙述内容。\n", encoding="utf-8")

    result = _run([str(ch)])
    mf = _must_fix(result)

    assert result["status"] == "FAIL"
    assert any("G4.cd.no_visual_scene" in m for m in mf)


@pytest.mark.unit
def test_fails_when_no_chapter_end_hook(tmp_path: Path) -> None:
    """Last paragraph (>=30 CJK) with no question/tension marker -> FAIL."""
    ch = tmp_path / "chapter-001.md"
    plain_end = "他回到了家中休息吃饭睡觉度过了一个平淡无奇的夜晚时光然后入睡。"
    ch.write_text(f"# 章节\n\n{plain_end}\n", encoding="utf-8")

    result = _run([str(ch)])
    mf = _must_fix(result)

    assert result["status"] == "FAIL"
    assert any("G4.cd.no_hook" in m for m in mf)


@pytest.mark.unit
def test_fails_when_pre_write_check_missing(tmp_path: Path) -> None:
    """Missing ## PRE_WRITE_CHECK block -> must_fix.

    pins current behavior: the plan labeled this WARN, but the checker appends
    G4.pre_check to must_fix, which makes the whole gate FAIL.
    """
    ch = tmp_path / "chapter-001.md"
    ch.write_text("# 章节\n\n他回到了家中。\n", encoding="utf-8")

    result = _run([str(ch)])
    mf = _must_fix(result)

    assert result["status"] == "FAIL"
    assert any("G4.pre_check" in m for m in mf)


@pytest.mark.unit
def test_fails_when_post_write_check_missing(tmp_path: Path) -> None:
    """PRE_WRITE_CHECK present but POST_WRITE_SELF_CHECK absent -> must_fix.

    pins current behavior: treated as FAIL (must_fix), not WARN.
    """
    ch = tmp_path / "chapter-001.md"
    ch.write_text("# 章节\n\n## PRE_WRITE_CHECK\n内容。\n", encoding="utf-8")

    result = _run([str(ch)])
    mf = _must_fix(result)

    assert result["status"] == "FAIL"
    assert any("G4.post_check" in m for m in mf)


@pytest.mark.unit
def test_fails_when_transition_density_too_high(tmp_path: Path) -> None:
    """Transition-word count exceeds the 1-per-3000-words budget -> FAIL."""
    ch = tmp_path / "chapter-001.md"
    ch.write_text("# 章节\n\n" + "此时终于于是" * 3 + "\n", encoding="utf-8")

    result = _run([str(ch)])
    mf = _must_fix(result)

    assert result["status"] == "FAIL"
    assert any("G4.transition" in m for m in mf)


@pytest.mark.unit
def test_fails_when_fatigue_words_exceeded(tmp_path: Path) -> None:
    """More than 8 fatigue-word hits -> FAIL (threshold relaxed from 3).

    Uses fatigue words that are NOT transition words (猛地/瞬间/一股/恐怖) so
    the failure is attributable to the fatigue check, not transition density.
    """
    ch = tmp_path / "chapter-001.md"
    ch.write_text("# 章节\n\n" + "猛地瞬间一股恐怖" * 3 + "\n", encoding="utf-8")

    result = _run([str(ch)])
    mf = _must_fix(result)

    assert result["status"] == "FAIL"
    assert any("G4.fatigue" in m for m in mf)
