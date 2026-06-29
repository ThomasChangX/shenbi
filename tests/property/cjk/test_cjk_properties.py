from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from shenbi.text.cjk import count_punctuation, count_words, find_terms

cjk_text = st.text(
    alphabet=st.sampled_from(list("你好世界革命暴动和平发展——……。！？，level123")),
    min_size=0,
    max_size=50,
)


@given(cjk_text)
def test_find_terms_substring_found(text: str) -> None:
    if len(text) >= 2:
        term = text[:2]
        assert len(find_terms(text, [term])) >= 1


@given(cjk_text)
def test_punctuation_matches_all_tokens(text: str) -> None:
    counts = count_punctuation(text)
    assert counts["破折号"] == text.count("——") + text.count("──")
    assert counts["省略号"] == text.count("……") + text.count("。。。")


@given(cjk_text)
def test_mixed_ge_cjk_only(text: str) -> None:
    assert count_words(text, "mixed") >= count_words(text, "cjk_only")


@given(st.text(min_size=0, max_size=100))
def test_count_words_non_negative(text: str) -> None:
    assert count_words(text, "cjk_only") >= 0
    assert count_words(text, "mixed") >= 0
