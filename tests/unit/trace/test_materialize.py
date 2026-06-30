from __future__ import annotations

import json
from pathlib import Path

from shenbi.trace.materialize import materialize_progress
from shenbi.trace.writer import TraceWriter

SKILLS = ["shenbi-a", "shenbi-b"]


def test_materialize_from_init_and_marks(tmp_path: Path) -> None:
    rd = tmp_path / "round"
    rd.mkdir()
    w = TraceWriter(rd)
    w.append(
        actor="d",
        actor_role="GATE",
        action="INIT",
        target="progress.json",
        payload={"tier": "T1", "expected_chapters": 5},
    )
    for tt in ("generative", "bug-hunt", "clean"):
        w.append(
            actor="d",
            actor_role="GATE",
            action="MARK_DONE",
            target="progress.json",
            payload={"skill": "shenbi-a", "test_type": tt, "score": 94.0, "status": "done"},
        )
    prog = materialize_progress(rd, total_skills=SKILLS)
    assert prog["completed_skill_names"] == ["shenbi-a"]
    assert prog["tier"] == "T1"
    assert json.loads((rd / "progress.json").read_text(encoding="utf-8"))[
        "completed_skill_names"
    ] == ["shenbi-a"]


def test_materialize_empty_trace(tmp_path: Path) -> None:
    rd = tmp_path / "round"
    rd.mkdir()
    prog = materialize_progress(rd, total_skills=SKILLS)
    assert prog["completed_skill_names"] == []
    assert set(prog["remaining_generative"]) == set(SKILLS)
    # I2 fix: unmarked skills get three-pending structure (not empty)
    assert prog["skills"]["shenbi-a"]["generative"]["status"] == "pending"


def test_materialize_partial_skill_per_phase_queue(tmp_path: Path) -> None:
    """I1 fix: per-phase queue. Skill done on generative ONLY should NOT be
    in remaining_generative, but SHOULD be in remaining_bug_hunt/clean.
    """
    rd = tmp_path / "round"
    rd.mkdir()
    w = TraceWriter(rd)
    w.append(
        actor="d",
        actor_role="GATE",
        action="MARK_DONE",
        target="progress.json",
        payload={"skill": "shenbi-a", "test_type": "generative", "score": 94.0, "status": "done"},
    )
    prog = materialize_progress(rd, total_skills=SKILLS)
    # shenbi-a done on generative only -> NOT fully complete, NOT in remaining_generative
    assert "shenbi-a" not in prog["completed_skill_names"]
    assert "shenbi-a" not in prog["remaining_generative"]
    assert "shenbi-a" in prog["remaining_bug_hunt"]  # still pending bug-hunt
    assert "shenbi-a" in prog["remaining_clean"]
