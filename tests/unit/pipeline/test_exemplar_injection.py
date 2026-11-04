"""Spec #95 T5: exemplar chapter injection (prev passed chapter, META-stripped)."""

from __future__ import annotations

from pathlib import Path

from shenbi.pipeline.chapter_loop import (
    _append_feedback_injections,
    _strip_meta_from_exemplar,
)
from shenbi.pipeline.state import PipelineState


def _state() -> PipelineState:
    return PipelineState()


def test_meta_block_stripped() -> None:
    text = "```META\nchapter_role: 推进/转折\n```\n# 第8章\n\n正文。"
    out = _strip_meta_from_exemplar(text)
    assert "META" not in out and "推进/转折" not in out
    assert "# 第8章" in out and "正文。" in out


def test_no_meta_passthrough() -> None:
    assert _strip_meta_from_exemplar("# 第8章\n正文。") == "# 第8章\n正文。"


def test_prev_passed_chapter_injected_for_drafting(tmp_path: Path) -> None:
    (tmp_path / "chapters").mkdir()
    (tmp_path / "chapters" / "chapter-8.md").write_text(
        "```META\nchapter_role: 高潮\n```\n\n# 第8章\n\n上一通过章正文。",
        encoding="utf-8",
    )
    out = _append_feedback_injections(
        "基础 prompt", _state(), 9, "shenbi-chapter-drafting", tmp_path
    )
    assert "EXEMPLAR CHAPTER" in out
    assert "<exemplar_chapter>" in out
    assert "上一通过章正文。" in out
    assert "chapter_role" not in out  # META 剥离（R1 再教学面）


def test_first_chapter_skips_injection(tmp_path: Path) -> None:
    out = _append_feedback_injections(
        "基础 prompt", _state(), 1, "shenbi-chapter-drafting", tmp_path
    )
    assert "EXEMPLAR CHAPTER" not in out


def test_non_drafting_skill_skips(tmp_path: Path) -> None:
    (tmp_path / "chapters").mkdir()
    (tmp_path / "chapters" / "chapter-8.md").write_text("# 第8章\n正文。", encoding="utf-8")
    out = _append_feedback_injections("基础 prompt", _state(), 9, "shenbi-state-settling", tmp_path)
    assert "EXEMPLAR CHAPTER" not in out
