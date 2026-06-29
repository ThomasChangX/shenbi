from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from shenbi.text.cjk import tokenize

# 实测于 jieba==0.42.1（pyproject.toml:10 已 pin）。升级改变分词 → 失败 → 审查。
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
    """冻结分词基线（spec M2）。token 列表来自 jieba==0.42.1 实测，非 t1==t2 同义反复。"""
    for text, exp_words, _exp_pos in _FROZEN:
        toks = tokenize(text)
        assert [t.word for t in toks] == exp_words, text


def test_frozen_pos_tags_match() -> None:
    """词性标注也冻结（pseg 输出稳定）。"""
    for text, _words, exp_pos in _FROZEN:
        toks = tokenize(text)
        assert [t.pos for t in toks] == exp_pos, text


def test_tokenize_preserves_chars_concat() -> None:
    """不变量：tok2word 拼接 == 原文（分词不丢/不增字符）。"""
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
    """确定性不变量：同一输入两次分词完全一致（冻结版本下稳定）。"""
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
