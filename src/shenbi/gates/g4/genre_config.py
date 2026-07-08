"""G4 checker for shenbi-genre-config (rewritten: structured Pydantic validation).

Replaces keyword-existence checks with model_validate. Any constraint
violation becomes a G4 FAIL.
"""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from shenbi.contracts.skills.genre_config import GenreConfig
from pathlib import Path

from shenbi.gates.shared import fail, jload, passed


def g4_genre_config(
    fps: list[str],
    rd: str | None = None,
    project_dir: str | None = None,  # threaded by 15a, consumed by 15b
    repo_root: str | None = None,  # threaded by 15a, consumed by 15b
) -> str:
    """Genre config: structured validation via GenreConfig Pydantic model."""
    c: list[dict[str, Any]] = []
    mf: list[str] = []
    gc_path = str(Path(rd) / fps[0]) if rd and fps else (fps[0] if fps else "")

    if not gc_path:
        mf.append("G4.gc.no_input")
    else:
        try:
            data = jload(gc_path)
            try:
                GenreConfig.model_validate(data)
                c.append({"id": "G4.gc.validated", "s": "PASS"})
            except ValidationError as e:
                errors = e.errors()
                for err in errors[:5]:
                    mf.append(f"G4.gc.{err['loc']}: {err['msg']}")
        except Exception:
            mf.append("G4.gc.invalid_json")

    if mf:
        return fail("G4-genre-config", c, "scoring", mf)
    return passed("G4-genre-config", c)
