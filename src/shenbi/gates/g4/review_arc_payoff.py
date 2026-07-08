"""G4 checker for shenbi-review-arc-payoff.

Validates the arc-payoff scoring report carries the structured signal the
spec §6.4 gate depends on: a 5-dimension 评分明细 table with the required
column set, all five dimension rows, a 门判定 section with a valid verdict,
an explicit 伏笔兑现质量 ≥15 sub-floor check, and file+line evidence.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from shenbi.gates.shared import (
    fail,
    passed,
    resolve_input_path,
)

# Required 评分明细 columns. The header row is matched as a whole so the
# table must carry every column regardless of order or extra columns.
_DETAIL_COLS = ("维度", "得分", "满分", "置信度", "证据", "裁判理由")

# All five arc-payoff dimensions must appear as rows in the 评分明细 table.
_DIMS = ("弧情感交付", "伏笔兑现质量", "线索收束", "期待债务结算", "角色弧推进")

# Accepted 门判定 verdicts (spec §6.4: pass -> 放行, block -> 阻断+处方).
_VERDICTS = ("放行", "阻断")

# The 伏笔兑现质量 sub-floor: the report's 门判定 section must evaluate it
# against the §6.4 floor of 15 (e.g. "伏笔兑现质量 18 ≥ 子地板 15 ✓").
_FORESHADOW_FLOOR_RE = re.compile(r"伏笔兑现质量.{0,30}?15", re.DOTALL)


def g4_review_arc_payoff(
    fps: list[str],
    rd: str | None = None,
    project_dir: str | None = None,  # threaded by 15a, consumed by 15b
    repo_root: str | None = None,  # threaded by 15a, consumed by 15b
) -> str:
    """review-arc-payoff: 5-dim 评分明细 table, 门判定 verdict,
    伏笔兑现质量 ≥15 sub-floor, and file+line evidence.
    """
    c: list[dict[str, Any]] = []
    mf: list[str] = []

    for fp in fps or []:
        pf = resolve_input_path(fp, rd)
        if not pf.exists():
            mf.append(f"G4.ap.not_found:{fp}")
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
            mf.append(f"G4.ap.detail_table:{Path(fp).name}:missing_{missing_cols}")
        else:
            c.append({"id": "G4.ap.detail_table", "file": fp, "s": "PASS"})

        # 2. All five dimensions appear as rows in the 评分明细 table.
        missing_dims = [d for d in _DIMS if d not in detail_section]
        if missing_dims:
            mf.append(f"G4.ap.dims:{Path(fp).name}:missing_{missing_dims}")
        else:
            c.append({"id": "G4.ap.dims", "file": fp, "s": "PASS"})

        # 3. 门判定 section with a 判定 line carrying a valid verdict.
        has_gate = "门判定" in content
        verdict = None
        verdict_match = re.search(r"判定\s*[:：]\s*(\S+)", content)
        if verdict_match:
            for v in _VERDICTS:
                if verdict_match.group(1).startswith(v):
                    verdict = v
                    break
        if not has_gate or verdict is None:
            mf.append(f"G4.ap.verdict:{Path(fp).name}:no_valid_verdict")
        else:
            c.append({"id": "G4.ap.verdict", "file": fp, "s": "PASS", "v": verdict})

        # 4. 伏笔兑现质量 sub-floor: the 门判定 section must evaluate the
        #    伏笔兑现质量 dimension against the §6.4 floor of 15.
        gate_section = content.split("门判定", 1)[1] if has_gate else ""
        if not _FORESHADOW_FLOOR_RE.search(gate_section):
            mf.append(f"G4.ap.foreshadow_floor:{Path(fp).name}:no_subfloor_check")
        else:
            c.append({"id": "G4.ap.foreshadow_floor", "file": fp, "s": "PASS"})

        # 5. Evidence must carry at least one file + line reference
        #    (Lnn / line nn / path:nn). The detail table is the canonical
        #    evidence carrier, so scan the whole report.
        has_location = bool(re.search(r"L\d+|line\s+\d+|:\d+(?!\d)", content, re.IGNORECASE))
        if not has_location:
            mf.append(f"G4.ap.evidence:{Path(fp).name}:no_file_line_ref")
        else:
            c.append({"id": "G4.ap.evidence", "file": fp, "s": "PASS"})

    if not fps:
        c.append({"id": "G4.ap", "s": "SKIP", "r": "no files"})

    if mf:
        return fail("G4-review-arc-payoff", c, "scoring", mf)
    return passed("G4-review-arc-payoff", c)
