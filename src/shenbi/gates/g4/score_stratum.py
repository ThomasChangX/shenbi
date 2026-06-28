"""G4 checker for shenbi-score-stratum."""
from __future__ import annotations

import re
from pathlib import Path

from shenbi.gates.shared import fail, passed


def g4_score_stratum(fps: list[str], rd: str | None = None) -> str:
    """Validate shenbi-score-stratum output has Route C + Route A sections."""
    c, mf = [], []
    for fp in fps or []:
        p = Path(fp)
        if not p.exists():
            mf.append(f"G4.not_found:{fp}")
            continue
        content = p.read_text(encoding="utf-8")
        if "Route C" not in content:
            mf.append("G4.no_route_c:must have Route C section")
        if "Route A" not in content and "锚点" not in content:
            mf.append("G4.no_route_a:must have Route A anchor section")
    if not fps:
        c.append({"id": "G4", "s": "SKIP", "r": "no files"})
    if mf:
        return fail("G4-score-stratum", c, "scoring", mf)
    return passed("G4-score-stratum", c)
