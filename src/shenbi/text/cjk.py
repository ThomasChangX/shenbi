"""Centralized CJK text operations (spec pillar 3)."""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal

import jieba
import jieba.posseg as pseg


@dataclass(frozen=True)
class TermHit:
    """A single term match found in text."""

    term: str
    start: int
    end: int


def find_terms(text: str, terms: Iterable[str]) -> list[TermHit]:
    r"""Find terms as exact substrings. Replaces broken \w-anchored regex.

    Semantics: exact substring match. For pure CJK text every char position
    is a valid boundary. False-positive handling deferred to integration.
    """
    hits: list[TermHit] = []
    for term in terms:
        if not term:
            continue
        start = 0
        while True:
            idx = text.find(term, start)
            if idx == -1:
                break
            hits.append(TermHit(term=term, start=idx, end=idx + len(term)))
            start = idx + 1
    hits.sort(key=lambda h: h.start)
    return hits


PUNCTUATION_TOKENS: dict[str, list[str]] = {
    "句号": ["。"],
    "逗号": ["，"],
    "感叹号": ["！", "!"],
    "问号": ["？", "?"],
    "破折号": ["——", "──"],
    "省略号": ["……", "。。。"],
    "顿号": ["、"],
    "分号": ["；"],
    "冒号": ["：", ":"],
}
# 引号 bucket is NOT in PUNCTUATION_TOKENS: it is pair-based (spec #32 F601).
# The old two-char literals ('""', '「」', ...) only matched EMPTY pairs, so
# any quote with content counted 0. Pair counting lives below.

# Spec #32 F652: single exclusion set for TTR-style char filtering.
# Includes CJK curly quotes “”‘’ (previously missing downstream).
TTR_EXCLUDED_CHARS = "。，！？；：''“”‘’「」『』（）——……、\n"


_PAIR_RE = re.compile(r"“[^“”]*”|‘[^‘’]*’|「[^「」]*」|『[^『』]*』|\"[^\"]*\"")


def find_quote_spans(text: str) -> list[tuple[int, int]]:
    """Return (start, end) spans of paired quotes, including the quote marks.

    Inner quotes nested inside an outer pair are content of the outer span
    (non-greedy per-form char classes). Unmatched open quotes yield nothing.
    Empty pairs (“”) are valid spans.
    """
    return [(m.start(), m.end()) for m in _PAIR_RE.finditer(text)]


def count_quote_pairs(text: str) -> int:
    """Count paired quotes (引语数), content-bearing or empty (spec #32 F601)."""
    return len(find_quote_spans(text))


def dialogue_char_count(text: str) -> int:
    """Characters inside paired quotes, including the quote marks themselves."""
    return sum(end - start for start, end in find_quote_spans(text))


def dialogue_char_ratio(text: str) -> float:
    """dialogue_char_count / non-whitespace total chars; 0.0 when empty."""
    total = len([c for c in text if not c.isspace()])
    if total == 0:
        return 0.0
    return dialogue_char_count(text) / total


def count_punctuation(text: str) -> dict[str, int]:
    """Count punctuation by whole tokens, not per-char.

    Bug fix: old code used sum(text.count(c) for c in chars), iterating
    each char of multi-char marks. A single -- (2 chars) was counted as 4.

    Note: half-width and full-width variants in the same bucket (e.g. ！ and !)
    are counted separately and summed. A string "！!" yields 2 for 感叹号.

    引号 counts PAIRS (see count_quote_pairs), not per-char occurrences.
    """
    counts = {
        name: sum(text.count(token) for token in tokens)
        for name, tokens in PUNCTUATION_TOKENS.items()
    }
    counts["引号"] = count_quote_pairs(text)
    return counts


_CJK_RE = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff]")
_NON_CJK_WORD_RE = re.compile(r"[a-zA-Z0-9]+")


def count_words(text: str, mode: Literal["cjk_only", "mixed"]) -> int:
    """Count words: cjk_only = CJK chars only; mixed = CJK + Latin words + digits."""
    cjk = len(_CJK_RE.findall(text))
    if mode == "cjk_only":
        return cjk
    return cjk + len(_NON_CJK_WORD_RE.findall(text))


@dataclass(frozen=True)
class Token:
    """A tokenized word with part-of-speech tag."""

    word: str
    pos: str


def tokenize(text: str, domain_dict: Iterable[str] | None = None) -> list[Token]:
    """Tokenize with jieba. Domain terms registered to prevent splitting.

    Note: jieba.add_word mutates the global jieba dictionary. Domain terms
    persist across calls. This is a known limitation for the current skeleton;
    the integration pillar should use jieba.Tokenizer instances for isolation.
    """
    jieba.initialize()  # idempotent: jieba skips re-init if already loaded
    if domain_dict:
        for term in domain_dict:
            jieba.add_word(term)
    return [Token(word=w, pos=f) for w, f in pseg.cut(text) if w.strip()]
