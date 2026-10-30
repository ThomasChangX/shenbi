"""spec #82 T1 quote anchoring: verbatim quote-in-chapter checker.

Shared base with spec #83 T1 (POST/PRE 引句 verbatim 门) — built here first,
#83 reuses it (specs' 共基声明: 勿各造一份). The 张力拍 declaration line in a
v4 memo carries the chapter's closing sentence verbatim
(``章尾张力拍: 大｜『<章尾句原文引句>』``); the drafting gate replays the quote
against the chapter prose — quote presence, not temperature semantics
(the temperature judgment is the audit's blocking finding, per the spec).
"""

from __future__ import annotations

import re

_META_BLOCK_RE = re.compile(r"<!--META-BEGIN-->.*?<!--META-END-->", re.DOTALL)
_META_LINE_RE = re.compile(r"<!--META[^>]*-->")
_SCENE_SEP_RE = re.compile(r"<!--SCENE-->")


def strip_to_prose(chapter_text: str) -> str:
    """Strip META blocks and scene separators, keep the prose body."""
    text = _META_BLOCK_RE.sub("", chapter_text)
    text = _META_LINE_RE.sub("", text)  # stray single META markers
    return _SCENE_SEP_RE.sub("", text)


def quote_in_chapter(quote: str, chapter_text: str) -> bool:
    """Exact substring presence of *quote* in the chapter prose.

    The quote is compared verbatim after stripping whitespace at both ends
    of each line-joined form (the memo may wrap the quote across lines).
    """
    if not quote.strip():
        return False
    prose = strip_to_prose(chapter_text)
    if quote in prose:
        return True
    # newline-tolerant form: memo-wrapped quotes vs single-line prose
    flattened = "".join(quote.split())
    return bool(flattened) and flattened in "".join(prose.split())


def extract_anchor_quotes(memo_text: str) -> list[tuple[str, str]]:
    """Extract (tier, quote) pairs from v4 张力拍 anchor lines.

    v4 form: ``章尾张力拍: [微|章|大]｜『<quote>』`` (＋形态 legacy v3 tail is
    tolerated after the quote).
    """
    out: list[tuple[str, str]] = []
    for m in re.finditer(
        r"^[-* ]*\*{0,2}章尾张力拍\*{0,2}[：:]\s*\[?(微|章|大)\]?\s*｜\s*『(.+?)』",
        memo_text,
        re.MULTILINE,
    ):
        out.append((m.group(1), m.group(2)))
    return out
