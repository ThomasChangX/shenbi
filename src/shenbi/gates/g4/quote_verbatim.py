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

QUOTE_RE = re.compile('[『“"]([^『“”"]+)[』”"]')
# spec #83 T1: nested-aware 「」 extraction (r4 钉死嵌套感知式；不用最长匹配——
# 按行 greedy 会把双引句行〔ch1:234/235、ch6:298「场景1「…」／场景2「…」」形〕
# 合并成跨 / 假引句)。『』“” 保留单层族（语料无该族嵌套）。
NESTED_QUOTE_RE = re.compile("「((?:[^「」]|「[^「」]*」)*)」")
_META_BLOCK_RE = re.compile(r"<!--META-BEGIN-->.*?<!--META-END-->", re.DOTALL)
_META_SECTION_RE = re.compile(
    r"^## (?:PRE_WRITE_CHECK|POST_WRITE_SELF_CHECK).*?(?=^## |^# |<!--META|\Z)",
    re.DOTALL | re.M,
)
# 位置法排尾注（r5 定稿）：引句起点落在全角括号区间（…）内即弃——尾注
# 〔（含张力词「…」）（三点同型…）〕构造上不可能逐字命中；用位置法而非文本
# 剥除，防主引句内含括号被误改写。
PAREN_SPAN_RE = re.compile(r"（[^（）]*）")


def meta_regions(chapter_text: str) -> list[tuple[str, int, int]]:
    """(region_text, start, end) —— META 块 + PRE/POST H2 节，带绝对位置。"""
    regions: list[tuple[str, int, int]] = []
    for m in _META_BLOCK_RE.finditer(chapter_text):
        regions.append((m.group(0), m.start(), m.end()))
    for m in _META_SECTION_RE.finditer(chapter_text):
        regions.append((m.group(0), m.start(), m.end()))
    return regions


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

    spec #83 T1 定稿形: 嵌套感知「」提取（外层捕获含内层「」全文）＋全角括号
    尾注区间位置排除＋span 级去重（『』“” 单层命中落在嵌套 span 内则弃——
    ch31「…『制度』…」形，防内层片段重复入面）。
    """
    out: list[str] = []
    for region, _rs, _re in meta_regions(chapter_text):
        paren_spans = [m.span() for m in PAREN_SPAN_RE.finditer(region)]
        nested_spans: list[tuple[int, int]] = []
        for m in NESTED_QUOTE_RE.finditer(region):
            nested_spans.append(m.span())
            if len(m.group(1)) < min_len:
                continue
            if any(ps <= m.start() < pe for ps, pe in paren_spans):
                continue
            out.append(m.group(1))
        for m in QUOTE_RE.finditer(region):
            if any(ns <= m.start() < ne for ns, ne in nested_spans):
                continue  # span 级去重（M16）
            if len(m.group(1)) < min_len:
                continue
            if any(ps <= m.start() < pe for ps, pe in paren_spans):
                continue
            out.append(m.group(1))
    return out
