"""G4 checker for shenbi-score-stratum."""

from __future__ import annotations
from typing import Any

import re
from pathlib import Path

from shenbi.gates.shared import fail, passed


def g4_score_stratum(fps: list[str], rd: str | None = None) -> str:
    """Validate shenbi-score-stratum output has Route C + Route A sections."""
    c: list[dict[str, Any]] = []
    mf: list[str] = []
    base = Path(rd) if rd else Path.cwd()
    for fp in fps or []:
        pf = base / fp if not Path(fp).is_absolute() else Path(fp)
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
        return fail("G4-score-stratum", c, "scoring", mf)
    return passed("G4-score-stratum", c)
