"""Spec #95 T4: three-part content_dropped feedback — verbatim/action/exemplar."""

from __future__ import annotations

from shenbi.gates.g4.state_settling import _format_drops


def test_three_part_template_shape() -> None:
    out = _format_drops(["| a | 1 |", "| b | 2 |"], samples=3, quote_example=True)
    assert len(out) == 1
    text = out[0]
    assert text.startswith("content_dropped:2行")  # 前缀 token 保留（消费面 sweep 已核）
    assert "  | a | 1 |" in text and "  | b | 2 |" in text  # verbatim 全行
    assert "原样保留于输出（作为基底行）" in text  # 操作指令段
    assert "正例" in text and "`| c | 3 |`" in text  # 最小正例段
    assert "引语行正例" in text and "自陈补全（第N章原句）" in text  # spec #99 ③ 引语双行正例


def test_quote_example_gated_to_matrix_face() -> None:
    """audit-T4 I-2: hooks face (default quote_example=False) must NOT carry the
    matrix-only quote dual-line example.
    """
    hooks_out = _format_drops(["| a | 1 |"], samples=1)[0]
    assert "引语行正例" not in hooks_out and "自陈补全" not in hooks_out
    matrix_out = _format_drops(["| a | 1 |"], samples=1, quote_example=True)[0]
    assert "引语行正例" in matrix_out and "本章自己的" in matrix_out


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
