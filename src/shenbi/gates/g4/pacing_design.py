"""G4 checker for shenbi-pacing-design (rewritten: structured validation).

Uses PacingDesign.from_markdown + model_validate instead of keyword checks.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import ValidationError

from shenbi.contracts.skills.pacing_design import PacingDesign
from shenbi.gates.shared import PROJECT, fail, passed
from shenbi.paths import RoundPaths


def g4_pacing_design(
    fps: list[str],
    rd: str | None = None,
    project_dir: str | None = None,  # threaded by 15a; consumed below (no shadow)
    repo_root: str | None = None,  # threaded by 15a, consumed by 15b
) -> str:
    """Pacing design: structured validation via PacingDesign Pydantic model."""
    c: list[dict[str, Any]] = []
    mf: list[str] = []

    # Resolve the project root without shadowing the threaded project_dir param.
    # Preference order: explicit project_dir > rd > legacy fps[0] heuristic.
    if not project_dir:
        project_dir = rd or (str(Path(fps[0]).parent.parent) if fps else None)

    if rd is None and project_dir is None:
        raise ValueError("round_dir or project_dir required for G4 RoundPaths checkers")
    rp = RoundPaths(
        round_dir=Path(str(rd or project_dir)),
        project_dir=Path(str(project_dir or rd)),
        repo_root=Path(repo_root or PROJECT),
    )

    rhythm_path = rp.read("outline/rhythm_principles.md")
    if not rhythm_path.exists():
        mf.append("G4.rhythm.not_found")
    else:
        content = rhythm_path.read_text(encoding="utf-8")
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
