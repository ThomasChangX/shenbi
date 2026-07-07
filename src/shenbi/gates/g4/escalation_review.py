"""G4 checker for shenbi-escalation-review."""

from __future__ import annotations
from typing import Any

import re
from pathlib import Path

from shenbi.gates.shared import fail, passed


def g4_escalation_review(fps: list[str], rd: str | None = None) -> str:
    """Validate escalation review report has trigger + context + options."""
    c: list[dict[str, Any]] = []
    mf: list[str] = []
    base = Path(rd) if rd else Path.cwd()
    for fp in fps or []:
        pf = base / fp if not Path(fp).is_absolute() else Path(fp)
        if not pf.exists():
            mf.append(f"G4.er.not_found:{fp}")
            continue
        content = pf.read_text(encoding="utf-8")
        normalized = re.sub(r"\s+", "", content)
        for section in ["触发信号", "升级上下文", "决策选项"]:
            if section not in normalized:
                mf.append(f"G4.er.missing_section:{section}")
    if not fps:
        c.append({"id": "G4.er", "s": "SKIP", "r": "no files"})
    if mf:
        return fail("G4-escalation-review", c, "scoring", mf)
    return passed("G4-escalation-review", c)
