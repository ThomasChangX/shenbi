from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from shenbi.text.cjk import PUNCTUATION_TOKENS, count_punctuation

# 所有标点 token 字符 + 普通 CJK，覆盖边界（token 在首/尾/中间/重叠）
_PUNCT_CHARS = "".join(t for toks in PUNCTUATION_TOKENS.values() for t in toks)
punct_text = st.text(
    alphabet=st.sampled_from(list(_PUNCT_CHARS + "你好世界正文内容level123 空格")),
    min_size=0,
    max_size=80,
)


@given(punct_text)
@settings(max_examples=200, deadline=None)
def test_each_punct_count_matches_text_count(text: str) -> None:
    """整 token 计数：counts[name] == sum(text.count(token) for token in tokens)。

    对照 bug：compute_stats.compute_punctuation 对多字符标点（——/……）per-char
    迭代导致重复计数；cjk.count_punctuation 用整 token 正确。
    """
    counts = count_punctuation(text)
    for name, tokens in PUNCTUATION_TOKENS.items():
        assert counts[name] == sum(text.count(token) for token in tokens), name


@given(punct_text)
@settings(max_examples=200, deadline=None)
def test_dash_counted_once_not_per_char(text: str) -> None:
    """破折号 ——（2 字符）整体计数，绝不 per-char 翻倍。

    '你好——世界'：text.count('——')==1（不是 text.count('—')*迭代==4）。
    """
    assert count_punctuation(text)["破折号"] == text.count("——") + text.count("──")


@given(punct_text)
@settings(max_examples=100, deadline=None)
def test_all_counts_non_negative(text: str) -> None:
    counts = count_punctuation(text)
    assert all(v >= 0 for v in counts.values())
