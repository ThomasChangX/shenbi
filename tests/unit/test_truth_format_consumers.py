"""Spec #85 T6 (audit I3) — consumer-level frontmatter flip assertions."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.mark.unit
def test_ensure_truth_frontmatter_backfills_thematic_break(tmp_path: Path) -> None:
    """Presence flip: a `----` first line is NOT frontmatter (legacy loose
    startswith counted it) — ensure_truth_frontmatter now backfills the
    canonical block (spec acceptance-7 registered direction).
    """
    from shenbi.pipeline.truth_io import ensure_truth_frontmatter

    out = ensure_truth_frontmatter("truth/pending_hooks.md", "----\n正文\n")
    assert out.startswith("---\n")  # canonical block backfilled


@pytest.mark.unit
def test_increment_thematic_break_not_frontmatter_violation() -> None:
    """Dispatch presence flip: `----` increment content is no longer flagged
    as carrying a frontmatter block.
    """
    from shenbi.exceptions import IncrementShapeError
    from shenbi.pipeline.dispatch_helper import _validate_increment_package

    base = "| 名 | 值 |\n| --- | --- |\n| 甲 | 1 |\n"  # non-shell base
    # `----` 主题断线：presence 翻转后不再算 frontmatter 违规（旧宽松 startswith 会 raise）
    _validate_increment_package("----\n增量正文\n", key_field="名", base_text=base)  # 不 raise
    # 对照：真 frontmatter 增量仍被拦（presence 判定非全盲）
    with pytest.raises(IncrementShapeError, match="frontmatter"):
        _validate_increment_package("---\nname: x\n---\n增量\n", key_field="名", base_text=base)


@pytest.mark.unit
def test_checkpoint_splice_single_blank_line(tmp_path: Path) -> None:
    """byte-form parity (audit I1): the spliced fm block keeps ONE blank
    line separator, matching the legacy find-splice output.
    """
    from shenbi.pipeline.checkpoint import _merge_staged_rows_keyed

    staged = "正文 staged\n"
    live = "---\nname: 主角\n---\n\n正文 live\n"
    merged = _merge_staged_rows_keyed(staged, live, key_field="名")
    assert merged.startswith("---\nname: 主角\n---\n\n")  # 恰一空行（I1 字节形）


@pytest.mark.unit
def test_truth_index_thematic_break_has_no_frontmatter() -> None:
    """core-consumer flip: `----` first line → no frontmatter keys."""
    from shenbi.pipeline.truth_index import _parse_frontmatter

    assert _parse_frontmatter("----\nlast_chapter: 5\n") == {}
