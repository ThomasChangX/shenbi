"""Spec #75 cross-chapter invariants: six hard checks across chapter seams.

Data path (dual-source, decoupled from the settling step's timing):
primary = memo declaration lines (planning batch product, on disk at the
split step) + deterministic derivation from the PREVIOUS chapter's prose;
the truth registry tables are a cross-check layer, never the sole truth at
check time. Pure validation: no side effects, idempotent.

Detection vocabulary is DATA-DERIVED first (name_registry rows, card
frontmatter, prop_registry keys) with a documented bootstrap fallback that
holds until spec #74 lands the real registries — framework code never
carries one novel's proper nouns as its only source.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from shenbi.logging import get_logger
from shenbi.status import GateStatus

log = get_logger(__name__)

# ---------- context / bootstrap vocabulary ----------

#: #74 项 4 落地前的 bootstrap：registry 在场时由 load_name_registry 接管。
_BOOTSTRAP_WHITELIST: tuple[str, ...] = ("临", "他")
_BOOTSTRAP_RESERVED: tuple[str, ...] = ("灯",)
#: 机构扫描种子（#74 项 2 修卡后由卡字段接管；prose 侧词表 = 种子 ∪ 卡机构字段）。
_BOOTSTRAP_ORGS: tuple[str, ...] = ("星象局", "历法房")


@dataclass
class CrossChapterContext:
    """Inputs the checks consult; registry layers are optional (WARN)."""

    project_dir: Path | None = None
    name_whitelist: tuple[str, ...] = _BOOTSTRAP_WHITELIST  # registry 在场时覆盖
    registry_dir: Path | None = None  # truth/ 三表所在；缺席 → 交叉校验 WARN


def load_name_registry(registry_dir: Path | None) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """name_registry → (whitelist, reserved)。

    Rows follow the seeded layout ``| 类别 | 名 | 备注 |``; 登记名/代词白名单
    rows feed the whitelist, 禁用名 rows feed the reserved-name scan. Absent
    or unparseable registry → bootstrap pair (caller-visible WARN covers the
    degradation).
    """
    whitelist = list(_BOOTSTRAP_WHITELIST)
    reserved = list(_BOOTSTRAP_RESERVED)
    path = registry_dir / "name_registry.md" if registry_dir else None
    if not path or not path.is_file():
        return tuple(whitelist), tuple(reserved)
    for ln in path.read_text(encoding="utf-8").split("\n"):
        m = re.match(r"\|\s*(登记名|代词白名单|禁用名)\s*\|\s*([^|]+)\|", ln)
        if not m:
            continue
        name = m.group(2).strip()
        if not name:
            continue
        if m.group(1) == "禁用名":
            reserved.append(name)
        else:
            whitelist.append(name)
    return tuple(whitelist), tuple(reserved)


# ---------- memo declaration lines (planning 场景预算块同区) ----------

_DECL_LINE_RES = {
    "时间锚": re.compile(r"^-\s*时间锚[：:]\s*(\[回拨\])?\s*(.+?)\s*$", re.MULTILINE),
    "余额": re.compile(r"^-\s*余额[：:]\s*(.+?)\s*$", re.MULTILINE),
    # 混称 = declared intentional mix (mixed narration chapters are legal
    # when declared — an undeclarable mixed chapter would be a gate dead end)
    "POV": re.compile(r"^-\s*POV[：:]\s*(我|他|她|混称)\s*$", re.MULTILINE),
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


def load_known_props(registry_path: Path | None) -> dict[str, str]:
    """prop_registry 已知实体 → 当前 owner（缺席 → 空 dict，WARN 交叉层）。

    Entity keys come from the table's first column — any entity the registry
    knows, no hardcoded novel vocabulary.
    """
    if not registry_path or not registry_path.is_file():
        return {}
    out: dict[str, str] = {}
    for ln in registry_path.read_text(encoding="utf-8").split("\n"):
        m = re.match(r"\|\s*([^|\s][^|]*?)\s*\|\s*([^|]+)\|", ln)
        if not m or m.group(1).startswith(("实体", "---")):
            continue
        out[m.group(1)] = m.group(2).strip()
    return out


def load_known_orgs(card_dir: Path | None) -> set[str]:
    """Prose-side org scan vocabulary: bootstrap seeds ∪ card 机构 fields.

    #74 项 2 修卡后 real data flows in via the cards; the bootstrap pair is
    the documented fallback for the old corpus (and the fixture regression
    set), not a second source of truth.
    """
    orgs = set(_BOOTSTRAP_ORGS)
    if card_dir and card_dir.is_dir():
        for f in sorted(card_dir.glob("*.md")):
            m = re.search(r"^\s*机构[：:]\s*(\S+)", f.read_text(encoding="utf-8"), re.MULTILINE)
            if m:
                orgs.add(m.group(1))
    return orgs


def load_card_attributes(card_dir: Path | None) -> dict[str, dict[str, str]]:
    """characters/major/*.md → 正文用名 → 卡属性（性别代词/机构）。

    Keyed by the card's ``name:`` frontmatter (the prose name); 性别 prefers
    an explicit 性别 field, else 他/她 density over the card prose; 机构 from
    an explicit 机构 field, else the first known-org mention in the card.
    """
    if not card_dir or not card_dir.is_dir():
        return {}
    known_orgs = load_known_orgs(card_dir)
    org_re = re.compile("|".join(re.escape(o) for o in sorted(known_orgs))) if known_orgs else None
    out: dict[str, dict[str, str]] = {}
    for f in sorted(card_dir.glob("*.md")):
        text = f.read_text(encoding="utf-8")
        name_m = re.search(r"^name[：:]\s*(\S+)", text, re.MULTILINE)
        prose_name = name_m.group(1) if name_m else f.stem
        prose = "\n".join(
            ln for ln in text.split("\n") if not ln.startswith(("---", "name:", "role:", "source:"))
        )
        card: dict[str, str] = {}
        gender_m = re.search(r"^\s*性别[：:]\s*(男|女)", text, re.MULTILINE)
        if gender_m:
            card["性别代词"] = "他" if gender_m.group(1) == "男" else "她"
        else:
            card["性别代词"] = (
                "他" if len(re.findall(r"他", prose)) > len(re.findall(r"她", prose)) else "她"
            )
        org_m = re.search(r"^\s*机构[：:]\s*(\S+)", text, re.MULTILINE)
        if org_m:
            card["机构"] = org_m.group(1)
        else:
            m = org_re.search(text) if org_re else None
            card["机构"] = m.group(0) if m else ""
        res_m = re.search(r"^\s*住所[：:]\s*(\S+)", text, re.MULTILINE)
        card["住所"] = res_m.group(1) if res_m else ""
        out[prose_name] = card
    return out


# ---------- invariant 1: POV mode (prose-derived) ----------

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


# ---------- invariant 2: protagonist naming (reserved-name binding + hijack) ----------

# 内汲动词绑定形态（ch4:88「灯在心里过了一遍」实证）
_INNER_VERBS = ("在心里", "暗自", "心里过了一遍", "心想", "暗想", "寻思")

# 复合词边界（语言学常量，非某部小说词汇）：单字保留名嵌进复合词时不是
# 人名指称——「灯芯/灯花/灯笼」是器物、「点灯/掌灯」是动宾。前瞻/后顾集合
# 覆盖常见复合形态；句中无可独立成词的裸名出现时该句不参与绑定计分。
_COMPOUND_NEXT = "芯花笼盏油丝罩塔杆火光焰苗台捻座"
_COMPOUND_PREV = "点吹挑熄提掌街宫路桌吊酒精赏张"


def _standalone_count(sent: str, name: str) -> int:
    n = 0
    for m in re.finditer(re.escape(name), sent):
        after = sent[m.end() : m.end() + 1]
        before = sent[max(0, m.start() - 1) : m.start()]
        if (after and after in _COMPOUND_NEXT) or (before and before in _COMPOUND_PREV):
            continue
        n += 1
    return n


def _sentence_spans(text: str) -> list[str]:
    parts = re.split(r"[。！？\n]", text)
    return [s for s in (p.strip() for p in parts) if s]


def protagonist_binding_hits(text: str, name: str, whitelist: tuple[str, ...]) -> list[str]:
    """Three-signal binding: 主语位 / 内汲动词绑定 / 同句代词共指 (any two).

    Signal discipline (final-review tuning against the real corpus): 主语位
    counts only at TRUE sentence starts (clause-initial after ，/； is a
    compound-sentence continuation — «册子丢了，灯还亮着» is a lamp, not a
    name); 代词共指 must sit in the SAME sentence as the name (adjacent-
    sentence co-reference misbinds side characters acting near the POV
    protagonist); compound-embedded occurrences (灯芯/点灯) never score.
    """
    if name in whitelist:
        return []
    hits: list[str] = []
    esc = re.escape(name)
    for sent in _sentence_spans(text):
        if name not in sent or _standalone_count(sent, name) == 0:
            continue
        signals = 0
        if re.search(rf"^{esc}", sent):
            signals += 1  # 句首主语位
        if any(v in sent for v in _INNER_VERBS):
            signals += 1  # 内汲动词绑定
        if re.search(rf"{esc}[^。！？]{{0,20}}他|他[^。！？]{{0,8}}{esc}", sent):
            signals += 1  # 同句代词共指
        if signals >= 2:
            hits.append(f"「{name}」主角指称绑定（信号 {signals}/3）: {sent[:24]}")
    return hits


def reserved_name_hijack_hits(text: str, reserved: tuple[str, ...]) -> list[str]:
    """Wound 2b (ch7): a reserved name used as a PRESENT character's name.

    The ch7 form: a walk-on (井台女) carries the heroine's reserved name —
    dialogue vocative («「灯，水凉…」») or ≥2 paragraphs where the bare name
    opens a sentence while 她 refers to it in the same paragraph. Compound
    uses (灯芯/灯花) score nothing via _standalone_count.
    """
    hits: list[str] = []
    for name in reserved:
        esc = re.escape(name)
        if re.search(rf"「\s*{esc}\s*[,，]", text):
            hits.append(f"禁用名「{name}」被用作在场角色名（对话呼格；修复者: planning）")
            continue
        bound = 0
        for para in text.split("\n\n"):
            for sent in _sentence_spans(para):
                if re.search(rf"^{esc}", sent) and _standalone_count(sent, name) > 0:
                    if "她" in para:
                        bound += 1
                    break
        if bound >= 2:
            hits.append(
                f"禁用名「{name}」被用作在场角色名（她共指段 {bound} 处；修复者: planning）"
            )
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


def _cn_day(tok: str) -> int | None:
    """初十/十五/廿三/二十九/三十 → 日数；不可解析 None。

    Final-review fix: the twenty-forms (二十九 etc.) previously fell through
    every branch and callers matched only the leading digit — every 二十X
    date parsed as day 2.
    """
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
    if len(tok) == 3 and tok[:2] == "二十" and tok[2] in _CN_NUMS:
        return 20 + _CN_NUMS[tok[2]]
    if len(tok) == 3 and tok[0] == "三十" and tok[1:] == "十":
        return None
    return None


# day 后负向前瞻排除量词（十二天/二十步类误命中）与续位数字（防回溯把
# 「二十九天」截成「二十」——数字字符入类后任何截断形态都被否决）；
# 「月名+日」或裸「初X/日」形态。日组覆盖 初X / 十X / 二十X / 三十[X] /
# 廿X / 单字（final-review fix：二十X 形态此前无分支可配）
_DAY_GROUP = (
    r"(初[一二三四五六七八九十]|三十[一二]?|(?:[一二]?十)[一二三四五六七八九]?|"
    r"廿[一二三四五六七八九]?|[一二三四五六七八九])"
)
_MONTHDAY_RE = re.compile(
    r"(?:(\d{1,2})月|([正腊冬]+月|十一月|十二月|一月|二月))"
    + _DAY_GROUP
    + r"(?![天步年遍次章人条枚文块日历谱卷一二三四五六七八九十廿两倍斤页行个])"
)
# 无月锚：两字日形态（初X/十X/廿X）——单字裸数字过宽禁用
_BARE_DAY_RE = re.compile(
    r"(初[一二三四五六七八九十]|三十[一二]?|(?:[一二]?十)[一二三四五六七八九]?|"
    r"廿[一二三四五六七八九]?)(?![天步年遍次章人条枚文块日历谱卷一二三四五六七八九十廿两倍斤页行个])"
)
# 阿拉伯形态（G6.4 退役后唯一的 arabic 日期防线）：12月7日
_ARABIC_MD_RE = re.compile(r"(\d{1,2})月(\d{1,2})[日号]")


_MONTH_ALIAS = {
    "正月": 1,
    "腊月": 12,
    "冬月": 11,
    "十一月": 11,
    "十二月": 12,
    "一月": 1,
    "二月": 2,
}


def normalize_anchor(text: str, default_month: int | None) -> tuple[int, int] | None:
    """正文/声明中的中文锚 → (month, day)；无月继承 default_month。"""
    ar = _ARABIC_MD_RE.search(text)
    if ar:
        return (int(ar.group(1)), int(ar.group(2)))
    m = _MONTHDAY_RE.search(text)
    if m:
        if m.group(1):
            month: int | None = int(m.group(1))
        else:
            month = _MONTH_ALIAS.get(m.group(2), default_month)
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
    """前章末锚（从后向前；裸日继承其更晚文本的显式月——后向携带）。

    Final-review fix: inheriting the CURRENT chapter's month hint made a
    prev-chapter bare day («…十») masquerade as the new month, turning the
    legitimate 腊月→正月 year wrap into a same-month "rollback" (ch4/ch8
    false positives). Own-text derivation first; default_month only as the
    no-explicit-month-anywhere fallback.
    """
    for init in (None, default_month):
        carry: int | None = init
        for chunk in reversed(text.split("\n")):
            m = _MONTHDAY_RE.search(chunk)
            if m:
                month = int(m.group(1)) if m.group(1) else _MONTH_ALIAS.get(m.group(2), carry)
                day = _cn_day(m.group(3)) if month is not None else None
                if month is not None and day is not None:
                    return (month, day)
                if month is not None:
                    carry = month
                    continue
            b = _BARE_DAY_RE.search(chunk)
            if b and carry is not None:
                day = _cn_day(b.group(1))
                if day is not None:
                    return (carry, day)
        if init is None and default_month is None:
            break
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
    memo_text = memo_path.read_text(encoding="utf-8") if memo_path and memo_path.is_file() else ""
    whitelist, reserved = load_name_registry(ctx.registry_dir)
    whitelist = whitelist if ctx.registry_dir else ctx.name_whitelist

    # ── 不变量 5: 卡属性一致（卡 vs 正文——不依赖前章，首章亦跑）──
    # 派生数据面：卡 name: frontmatter = 正文用名（无硬编码人名字典）；
    # 机构词表 = bootstrap ∪ 卡机构字段（load_known_orgs）。
    cards = load_card_attributes(
        ctx.project_dir / "characters" / "major" if ctx.project_dir else None
    )
    for name, card in cards.items():
        if name not in cur_text or not card["机构"]:
            continue
        # 段内共现：名字所在段落内「她」作主语起句 ≥1（跨句代词回指）
        para_hits = 0
        for para in cur_text.split("\n\n"):
            if name in para:
                para_hits += len(re.findall(r"(?:^|[。！？])\s*她", para))
        if card["性别代词"] == "他" and para_hits >= 1:
            issues.append(f"角色「{name}」正文用「她」而卡为男性代词（修复者: 卡修/settling）")
        # 同表其它已知机构在正文成主导（卡机构被边缘化）→ 机构漂移
        others = load_known_orgs(
            ctx.project_dir / "characters" / "major" if ctx.project_dir else None
        ) - {card["机构"]}
        for other in others:
            if cur_text.count(other) >= 2 and cur_text.count(other) > cur_text.count(card["机构"]):
                issues.append(
                    f"卡机构「{card['机构']}」与正文主导机构「{other}」不一致（修复者: 卡修）"
                )
        # 住所轨迹（#75 不变量 5 第三面；卡字段缺席 → 不检）
        if card["住所"]:
            for para in cur_text.split("\n\n"):
                if name not in para:
                    continue
                for rm in re.finditer(r"(?:住|搬|迁)[到进在]了?([^\s。，,「」]{2,8})", para):
                    loc = rm.group(1)
                    if loc not in card["住所"] and card["住所"] not in loc:
                        issues.append(
                            f"角色「{name}」正文住所「{loc}」与卡（{card['住所']}）不一致（修复者: 卡修）"
                        )

    # ── 不变量 2: 主角称谓（禁用名绑定 + 撞名——不依赖前章，首章亦跑）──
    # 扫描集 = name_registry 禁用名（缺席 bootstrap）：白名单外名绑定到主角
    # 内汲信号 = 主角被误名；禁用名被用作在场角色名 = 撞名（ch7 井台女）。
    for name in reserved:
        hits = protagonist_binding_hits(cur_text, name, whitelist)
        if hits:
            issues.append("称谓违例（修复者: planning+drafting）: " + "; ".join(hits[:2]))
    issues.extend(reserved_name_hijack_hits(cur_text, reserved))

    # ── 不变量 4: 物象 owner 链（正文唯一真值；经手事件还原；首章亦跑）──
    known_props = load_known_props(
        ctx.registry_dir / "prop_registry.md" if ctx.registry_dir else None
    )
    prop_decls = dict(_PROP_DECL_RE.findall(memo_text)) if memo_text else {}
    for prop in known_props:
        if prop in cur_text and prop not in prop_decls:
            issues.append(
                f"物象「{prop}」出现但无经手声明（registry owner: {known_props[prop]}；修复者: settling）"
            )

    if prev_path is None:
        return issues  # 首章：前章依赖项（POV/时间锚/资产）跳过

    prev_text = prev_path.read_text(encoding="utf-8")

    # ── 不变量 1: POV 人称一致（正文推导；变更须 memo 声明；混称可声明）──
    cur_pov = derive_pov_mode(cur_text)
    prev_pov = derive_pov_mode(prev_text)
    decls = load_memo_declarations(memo_path) if memo_path else {}
    declared = decls.get("POV")
    if cur_pov != prev_pov and cur_pov != "unknown" and prev_pov != "unknown":
        declared_matches = declared == cur_pov or (declared == "混称" and cur_pov == "mixed")
        if not declared_matches:
            issues.append(
                f"POV 人称断裂: 前章 {prev_pov} → 本章 {cur_pov} 且无 POV 变更声明"
                "（修复者: planning+drafting）"
            )

    # ── 不变量 3: 时间锚单调（正文派生恒跑；[回拨] 声明豁免全章）──
    # 本章任一叙事锚早于前章末锚即回拨（无月锚继承本章最早月上下文）。
    # 跨年 wrap：腊月(N)末 → 正月(N+1 年 1 月)是前进不是回拨。
    cur_anchors = chapter_all_anchors(cur_text)
    month_hint = cur_anchors[0][0] if cur_anchors else None
    prev_anchor = chapter_last_anchor(prev_text, month_hint)
    if prev_anchor and cur_anchors:
        declared_anchor = decls.get("时间锚", "")
        flashback = declared_anchor.startswith("[回拨]")
        back = min(cur_anchors)
        year_wrap = prev_anchor[0] == 12 and back[0] == 1
        if back < prev_anchor and not flashback and not year_wrap:
            issues.append(
                f"时间锚回拨: 前章末 {prev_anchor} → 本章最早锚 {back} 无 [回拨] 声明"
                "（修复者: planning+drafting）"
            )

    # ── 不变量 6: 资产连续性（memo 余额声明行主源；≥10 文跳变须事件对账）──
    cur_bal = _BALANCE_DECL_RE.search(memo_text)
    # prev 余额双源：prev memo（plans/ 下）优先，正文余额行回退
    prev_bal = None
    if ctx.project_dir:
        _pn = re.search(r"chapter-(\d+)", prev_path.name)
        if _pn:
            _pm = ctx.project_dir / "plans" / f"chapter-{int(_pn.group(1))}-plan.md"
            if _pm.is_file():
                prev_bal = _BALANCE_DECL_RE.search(_pm.read_text(encoding="utf-8"))
    if prev_bal is None:
        prev_bal = _BALANCE_DECL_RE.search(prev_text)
    if cur_bal and prev_bal:
        cur_amt = _cn_amount(cur_bal.group(1))
        prev_amt = _cn_amount(prev_bal.group(1))
        events = _EVENT_DECL_RE.findall(memo_text)
        delta = (cur_amt - prev_amt) if (cur_amt is not None and prev_amt is not None) else None
        if delta is not None and abs(delta) >= 10:
            if not events:
                issues.append(
                    f"余额跳变 {prev_amt}文→{cur_amt}文（Δ{delta}）无事件声明（修复者: settling）"
                )
            else:
                # 对账：声明事件净额须覆盖跳变（容差 max(10, 20%)——散文允许
                # 未声明的小额流动）；方向相反或量级悬殊 = 假声明
                net = sum(
                    _cn_amount(amt) or 0 if kind == "收入" else -(_cn_amount(amt) or 0)
                    for kind, amt, _src in events
                )
                if abs(delta - net) > max(10, abs(delta) * 0.2):
                    issues.append(
                        f"余额跳变 {prev_amt}文→{cur_amt}文（Δ{delta}）与事件净额 {net}文 对账不符"
                        "（修复者: settling）"
                    )
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
    # #75: the registry tables are a cross-check layer, never the sole
    # truth — absence degrades to the prose-derived primary source, but the
    # degradation must be visible (WARN check, not silence).
    if project_dir:
        truth_dir = Path(project_dir) / "truth"
        for _rel in ("name_registry.md", "timeline.md", "prop_registry.md"):
            if not (truth_dir / _rel).is_file():
                log.info("xc_registry_absent", table=_rel)
                c.append(
                    {
                        "id": "XC.registry",
                        "file": f"truth/{_rel}",
                        "s": GateStatus.WARN,
                        "r": (
                            "registry absent — cross-check layer degraded (prose-derived"
                            " primary still runs; name_registry seedable via"
                            " python -m shenbi.pipeline.registry_seeding, timeline/"
                            "prop_registry grow via settling increments)"
                        ),
                    }
                )
    for fp in fps or []:
        ch_path = Path(fp)
        if not ch_path.is_absolute() and rd:
            ch_path = Path(resolve_input_path(fp, rd))
        if not ch_path.is_file():
            mf.append(f"XC.not_found:{fp}")
            continue
        prev = prev_chapter_path(ch_path)
        ch_num_m = re.search(r"chapter-(\d+)", ch_path.name)
        memo = None
        if project_dir and ch_num_m:
            memo = Path(project_dir) / "plans" / f"chapter-{ch_num_m.group(1)}-plan.md"
        ctx = CrossChapterContext(
            project_dir=Path(project_dir) if project_dir else None,
            registry_dir=(Path(project_dir) / "truth") if project_dir else None,
        )
        # 编号断档：N>1 而前章缺席 → 时间锚/POV 基线丢失，降级须可见
        if prev is None and ch_num_m and int(ch_num_m.group(1)) > 1:
            log.info("xc_prev_missing", chapter=int(ch_num_m.group(1)))
            c.append(
                {
                    "id": "XC.prev_missing",
                    "file": fp,
                    "s": GateStatus.WARN,
                    "r": f"chapter-{int(ch_num_m.group(1)) - 1}.md absent — seam checks (POV/timeline) skipped for this chapter",
                }
            )
        issues = check_cross_chapter(ch_path, prev, memo, ctx)
        # 相对锚：月名在场而全章无可解析锚 → 单调比较被静默跳过，须可见
        _body = ch_path.read_text(encoding="utf-8")
        _month_named = re.search(r"(?:正|腊|冬|十一|十二|[一二三四五六七八九十\d]{1,2})月", _body)
        if _month_named and not chapter_all_anchors(_body):
            log.info("xc_relative_anchor", file=fp)
            c.append(
                {
                    "id": "XC.relative_anchor",
                    "file": fp,
                    "s": GateStatus.WARN,
                    "r": "month names present but no absolute anchor parsed — relative-only timeline, monotonicity comparison skipped",
                }
            )
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
