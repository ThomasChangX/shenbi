from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from shenbi.skill_utils.style_learning.compute_stats import (
    compute_percentiles,
    compute_sentence_stats,
)

sorted_pos_ints = st.lists(st.integers(min_value=1, max_value=999), min_size=1, max_size=60).map(
    sorted
)


@given(sorted_pos_ints)
@settings(max_examples=200, deadline=None)
def test_p50_equals_median_index(vs: list[int]) -> None:
    """P50 == 地板中点 vs[n//2]（与 compute_sentence_stats 的 median 同索引）。

    旧 bug：P50 用 int(n*0.50)-1，median 用 n//2，n≥2 时不等。修复后二者一致。
    """
    pct = compute_percentiles(vs)
    assert pct["P50"] == vs[len(vs) // 2]


@given(sorted_pos_ints)
@settings(max_examples=200, deadline=None)
def test_p50_equals_sentence_stats_median(vs: list[int]) -> None:
    """compute_percentiles P50 与 compute_sentence_stats median 必须相等（同一排序序列）。"""
    pct = compute_percentiles(vs)
    # compute_sentence_stats 内部 sort，故传已排序即稳定
    sentences = [("", x) for x in vs]
    stats = compute_sentence_stats(sentences)
    assert stats["P50"] == stats["median"] == pct["P50"]


@given(sorted_pos_ints)
@settings(max_examples=100, deadline=None)
def test_percentiles_within_range(vs: list[int]) -> None:
    """所有百分位必须在 [min, max] 区间（值域约束，非跨级单调）。

    nearest-rank 百分位方案不保证跨级单调（P25<=P50<=P95）：
    n=2 时 P50=values[1] 而 P25/P95=values[0]，故 P25<=P50 但 P50>P95 可能成立。
    正确不变量是每个百分位值落在数据 [min,max] 区间内。
    """
    pct = compute_percentiles(vs)
    lo, hi = vs[0], vs[-1]
    for key in ("P25", "P50", "P75", "P95"):
        assert lo <= pct[key] <= hi, key


def test_percentiles_empty_returns_zeros() -> None:
    assert compute_percentiles([]) == {"P25": 0, "P50": 0, "P75": 0, "P95": 0}
