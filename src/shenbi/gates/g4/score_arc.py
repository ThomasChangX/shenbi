"""G4 checker for shenbi-score-arc."""

from __future__ import annotations
from typing import Any

import re

from shenbi.gates.shared import fail, passed, resolve_input_path


def g4_score_arc(
    fps: list[str],
    rd: str | None = None,
    project_dir: str | None = None,  # threaded by 15a, consumed by 15b
    repo_root: str | None = None,  # threaded by 15a, consumed by 15b
) -> str:
    """Validate shenbi-score-arc output has Route C + Route A sections."""
    c: list[dict[str, Any]] = []
    mf: list[str] = []
    for fp in fps or []:
        pf = resolve_input_path(fp, rd)
        if not pf.exists():
            mf.append(f"G4.not_found:{fp}")
            continue
        content = pf.read_text(encoding="utf-8")
        normalized = re.sub(r"\s+", "", content)
        if "RouteC" not in normalized:
            mf.append("G4.no_route_c:must have Route C section")
        if "RouteA" not in normalized and "锚点" not in content:
            mf.append("G4.no_route_a:must have Route A anchor section")
    if not fps:
        c.append({"id": "G4", "s": "SKIP", "r": "no files"})
    if mf:
        return fail("G4-score-arc", c, "scoring", mf)
    return passed("G4-score-arc", c)
