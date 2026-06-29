"""G4 checker for shenbi-memory-distill (traceability validation)."""

from __future__ import annotations

import re
from pathlib import Path

from shenbi.gates.shared import fail, passed


def g4_memory_distill(fps: list[str], rd: str | None = None) -> str:
    """Validate arc/strata output has traceability (chapter refs) + required sections."""
    c, mf = [], []
    for fp in fps or []:
        p = Path(fp)
        if not p.exists():
            mf.append(f"G4.md.not_found:{fp}")
            continue
        content = p.read_text(encoding="utf-8")
        if not re.search(r"第\d+章|chapter.*\d+", content):
            mf.append("G4.md.no_chapter_ref:distillation must reference chapter numbers")
        if "arc" in fp.lower() or "arcs" in fp.lower():
            for section in ["事件链", "伏笔", "角色状态"]:
                if section not in content:
                    mf.append(f"G4.md.missing_section:{section}")
    if not fps:
        c.append({"id": "G4.md", "s": "SKIP", "r": "no files"})
    if mf:
        return fail("G4-memory-distill", c, "scoring", mf)
    return passed("G4-memory-distill", c)
