"""G_RECONCILE: reconciliation gate.

Gate validation logic (originally extracted from tests/validate-gate.py in PR-19).
"""

from shenbi.logging import get_logger

log = get_logger(__name__)


from pathlib import Path
from typing import Any

from shenbi.gates.shared import (
    ALL_SKILLS,
    find_report,
    fail,
    jload,
    passed,
)


def gate_G_RECONCILE(round_dir: str | None = None) -> str:
    """G_RECONCILE: Mid-execution filesystem consistency check."""
    c: list[Any] = []
    mf: list[Any] = []
    rd = Path(round_dir) if round_dir else None
    if not rd:
        return fail("G_RECONCILE", [], "reconcile", ["no_round_dir"])
    pp = rd / "progress.json"
    if not pp.exists():
        return fail("G_RECONCILE", [], "reconcile", ["no_progress"])
    progress = jload(str(pp))
    skills = progress.get("skills", {})
    # GR.1: DONE skills have t1-reports/ files
    for sn, sd in skills.items():
        if not isinstance(sd, dict):
            continue
        for tt, td in sd.items():
            if isinstance(td, dict) and td.get("status") == "DONE":
                report = find_report(rd / "t1-reports", sn, tt)
                if not report or not report.exists():
                    mf.append(f"GR.1:{sn}-{tt}:no_report")
    # GR.2: reports on disk have DONE status in progress
    # Use robust rsplit to handle skill names with hyphens (e.g. shenbi-story-architecture)
    # and test_types with hyphens (e.g. bug-hunt)
    reports_dir = rd / "t1-reports"
    if reports_dir.exists():
        for rp in reports_dir.glob("*.json"):
            stem = rp.stem
            matched = False
            for n_split in range(1, 6):
                parts = stem.rsplit("-", n_split)
                if len(parts) < 2:
                    continue
                candidate_skill = parts[0]
                candidate_tt = "-".join(parts[1:])
                if candidate_skill in ALL_SKILLS:
                    matched = True
                    td = skills.get(candidate_skill, {}).get(candidate_tt, {})
                    if isinstance(td, dict) and td.get("status") != "DONE":
                        mf.append(f"GR.2:{rp.stem}:status={td.get('status', '?')}")
                    break
            if not matched:
                c.append(
                    {
                        "id": "GR.2",
                        "file": rp.name,
                        "s": "SKIP",
                        "r": "cannot parse skill/test_type from filename",
                    }
                )

    # GR.3 / GR.4 — deferred
    c.append(
        {"id": "GR.3", "s": "UNIMPLEMENTED", "note": "cross-file hash check not yet implemented"}
    )
    c.append(
        {"id": "GR.4", "s": "UNIMPLEMENTED", "note": "agent trace consistency not yet implemented"}
    )
    if mf:
        return fail("G_RECONCILE", c, "reconcile", mf)
    return passed("G_RECONCILE", c)
