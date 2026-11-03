"""Spec #85 T3 — M4 red tests: P family visible in cell and heading faces."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from shenbi.truth_format import HOOK_ID_RE

FIXTURE = Path("tests/fixtures/truth-pending_hooks-ch56.md")


@pytest.mark.unit
def test_m4_p_family_cell_and_heading() -> None:
    """M4: P-family ids in table cells (:29-35) and headings (:65) must be
    recognized by the truth_io hook faces (cell integral match + heading).
    """
    from shenbi.pipeline.truth_io import (
        _HOOK_HEADING_BLOCK_RE,  # pyright: ignore[reportPrivateImportUsage]
    )

    text = FIXTURE.read_text(encoding="utf-8")
    # cell face: rows `| P0-4 (quiet阈结构) | ... |` — the integral matcher
    cell_ids = {m.group(0) for m in HOOK_ID_RE.finditer(text)}
    assert "P0-4" in cell_ids
    # heading face: `### P0-4 TRIGGER 证据` at :65
    heading_ids = {m.group(2) for m in _HOOK_HEADING_BLOCK_RE.finditer(text)}
    assert "P0-4" in heading_ids


@pytest.mark.unit
def test_m4_negative_no_partial_two_group_capture() -> None:
    """Negative: the retired two-group cell form captured only ``P0`` from
    ``P0-4`` (mid-number hyphen unmatched by ``-?``). The integral face
    must return the whole token.
    """
    m = HOOK_ID_RE.search("| P0-4 (quiet阈结构) |")
    assert m is not None and m.group(0) == "P0-4"
    from shenbi.truth_format import canon_hook_id

    assert canon_hook_id(m.group(0)) == "P0-4"  # spec 验收 1：canon 归一后匹配
    # 对照一：旧两分组形态对 P 族整行不命中（历史病灶钉死说明）
    legacy = re.compile(r"(MH|CP)-?(\d{1,4})(?!\d)")
    assert legacy.search("| P0-4 (quiet) |") is None
    assert legacy.search("CP-001") is not None  # 旧式 CP 形仍命中（对照）
    # 对照二：假想的「两分组扩展形」(MH|CP|P)-?(\d{1,4}) 只捕 P0 ——
    # spec §2.1/验收 1 明令钉死的部分匹配假阳性（-? 贪不上中位连字符）
    naive = re.compile(r"(MH|CP|P)-?(\d{1,4})(?!\d)")
    nm = naive.search("P0-4 (quiet)")
    assert nm is not None and nm.group(0) == "P0" and nm.group(0) != "P0-4"
