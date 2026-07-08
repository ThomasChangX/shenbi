"""G4 checker for shenbi-plot-thread-weaver."""

from __future__ import annotations
from typing import Any
import re
from pathlib import Path

from shenbi.gates.shared import (
    PROJECT,
    fail,
    passed,
)
from shenbi.paths import RoundPaths


def g4_plot_thread_weaver(
    fps: list[str],
    rd: str | None = None,
    project_dir: str | None = None,  # threaded by 15a, consumed by 15b
    repo_root: str | None = None,  # threaded by 15a, consumed by 15b
) -> str:
    """Plot thread weaver: A/B/C lines, thread advancement table, blank detection."""
    c: list[dict[str, Any]] = []
    mf: list[str] = []
    rp = RoundPaths(
        round_dir=Path(rd or project_dir or "."),
        project_dir=Path(project_dir or rd or "."),
        repo_root=Path(repo_root or PROJECT),
    )

    tm = rp.read("outline/thread_map.md")
    if not tm.exists():
        mf.append("G4.thread.not_found")
    else:
        content = tm.read_text(encoding="utf-8")
        # A线/B线/C线
        lines_found = []
        for label in ["A 长线", "B 中线", "C 短线", "## A", "## B", "## C"]:
            if label in content:
                lines_found.append(label)
        if not lines_found:
            mf.append("G4.pt.lines:missing_A/B/C")
        else:
            c.append({"id": "G4.pt.lines", "s": "PASS", "found": lines_found[:3]})

        # 线索推进表 (table format)
        table_rows = len(re.findall(r"^\|.+\|$", content, re.MULTILINE))
        if table_rows < 3:
            mf.append(f"G4.pt.table:{table_rows}<3")
        else:
            c.append({"id": "G4.pt.table", "s": "PASS", "rows": table_rows})

        # 空白检测
        if "空白" not in content:
            mf.append("G4.pt.blank_detection")
        else:
            c.append({"id": "G4.pt.blank_detection", "s": "PASS"})

    if mf:
        return fail("G4-plot-thread-weaver", c, "scoring", mf)
    return passed("G4-plot-thread-weaver", c)
