"""G4 checker for shenbi-plot-thread-weaver."""

from __future__ import annotations
from shenbi.status import GateStatus
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
    if rd is None and project_dir is None:
        raise ValueError("round_dir or project_dir required for G4 RoundPaths checkers")
    rp = RoundPaths(  # spec #48 C34: explicit roots, no silent fallthrough
        round_dir=Path(str(rd or project_dir)),
        project_dir=Path(str(project_dir or rd)),
        repo_root=Path(repo_root or PROJECT),
    )

    tm = rp.read("outline/thread_map.md")
    if not tm.exists():
        mf.append("G4.thread.not_found")
    else:
        content = tm.read_text(encoding="utf-8")
        # A/B/C three-tier line presence. Union match: the SKILL.md
        # contract's own vocabulary (铁律 2-4 and the classification
        # headings teach "A 线（长线）"; the summary block teaches
        # "**A 线数**"; the overview table's ID column is `A1/A2/...`) PLUS
        # the legacy literals for backward compatibility. Contract-faithful
        # output must pass (canary escalation #4, 2026-09-28).
        tier_patterns = {
            "A": [
                r"A 长线",
                r"^##\s+A\b",
                r"^#{2,3}\s*A\s*线",
                r"\*\*A\s*线数\*\*",
                r"^\|\s*A\d",
            ],
            "B": [
                r"B 中线",
                r"^##\s+B\b",
                r"^#{2,3}\s*B\s*线",
                r"\*\*B\s*线数\*\*",
                r"^\|\s*B\d",
            ],
            "C": [
                r"C 短线",
                r"^##\s+C\b",
                r"^#{2,3}\s*C\s*线",
                r"\*\*C\s*线数\*\*",
                r"^\|\s*C\d",
            ],
        }
        lines_found = [
            tier
            for tier, patterns in tier_patterns.items()
            if any(re.search(p, content, re.MULTILINE) for p in patterns)
        ]
        if not lines_found:
            mf.append("G4.pt.lines:missing_A/B/C")
        else:
            c.append({"id": "G4.pt.lines", "s": GateStatus.PASS, "found": lines_found[:3]})

        # 线索推进表 (table format)
        table_rows = len(re.findall(r"^\|.+\|$", content, re.MULTILINE))
        if table_rows < 3:
            mf.append(f"G4.pt.table:{table_rows}<3")
        else:
            c.append({"id": "G4.pt.table", "s": GateStatus.PASS, "rows": table_rows})

        # 空白检测
        if "空白" not in content:
            mf.append("G4.pt.blank_detection")
        else:
            c.append({"id": "G4.pt.blank_detection", "s": GateStatus.PASS})

    if mf:
        return fail("G4-plot-thread-weaver", c, "scoring", mf)
    return passed("G4-plot-thread-weaver", c)
