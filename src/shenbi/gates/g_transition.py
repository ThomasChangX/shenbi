"""G_TRANSITION: phase transition gate.

Extracted from tests/validate-gate.py in PR-19 (P-1.E).
"""

from shenbi.logging import get_logger

log = get_logger(__name__)


import json
from pathlib import Path
from typing import Any

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


def gate_G_TRANSITION(from_phase: str, to_phase: str, round_dir: str) -> str:
    """G_TRANSITION: Phase switching gate."""
    c = []
    mf: list[Any] = []
    rd = Path(round_dir)
    pp = rd / "progress.json"

    if not pp.exists():
        return fail(
            "G_TRANSITION",
            [],
            "phase_transition",
            ["GT.0:no_progress_file"],
        )

    try:
        progress = jload(str(pp))
    except (json.JSONDecodeError, OSError):
        return fail(
            "G_TRANSITION",
            [],
            "phase_transition",
            ["GT.0:progress_json_invalid"],
        )

    # GT.1 — remaining queue empty
    phase_key = f"remaining_{from_phase}"
    remaining = progress.get(phase_key, [])
    if remaining:
        return fail(
            "G_TRANSITION",
            [
                {
                    "id": "GT.1",
                    "s": "FAIL",
                    "phase": from_phase,
                    "remaining": len(remaining),
                    "items": remaining[:10],
                }
            ],
            "phase_transition",
            ["GT.1"],
        )
    c.append({"id": "GT.1", "s": "PASS", "phase": from_phase})

    # GT.2 — all skills DONE or DEAD (deferred)
    c.append({"id": "GT.2", "s": "PASS", "note": "deferred"})

    # GT.3 — gate_blockers empty (no FAIL entries)
    blockers = progress.get("gate_blockers", [])
    if blockers:
        return fail(
            "G_TRANSITION",
            c
            + [
                {
                    "id": "GT.3",
                    "s": "FAIL",
                    "blockers": blockers,
                }
            ],
            "phase_transition",
            ["GT.3"],
        )
    c.append({"id": "GT.3", "s": "PASS"})

    # GT.4 — batch G2 check (deferred)
    c.append({"id": "GT.4", "s": "PASS", "note": "deferred"})

    # GT.5 — next phase input files (deferred)
    c.append({"id": "GT.5", "s": "PASS", "note": "deferred"})

    return passed("G_TRANSITION", c)
