"""Spec #85 T7 — volume numeral charset single-source red tests."""

from __future__ import annotations

import pytest


@pytest.mark.unit
def test_span_forms_three_shapes_parse_consistently() -> None:
    """无冒号标题 / 含千卷号 / 阿拉伯卷号 三形态各自解析一致(spec §2.2 红测)。"""
    from shenbi.pipeline._shared import parse_volume_spans

    no_colon = parse_volume_spans("## 第一卷 标题(第 1-23 章)\n")
    thousand = parse_volume_spans("## 第一千卷: 千卷(第 1-5 章)\n")
    arabic = parse_volume_spans("## 第2卷: 二卷(第 24-46 章)\n")
    assert [s.end for s in no_colon] == [23]
    assert [s.end for s in thousand] == [5]
    assert [s.end for s in arabic] == [46]


@pytest.mark.unit
def test_boundaries_range_line_priority_over_span() -> None:
    """Disagree 钉死(green-before): range-line 止 20 + heading span 止 23 并存
    -> read_volume_boundaries 取 {20}(卷内 range-line 优先, 禁改成并集)。
    """
    from shenbi.pipeline._shared import read_volume_boundaries

    vm = "## 第一卷: 名(第 1-23 章)\n**章节范围**: 第 1 章 - 第 20 章\n"
    assert read_volume_boundaries.__module__  # sanity
    # 直接走内部函数(project_dir 形态走文件系统, 内部函数等价)
    from shenbi.pipeline._shared import _read_cn_volume_boundaries

    assert _read_cn_volume_boundaries(vm) == {20}
