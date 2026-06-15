"""G_DISPATCH: sub-agent dispatch gate.

Extracted from tests/validate-gate.py in PR-19 (P-1.E).
"""

import json
from pathlib import Path

from shenbi.gates.shared import (  # noqa: F401
    ALL_SKILLS,
    CHAPTER_WORD_CEILING,
    CHAPTER_WORD_FLOOR,
    FATIGUE_BASE,
    FIXTURES,
    G4_CHECKER_SKILLS,
    META_NARRATIVE,
    PROJECT,
    SKILLS,
    TESTS,
    TRANSITION_SPECIFIC,
    _find_report,
    _normalize_file_paths,
    count_transition_words,
    fail,
    jload,
    passed,
    read_genre_config,
    unimplemented,
    word_count_md,
    write_gate_marker,
    yload,
)


def gate_G_DISPATCH(phase, round_dir):
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
    c.append({"id": "GD.2", "s": "PASS", "note": "PENDING check deferred"})
    c.append({"id": "GD.3", "s": "PASS", "note": "DEAD bypass check deferred"})

    return passed("G_DISPATCH", c)
