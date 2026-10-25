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
