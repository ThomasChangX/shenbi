"""G4 checker for shenbi-relationship-map."""

from __future__ import annotations
from typing import Any
import re

from shenbi.gates.shared import (
    fail,
    passed,
    resolve_g4_base,
)


def g4_relationship_map(fps: list[str], rd: str | None = None) -> str:
    """Relationship map: >= 3 pairs, each with interest foundation, info boundary enum,
    evolution trajectory.
    """
    c: list[dict[str, Any]] = []
    mf: list[str] = []
    pd = resolve_g4_base(rd)

    rel_path = pd / "characters" / "relationships.md"
    if not rel_path.exists():
        mf.append("G4.rel.not_found")
    else:
        content = rel_path.read_text(encoding="utf-8")
        pairs = re.findall(r"#{2,3}\s*关系对[：:]", content)
        if len(pairs) < 3:
            mf.append(f"G4.rm.pairs:{len(pairs)}<3")
        else:
            c.append({"id": "G4.rm.pairs", "s": "PASS", "count": len(pairs)})
            valid = 0
            boundary_enums = {"SYMMETRIC", "ASYMMETRIC", "ISOLATED", "MUTUAL_SECRET"}
            for match in re.finditer(
                r"#{2,3}\s*关系对[：:].*?\n(?=#{2,3}\s*关系对|\Z)", content, re.DOTALL
            ):
                pair_text = match.group()
                has_interest = bool(re.search(r"\*\*利益根基\*\*[：:]\s*\S", pair_text))
                has_boundary = any(e in pair_text for e in boundary_enums)
                has_evolution = bool(re.search(r"演化轨迹|起始状态|预期终态", pair_text))
                if has_interest and has_boundary and has_evolution:
                    valid += 1
            if valid < 3:
                mf.append(f"G4.rm.complete:{valid}/{len(pairs)}")
            else:
                c.append({"id": "G4.rm.complete", "s": "PASS", "complete": valid})

    # truth/character_matrix.md: must exist (SKILL.md Updates target)
    cm_path = pd / "truth" / "character_matrix.md"
    if cm_path.exists():
        cm_content = cm_path.read_text(encoding="utf-8")
        if len(cm_content.strip()) > 0:
            c.append({"id": "G4.rm.character_matrix", "s": "PASS"})
        else:
            mf.append("G4.rm.character_matrix.empty")
    else:
        mf.append("G4.rm.character_matrix.not_found")

    if mf:
        return fail("G4-relationship-map", c, "scoring", mf)
    return passed("G4-relationship-map", c)
