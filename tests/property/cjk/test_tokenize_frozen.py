from __future__ import annotations

import jieba
import jieba.posseg as pseg
from hypothesis import given, settings
from hypothesis import strategies as st

from shenbi.text.cjk import tokenize

# Isolated jieba instances: immune to global-dict pollution from cjk.tokenize()
# (which calls jieba.add_word for domain terms). We verify factory behavior.
_t = jieba.Tokenizer()
_t.check_initialized()
_pt = pseg.POSTokenizer(_t)


def _isolate(text: str) -> list[tuple[str, str]]:
    """Tokenize with a clean jieba instance (no add_word pollution)."""
    return [(w.word, w.flag) for w in _pt.lcut(text)]


# Frozen on jieba==0.42.1 (pyproject.toml pinned). Upgrade changes tokens -> fail.
_FROZEN: list[tuple[str, list[str], list[str]]] = [
    (
        "他在黑暗中看到了一束光明",
        ["他", "在", "黑暗", "中", "看到", "了", "一束", "光明"],
        ["r", "p", "z", "f", "v", "ul", "m", "n"],
    ),
    (
        "主角缓缓地走向了那扇古老的大门",
        ["主角", "缓缓", "地", "走向", "了", "那", "扇", "古老", "的", "大门"],
        ["n", "d", "uv", "v", "ul", "r", "q", "nr", "uj", "n"],
    ),
    (
        "革命运动在这个时代悄然兴起",
        ["革命", "运动", "在", "这个", "时代", "悄然兴起"],
        ["vn", "vn", "p", "r", "n", "l"],
    ),
    (
        "筑基期的修炼需要极大的耐心",
        ["筑", "基期", "的", "修炼", "需要", "极大", "的", "耐心"],
        ["v", "n", "uj", "v", "v", "a", "uj", "a"],
    ),
]


def test_frozen_baseline_matches_jieba_0_42_1() -> None:
    """Frozen token baseline (spec M2). Uses isolated tokenizer to avoid global pollution."""
    for text, exp_words, _exp_pos in _FROZEN:
        toks = _isolate(text)
        assert [w for w, _ in toks] == exp_words, text


def test_frozen_pos_tags_match() -> None:
    """POS tags also frozen (pseg output stable on isolated tokenizer)."""
    for text, _words, exp_pos in _FROZEN:
        toks = _isolate(text)
        assert [p for _, p in toks] == exp_pos, text


def test_tokenize_preserves_chars_concat() -> None:
    """Invariant: tok2word concatenation == original text."""
    for text, _w, _p in _FROZEN:
        assert "".join(t.word for t in tokenize(text)) == text


cjk_sample = st.text(
    alphabet=st.sampled_from(list("主角缓缓走向古老大门光明黑暗耐心修炼需要")),
    min_size=0,
    max_size=30,
)


@given(cjk_sample)
@settings(max_examples=80, deadline=None)
def test_tokenize_is_deterministic(text: str) -> None:
    """Determinism invariant: same input tokenizes identically twice."""
    a = tokenize(text)
    b = tokenize(text)
    assert [t.word for t in a] == [t.word for t in b]
    assert [t.pos for t in a] == [t.pos for t in b]


@given(cjk_sample)
@settings(max_examples=60, deadline=None)
def test_tokenize_concat_equals_input(text: str) -> None:
    if not text.strip():
        return
    assert "".join(t.word for t in tokenize(text)) == text
