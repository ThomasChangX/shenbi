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
    "引号": ['""', "''", "「」", "『』"],
}


def count_punctuation(text: str) -> dict[str, int]:
    """Count punctuation by whole tokens, not per-char.

    Bug fix: old code used sum(text.count(c) for c in chars), iterating
    each char of multi-char marks. A single -- (2 chars) was counted as 4.
    """
    return {
        name: sum(text.count(token) for token in tokens)
        for name, tokens in PUNCTUATION_TOKENS.items()
    }


_CJK_RE = re.compile(r"[\u4e00-\u9fff]")
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


_jieba_ready = False


def tokenize(text: str, domain_dict: Iterable[str] | None = None) -> list[Token]:
    """Tokenize with jieba. Domain terms registered to prevent splitting."""
    global _jieba_ready  # noqa: PLW0603
    if not _jieba_ready:
        jieba.initialize()
        _jieba_ready = True
    if domain_dict:
        for term in domain_dict:
            jieba.add_word(term)
    return [Token(word=w, pos=f) for w, f in pseg.cut(text) if w.strip()]
