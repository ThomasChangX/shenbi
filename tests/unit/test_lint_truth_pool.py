"""GO① pool two-table reconciliation lint (tools/lint_truth_pool.py)."""

from __future__ import annotations

from tools.lint_truth_pool import lint_pool

_CLEAN_POOL = """---
type: truth
---

# 伏笔池

## 总览

| Hook ID（钩子名） | 当前生命周期 | 种植章 | 兑现章（卷） | 类型 | 微妙度 | max_distance(14) | 升级曲线 |
|------|------|------|------|------|------|------|------|
| MH01（灵印） | RESOLVED | 4 | 30 | MYSTERY | 0.5 | 10 | STAIRCASE |

## 详情

### MH01（灵印）

- lifecycle_state: RESOLVED
- plant_chapter: 4
- resolve_chapter: 30
"""


def test_clean_pool_has_no_findings() -> None:
    assert lint_pool(_CLEAN_POOL) == []


def test_frozen_overview_row_is_flagged() -> None:
    """The phase3 pathology: detail advanced to RESOLVED@104 while the
    overview row still reads PLANTED with an empty 兑现章.
    """
    stale = _CLEAN_POOL.replace(
        "| MH01（灵印） | RESOLVED | 4 | 30 |", "| MH01（灵印） | PLANTED | 4 |  |"
    )
    checks = {f.check for f in lint_pool(stale)}
    assert "row_state_mismatch" in checks


def test_section_without_row_and_row_without_section() -> None:
    no_row = _CLEAN_POOL.replace(
        "| MH01（灵印） | RESOLVED | 4 | 30 | MYSTERY | 0.5 | 10 | STAIRCASE |", ""
    )
    assert {f.check for f in lint_pool(no_row)} == {"section_without_row"}

    no_section = _CLEAN_POOL.split("## 详情", maxsplit=1)[0] + "## 详情\n"
    assert {f.check for f in lint_pool(no_section)} == {"row_without_section"}


def test_planted_with_resolve_contradiction_is_flagged_not_repaired() -> None:
    """The CP-006/MH10 shape: PLANTED row carrying a filled 兑现章 — an
    evidence-level contradiction the lint must surface (repair cannot
    invent the disposition).
    """
    pool = (
        _CLEAN_POOL.replace(
            "| MH01（灵印） | RESOLVED | 4 | 30 |", "| MH01（灵印） | PLANTED | 4 | 40 |"
        )
        .replace("- lifecycle_state: RESOLVED", "- lifecycle_state: PLANTED")
        .replace("- resolve_chapter: 30", "")
    )
    checks = {f.check for f in lint_pool(pool)}
    assert "planted_with_resolve" in checks


def test_tombstone_with_live_row_is_flagged() -> None:
    pool = _CLEAN_POOL.replace(
        "- resolve_chapter: 30\n",
        "- resolve_chapter: 30\n- archived_to: truth/pending_hooks_archive.md\n",
    )
    checks = {f.check for f in lint_pool(pool)}
    assert "tombstone_has_row" in checks
