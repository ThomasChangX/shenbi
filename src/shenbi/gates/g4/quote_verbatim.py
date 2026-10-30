"""spec #82 T1 quote anchoring: verbatim quote-in-chapter checker.

Shared base with spec #83 T1 (POST/PRE 引句 verbatim 门) — built here first,
#83 reuses it (specs' 共基声明: 勿各造一份). The v4 张力拍 declaration carries
the chapter's closing sentence verbatim; the drafting gate replays the quote
against the chapter prose — quote presence, not temperature semantics (the
temperature judgment is the audit's blocking finding, per the spec).

Prose stripping reuses the canonical ``strip_narrative_body`` (single
construction site for the chapter-body 口径) — the naive BEGIN/END-only
strip misses real-corpus shapes (frontmatter headers, H2 PRE/POST sections,
orphan META-END markers).
"""

from __future__ import annotations

import re

from shenbi.gates.shared import strip_narrative_body

_QUOTE_RE = re.compile(r"[「「" "『]([^「」『』" "]{6,})[」」" "』]")
_META_BLOCK_RE = re.compile(r"<!--META-BEGIN-->.*?<!--META-END-->", re.DOTALL)
_META_SECTION_RE = re.compile(
    r"^## (?:PRE_WRITE_CHECK|POST_WRITE_SELF_CHECK).*?(?=^## |^# |<!--META|\Z)",
    re.DOTALL | re.M,
)


def strip_to_prose(chapter_text: str) -> str:
    """Canonical chapter-body 口径 (audit-T5/C2): strip_narrative_body."""
    return strip_narrative_body(chapter_text)


def quote_in_chapter(quote: str, chapter_text: str) -> bool:
    """Exact substring presence of *quote* in the chapter prose.

    Verbatim first; a newline-flattened fallback catches memo-wrapped quotes
    (flattening is comparison-only — it never mutates the prose source).
    """
    if not quote.strip():
        return False
    prose = strip_to_prose(chapter_text)
    if quote in prose:
        return True
    flattened = "".join(quote.split())
    return bool(flattened) and flattened in "".join(prose.split())


def extract_anchor_quotes(memo_text: str) -> list[tuple[str, str]]:
    """Extract (tier, quote) pairs from v4 张力拍 anchor lines.

    v4 form: ``章尾张力拍: [微|章|大]｜『<quote>』``.
    """
    out: list[tuple[str, str]] = []
    for m in re.finditer(
        r"^[-* ]*\*{0,2}章尾张力拍\*{0,2}[：:]\s*\[?(微|章|大)\]?\s*｜\s*『(.+?)』",
        memo_text,
        re.MULTILINE,
    ):
        out.append((m.group(1), m.group(2)))
    return out


def extract_meta_quotes(chapter_text: str, *, min_len: int = 6) -> list[str]:
    """Extract 「」/『』/""-quoted sentences (>= min_len) from META blocks only.

    The extraction seam for spec #83 T1 (POST/PRE 引句 verbatim 门): quotes
    living in the declarations must be replayed against the prose. Only the
    META regions (BEGIN..END blocks + H2 PRE/POST sections) are scanned —
    prose quotes are never collected (audit-T5/I2a: the naive
    raw-minus-prose replace is a no-op once META interleaves the prose).
    """
    regions: list[str] = []
    regions.extend(_META_BLOCK_RE.findall(chapter_text))
    regions.extend(_META_SECTION_RE.findall(chapter_text))
    meta_text = "\n".join(regions)
    return [m.group(1) for m in _QUOTE_RE.finditer(meta_text) if len(m.group(1)) >= min_len]
