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
