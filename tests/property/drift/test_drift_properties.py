from __future__ import annotations

import re

from hypothesis import given, settings
from hypothesis import strategies as st

from shenbi.skill_utils.drift_detection.compute_drift import (
    detect_chapter_drift,
    detect_volume_drift,
)

_CHAPTER_RE = re.compile(r"chapters (\d+)-(\d+)")

scores_st = st.lists(
    st.floats(min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False),
    min_size=0,
    max_size=20,
)


@given(
    raw=scores_st,
    excl=st.sets(st.integers(min_value=0, max_value=19), max_size=8),
)
@settings(max_examples=200, deadline=None)
def test_monotonic_decline_span_excludes_overridden(raw: list[float], excl: set[int]) -> None:
    """Drift 排除不泄漏（触发层）：任何 MONOTONIC_DECLINE 的章节跨度不含 excl 索引。

    excl reset run/start/prev（compute_drift.py:91-92），故递减不可能跨越被排除章。
    detail 形如 '...chapters {start+1}-{i+1}'，0-基区间 [start, i] 必与 excl 不交。
    """
    if len(raw) < 2:
        return
    findings = detect_chapter_drift(raw, dim="情感落地", exclude_indices=excl)
    for f in findings:
        if f.kind != "monotonic_decline":
            continue
        m = _CHAPTER_RE.search(f.detail)
        assert m is not None, f.detail
        start1, end1 = int(m.group(1)), int(m.group(2))  # 1-based chapter numbers
        span0 = set(range(start1 - 1, end1))  # 0-based indices [start, i]
        assert not (span0 & excl), f"{f.detail} 跨越被排除索引 {span0 & excl}"


@given(
    series=st.lists(
        st.floats(min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False),
        min_size=3,
        max_size=8,
    ).map(sorted)  # 传入 sorted() —— ruff PLW0108 要求去掉冗余 lambda
)
@settings(max_examples=80, deadline=None)
def test_excluding_all_decline_indices_suppresses_finding(series: list[float]) -> None:
    """把递减序列全部排除 → 无 monotonic_decline（排除真起作用，不空转）。

    注：sorted() 默认升序；detect_chapter_drift 检测递减。全排除后必无 finding。
    """
    if len(series) < 3:
        return
    excl_all = set(range(len(series)))
    findings = detect_chapter_drift(series, dim="情感落地", exclude_indices=excl_all)
    assert all(f.kind != "monotonic_decline" for f in findings)


@given(scores=scores_st.filter(lambda xs: len(xs) >= 2))
@settings(max_examples=200, deadline=None)
def test_volume_decline_iff_last_below_second_to_last(scores: list[float]) -> None:
    """volume_decline 当且仅当末卷 < 倒数第二卷触发（compute_drift.py:138）。"""
    findings = detect_volume_drift(scores)
    expected = scores[-1] < scores[-2]
    assert bool(findings) == expected


@given(
    scores=st.lists(
        st.floats(min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False),
        min_size=2,
        max_size=8,
    )
)
@settings(max_examples=120, deadline=None)
def test_volume_decline_at_most_one_finding(scores: list[float]) -> None:
    findings = detect_volume_drift(scores)
    assert len(findings) <= 1
    for f in findings:
        assert f.kind == "volume_decline" and f.dim == "overall"
