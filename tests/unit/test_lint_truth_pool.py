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


# --- B 批: thread ledger reconciliation ---------------------------------------

_CLEAN_THREAD = """---
total_chapters: 118
---

# 线索地图

## 线索总览表

| ID | 名称 | 优先级 | 类型 | max_gap | 起始章 | 终点章 | 状态 |
|----|------|--------|------|---------|--------|--------|------|
| A1 | 灵印 | P0 | 长线 | 2 | 1 | 118 | RELEVANT |
| C1 | 册上空格 | P2 | 短线 | 8 | 3 | 17 | RESOLVED |

## 线索详情

### A1: 灵印

- **状态**: RELEVANT
- **跨度**: 第1章 - 第118章

### C1: 册上空格

- **状态**: RESOLVED
- **跨度**: 第3章 - 第17章
"""


def test_clean_thread_ledger_has_no_findings() -> None:
    from tools.lint_truth_pool import lint_thread

    assert lint_thread(_CLEAN_THREAD) == []


def test_frozen_thread_row_is_flagged_and_repairable() -> None:
    from tools.lint_truth_pool import lint_thread

    frozen = _CLEAN_THREAD.replace(
        "| C1 | 册上空格 | P2 | 短线 | 8 | 3 | 17 | RESOLVED |",
        "| C1 | 册上空格 | P2 | 短线 | 8 | 3 | 99 | RELEVANT |",
    )
    checks = {f.check for f in lint_thread(frozen)}
    assert "row_state_mismatch" in checks

    from shenbi.pipeline.truth_io import sync_thread_overview_rows

    repaired = sync_thread_overview_rows(frozen)
    assert lint_thread(repaired) == [], "repair re-derives the frozen row"


def test_thread_section_without_row_and_tombstone() -> None:
    from tools.lint_truth_pool import lint_thread

    orphan = _CLEAN_THREAD.replace("### C1: 册上空格\n", "### C2: 拦船验牌\n").replace(
        "- **跨度**: 第3章 - 第17章", "- **跨度**: 第4章 - 第13章"
    )
    checks = {f.check for f in lint_thread(orphan)}
    assert "row_without_section" in checks  # C1 row lost its section (now C2)
    assert "section_without_row" in checks  # C2 section has no row

    tombstoned = _CLEAN_THREAD.replace(
        "- **跨度**: 第3章 - 第17章",
        "- **跨度**: 第3章 - 第17章\n- archived_to: outline/thread_map_archive.md",
    )
    checks = {f.check for f in lint_thread(tombstoned)}
    assert "tombstone_has_row" in checks  # C1 tombstone still holds its row
