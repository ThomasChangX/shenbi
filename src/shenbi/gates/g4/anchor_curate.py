"""G4 checker for shenbi-anchor-curate — AC1 drill scaffold (spec #90).

Minimal thin checker for the add-a-checker editing-surface drill: wired into
build_checkers + the shared.py authoritative roster, then reverted together
with the drill commit.
"""

from __future__ import annotations

from typing import Any

from shenbi.gates.shared import fail, passed


def g4_anchor_curate(fps: list[str], rd: str | None = None, project_dir: str | None = None) -> str:
    """Drill wiring check: always PASS — the drill validates roster plumbing only."""
    c: list[dict[str, Any]] = [{"check": "G4.anchor-curate drill wiring", "ok": True}]
    mf: list[str] = []
    if not fps:
        mf.append("G4.anchor-curate.no_input")
    if mf:
        return fail("G4-anchor-curate", c, "drill", mf)
    return passed("G4-anchor-curate", c)
