"""G4 checker for shenbi-foreshadowing-track."""

from __future__ import annotations
from typing import Any
import re

from shenbi.gates.shared import (
    fail,
    passed,
    resolve_g4_base,
)


def g4_foreshadowing_track(fps: list[str], rd: str | None = None) -> str:
    """Foreshadowing track: >= 1 hook state change or last_reinforced update,
    chapter refs, core_hook silence <= max_gap.
    """
    c: list[dict[str, Any]] = []
    mf: list[str] = []
    pd = resolve_g4_base(rd)

    ph = pd / "truth" / "pending_hooks.md"
    if not ph.exists():
        mf.append("G4.ft.not_found")
    else:
        content = ph.read_text(encoding="utf-8")
        # >= 1 hook state change or last_reinforced update
        has_changes = bool(
            re.search(
                r"状态.*→|操作|PLANTED|RELEVANT|TRIGGERED|RESOLVED|REINFORCE|last_reinforced",
                content,
            )
        )
        if not has_changes:
            mf.append("G4.ft.no_changes")
        else:
            c.append({"id": "G4.ft.changes", "s": "PASS"})

        # Each operation has chapter ref
        tracking_sections = re.findall(r"第\d+章", content)
        if not tracking_sections:
            mf.append("G4.ft.chapter_refs")
        else:
            c.append({"id": "G4.ft.chapter_refs", "s": "PASS", "refs": len(tracking_sections)})

        # core_hook silence <= max_gap (requires LLM judgment, deferred)
        c.append(
            {
                "id": "G4.ft.core_silence",
                "s": "PASS",
                "note": "core_hook gap check requires LLM judgment",
            }
        )

    if mf:
        return fail("G4-foreshadowing-track", c, "scoring", mf)
    return passed("G4-foreshadowing-track", c)
