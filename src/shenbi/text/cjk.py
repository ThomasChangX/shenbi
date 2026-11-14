"""Centralized CJK text operations (spec pillar 3)."""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass


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
    total = sum(1 for c in text if not c.isspace())
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


QUOTE_PAIR = {"”": "“", "’": "‘", "」": "「", "』": "『"}
# 迁自 skill_utils/style_learning/compute_stats.py（spec #71 单信源化：
# G4.cd 与 compute_stats 同源切分；compute_stats re-export 保 API 兼容）。


def segment_sentences(text: str) -> list[tuple[str, int]]:
    r"""Segment Chinese text into sentences. Returns list of (sentence_text, char_count).

    F628: ； terminates sentences (unified with SENT_ENDS).
    F668: sentence-final punctuation inside open quotes does not split;
    \n splits unconditionally (escape hatch for unterminated quotes).
    """
    sentences: list[tuple[str, int]] = []
    current: list[str] = []
    quote_stack: list[str] = []
    ascii_quote_open = False

    def flush() -> None:
        sent = "".join(current).strip()
        if sent:
            char_count = len(sent.replace("\n", "").replace(" ", ""))
            if char_count > 0:
                sentences.append((sent, char_count))
        current.clear()

    for ch in text:
        current.append(ch)
        quote_closed = False
        if ch in QUOTE_PAIR.values():
            quote_stack.append(ch)
        elif ch in QUOTE_PAIR:
            if quote_stack and quote_stack[-1] == QUOTE_PAIR[ch]:
                quote_stack.pop()
                quote_closed = True
        elif ch == '"':
            if ascii_quote_open:
                quote_closed = True
            ascii_quote_open = not ascii_quote_open
        in_quote = bool(quote_stack) or ascii_quote_open
        if ch == "\n" or (ch in "。！？；" and not in_quote):
            if ch == "\n":
                # reset quote state so an unterminated quote on one line cannot
                # suppress splitting on later lines (Copilot review, PR #100)
                quote_stack.clear()
                ascii_quote_open = False
            flush()
        elif (
            quote_closed
            and not quote_stack
            and not ascii_quote_open
            and len(current) >= 2
            and current[-2] in "。！？；"
        ):
            # F668: sentence-final punct right before the OUTERMOST closing quote
            # ends the sentence (nested inner closes do not split the outer one)
            flush()
    if current:
        flush()
    return sentences
