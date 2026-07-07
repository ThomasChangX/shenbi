"""G4 checker for shenbi-state-settling."""

from __future__ import annotations
from typing import Any
import re
from pathlib import Path

from shenbi.gates.shared import (
    fail,
    passed,
)


def g4_state_settling(fps: list[str], rd: str | None = None) -> str:
    """State settling: current_state has position, char_matrix has characters, summaries appended, emotional arcs."""
    c: list[dict[str, Any]] = []
    mf: list[str] = []

    base = Path(rd) if rd else Path.cwd()
    for fp in fps or []:
        pf = base / fp if not Path(fp).is_absolute() else Path(fp)
        if not pf.exists():
            mf.append(f"G4.ss.not_found:{fp}")
            continue

        content = pf.read_text(encoding="utf-8")

        if "current_state" in str(fp):
            # Accept: ## 位置, ### 位置变化, 当前位置, 场景位置, etc.
            if not re.search(r"#{1,4}\s*(位置|当前位置|场景位置|地点)", content):
                c.append(
                    {
                        "id": "G4.ss.position",
                        "file": fp,
                        "s": "WARN",
                        "r": "no position/location heading found",
                    }
                )
            else:
                c.append({"id": "G4.ss.position", "file": fp, "s": "PASS"})

        if "character_matrix" in str(fp):
            # Accept: ## 已登场角色, ## 角色, ## 出场角色, ## 登场人物, ## 人物, etc.
            if not re.search(r"#{1,4}\s*(已登场角色|出场角色|登场人物|角色|人物)", content):
                c.append(
                    {
                        "id": "G4.ss.characters",
                        "file": fp,
                        "s": "WARN",
                        "r": "no character heading found",
                    }
                )
            else:
                c.append({"id": "G4.ss.characters", "file": fp, "s": "PASS"})

        if "chapter_summaries" in str(fp):
            if not re.search(r"#{1,4}\s*第\d+章", content):
                c.append(
                    {
                        "id": "G4.ss.summaries",
                        "file": fp,
                        "s": "WARN",
                        "r": "no chapter summary heading found",
                    }
                )
            else:
                c.append({"id": "G4.ss.summaries", "file": fp, "s": "PASS"})

        if "emotional_arcs" in str(fp):
            if not re.search(r"#{1,4}\s*第\d+章", content):
                c.append(
                    {
                        "id": "G4.ss.arcs",
                        "file": fp,
                        "s": "WARN",
                        "r": "no emotional arc chapter heading found",
                    }
                )
            else:
                c.append({"id": "G4.ss.arcs", "file": fp, "s": "PASS"})

        if "particle_ledger" in str(fp):
            # Accept: 粒子账本, 粒子记录, particle ledger, 账本, etc.
            if not re.search(
                r"(粒子账本|粒子记录|particle.*ledger|账本|资源)", content, re.IGNORECASE
            ):
                c.append(
                    {
                        "id": "G4.ss.particle_ledger",
                        "file": fp,
                        "s": "WARN",
                        "r": "no particle ledger heading found",
                    }
                )
            else:
                c.append({"id": "G4.ss.particle_ledger", "file": fp, "s": "PASS"})

        if "pending_hooks" in str(fp):
            if "state" not in content:
                mf.append(f"G4.ss.no_hook_state:{fp}")
            else:
                c.append({"id": "G4.ss.pending_hooks", "file": fp, "s": "PASS"})

    if not fps:
        c.append({"id": "G4.ss", "s": "SKIP", "r": "no files"})

    if mf:
        return fail("G4-state-settling", c, "scoring", mf)
    return passed("G4-state-settling", c)
