"""Spec #75 cross-chapter invariants: six hard checks across chapter seams.

Data path (dual-source, decoupled from the settling step's timing):
primary = memo declaration lines (planning batch product, on disk at the
split step) + deterministic derivation from the PREVIOUS chapter's prose;
the truth registry tables are a cross-check layer, never the sole truth at
check time. Pure validation: no side effects, idempotent.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from shenbi.status import GateStatus

# ---------- context ----------


@dataclass
class CrossChapterContext:
    """Inputs the checks consult; registry layers are optional (WARN)."""

    project_dir: Path | None = None
    name_whitelist: tuple[str, ...] = ("临", "他")  # #74 项 4 落地前 bootstrap
    registry_dir: Path | None = None  # truth/ 三表所在；缺席 → 交叉校验 WARN


# ---------- memo declaration lines (planning 场景预算块同区) ----------

_DECL_LINE_RES = {
    "时间锚": re.compile(r"^-\s*时间锚[：:]\s*(\[回拨\])?\s*(.+?)\s*$", re.MULTILINE),
    "余额": re.compile(r"^-\s*余额[：:]\s*(.+?)\s*$", re.MULTILINE),
    "POV": re.compile(r"^-\s*POV[：:]\s*(我|他|她)\s*$", re.MULTILINE),
}


def load_memo_declarations(memo_path: Path) -> dict[str, str]:
    """Declaration lines from a planning memo (时间锚/余额/POV).

    Missing file or pre-#72 memo (no scene-budget block) → {} — the caller
    treats that as the legacy-WARN path; prose-derived anchors still run.
    """
    if not memo_path.is_file():
        return {}
    text = memo_path.read_text(encoding="utf-8")
    out: dict[str, str] = {}
    for key, rx in _DECL_LINE_RES.items():
        m = rx.search(text)
        if m:
            out[key] = (
                m.group(2)
                if key == "时间锚" and m.group(1) is None
                else (("[回拨]" + m.group(2)) if key == "时间锚" else m.group(1))
            )
    return out


# ---------- skeleton entry ----------


def prev_chapter_path(chapter_path: Path) -> Path | None:
    """章 N 前章恒为 N-1（双章批语义：leader 前章=批外，follower=leader）。"""
    m = re.search(r"chapter-(\d+)", chapter_path.name)
    if not m:
        return None
    n = int(m.group(1))
    if n <= 1:
        return None
    prev = chapter_path.parent / f"chapter-{n - 1}.md"
    return prev if prev.is_file() else None


# ---------- invariant 6: asset continuity (memo balance declaration line) ----------

_CN_NUM_VALS = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
_EVENT_DECL_RE = re.compile(
    r"^-\s*事件[：:]\s*(收入|支出)\|\s*([一二三四五六七八九十百千\d]+)文\|\s*(.+?)\s*$",
    re.MULTILINE,
)
_BALANCE_DECL_RE = re.compile(
    r"^-\s*余额[：:]\s*([一二三四五六七八九十百千\d]+)文\s*$", re.MULTILINE
)


def _cn_amount(tok: str) -> int | None:
    """中文金额 → int（一百九十二/十二/300）；不可解析 None。"""
    if tok.isdigit():
        return int(tok)
    total, num = 0, 0
    for ch in tok:
        if ch in _CN_NUM_VALS:
            num = _CN_NUM_VALS[ch]
        elif ch == "十":
            total += (num or 1) * 10
            num = 0
        elif ch == "百":
            total += (num or 1) * 100
            num = 0
        elif ch == "千":
            total += (num or 1) * 1000
            num = 0
    return total + num if (total or num) else None


# ---------- invariant 4/5: prop chain + card attributes ----------

_PROP_DECL_RE = re.compile(r"^-\s*物象[：:]\s*(.+?)\s*\|\s*(.+?)\s*$", re.MULTILINE)
_PROP_MENTION_RE = re.compile(r"(红纸包|半张红纸|红纸|骨哨|怀表|童鞋|活字)")

_CARD_ORG_RE = re.compile(r"(星象局|历法房)")


def load_known_props(registry_path: Path | None) -> dict[str, str]:
    """prop_registry 已知实体 → 当前 owner（缺席 → 空 dict，WARN 交叉层）。"""
    if not registry_path or not registry_path.is_file():
        return {}
    out: dict[str, str] = {}
    for ln in registry_path.read_text(encoding="utf-8").split("\n"):
        m = re.match(r"\|\s*(红纸包|骨哨|怀表|童鞋|活字|半张红纸)\s*\|\s*([^|]+)\|", ln)
        if m:
            out[m.group(1)] = m.group(2).strip()
    return out


def load_card_attributes(card_dir: Path | None) -> dict[str, dict[str, str]]:
    """characters/major/*.md frontmatter + prose 关键属性（性别代词/机构）。"""
    out: dict[str, dict[str, str]] = {}
    if not card_dir or not card_dir.is_dir():
        return out
    for f in sorted(card_dir.glob("*.md")):
        text = f.read_text(encoding="utf-8")
        prose = "\n".join(
            ln for ln in text.split("\n") if not ln.startswith(("---", "name:", "role:", "source:"))
        )
        card: dict[str, str] = {}
        card["性别代词"] = (
            "他" if len(re.findall(r"他", prose)) > len(re.findall(r"她", prose)) else "她"
        )
        m = _CARD_ORG_RE.search(text)
        card["机构"] = m.group(1) if m else ""
        out[f.stem] = card
    return out


_NAME_IN_PROSE = {"小满": "xiao-man"}


# ---------- invariant 1: POV mode (prose-derived) ----------

_FIRST_PERSON = re.compile(r"^[^「”』]*?我(?![们们])", re.MULTILINE)
_THIRD_PERSON = re.compile(r"他|她")


def derive_pov_mode(text: str) -> str:
    """Deterministic POV derivation: first-person vs third-person density."""
    body = "\n".join(
        ln for ln in text.split("\n") if not ln.startswith("#") and not ln.startswith("<!--")
    )
    first = len(re.findall(r"我", body))
    third = len(_THIRD_PERSON.findall(body))
    if first + third == 0:
        return "unknown"
    return "我" if first > third * 2 else ("他" if third > first * 2 else "mixed")


# ---------- invariant 2: protagonist naming (three-signal binding) ----------

# 内汲动词绑定形态（ch4:88「灯在心里过了一遍」实证）
_INNER_VERBS = ("在心里", "暗自", "心里过了一遍", "心想", "暗想", "寻思")


def _sentence_spans(text: str) -> list[str]:
    parts = re.split(r"[。！？\n]", text)
    return [s for s in (p.strip() for p in parts) if s]


def protagonist_binding_hits(text: str, name: str, whitelist: tuple[str, ...]) -> list[str]:
    """Three-signal binding: 主语位 / 内汲动词绑定 / 邻句代词共指 (any two).

    Returns violation descriptions for occurrences where `name` binds to the
    protagonist while sitting outside the whitelist.
    """
    if name in whitelist:
        return []
    hits: list[str] = []
    sents = _sentence_spans(text)
    for i, sent in enumerate(sents):
        if name not in sent:
            continue
        signals = 0
        if re.search(rf"(?:^|[。！？，；]|接着|然后|而)\s*{re.escape(name)}", sent):
            signals += 1  # 主语位
        if any(v in sent for v in _INNER_VERBS) and name in sent:
            signals += 1  # 内汲动词绑定
        window = " ".join(sents[max(0, i - 1) : i + 2])
        if re.search(
            rf"{re.escape(name)}[^。！？]{{0,20}}他\b|他[^。！？]{{0,8}}{re.escape(name)}", window
        ):
            signals += 1  # 邻句代词共指
        if signals >= 2:
            hits.append(f"「{name}」主角指称绑定（信号 {signals}/3）: {sent[:24]}")
    return hits


_CN_NUMS = {
    "一": 1,
    "二": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
    "十": 10,
}
_CN_MONTHS = {f"{m}月": m for m in range(1, 13)}


def _cn_day(tok: str) -> int | None:
    """初十/十五/廿三/初七 → 日数；不可解析 None。"""
    tok = tok.replace("初", "").replace("廿", "二十")
    if tok == "十":
        return 10
    if tok == "二十":
        return 20
    if tok == "三十":
        return 30
    if len(tok) == 1 and tok in _CN_NUMS:
        return _CN_NUMS[tok]
    if len(tok) == 2 and tok[0] == "十" and tok[1] in _CN_NUMS:
        return 10 + _CN_NUMS[tok[1]]
    if len(tok) == 2 and tok[1] == "十" and tok[0] in _CN_NUMS:
        return _CN_NUMS[tok[0]] * 10
    return None


# day 后负向前瞻排除量词（十二天/二十步类误命中）；「月名+日」或裸「初X/日」形态
# 带月锚：月名 + 中文日（单字允许——「腊月初七」）
_MONTHDAY_RE = re.compile(
    r"(?:(\d{1,2})月|([正腊冬]+月|十一月|十二月|一月|二月))"
    r"(初[一二三四五六七八九十]|十[一二三四五六七八九]|廿[一二三四五六七八九]|[一二三四五六七八九])(?![天步年遍次章人条枚文块日历谱卷])"
)
# 无月锚：两字日形态（初X/十X/廿X）——单字裸数字过宽禁用
_BARE_DAY_RE = re.compile(
    r"(初[一二三四五六七八九十]|十[一二三四五六七八九]|廿[一二三四五六七八九])(?![天步年遍次章人条枚文块日历谱卷])"
)


def normalize_anchor(text: str, default_month: int | None) -> tuple[int, int] | None:
    """正文/声明中的中文锚 → (month, day)；无月继承 default_month。"""
    m = _MONTHDAY_RE.search(text)
    if m:
        if m.group(1):
            month: int | None = int(m.group(1))
        else:
            alias = {
                "正月": 1,
                "腊月": 12,
                "冬月": 11,
                "十一月": 11,
                "十二月": 12,
                "一月": 1,
                "二月": 2,
            }
            month = alias.get(m.group(2), default_month)
        day = _cn_day(m.group(3))
        if month is not None and day is not None:
            return (month, day)
    b = _BARE_DAY_RE.search(text)
    if b and default_month is not None:
        day = _cn_day(b.group(1))
        if day is not None:
            return (default_month, day)
    return None


def chapter_last_anchor(text: str, default_month: int | None = None) -> tuple[int, int] | None:
    """前章末锚（正文派生——从后向前找可解析锚；无月锚继承 default_month）。"""
    for chunk in reversed(text.split("\n")):
        a = normalize_anchor(chunk, default_month)
        if a:
            return a
    return None


def chapter_all_anchors(text: str, default_month: int | None = None) -> list[tuple[int, int]]:
    """本章全部可解析锚（wound 形态：任一叙事锚早于前章末锚即回拨——
    引用/书本日期与叙事日期同集合比较，回忆句属回拨须标记，设计内）。
    """
    out = []
    for chunk in text.split("\n"):
        a = normalize_anchor(chunk, default_month)
        if a:
            out.append(a)
    return out


def check_cross_chapter(
    chapter_path: Path,
    prev_path: Path | None,
    memo_path: Path | None,
    ctx: CrossChapterContext,
) -> list[str]:
    """Run the six invariants; returns violation strings (empty = clean).

    First chapter (prev_path None): skip the seam-dependent items entirely.
    """
    issues: list[str] = []
    cur_text = chapter_path.read_text(encoding="utf-8")

    # ── 不变量 5: 卡属性一致（卡 vs 正文——不依赖前章，首章亦跑）──
    cards = load_card_attributes(
        ctx.project_dir / "characters" / "major" if ctx.project_dir else None
    )
    for name, card_key in _NAME_IN_PROSE.items():
        if name not in cur_text or card_key not in cards:
            continue
        card = cards[card_key]
        # 段内共现：名字所在段落内「她」作主语起句 ≥2（跨句代词回指）
        para_hits = 0
        for para in cur_text.split("\n\n"):
            if name in para:
                para_hits += len(re.findall(r"(?:^|[。！？])\s*她", para))
        prose_pronouns = para_hits
        if card["性别代词"] == "他" and prose_pronouns >= 1:
            issues.append(f"角色「{name}」正文用「她」而卡为男性代词（修复者: 卡修/settling）")
        wrong_org = "星象局" if card["机构"] == "历法房" else None
        if wrong_org and wrong_org in cur_text:
            issues.append(f"机构名「{wrong_org}」与卡（{card['机构']}）不一致（修复者: 卡修）")
        # 反向：卡机构与正文主导机构不一致（卡=星象局 而正文=历法房 N 处）
        if card["机构"] == "星象局" and cur_text.count("历法房") >= 2:
            issues.append("卡机构「星象局」与正文主导机构「历法房」不一致（修复者: 卡修）")

    if prev_path is None:
        return issues  # 首章：其余前章依赖项跳过（卡属性已跑）

    prev_text = prev_path.read_text(encoding="utf-8")

    # ── 不变量 1: POV 人称一致（正文推导；变更须 memo 声明）──
    cur_pov = derive_pov_mode(cur_text)
    prev_pov = derive_pov_mode(prev_text)
    decls = load_memo_declarations(memo_path) if memo_path else {}
    declared = decls.get("POV")
    if cur_pov != prev_pov and cur_pov != "unknown" and prev_pov != "unknown":
        if not declared or declared != cur_pov:
            issues.append(
                f"POV 人称断裂: 前章 {prev_pov} → 本章 {cur_pov} 且无 POV 变更声明"
                "（修复者: planning+drafting）"
            )

    # ── 不变量 3: 时间锚单调（正文派生恒跑；[回拨] 声明豁免全章）──
    # 本章任一叙事锚早于前章末锚即回拨（无月锚继承本章最早月上下文）
    cur_anchors = chapter_all_anchors(cur_text)
    month_hint = cur_anchors[0][0] if cur_anchors else None
    prev_anchor = chapter_last_anchor(prev_text, month_hint)
    if prev_anchor and cur_anchors:
        declared_anchor = decls.get("时间锚", "")
        flashback = declared_anchor.startswith("[回拨]")
        back = min(cur_anchors)
        if back < prev_anchor and not flashback:
            issues.append(
                f"时间锚回拨: 前章末 {prev_anchor} → 本章最早锚 {back} 无 [回拨] 声明"
                "（修复者: planning+drafting）"
            )

    # ── 不变量 4: 物象 owner 链（正文唯一真值；经手事件还原）──
    known_props = load_known_props(
        ctx.registry_dir / "prop_registry.md" if ctx.registry_dir else None
    )
    prop_decls = (
        dict(_PROP_DECL_RE.findall(memo_path.read_text(encoding="utf-8")))
        if memo_path and memo_path.is_file()
        else {}
    )
    mentions = set(_PROP_MENTION_RE.findall(cur_text)) | set(prop_decls.keys())
    for prop in mentions:
        owner_declared = prop_decls.get(prop)
        if prop in known_props and owner_declared is None:
            issues.append(
                f"物象「{prop}」出现但无经手声明（registry owner: {known_props[prop]}；修复者: settling）"
            )

    # ── 不变量 6: 资产连续性（memo 余额声明行主源；≥10 文跳变须事件）──
    cur_text_full = (
        memo_path.read_text(encoding="utf-8") if memo_path and memo_path.is_file() else ""
    )
    cur_bal = _BALANCE_DECL_RE.search(cur_text_full)
    # prev 余额双源：prev memo（plans/ 下）优先，正文余额行回退
    prev_bal = None
    if ctx.project_dir:
        import re as _re

        _pn = _re.search(r"chapter-(\d+)", prev_path.name)
        if _pn:
            _pm = ctx.project_dir / "plans" / f"chapter-{int(_pn.group(1))}-plan.md"
            if _pm.is_file():
                prev_bal = _BALANCE_DECL_RE.search(_pm.read_text(encoding="utf-8"))
    if prev_bal is None:
        prev_bal = _BALANCE_DECL_RE.search(prev_text)
    if cur_bal and prev_bal:
        cur_amt = _cn_amount(cur_bal.group(1))
        prev_amt = _cn_amount(prev_bal.group(1))
        events = _EVENT_DECL_RE.findall(cur_text_full)
        delta = (cur_amt - prev_amt) if (cur_amt is not None and prev_amt is not None) else None
        if delta is not None and abs(delta) >= 10 and not events:
            issues.append(
                f"余额跳变 {prev_amt}文→{cur_amt}文（Δ{delta}）无事件声明（修复者: settling）"
            )

    # ── 不变量 2: 主角称谓（三信号绑定；白名单外名绑定即 FAIL）──
    for name in ("灯", "小满", "萤"):
        hits = protagonist_binding_hits(cur_text, name, ctx.name_whitelist)
        if hits:
            issues.append("称谓违例（修复者: planning+drafting）: " + "; ".join(hits[:2]))
    return issues


def g4_cross_chapter(
    fps: list[str],
    rd: str | None = None,
    project_dir: str | None = None,
    repo_root: str | None = None,
) -> str:
    """G4 checker entry (signature aligned with the existing checker family)."""
    from shenbi.gates.shared import fail, passed, resolve_input_path

    c: list[dict[str, Any]] = []
    mf: list[str] = []
    for fp in fps or []:
        ch_path = Path(fp)
        if not ch_path.is_absolute() and rd:
            ch_path = Path(resolve_input_path(fp, rd))
        if not ch_path.is_file():
            mf.append(f"XC.not_found:{fp}")
            continue
        prev = prev_chapter_path(ch_path)
        memo = None
        if project_dir:
            m = re.search(r"chapter-(\d+)", ch_path.name)
            if m:
                memo = Path(project_dir) / "plans" / f"chapter-{m.group(1)}-plan.md"
        ctx = CrossChapterContext(
            project_dir=Path(project_dir) if project_dir else None,
            registry_dir=(Path(project_dir) / "truth") if project_dir else None,
        )
        issues = check_cross_chapter(ch_path, prev, memo, ctx)
        if issues:
            mf.extend(f"XC:{ch_path.name}:{i}" for i in issues)
        else:
            c.append({"id": "XC.clean", "file": fp, "s": GateStatus.PASS})
    if mf:
        return fail(
            "G4-cross-chapter",
            [{"id": "XC", "s": GateStatus.FAIL, "r": m} for m in mf],
            "chapter_split",
            mf,
        )
    return passed("G4-cross-chapter", c)
