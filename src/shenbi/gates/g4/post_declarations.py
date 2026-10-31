"""spec #83 T1: POST 声明引句 verbatim 门判定器（声明↔正文对账）。

执法面＝POST「金句位」＋「章尾张力（G4.cd 口径）」两行（r5 全语料回放
36 章 68 行，`- [ ]`/`- [x]` 两态均收；ch25 变体行〔无 G4.cd 口径标签〕
不入面）。两臂判定（r5 定稿）：逐字臂（quote_in_chapter 共基）缺席 →
子句臂（标点族切分与归一同源一次完成，声明每子句须等值出现在剥后正文
子句集）：任一子句缺席 → FAIL（修复者 drafting 改声明一行）；子句全在
→ WARN（标点/复合变体，交 G3.4 评审）。微粒钩/PRE 面/无引号裸句张力
声明不入执法面（spec §1 裁定——G3.4 兜底）。铁律 L-C：只做结构化可
判定的引句存在性，不做语义级判定。
"""

from __future__ import annotations

import re

from shenbi.gates.g4.quote_verbatim import (
    NESTED_QUOTE_RE,
    PAREN_SPAN_RE,
    QUOTE_RE,
    quote_in_chapter,
)
from shenbi.gates.shared import strip_narrative_body

POST_GOLDEN_LINE_RE = re.compile(r"^\s*[-*]\s*\[[ xX]\]\s*金句位\s*[：:](.*)$", re.M)
POST_TAIL_LINE_RE = re.compile(r"^\s*[-*]\s*\[[ xX]\]\s*章尾张力（G4\.cd 口径）\s*[：:](.*)$", re.M)
# r4b _PUNCT 全标点族——切分与归一同源一次完成：按标点族 split 即得纯文字子句
_CLAUSE_SPLIT_RE = re.compile(
    r"[。！？；，、：·—–…「」『』“”\"'（）()\[\]【】《》〈〉？！!?:;,./｜|＝=＋+＊*～\s]+"
)


def _line_quotes(line_text: str) -> list[str]:
    """执法行内引句提取：嵌套「」优先＋『』“”单层族；尾注括号区间位置排除；
    span 级去重（单层命中落在嵌套 span 内则弃——ch31『』内嵌形）＋
    dict 去重（audit-T1 I：META 双区重叠时同一引句可能双入列，门侧幂等）。
    """
    paren_spans = [m.span() for m in PAREN_SPAN_RE.finditer(line_text)]
    nested_spans: list[tuple[int, int]] = []
    seen: dict[str, None] = {}
    for m in NESTED_QUOTE_RE.finditer(line_text):
        nested_spans.append(m.span())
        if any(ps <= m.start() < pe for ps, pe in paren_spans):
            continue
        seen.setdefault(m.group(1), None)
    for m in QUOTE_RE.finditer(line_text):
        if any(ns <= m.start() < ne for ns, ne in nested_spans):
            continue
        if any(ps <= m.start() < pe for ps, pe in paren_spans):
            continue
        seen.setdefault(m.group(1), None)
    return list(seen)


def _clauses(text: str, min_len: int = 2) -> set[str]:
    return {c for c in _CLAUSE_SPLIT_RE.split(text) if len(c) >= min_len}


def check_post_quote_verbatim(content: str) -> tuple[list[str], list[str]]:
    """执法两行两臂判定 → (fail_items, warn_items)。

    fail 项形 ``cd.post_quote_verbatim:『…』…``（无 G4. 前缀——调用方
    id-first 拼装；消费点分流按 startswith("G4.")）。1 字引句（语料「查」
    「叁」形）逐字臂平凡命中即绿/缺席落 WARN——已知逃逸面（spec r5.1），
    子句 ≥2 字下限承载 min_len 分档。
    """
    fails: list[str] = []
    warns: list[str] = []
    prose_clauses: set[str] | None = None
    for line_re in (POST_GOLDEN_LINE_RE, POST_TAIL_LINE_RE):
        for m in line_re.finditer(content):
            for q in _line_quotes(m.group(1)):
                if quote_in_chapter(q, content):
                    continue  # 逐字臂绿
                if prose_clauses is None:
                    prose_clauses = _clauses(strip_narrative_body(content))
                missing = [c for c in _clauses(q) if c not in prose_clauses]
                if missing:
                    fails.append(
                        f"cd.post_quote_verbatim:『{q[:24]}…』声明子句缺席"
                        f"「{'、'.join(missing[:3])}」——POST 自检引句须逐字/子句"
                        "取自正文（修复者: drafting 改声明一行）"
                    )
                else:
                    warns.append(
                        f"cd.post_quote_verbatim:『{q[:24]}…』逐字缺席但子句全在"
                        "（标点/复合变体，交评审）"
                    )
    return fails, warns
