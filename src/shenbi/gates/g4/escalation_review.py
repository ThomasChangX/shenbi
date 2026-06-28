"""G4 checker for shenbi-escalation-review."""
from __future__ import annotations

from pathlib import Path

from shenbi.gates.shared import fail, passed


def g4_escalation_review(fps: list[str], rd: str | None = None) -> str:
    """Validate escalation review report has trigger + context + options."""
    c, mf = [], []
    for fp in fps or []:
        p = Path(fp)
        if not p.exists():
            mf.append(f"G4.er.not_found:{fp}")
            continue
        content = p.read_text(encoding="utf-8")
        for section in ["触发信号", "升级上下文", "决策选项"]:
            if section not in content:
                mf.append(f"G4.er.missing_section:{section}")
    if not fps:
        c.append({"id": "G4.er", "s": "SKIP", "r": "no files"})
    if mf:
        return fail("G4-escalation-review", c, "scoring", mf)
    return passed("G4-escalation-review", c)
