"""Starvation-marker word families and the verdict-line anchor (spec #109).

Single source for the T4 production gate and the replay/baseline tool —
the spec's prose is a gloss, never authoritative (spec appendix A; erratum).
The families are Chinese corpus data (the measured vocabulary), kept verbatim
from the baseline tool that established the pinned manifest.
"""

from __future__ import annotations

import re

NARROW6: tuple[str, ...] = ("待补", "不适用", "无法核对", "附条件", "待正文核验", "正文未提供")
WIDE12: tuple[str, ...] = (
    *NARROW6,
    "待核验",
    "无法验证",
    "无法评估",
    "正文缺失",
    "未能提供",
    "未提供正文",
)
# spec #109 T4 production-gate variants — NOT part of baseline metrics: the
# replay comparisons stay pinned to narrow6/wide12.
T4_VARIANTS: tuple[str, ...] = ("待核", "暂记", "留待后续核验", "建议复核", "数据未注入")
PRODUCTION_FAMILY: tuple[str, ...] = (*NARROW6, *T4_VARIANTS)
# Line-anchored bold verdict form. TWO consumption modes share this ONE
# regex (spec I1 双锚定): baseline/replay = FIRST match per file;
# production gate = ALL matches' value segments. A third anchor form is
# forbidden (spec appendix A).
VERDICT_LINE_RE: re.Pattern[str] = re.compile(
    r"^\s*(?:[-*>|#]+\s*)?\*\*判定\*\*\s*[：:]\s*(.*)$", re.MULTILINE
)
