"""Spec #83 T4: RETRY-family feedback routing (routing face, not a gate face).

Family classification reads the retry_feedback TEXT prefix tokens — the
structured issue strings monitor_rewind carries into feedback verbatim.
This is NOT free-text judging: the 打摆 trigger determination lives in the
durable counter (streak_monitor_rewinds, spec r3 纪律), routing only picks
the 定向 addendum for already-structured prefixes.

Prefix families (r5 full-corpus replay, 147 issues): scene_domain 61 / word_band 19 /
chapter_band 19 / G4.cd 31 / composition 9 / CH 4 / XC 4; g4_hard check_ids
join the same prefix channel. Mixed strings route by length > structure >
content (heaviest constraint first - the ch25 all-mixed main shape).
"""

from __future__ import annotations

_LENGTH_TOKENS = ("word_band", "chapter_band", "G4.word_count", "word_count")
_STRUCTURE_TOKENS = (
    "scene_domain",
    "composition",
    "CH:",
    "CH ",
)  # CH 空格形=语料实形（audit-T7 M1：4/4 全为 `CH 标记…` 无冒号）
_CONTENT_TOKENS = ("G4.cd", "XC:")


def classify_retry_family(feedback_text: str) -> str:
    """Return "length" | "structure" | "content" | "other" by prefix tokens."""
    fams = set()
    for tok in _LENGTH_TOKENS:
        if tok in feedback_text:
            fams.add("length")
    for tok in _STRUCTURE_TOKENS:
        if tok in feedback_text:
            fams.add("structure")
    for tok in _CONTENT_TOKENS:
        if tok in feedback_text:
            fams.add("content")
    for fam in ("length", "structure", "content"):  # 混合串优先级（M5 入 Interfaces）
        if fam in fams:
            return fam
    return "other"


def targeted_feedback_addendum(family: str, prev_feedback: str) -> str:
    """Family-routed targeted addendum block (routing face, not the streak gate)."""
    if family == "length":
        return (
            "\n\n## 定向修复（长度族）\n"
            "按反馈实测缺口在既有场景内扩写——持久化前稿逐字保留，"
            "禁止整章重写（扩写定向与 _length_family 通道同款）。\n"
        )
    if family == "structure":
        return (
            "\n\n## 定向修复（场景结构族）\n"
            "只调整反馈点名的场景结构问题（场景数/标题/H1/合并形态）——"
            "未点名场景的正文逐字保留，禁止全档重组。\n"
        )
    if family == "content":
        return (
            "\n\n## 定向修复（内容门族）\n"
            "逐条核对反馈中的引句/数字锚问题（G4.cd/XC 面）：引句声明改到与"
            "正文逐字一致或子句有据；计数/余额声明对齐 facts 现值。"
            "禁止为过门改写正文事实。\n"
        )
    return ""
