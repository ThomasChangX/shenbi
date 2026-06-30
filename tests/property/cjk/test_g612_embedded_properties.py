from __future__ import annotations

import re

from hypothesis import given, settings
from hypothesis import strategies as st

from shenbi.text.cjk import find_terms

cjk_pad = st.text(
    alphabet=st.sampled_from(list("在这个时代悄然兴起运动发展和平")), min_size=1, max_size=6
)
term_st = st.sampled_from(["革命", "暴动", "起义", "敏感词"])


@given(pre=cjk_pad, post=cjk_pad, term=term_st)
@settings(max_examples=200, deadline=None)
def test_find_terms_detects_embedded_cjk(pre: str, term: str, post: str) -> None:
    r"""G6.12 内嵌必检出：敏感词被 CJK 包夹时 find_terms 必命中（substring 语义）。

    旧 g6.py 正则 [^\w] 边界对纯 CJK 文本失效（CJK 全是 \w），内嵌不检出；
    find_terms 用精确子串，正确。
    """
    text = pre + term + post
    hits = find_terms(text, [term])
    assert len(hits) >= 1
    assert hits[0].term == term


@given(term=term_st)
@settings(max_examples=20, deadline=None)
def test_old_word_boundary_regex_fails_on_embedded(term: str) -> None:
    r"""回归对照：g6.py 旧 `[^\w]` 边界正则在纯 CJK 内嵌场景**不命中**——
    记录 bug 行为，证明 find_terms 是正确替代（接线在支柱二）。
    """
    text = "这个时代" + term + "运动开始"
    old = re.search(rf"(?:^|[^\w]){re.escape(term)}(?:$|[^\w])", text)
    assert old is None  # 旧正则失效（确认 bug 存在）
    assert len(find_terms(text, [term])) == 1  # find_terms 正确


@given(pre=cjk_pad, post=cjk_pad, term=term_st)
@settings(max_examples=100, deadline=None)
def test_find_terms_hit_position_correct(pre: str, term: str, post: str) -> None:
    text = pre + term + post
    hits = find_terms(text, [term])
    h = hits[0]
    assert h.start == len(pre)
    assert h.end == len(pre) + len(term)
    assert text[h.start : h.end] == term
