"""spec #88 T4: floor-source citations in word-count failure details."""

from __future__ import annotations

from pathlib import Path


def _write_chapter(tmp_path: Path, chars: int) -> Path:
    ch = tmp_path / "chapters/chapter-1.md"
    ch.parent.mkdir(parents=True, exist_ok=True)
    ch.write_text("灯" * chars, encoding="utf-8")
    return ch


def test_word_count_message_cites_floor_source(tmp_path: Path) -> None:
    """G4.word_count must_fix cites chapter_word_floor as the authority."""
    from shenbi.gates.g4.chapter_drafting import g4_chapter_drafting

    ch = _write_chapter(tmp_path, 10)  # far below any floor
    result = g4_chapter_drafting([str(ch)])
    msgs = [line for line in result.splitlines() if "G4.word_count" in line]
    assert msgs, "short chapter must fire word_count"
    assert any("chapter_word_floor" in m for m in msgs), msgs


def test_ln_below_floor_cites_floor_source(tmp_path: Path) -> None:
    """G4.ln.below_floor must_fix cites chapter_word_floor as the authority."""
    from shenbi.gates.g4.length_normalizing import g4_length_normalizing

    short = tmp_path / "short.md"
    short.write_text("短", encoding="utf-8")
    result = g4_length_normalizing([str(short)], str(tmp_path))
    assert "G4.ln.below_floor" in result
    assert "chapter_word_floor" in result
