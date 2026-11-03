"""Spec #85 T5 (audit I2) — C-layer per-site assertions for lint_truth_pool."""

from __future__ import annotations

import pytest

from tools.lint_truth_pool import lint_pool


@pytest.mark.unit
def test_c_layer_p_family_now_visible_in_pool_findings() -> None:
    """P-family hooks enter the pool-lint findings face (was blind)."""
    t = (
        "# 伏笔池\n## 总览\n"
        "| Hook ID（钩名） | 当前生命周期 |\n|------|------|\n"
        "| P0-4（quiet阈结构） | RELEVANT |\n"
    )
    findings = lint_pool(t)
    assert any("P0-4" in getattr(f, "code", str(f)) or "P0-4" in str(f) for f in findings)


@pytest.mark.unit
def test_c1_malformed_unpiped_row_skips_not_crashes() -> None:
    """audit-T5 C1 regression: un-piped table rows must be skipped, not
    raise TypeError (the weak-guard retirement needs None guards).
    """
    t = (
        "# 伏笔池\n## 总览\n"
        "| Hook ID（钩名） | 当前生命周期 |\n|------|------|\n"
        "| P0-4（quiet阈结构） | RELEVANT\n"  # 无尾管
    )
    findings = lint_pool(t)  # 不应 raise
    assert not any("P0-4" in str(f) for f in findings)


# --- spec #85 T8: M5 red test (D-tier thread visibility, both maps) ---


@pytest.mark.unit
def test_m5_d12_visible_in_both_maps() -> None:
    """M5: the thread row map and section map were ABC-blind - D-tier
    clue ids must now be visible in BOTH (single-sourced THREAD_ID_RE).
    """
    from tools.lint_truth_pool import (
        _thread_row_map,  # pyright: ignore[reportPrivateImportUsage]
        _thread_section_map,  # pyright: ignore[reportPrivateImportUsage]
    )

    text = (
        "## 线索总览表\n"
        "| ID | 名称 | 优先级 | 类型 | max_gap | 起始章 | 终点章 | 状态 |\n"
        "|----|------|--------|------|---------|--------|--------|------|\n"
        "| D12 | 某线索 | P1 | 长线 | 4 | 1 | 40 | 开放 |\n\n"
        "### D12: 某线索\n- lifecycle_state: 开放\n"
    )
    rows = _thread_row_map(text)
    sections = _thread_section_map(text)
    assert "D12" in rows
    assert "D12" in sections
