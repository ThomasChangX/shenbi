from __future__ import annotations

import math

from hypothesis import given, settings
from hypothesis import strategies as st

from shenbi.skill_utils.chapter_pattern.compute_pattern import PATTERNS, compute_entropy

# input 必须取自 PATTERNS（compute_entropy 的契约：未知模式不入归一分母）
pattern_lists = st.lists(st.sampled_from(PATTERNS), min_size=1, max_size=40)


@given(pattern_lists)
@settings(max_examples=200, deadline=None)
def test_present_counts_sum_to_n(patterns: list[str]) -> None:
    """归一：出现模式的计数之和 == 总数（精确整数，非浮点近似）。

    compute_entropy 对 input⊆PATTERNS 保证 Σ(count/n)==1。本测试断言其整数
    等价 Σcount==n，避免浮点舍入噪音。
    """
    _, terms = compute_entropy(patterns)
    n = len(patterns)
    assert sum(t["count"] for t in terms if t["count"] > 0) == n


@given(pattern_lists)
@settings(max_examples=200, deadline=None)
def test_entropy_matches_recompute(patterns: list[str]) -> None:
    """熵重算一致：返回值 == round(-Σ(count/n)·log2(count/n), 4)。"""
    entropy, terms = compute_entropy(patterns)
    n = len(patterns)
    recompute = round(
        sum(-(t["count"] / n) * math.log2(t["count"] / n) for t in terms if t["count"] > 0),
        4,
    )
    assert entropy == recompute


@given(pattern_lists)
@settings(max_examples=200, deadline=None)
def test_entropy_bounded_non_negative(patterns: list[str]) -> None:
    """0 ≤ H ≤ log2(不同模式数)。

    compute_entropy 把 H round 到 4 位小数，round 可使返回值比真值高出半个
    4 位 ULP（5e-5），故上界容差取 1e-4 覆盖舍入上行。
    """
    entropy, _ = compute_entropy(patterns)
    assert entropy >= 0.0
    k = len(set(patterns))
    assert entropy <= math.log2(k) + 1e-4


@given(st.lists(st.sampled_from(PATTERNS), min_size=1, max_size=10))
@settings(max_examples=50, deadline=None)
def test_single_pattern_zero_entropy(patterns: list[str]) -> None:
    if len(set(patterns)) == 1:
        entropy, _ = compute_entropy(patterns)
        assert entropy == 0.0
