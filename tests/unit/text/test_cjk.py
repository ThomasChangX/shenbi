from __future__ import annotations

from shenbi.text.cjk import TermHit, find_terms


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
