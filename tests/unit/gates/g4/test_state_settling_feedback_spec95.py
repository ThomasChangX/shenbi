"""Spec #95 T4: three-part content_dropped feedback — verbatim/action/exemplar."""

from __future__ import annotations

from shenbi.gates.g4.state_settling import _format_drops


def test_three_part_template_shape() -> None:
    out = _format_drops(["| a | 1 |", "| b | 2 |"], samples=3)
    assert len(out) == 1
    text = out[0]
    assert text.startswith("content_dropped:2行")  # 前缀 token 保留（消费面 sweep 已核）
    assert "  | a | 1 |" in text and "  | b | 2 |" in text  # verbatim 全行
    assert "原样保留于输出（作为基底行）" in text  # 操作指令段
    assert "正例" in text and "`| c | 3 |`" in text  # 最小正例段


def test_dedup_and_cap() -> None:
    lines = [f"| k{i} | {i} |" for i in range(30)]
    dup = lines + lines[:5]
    text = _format_drops(dup, samples=3)[0]
    assert "去重后 30" in text  # 35 → 30
    assert text.count("| k0 | 0 |") == 1  # 去重
    assert "……（共 30 行，超出 20 行上限" in text  # cap=20 披露
    for i in range(20):
        assert f"| k{i} | {i} |" in text  # 前 20 行全示


def test_empty_missing_stays_empty() -> None:
    assert _format_drops([], samples=3) == []
