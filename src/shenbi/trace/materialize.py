"""materialize_progress：progress.json 降级为 trace 派生视图（spec 支柱四）。
重放 INIT/MARK_DONE 重建 progress dict，经 safe_write 落盘。语义对齐
update_progress.py（三个 test_type 均 done/skip → completed）。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from shenbi.safe_write import safe_write
from shenbi.trace.replay import replay

_TEST_TYPES = ("generative", "bug-hunt", "clean")


def _as_int(value: object, default: int) -> int:
    return int(value) if isinstance(value, (int, float, str)) else default


def _as_float(value: object, default: float) -> float:
    return float(value) if isinstance(value, (int, float)) else default


def _empty_skill() -> dict[str, dict[str, Any]]:
    """Match update_progress.cmd_init: every skill starts three-phase pending."""
    return {tt: {"status": "pending"} for tt in _TEST_TYPES}


def materialize_progress(
    round_dir: Path,
    *,
    total_skills: list[str],
    tier: str = "T1",
    expected_chapters: int = 67,
) -> dict[str, Any]:
    """Reconstruct progress.json from trace (I1/I2 fix: match update_progress semantics).

    Per-phase queues (NOT total - genuinely_done): remaining_generative = skills
    not done on generative specifically. Skills sub-structure defaults to
    three-pending (not empty) for unmarked skills — matches cmd_init.
    """
    events = replay(round_dir)
    skills_state: dict[str, dict[str, dict[str, Any]]] = {}
    init_tier, init_chapters = tier, expected_chapters
    done_counter = 0
    for e in events:
        if e.action == "INIT":
            payload = e.payload
            init_tier = str(payload.get("tier", tier))
            init_chapters = _as_int(payload.get("expected_chapters"), expected_chapters)
        elif e.action == "MARK_DONE":
            payload = e.payload
            skill = str(payload.get("skill"))
            tt = str(payload.get("test_type"))
            sd = skills_state.setdefault(skill, _empty_skill())  # I2: default three-pending
            sd[tt] = {
                "status": str(payload.get("status", "done")),
                "score": _as_float(payload.get("score"), 0.0),
            }
            if sd[tt]["status"] in ("done", "skip"):
                done_counter += 1

    all_skills_set = set(total_skills)

    # I1 fix: per-phase pending (mirror cmd_rebuild_queues semantics)
    def _pending(test_type: str) -> set[str]:
        return all_skills_set - {
            sn
            for sn, sd in skills_state.items()
            if sd.get(test_type, {}).get("status") in ("done", "skip")
        }

    genuinely_done = sorted(
        all_skills_set - (_pending("generative") | _pending("bug-hunt") | _pending("clean"))
    )
    # I2 fix: unmarked skills get three-pending structure (not empty)
    skills_full = {skill: skills_state.get(skill, _empty_skill()) for skill in sorted(total_skills)}
    out: dict[str, Any] = {
        "round": Path(round_dir).name.split("-")[1] if "round-" in str(round_dir) else "???",
        "tier": init_tier,
        "test_cycle_phase": "generative",
        "subagent_completion_count": done_counter,
        "completed_skill_names": genuinely_done,
        "skills": skills_full,
        "remaining_generative": sorted(_pending("generative")),
        "remaining_bug_hunt": sorted(_pending("bug-hunt")),
        "remaining_clean": sorted(_pending("clean")),
        "gate_blockers": [],
        "total_framework_skills": len(total_skills),
        "expected_chapters": init_chapters,
    }
    safe_write(
        Path(round_dir) / "progress.json",
        json.dumps(out, indent=2, ensure_ascii=False),
        round_dir=Path(round_dir),
        trace_action="MATERIALIZE",
        trace_target="progress.json",
    )
    return out
