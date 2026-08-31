"""jieba global-dictionary isolation (spec #32 F615).

Old bug: ``tokenize`` called ``jieba.add_word``, mutating the *global*
``jieba.dt`` dictionary. Domain terms leaked across calls/tests/any other
jieba consumer in the process. The fix: a module-level private
``jieba.Tokenizer`` instance; the global dict must never be touched.

NOTE: pytest-randomly shuffles test order (also within this file), so each
test uses a unique random domain term and asserts the precondition
(term absent from the global dict) before exercising ``tokenize`` — otherwise
pollution from a same-process sibling test masks the leak.
"""

from __future__ import annotations

from uuid import uuid4

import jieba

from shenbi.text.cjk import tokenize


def _fresh_term() -> str:
    """A made-up CJK domain term that is not in any dictionary."""
    return f"玄天九转诀{uuid4().hex[:6]}"


def test_tokenize_does_not_pollute_global_dict() -> None:
    """After tokenize with a domain dict, jieba.dt.FREQ must be unchanged."""
    term = _fresh_term()
    jieba.dt.initialize()  # ensure a comparable initialized state
    assert term not in jieba.dt.FREQ  # precondition: term is genuinely new
    before = set(jieba.dt.FREQ)
    tokenize(f"他开始修炼{term}功法", domain_dict=[term])
    after = set(jieba.dt.FREQ)
    assert not (after - before), f"global dict polluted with: {after - before}"


def test_domain_term_effective_in_isolated_tokenizer() -> None:
    """The module-level isolated tokenizer must honor domain_dict: the term
    survives as a single token (not split).
    """
    term = _fresh_term()
    tokens = tokenize(f"他开始修炼{term}功法", domain_dict=[term])
    assert term in [t.word for t in tokens]
    # ... while the global dict still does not know the term
    assert term not in jieba.dt.FREQ


def test_isolated_tokenizer_still_tokenizes_plain_text() -> None:
    tokens = tokenize("他是一个高手")
    assert "".join(t.word for t in tokens) == "他是一个高手"
    assert all(t.pos for t in tokens)  # posseg tags still present
