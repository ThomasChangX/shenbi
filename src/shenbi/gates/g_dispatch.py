"""G_DISPATCH: sub-agent dispatch gate.

Gate validation logic (originally extracted from tests/validate-gate.py in PR-19).
"""

from shenbi.logging import get_logger

log = get_logger(__name__)


import json
from pathlib import Path

from shenbi.gates.shared import (
    ALL_SKILLS,
    fail,
    jload,
    passed,
)


def gate_G_DISPATCH(phase: str, round_dir: str) -> str:
    """G_DISPATCH: Phase completion gate."""
    rd = Path(round_dir)
    pp = rd / "progress.json"

    if not pp.exists():
        return fail(
            "G_DISPATCH",
            [],
            "phase_completion",
            ["GD.0:no_progress_file"],
        )

    try:
        progress = jload(str(pp))
    except (json.JSONDecodeError, OSError):
        return fail(
            "G_DISPATCH",
            [],
            "phase_completion",
            ["GD.0:progress_json_invalid"],
        )

    completed = set(progress.get("completed_skill_names", []))
    all_skills = set(ALL_SKILLS)
    missing = all_skills - completed

    # GD.1 — completed_skill_names == all skills
    if missing:
        return fail(
            "G_DISPATCH",
            [
                {
                    "id": "GD.1",
                    "s": "FAIL",
                    "missing": sorted(missing),
                    "completed": len(completed),
                    "total": len(all_skills),
                }
            ],
            "phase_completion",
            ["GD.1"],
        )
    c = [{"id": "GD.1", "s": "PASS", "completed": len(completed)}]

    # GD.2 / GD.3 — deferred
    c.append({"id": "GD.2", "s": "UNIMPLEMENTED", "note": "PENDING check not yet implemented"})
    c.append({"id": "GD.3", "s": "UNIMPLEMENTED", "note": "DEAD bypass check not yet implemented"})

    return passed("G_DISPATCH", c)
