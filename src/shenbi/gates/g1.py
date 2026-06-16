"""G1: input validation gate.

Extracted from tests/validate-gate.py in PR-19 (P-1.E).
"""

from shenbi.logging import get_logger

log = get_logger(__name__)


import json
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from shenbi.gates.shared import (
    normalize_file_paths,
    fail,
    jload,
    passed,
    yload,
)


def gate_G1(
    skill_name: str | None = None,
    input_files: str | list[str] | None = None,
    round_dir: str | None = None,
) -> str:
    """G1: Pre-dispatch input validation."""
    c: list[Any] = []
    mf: list[Any] = []

    # Normalize input_files (accept JSON string, list, or comma-separated string)
    if isinstance(input_files, str):
        try:
            input_files = json.loads(input_files)
        except (json.JSONDecodeError, ValueError):
            pass
    fps = normalize_file_paths(input_files)
    rd = Path(round_dir) if round_dir else None

    # In-place modifying skills that need .bak creation
    inplace_skills = {
        "shenbi-faction-builder",
        "shenbi-location-builder",
        "shenbi-relationship-map",
        "shenbi-volume-outlining",
        "shenbi-power-system",
        "shenbi-foreshadowing-track",
        "shenbi-truth-sync",
        "shenbi-state-settling",
        "shenbi-genre-config",
    }

    for fp in fps:
        p = Path(fp)

        # G1.1 — file exists and non-empty
        if not p.exists():
            mf.append({"id": "G1.1", "file": fp, "s": "FAIL", "r": "not found"})
            continue
        if p.stat().st_size == 0:
            mf.append({"id": "G1.1", "file": fp, "s": "FAIL", "r": "empty"})
            continue
        c.append({"id": "G1.1", "file": fp, "s": "PASS"})

        # G1.2 — JSON files parse successfully
        if fp.endswith(".json"):
            try:
                jload(fp)
                c.append({"id": "G1.2", "file": fp, "s": "PASS"})
            except (json.JSONDecodeError, OSError):
                mf.append({"id": "G1.2", "file": fp, "s": "FAIL", "r": "JSON parse error"})

        # G1.3 — YAML frontmatter parses successfully
        if fp.endswith(".md"):
            try:
                fm = yload(fp)
                c.append({"id": "G1.3", "file": fp, "s": "PASS", "has_fm": bool(fm)})
            except Exception:
                mf.append({"id": "G1.3", "file": fp, "s": "FAIL", "r": "YAML parse error"})

        # G1.4 — create .bak for in-place modifying skills
        if skill_name in inplace_skills and rd:
            bak_path = Path(str(fp) + ".bak")
            if not bak_path.exists():
                try:
                    shutil.copy2(fp, str(bak_path))
                    c.append({"id": "G1.4", "file": fp, "s": "PASS", "r": ".bak created"})
                except OSError:
                    mf.append({"id": "G1.4", "file": fp, "s": "FAIL", "r": "cannot create .bak"})
            else:
                c.append({"id": "G1.4", "file": fp, "s": "PASS", "r": ".bak exists"})
        elif skill_name not in inplace_skills:
            c.append({"id": "G1.4", "file": fp, "s": "SKIP", "r": "not in-place skill"})

    # G1.5 — file lock check (round-level .gate-lock file)
    if rd:
        lock_path = rd / ".gate-lock"
        if lock_path.exists():
            age = datetime.now(UTC).timestamp() - lock_path.stat().st_mtime
            if age <= 300:
                mf.append({"id": "G1.5", "s": "FAIL", "r": f"lock active ({age:.0f}s old)"})
            else:
                c.append({"id": "G1.5", "s": "PASS", "r": f"stale lock ({age:.0f}s, >300s)"})
        else:
            c.append({"id": "G1.5", "s": "PASS", "r": "no lock file"})
    else:
        c.append({"id": "G1.5", "s": "SKIP", "r": "no round_dir"})

    # G1.6 — scoring_history check for scorer agent_id
    if rd:
        pp = rd / "progress.json"
        if pp.exists():
            try:
                progress = jload(str(pp))
                scoring_history = progress.get("scoring_history", [])
                if isinstance(scoring_history, list):
                    c.append(
                        {
                            "id": "G1.6",
                            "s": "PASS",
                            "note": f"scoring_history: {len(scoring_history)} entries",
                        }
                    )
                else:
                    c.append({"id": "G1.6", "s": "WARN", "r": "scoring_history not a list"})
            except (json.JSONDecodeError, OSError):
                c.append({"id": "G1.6", "s": "SKIP", "r": "progress.json unreadable"})
        else:
            c.append({"id": "G1.6", "s": "SKIP", "r": "no progress.json"})
    else:
        c.append({"id": "G1.6", "s": "SKIP", "r": "no round_dir"})

    if not fps:
        c.append({"id": "G1.0", "s": "SKIP", "r": "no input files"})

    if mf:
        return fail(
            "G1",
            c,
            "subagent_dispatch",
            [x["id"] + ":" + x.get("file", x.get("r", "")) for x in mf],
        )
    return passed("G1", c)
