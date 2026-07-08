"""G4 checker for shenbi-anti-detect."""

from __future__ import annotations
from typing import Any
import re
from pathlib import Path

from shenbi.gates.shared import (
    fail,
    passed,
)


def g4_anti_detect(fps: list[str], rd: str | None = None) -> str:
    """Anti-detect: 改写报告 block present, applied techniques listed."""
    c: list[dict[str, Any]] = []
    mf: list[str] = []

    base = Path(rd) if rd else Path.cwd()
    for fp in fps or []:
        pf = base / fp if not Path(fp).is_absolute() else Path(fp)
        if not pf.exists():
            mf.append(f"G4.ad.not_found:{fp}")
            continue

        content = pf.read_text(encoding="utf-8")

        if "## 改写报告" not in content:
            mf.append(f"G4.ad.no_report:{fp}")
        else:
            c.append({"id": "G4.ad.report", "file": fp, "s": "PASS"})

        # Check for applied techniques (table rows or numbered list)
        # Only search within the 改写报告 section to avoid false positives
        report_match = re.search(r"## 改写报告(.+?)(?=\n## |\Z)", content, re.DOTALL)
        report_section = report_match.group(1) if report_match else ""
        has_techniques = bool(
            re.search(r"^\|.*\|.*\|", report_section, re.MULTILINE)
            or re.search(r"^\d+[\.\)、]\s", report_section, re.MULTILINE)
        )

        if has_techniques:
            c.append({"id": "G4.ad.techniques", "file": fp, "s": "PASS"})
        else:
            mf.append(f"G4.ad.no_techniques:{fp}")

    if not fps:
        c.append({"id": "G4.ad", "s": "SKIP", "r": "no files"})

    if mf:
        return fail("G4-anti-detect", c, "scoring", mf)
    return passed("G4-anti-detect", c)
