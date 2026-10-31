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


# 形态锚：ch1:229 `- [ ] 转折词密度: 0 / 3625字 = 0 (≤ 1/3000)`（值后带 / N字 = N
# 尾巴，非行尾裸 0）；轮 8 M2 兼收 ch23 变体形 `0（正文零显式转折词）`
_POST_TRANSITION_DECL_RE = re.compile(
    r"^\s*[-*]\s*\[[ xX]\]\s*转折词密度\s*[：:]\s*0\s*(?:/|（)", re.M
)
# 形态锚：ch1:233 `…；总计 3625` / ch28:241 `总计 1029+1098+1060=3187`（裸数或 = 后数）
_POST_WORDCOUNT_DECL_RE = re.compile(
    r"^\s*[-*]\s*\[[ xX]\]\s*正文字数（逐段计数合计）\s*[：:].*?总计\s*[≈约]?\s*(?:[\d+]+\s*=\s*)?(\d+)\s*(?:（[^）]*）)?\s*$",
    re.M,
)  # audit-T3 I1：兼收尾注形（总计 3760（≥2800，≤4000））与 ≈/约 前缀；总计 a+b=N 形保持


def check_post_transition_cross(content: str) -> list[str]:
    """POST 报「转折词密度 0」而剥后正文词法计数 ≥1 → FAIL（声明↔门计数交叉对账）。"""
    from shenbi.gates.shared import count_transition_words

    if not _POST_TRANSITION_DECL_RE.search(content):
        return []
    if count_transition_words(strip_narrative_body(content)) >= 1:
        return [
            "cd.post_transition_cross:POST 报「转折词密度 0」但正文词法计数 ≥1"
            "——自检声明与词法门计数互斥（修复者: drafting 改声明一行）"
        ]
    return []


def check_post_wordcount_precision(content: str, actual_chars: int) -> list[str]:
    """Spec §1 字数行虚假精度：声明总计 vs 实测差 >2% → WARN。

    实测口径=total_chars_md_text（全字符剥后——与修订复验字数带同口径；
    wc（word_count_md）是 CJK 计数，与逐段全字符总计系统差 13-19%）。
    """
    issues: list[str] = []
    for m in _POST_WORDCOUNT_DECL_RE.finditer(content):
        declared = int(m.group(1))
        if declared <= 0:
            continue
        drift = abs(declared - actual_chars) / declared
        if drift > 0.02:
            issues.append(
                f"cd.post_wordcount_precision:声明总计 {declared} vs 实测 {actual_chars}"
                f"（差 {drift:.1%} >2%）——虚假精度（修复者: drafting 改声明一行）"
            )
    return issues


# spec #83 T6 余额锚（双面设计——轮 4 N1 定稿：raw content 输入；META/POST 区间
# 位置排除（quote_verbatim meta_regions 区间法）；场景跨度与匹配共用 raw 坐标系。
# 不得以 strip_narrative_body 为输入面——其尾部 strip_scene_markers 会剥掉
# <!--SCENE--> 标记，first_scene_span 恒走无标记退化、FAIL 臂回退全章首现。）
_BALANCE_RE = re.compile(
    r"(一共|还剩|只剩|剩下|剩|袋底|余额)[^。]{0,6}?([一二两三四五六七八九十百千\d]+)文"
)
_LEDGER_VALUE_RE = re.compile(r"余[额]?\s*[零一二两三四五六七八九十百千\d]+\s*文")


def parse_ledger_current_value(ledger_text: str) -> int | None:
    """Last matching value row of truth/particle_ledger.md (Chinese-digit).

    Real form (r5-C1 replay): ``| 第 36 章 | 余额一百零三文 | 未动 | …`` —
    余额-prefixed; bare-余 forms exist at multiple history rows, the LAST
    hit wins (tail rows may be out of chronological order); 无/未动 rows
    with no value form never match.
    """
    from shenbi.gates.g4.cross_chapter import cn_amount

    value: int | None = None
    for m in _LEDGER_VALUE_RE.finditer(ledger_text):
        raw = m.group(0).replace("余额", "").replace("余", "").strip()
        try:
            amount = cn_amount(raw)
        except (TypeError, ValueError):
            continue
        if amount is not None:
            value = amount
    return value


_SPEND_LINE_RE = re.compile(r"支出[|｜]([^|｜\s]+)文")


