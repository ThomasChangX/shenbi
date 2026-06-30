from __future__ import annotations

from shenbi.text.cjk import find_terms


def test_sensitive_word_embedded_in_chinese() -> None:
    text = "他在这个时代发起了革命运动"
    hits = find_terms(text, ["革命"])
    assert len(hits) == 1
    assert hits[0].term == "革命"


def test_term_at_boundary() -> None:
    assert len(find_terms("革命开始了", ["革命"])) == 1
    assert len(find_terms("开始了革命", ["革命"])) == 1


def test_multiple_terms() -> None:
    hits = find_terms("第一场革命和第二场暴动", ["革命", "暴动"])
    assert {h.term for h in hits} == {"革命", "暴动"}


def test_not_found() -> None:
    assert find_terms("和平发展", ["革命"]) == []


def test_empty_text() -> None:
    assert find_terms("", ["革命"]) == []


def test_positions() -> None:
    hits = find_terms("这是革命的故事", ["革命"])
    assert hits[0].start == 2
    assert hits[0].end == 4


def test_substring_match_semantics() -> None:
    assert len(find_terms("超级升级", ["升级"])) == 1
    assert len(find_terms("超级高手", ["升级"])) == 0


from shenbi.text.cjk import Token, count_punctuation, count_words, tokenize


def test_dash_counted_once() -> None:
    assert count_punctuation("你好——世界")["破折号"] == 1


def test_ellipsis_counted_once() -> None:
    assert count_punctuation("你好……世界")["省略号"] == 1


def test_single_char_punct() -> None:
    c = count_punctuation("你好。世界！")
    assert c["句号"] == 1
    assert c["感叹号"] == 1


def test_no_punctuation() -> None:
    assert all(v == 0 for v in count_punctuation("纯文本").values())


def test_multiple_dashes() -> None:
    assert count_punctuation("第一——第二——第三")["破折号"] == 2


def test_cjk_only_pure_chinese() -> None:
    assert count_words("这是一段中文文本", "cjk_only") == 8


def test_cjk_only_drops_english() -> None:
    assert count_words("这是level提升", "cjk_only") == 4


def test_mixed_includes_english() -> None:
    assert count_words("这是level提升", "mixed") >= 5


def test_mixed_ge_cjk_only() -> None:
    text = "这是level提升123"
    assert count_words(text, "mixed") >= count_words(text, "cjk_only")


def test_empty_words() -> None:
    assert count_words("", "cjk_only") == 0
    assert count_words("", "mixed") == 0


def test_numbers_in_mixed() -> None:
    assert count_words("第1章", "mixed") >= 2


def test_tokenize_returns_tokens() -> None:
    tokens = tokenize("他是一个高手")
    assert len(tokens) > 0
    assert all(isinstance(t, Token) for t in tokens)


def test_tokenize_preserves_chars() -> None:
    text = "他是一个高手"
    assert "".join(t.word for t in tokenize(text)) == text


def test_domain_dict_prevents_split() -> None:
    tokens = tokenize("他开始了筑基期修炼", domain_dict=["筑基期"])
    assert "筑基期" in [t.word for t in tokens]


def test_tokenize_empty() -> None:
    assert tokenize("") == []


def test_tokenize_frozen_baseline() -> None:
    """Frozen token baseline from jieba 0.42.1. Guards upgrade drift."""
    text = "他在黑暗中看到了一束光明"
    words = [t.word for t in tokenize(text)]
    assert words == ["他", "在", "黑暗", "中", "看到", "了", "一束", "光明"]
