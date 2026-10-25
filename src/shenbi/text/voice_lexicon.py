"""Spec #76 voice lexicon: shared single-source vocabulary for voice checks.

Consumed by G4.cd (chapter density), tools/lint_voice_meme.py (chapter/volume
modes) — one definition, no drift. Deterministic closed sets only; counting
is exact-string / regex over the stripped chapter body (G2 snapshot-exempt
domain), never LLM-judged.
"""

from __future__ import annotations

import re

#: 账房动词族（封闭多字形集）。单字排除：裸「记」在旧九章每章 8-26 次，
#: 计入即证伪密度基线（#76 plan R1 审查实测）；集合变更须 bump 版本注释。
#: v1 (2026-10-26, spec #76): 折旧/入账/对账/盘点/结余/亏空/利息/挂账/冲销/清账/翻账/结清
ACCOUNTING_VERBS: tuple[str, ...] = (
    "折旧",
    "入账",
    "对账",
    "盘点",
    "结余",
    "亏空",
    "利息",
    "挂账",
    "冲销",
    "清账",
    "翻账",
    "结清",
)

#: 自嘲式反问收尾句式（protagonist voice_profile 形态——反问+自答/吧呢收束）。
#: 密度下限缺省（genre-config 缺席时消费端回退——validator 不代入，无副作用）。
DEFAULT_VOICE_DENSITY_MIN = 2

#: 喻体域五类封闭词表（spec #77；v1 2026-10-26）。「其他」不入词表——
#: >70% 其他降级 INFO「词表需扩」。字面记账动词（ACCOUNTING_VERBS）不入
#: 喻体口径（#76 校准条款：字面用法 vs 比喻句喻体分账）。
SIMILE_DOMAINS: dict[str, tuple[str, ...]] = {
    "纸账册": ("纸", "账", "册", "簿", "卷", "页", "契", "帖", "鉴录"),
    "粮食物": ("米", "面", "饼", "粮", "粟", "谷", "粥", "盐", "糖"),
    "器物": ("刀", "绳", "布", "锁", "秤", "斗", "壶", "碗", "灯", "哨"),
    "自然": ("雪", "雨", "风", "河", "井", "土", "灰", "石", "月", "日"),
    "身体": ("手", "眼", "骨", "血", "心", "喉", "背", "指", "腕", "肩"),
}

#: 开头动作动词族（书 tic 词表；spec #77 v1）。genre-config seed 可扩。
OPENING_VERB_FAMILIES: dict[str, tuple[str, ...]] = {
    "清点": ("清点", "点数", "数了", "数着", "盘点", "清了清"),
    "数数": ("数到", "数完", "数了三", "数出"),
    "拆包": ("拆开", "解开", "翻开", "打开"),
    "量取": ("量了", "称了", "掂了", "比了比"),
    "翻检": ("翻检", "翻找", "检了", "归置", "收拢"),
}

_SELF_MOCK_RE = re.compile(r"[^。！？]{2,24}(吧|呢|不成|得了)[？?]\s*$", re.MULTILINE)


def catchphrases_from_card(card_text: str) -> list[str]:
    """Extract protagonist catchphrases from card YAML frontmatter.

    yaml.safe_load precedent (chapter_drafting frontmatter parsing); 类括注
    剥离——`（初期）` 等尾注剥去取净串（xinghuo-ranqiong fixture 卡全带括注）。
    """
    if not card_text.lstrip().startswith("---"):
        return []
    parts = card_text.split("---", 2)
    if len(parts) < 3:
        return []
    try:
        import yaml

        fm = yaml.safe_load(parts[1])
    except Exception:  # noqa: BLE001 (C13 allowlist: broad catch, structured fallback below)
        return []
    if not isinstance(fm, dict):
        return []
    raw = fm.get("voice_profile")
    if not isinstance(raw, dict):
        return []
    out: list[str] = []
    for phrase in raw.get("catchphrases") or []:
        if not isinstance(phrase, str):
            continue
        net = re.sub(r"[（(][^）)]*[）)]", "", phrase).strip(" 。.，,")
        if net:
            out.append(net)
    return out


def distinct_voice_signals(body: str, catchphrases: list[str] | None = None) -> int:
    """Count DISTINCT voice signals in a chapter body (each source scores once).

    Signal classes: protagonist catchphrases (exact strings), accounting-verb
    family (any member present), self-mock rhetorical closing (regex hit).
    """
    signals = 0
    for phrase in catchphrases or []:
        if phrase and phrase in body:
            signals += 1
    if any(v in body for v in ACCOUNTING_VERBS):
        signals += 1
    if _SELF_MOCK_RE.search(body):
        signals += 1
    return signals
