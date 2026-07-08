"""G4 checker for shenbi-pacing-design (rewritten: structured validation).

Uses PacingDesign.from_markdown + model_validate instead of keyword checks.
"""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from shenbi.contracts.skills.pacing_design import PacingDesign
from shenbi.gates.shared import fail, passed


def g4_pacing_design(
    fps: list[str],
    rd: str | None = None,
    project_dir: str | None = None,  # threaded by 15a, consumed by 15b
    repo_root: str | None = None,  # threaded by 15a, consumed by 15b
) -> str:
    """Pacing design: structured validation via PacingDesign Pydantic model."""
    c: list[dict[str, Any]] = []
    mf: list[str] = []

    rp = None
    if fps:
        from pathlib import Path

        project_dir = rd if rd else str(Path(fps[0]).parent.parent)
        rp = Path(project_dir) / "outline" / "rhythm_principles.md"

    if not rp or not rp.exists():
        mf.append("G4.rhythm.not_found")
    else:
        content = rp.read_text(encoding="utf-8")
        try:
            model = PacingDesign.from_markdown(content)
            if not model.beats:
                mf.append("G4.pd.no_beat_data")
            else:
                c.append({"id": "G4.pd.validated", "s": "PASS"})
        except ValidationError as e:
            for err in e.errors()[:5]:
                mf.append(f"G4.pd.{err['loc']}: {err['msg']}")

    if mf:
        return fail("G4-pacing-design", c, "scoring", mf)
    return passed("G4-pacing-design", c)
