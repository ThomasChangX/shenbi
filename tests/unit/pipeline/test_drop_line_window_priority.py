"""Spec #95 T4 (audit-T10 I1): unseen-first ordering of dropped lines."""

from __future__ import annotations

from shenbi.pipeline.chapter_loop import _prioritize_unseen_drop_lines

FEEDBACK = (
    "content_dropped:3行（去重后 3）——被丢行 verbatim 清单（原样保留于输出，作为基底行）：\n"
    "  | a | 1 |\n"
    "  | b | 2 |\n"
    "  | c | 3 |\n"
    "指令：以上行原样保留于输出（作为基底行），仅在其后追加本章新键行——\n"
    "不要重发整档，不要改写基底行。\n"
)


def test_unseen_lines_float_first() -> None:
    # 窗口面（prompt）只见 a 行——b/c 未见过须浮前（稳定序）
    prompt = "窗口内容 | a | 1 | 结束"
    out = _prioritize_unseen_drop_lines(FEEDBACK, prompt)
    b_idx, c_idx, a_idx = out.index("| b | 2 |"), out.index("| c | 3 |"), out.index("| a | 1 |\n")
    assert a_idx > b_idx and a_idx > c_idx  # 未见行(b,c)浮于已见行(a)前
    assert b_idx < c_idx  # 稳定：未见行保持原相对序
    assert "指令：" in out  # 指令/正例段不动


def test_all_seen_keeps_order() -> None:
    prompt = "| a | 1 |\n| b | 2 |\n| c | 3 |"
    out = _prioritize_unseen_drop_lines(FEEDBACK, prompt)
    assert out == FEEDBACK


def test_non_drop_feedback_passthrough() -> None:
    assert (
        _prioritize_unseen_drop_lines("G4.word_count: 差 26 字", "prompt")
        == "G4.word_count: 差 26 字"
    )


def test_ellipsis_disclosure_line_preserved_in_reorder() -> None:
    """Stage-8 r2 N1: reorder must KEEP the ellipsis overflow disclosure line."""
    fb = (
        "content_dropped:22行（去重后 22）——被丢行 verbatim 清单（原样保留于输出，作为基底行）：\n"
        "  | a | 1 |\n"
        "  ……（共 22 行，超出 20 行上限的部分以 live 文件为准）\n"
        "  | c | 3 |\n"
        "指令：以上行原样保留于输出（作为基底行）。\n"
    )
    out = _prioritize_unseen_drop_lines(fb, "窗口只见 | a | 1 |")
    assert "超出 20 行上限" in out  # 披露行保留
    assert out.index("| c | 3 |") < out.index("| a | 1 |")  # 未见行浮前
    assert out.index("| a | 1 |") < out.index("超出 20 行上限")  # …… 仍置尾
