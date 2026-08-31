"""Paired-quote counting (spec #32 F601): quotes with content must count.

Old bug: the 引号 token was the two-char literal `""`, matching only EMPTY
quote pairs — real quoted dialogue (“你好”) was counted as 0 everywhere.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from shenbi.text.cjk import count_quote_pairs, dialogue_char_ratio

FIXTURES = Path(__file__).resolve().parents[3] / "fixtures"


@pytest.mark.unit
def test_cjk_curly_double_quote_with_content_counts() -> None:
    assert count_quote_pairs("他说“你好”然后离开") == 1


@pytest.mark.unit
def test_cjk_corner_bracket_with_content_counts() -> None:
    assert count_quote_pairs("他说「带内容」然后离开") == 1


@pytest.mark.unit
def test_ascii_double_quote_with_content_counts() -> None:
    assert count_quote_pairs('他说"x"然后离开') == 1


@pytest.mark.unit
def test_curly_single_quote_with_content_counts() -> None:
    assert count_quote_pairs("他小声说‘好的’") == 1


@pytest.mark.unit
def test_empty_quote_pair_still_counts() -> None:
    assert count_quote_pairs("空引号“”占位") == 1
    assert count_quote_pairs("空括号「」占位") == 1


@pytest.mark.unit
def test_multiple_mixed_pairs() -> None:
    text = '“第一句”，第二段“第二句”，加上「第三句」和 "fourth"'
    assert count_quote_pairs(text) == 4


@pytest.mark.unit
def test_no_quotes_zero() -> None:
    assert count_quote_pairs("没有任何引号的纯文本。") == 0
    assert count_quote_pairs("") == 0


@pytest.mark.unit
def test_unmatched_open_quote_not_counted() -> None:
    assert count_quote_pairs("只有开引号“没有关闭") == 0


@pytest.mark.unit
def test_nested_outer_pair_counts_once() -> None:
    # 「外层“内层”外层」 — inner quotes are content of the outer pair
    assert count_quote_pairs("「外层“内层”外层」") == 1


# --- dialogue_char_ratio ---------------------------------------------------


@pytest.mark.unit
def test_ratio_positive_with_quotes() -> None:
    assert dialogue_char_ratio("他说“你好呀朋友”") > 0


@pytest.mark.unit
def test_ratio_zero_without_quotes() -> None:
    assert dialogue_char_ratio("纯叙述文本没有对白。") == 0.0


@pytest.mark.unit
def test_ratio_between_zero_and_one() -> None:
    text = "叙述部分较长，他说“对白”。更多叙述。"
    assert 0.0 < dialogue_char_ratio(text) < 1.0


@pytest.mark.unit
def test_ratio_empty_text_zero() -> None:
    assert dialogue_char_ratio("") == 0.0


# --- snapshot tests over real fixtures (spec #32 AC2) -----------------------


@pytest.mark.unit
def test_snapshot_curly_quote_fixture_has_dialogue() -> None:
    """snapshot-dir chapters use CJK curly quotes (“”) — must count > 0.

    Interval locked at measured value 0.126 ± 5pp (spec #32 AC2).
    """
    text = (FIXTURES / "snapshot-dir" / "chapter-005-20260715T232231.md").read_text(
        encoding="utf-8"
    )
    assert count_quote_pairs(text) > 700
    assert 0.076 < dialogue_char_ratio(text) < 0.176


@pytest.mark.unit
def test_ascii_quote_fixture_has_dialogue() -> None:
    """chapter-*-draft.md uses ASCII straight quotes — must count > 0.

    Interval locked at measured value 0.144 ± 5pp (spec #32 AC2).
    """
    text = (FIXTURES / "chapter-7-draft.md").read_text(encoding="utf-8")
    assert count_quote_pairs(text) > 30
    assert 0.094 < dialogue_char_ratio(text) < 0.194