def parse_spend_events(memo_text: str) -> list[int]:
    """Spend amounts from plan ``- 事件: 支出|N文|…`` segments (spec #83 T6).

    Line-anchored AND mid-line scans (ch4 compound ``收入|…｜支出|六文|…``);
    无/零文 yield nothing (0 never exempts).
    """
    from shenbi.gates.g4.cross_chapter import cn_amount

    out: list[int] = []
    for m in _SPEND_LINE_RE.finditer(memo_text):
        raw = m.group(1)
        if raw in ("无", "零", "0"):
            continue
        try:
            amount = cn_amount(raw)
        except (TypeError, ValueError):
            continue
        if amount:
            out.append(amount)
    return out


def first_scene_span(content: str) -> tuple[int, int] | None:
    """Char span of the first <!--SCENE--> scene (marker1 -> marker2/trailing
    meta boundary), None when no markers (caller degenerates to whole body).

    Line-level rescan on ``is_scene_marker_line`` (shared.py) — NOT
    ``split_scenes`` (returns ``(size, last_line)`` tuples, unusable as spans).
    """
    from shenbi.gates.shared import is_scene_marker_line

    lines = content.split("\n")
    marker_idx = [i for i, ln in enumerate(lines) if is_scene_marker_line(ln)]
    if not marker_idx:
        return None
    # trailing-meta boundary mirrors split_scenes' (first H2/META after last marker);
    # for the FIRST scene the boundary is simply the next marker.
    start_line = marker_idx[0]
    end_line = marker_idx[1] if len(marker_idx) > 1 else len(lines)
    start = sum(len(ln) + 1 for ln in lines[:start_line])
    end = sum(len(ln) + 1 for ln in lines[:end_line])
    return start, end


def check_balance_value_drift(
    content: str, ledger_value: int | None, *, spend_events: list[int] | None = None
) -> tuple[list[str], list[str]]:
    """Balance anchor (spec #83 T6): FAIL arm = first-scene first occurrence
    != ledger (ch26 opening-spoiler pathology); WARN arm = every other hit
    whose value differs and whose signed diff ``ledger - occurrence`` is not
    a declared spend (ch23 post-payment deep occurrence exempt; ch1
    multi-timepoint progression warns). Dual-surface: raw content, META
    regions positionally excluded, scene span in the same coordinates.
    """
    from shenbi.gates.g4.quote_verbatim import meta_regions
    from shenbi.gates.g4.cross_chapter import cn_amount

    if ledger_value is None:
        return [], []
    meta_spans: list[tuple[int, int]] = [(rs, re_) for _r, rs, re_ in meta_regions(content)]
    scene = first_scene_span(content)
    hits: list[tuple[int, int]] = []  # (char_start, value)
    for m in _BALANCE_RE.finditer(content):
        if any(ms <= m.start() < me for ms, me in meta_spans):
            continue  # POST/PRE self-restatements never enter (M9)
        amount = cn_amount(m.group(2))
        if amount is None:
            continue
        hits.append((m.start(), amount))
    if not hits:
        return [], []
    fails: list[str] = []
    warns: list[str] = []
    first_start, first_value = hits[0]
    in_first_scene = scene is None or (scene[0] <= first_start < scene[1])
    if in_first_scene and first_value != ledger_value:
        fails.append(
            f"cd.balance_value_drift:章首首现余额 {first_value} ≠ ledger 现值 {ledger_value}"
            "——时序泄漏（章首不应携带本章结算后值；修复者: drafting）"
        )
    spent = spend_events or []
    # WARN 面=FAIL 臂评估对象之外的全部命中（r5-I3/r7-I1）：首现在首场景时归
    # FAIL 臂评估（无论红绿）、WARN 从次命中起；首现不在首场景（ch23 深位形）
    # 时首现归 WARN 面——全部命中入迭代
    _warn_hits = hits[1:] if in_first_scene else hits
    for _start, value in _warn_hits:
        if value == ledger_value:
            continue
        if (ledger_value - value) in spent:
            continue  # declared spend covers the drop (signed: income never exempts)
        warns.append(
            f"cd.balance_value_drift:余额命中 {value} ≠ 现值 {ledger_value} 且无对应支出声明"
            "——异值余额供人工裁决"
        )
    return fails, warns
