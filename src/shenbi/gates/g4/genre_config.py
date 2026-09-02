"""G4 checker for shenbi-genre-config (rewritten: structured Pydantic validation).

Replaces keyword-existence checks with model_validate. Any constraint
violation becomes a G4 FAIL.
"""

from __future__ import annotations
from shenbi.status import GateStatus

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
    # F430 (spec #39 T10): validate EVERY provided file — the old fps[0]
    # silently ignored the rest.
    gc_paths = [str(Path(rd) / f) if rd else f for f in (fps or [])]

    if not gc_paths:
        mf.append("G4.gc.no_input")
    for gc_path in gc_paths:
        try:
            data = jload(gc_path)
            try:
                GenreConfig.model_validate(data)
                c.append({"id": "G4.gc.validated", "file": gc_path, "s": GateStatus.PASS})
            except ValidationError as e:
                errors = e.errors()
                for err in errors[:5]:
                    mf.append(f"G4.gc.{Path(gc_path).name}:{err['loc']}: {err['msg']}")
        except Exception:  # noqa: BLE001 (C13 allowlist: intentional broad catch, structured handling per spec #39 T5)
            mf.append(f"G4.gc.invalid_json:{Path(gc_path).name}")

    if mf:
        return fail("G4-genre-config", c, "scoring", mf)
    return passed("G4-genre-config", c)
