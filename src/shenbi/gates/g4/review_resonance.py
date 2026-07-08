"""G4 checker for shenbi-review-resonance.

Validates the resonance scoring report carries the structured signal the
downstream calibration (spec §5) and drift detection (spec §8.3) depend on:
a per-dimension 评分明细 table, a 校准门判定 verdict, and file+line evidence.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from shenbi.gates.shared import (
    fail,
    passed,
)

# Required 评分明细 columns. The header row is matched as a whole so the
# table must carry every column regardless of order or extra columns.
_DETAIL_COLS = ("维度", "得分", "满分", "置信度", "证据", "裁判理由")

# Accepted 校准门 verdicts (spec §5.4 routing: pass / block / human review).
_VERDICTS = ("通过", "阻断", "待人机复核")


def g4_review_resonance(
    fps: list[str],
    rd: str | None = None,
    project_dir: str | None = None,  # threaded by 15a, consumed by 15b
    repo_root: str | None = None,  # threaded by 15a, consumed by 15b
) -> str:
    """review-resonance: 评分明细 table (6 cols), 校准门判定 verdict,
    evidence carrying file+line references.
    """
    c: list[dict[str, Any]] = []
    mf: list[str] = []

    base = Path(rd) if rd else Path.cwd()
    for fp in fps or []:
        pf = base / fp if not Path(fp).is_absolute() else Path(fp)
        if not pf.exists():
            mf.append(f"G4.rr.not_found:{fp}")
            continue

        content = pf.read_text(encoding="utf-8")

        # 1. 评分明细 section with the full 6-column header row.
        has_detail_heading = "评分明细" in content
        detail_section = content.split("评分明细", 1)[1] if has_detail_heading else ""
        header_match = re.search(r"^\|(.+)\|\s*$", detail_section, re.MULTILINE)
        header_cells = (
            [cell.strip() for cell in header_match.group(1).split("|")] if header_match else []
        )
        missing_cols = [col for col in _DETAIL_COLS if col not in header_cells]
        if missing_cols:
            mf.append(f"G4.rr.detail_table:{Path(fp).name}:missing_{missing_cols}")
        else:
            c.append({"id": "G4.rr.detail_table", "file": fp, "s": "PASS"})

        # 2. 校准门判定 section with a 判定 line carrying a valid verdict.
        has_calibration = "校准门判定" in content
        verdict = None
        verdict_match = re.search(r"判定\s*[:：]\s*(\S+)", content)
        if verdict_match:
            for v in _VERDICTS:
                if verdict_match.group(1).startswith(v):
                    verdict = v
                    break
        if not has_calibration or verdict is None:
            mf.append(f"G4.rr.verdict:{Path(fp).name}:no_valid_verdict")
        else:
            c.append({"id": "G4.rr.verdict", "file": fp, "s": "PASS", "v": verdict})

        # 3. Evidence must carry at least one file + line reference
        # (Lnn / line nn / path:nn). The detail table is the canonical
        # evidence carrier, so scan the whole report.
        has_location = bool(re.search(r"L\d+|line\s+\d+|:\d+(?!\d)", content, re.IGNORECASE))
        if not has_location:
            mf.append(f"G4.rr.evidence:{Path(fp).name}:no_file_line_ref")
        else:
            c.append({"id": "G4.rr.evidence", "file": fp, "s": "PASS"})

    if not fps:
        c.append({"id": "G4.rr", "s": "SKIP", "r": "no files"})

    if mf:
        return fail("G4-review-resonance", c, "scoring", mf)
    return passed("G4-review-resonance", c)
