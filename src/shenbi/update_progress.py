#!/usr/bin/env python3
"""Single-writer progress.json updater with built-in consistency validation.

Usage:
    update-progress.py init <round_dir> <tier>
    update-progress.py mark-done <round_dir> <skill> <test_type> <score> [--note SKIP]
    update-progress.py validate <round_dir>
    update-progress.py rebuild-queues <round_dir>
"""

import json
import sys
from pathlib import Path
from typing import Any, cast

from shenbi.cli_utils import emit_json
from shenbi.logging import configure_logging, get_logger

log = get_logger(__name__)

PROJECT = Path(__file__).resolve().parents[2]
SKILLS = PROJECT / "skills"
ALL_SKILLS = (
    sorted(d.name for d in SKILLS.iterdir() if d.is_dir() and (d / "SKILL.md").exists())
    if SKILLS.exists()
    else []
)


def load(round_dir: str) -> dict[str, Any]:
    pp = Path(round_dir) / "progress.json"
    if not pp.exists():
        emit_json({"error": "progress.json not found", "round_dir": str(round_dir)})
        sys.exit(1)
    return cast(dict[str, Any], json.loads(pp.read_text(encoding="utf-8")))


def save(round_dir: str, data: dict[str, Any]) -> None:
    pp = Path(round_dir) / "progress.json"
    pp.write_text(json.dumps(data, indent=2, ensure_ascii=False))


def validate_internal(
    progress: dict[str, Any], label: str = "validate"
) -> tuple[list[str], set[str], dict[str, int]]:
    """Return (issues, genuinely_done_set)."""
    issues: list[str] = []
    completed = set(progress.get("completed_skill_names", []))
    skills = progress.get("skills", {})
    _total = progress.get("total_framework_skills", len(ALL_SKILLS))

    genuinely_done: set[str] = set()
    partly_done: dict[str, int] = {}
    for sn, sd in skills.items():
        if not isinstance(sd, dict):
            continue
        done_count = 0
        for tt in ("generative", "bug-hunt", "clean"):
            td = cast(dict[str, Any], sd.get(tt, {}))
            if td.get("status") in ("done", "skip"):
                done_count += 1
        if done_count == 3:
            genuinely_done.add(sn)
        elif done_count > 0:
            partly_done[sn] = done_count

    if completed != genuinely_done:
        issues.append(
            f"completed_skill_names ({len(completed)}) != genuinely done ({len(genuinely_done)})"
        )
        extra = completed - genuinely_done
        missing = genuinely_done - completed
        if extra:
            issues.append(f"  in completed but not done: {sorted(extra)}")
        if missing:
            issues.append(f"  done but not in completed: {sorted(missing)}")

    remaining_gen = set(progress.get("remaining_generative", []))
    remaining_bug = set(progress.get("remaining_bug_hunt", []))
    remaining_cln = set(progress.get("remaining_clean", []))

    expected_pending = set(ALL_SKILLS) - genuinely_done
    all_remaining_from_queues = remaining_gen | remaining_bug | remaining_cln

    if expected_pending and not all_remaining_from_queues:
        issues.append(f"expected {len(expected_pending)} remaining skills but all queues are empty")

    if expected_pending and all_remaining_from_queues:
        queue_diff = expected_pending - all_remaining_from_queues
        extra_in_queue = all_remaining_from_queues - expected_pending
        if queue_diff:
            issues.append(f"skills missing from all queues: {sorted(queue_diff)}")
        if extra_in_queue:
            issues.append(f"skills in queues but already done: {sorted(extra_in_queue)}")

    return issues, genuinely_done, partly_done


def cmd_init(round_dir: str, tier: str, expected_chapters: int | None = None) -> None:
    rd = Path(round_dir)
    rd.mkdir(parents=True, exist_ok=True)
    pp = rd / "progress.json"

    if pp.exists():
        emit_json(
            {"status": "error", "message": "progress.json already exists — use validate instead"}
        )
        sys.exit(1)

    total = len(ALL_SKILLS)
    if expected_chapters is None:
        expected_chapters = 67  # default; G0.3 will recalculate
    for sub in ["t1-reports", "t2-reports", "t3-reports", "skill-output", "skill-traces"]:
        (rd / sub).mkdir(parents=True, exist_ok=True)
    for sub in ["gate-markers", "phase-state"]:
        (rd / sub).mkdir(parents=True, exist_ok=True)

    out: dict[str, Any] = {
        "round": Path(round_dir).name.split("-")[1] if "round-" in str(round_dir) else "???",
        "tier": tier,
        "test_cycle_phase": "generative",
        "subagent_completion_count": 0,
        "completed_skill_names": [],
        "skills": {},
        "remaining_generative": sorted(ALL_SKILLS),
        "remaining_bug_hunt": [],
        "remaining_clean": [],
        "gate_blockers": [],
        "total_framework_skills": total,
        "expected_chapters": expected_chapters,
    }
    save(round_dir, out)
    emit_json(
        {
            "status": "ok",
            "action": "init",
            "total_skills": total,
            "expected_chapters": expected_chapters,
        }
    )


def cmd_mark_done(
    round_dir: str, skill: str, test_type: str, score: float, note: str | None = None
) -> None:
    progress = load(round_dir)
    skills = progress.setdefault("skills", {})
    sd = skills.setdefault(skill, {})

    entry = {"status": "skip" if note else "done", "score": float(score)}
    if note:
        entry["note"] = str(note)
    sd[test_type] = entry

    genuinely_done: set[str] = set()
    for sn, sdata in skills.items():
        if not isinstance(sdata, dict):
            continue
        if all(
            isinstance(sdata.get(tt, {}), dict)
            and sdata.get(tt, {}).get("status") in ("done", "skip")
            for tt in ("generative", "bug-hunt", "clean")
        ):
            genuinely_done.add(sn)

    progress["completed_skill_names"] = sorted(genuinely_done)
    progress["subagent_completion_count"] = progress.get("subagent_completion_count", 0) + 1

    all_skills = set(ALL_SKILLS)
    pending_gen = all_skills - {
        s
        for s, sdata in skills.items()
        if isinstance(sdata, dict)
        and isinstance(sdata.get("generative", {}), dict)
        and sdata.get("generative", {}).get("status") in ("done", "skip")
    }
    pending_bug = all_skills - {
        s
        for s, sdata in skills.items()
        if isinstance(sdata, dict)
        and isinstance(sdata.get("bug-hunt", {}), dict)
        and sdata.get("bug-hunt", {}).get("status") in ("done", "skip")
    }
    pending_cln = all_skills - {
        s
        for s, sdata in skills.items()
        if isinstance(sdata, dict)
        and isinstance(sdata.get("clean", {}), dict)
        and sdata.get("clean", {}).get("status") in ("done", "skip")
    }

    progress["remaining_generative"] = sorted(pending_gen)
    progress["remaining_bug_hunt"] = sorted(pending_bug)
    progress["remaining_clean"] = sorted(pending_cln)

    issues, gd, _pd = validate_internal(progress)
    if issues:
        emit_json({"status": "warn", "action": "mark-done", "consistency_issues": issues})
    save(round_dir, progress)
    emit_json(
        {
            "status": "ok",
            "skill": skill,
            "test_type": test_type,
            "score": score,
            "genuinely_done": len(gd),
            "remaining_gen": len(pending_gen),
        }
    )


def cmd_validate(round_dir: str) -> None:
    progress = load(round_dir)
    issues, gd, pd = validate_internal(progress)
    _total = progress.get("total_framework_skills", len(ALL_SKILLS))

    result: dict[str, Any] = {
        "status": "fail" if issues else "ok",
        "total_skills": _total,
        "genuinely_done": len(gd),
        "partly_done": {k: v for k, v in pd.items()},
        "remaining_gen": len(progress.get("remaining_generative", [])),
        "remaining_bug": len(progress.get("remaining_bug_hunt", [])),
        "remaining_clean": len(progress.get("remaining_clean", [])),
    }
    if issues:
        result["issues"] = issues
    emit_json(result)
    sys.exit(0 if not issues else 1)


def cmd_rebuild_queues(round_dir: str) -> None:
    progress = load(round_dir)
    skills = progress.get("skills", {})
    all_skills = set(ALL_SKILLS)

    pending_gen = all_skills - {
        s
        for s, sdata in skills.items()
        if isinstance(sdata, dict)
        and isinstance(sdata.get("generative", {}), dict)
        and sdata.get("generative", {}).get("status") in ("done", "skip")
    }
    pending_bug = all_skills - {
        s
        for s, sdata in skills.items()
        if isinstance(sdata, dict)
        and isinstance(sdata.get("bug-hunt", {}), dict)
        and sdata.get("bug-hunt", {}).get("status") in ("done", "skip")
    }
    pending_cln = all_skills - {
        s
        for s, sdata in skills.items()
        if isinstance(sdata, dict)
        and isinstance(sdata.get("clean", {}), dict)
        and sdata.get("clean", {}).get("status") in ("done", "skip")
    }

    progress["remaining_generative"] = sorted(pending_gen)
    progress["remaining_bug_hunt"] = sorted(pending_bug)
    progress["remaining_clean"] = sorted(pending_cln)

    genuinely_done = {
        s
        for s in all_skills
        if s not in pending_gen and s not in pending_bug and s not in pending_cln
    }
    progress["completed_skill_names"] = sorted(genuinely_done)

    save(round_dir, progress)
    emit_json(
        {
            "status": "ok",
            "action": "rebuild-queues",
            "remaining_gen": len(pending_gen),
            "remaining_bug": len(pending_bug),
            "remaining_clean": len(pending_cln),
            "genuinely_done": len(genuinely_done),
        }
    )


def main() -> None:
    configure_logging()
    if len(sys.argv) < 2:
        log.info(
            "usage",
            message="Usage: update-progress.py <command> [args...]\nCommands: init mark-done validate rebuild-queues",
        )
        sys.exit(1)

    cmd = sys.argv[1]
    args = sys.argv[2:]

    if cmd == "init":
        ec: int | None = None
        if "--expected-chapters" in args:
            idx = args.index("--expected-chapters")
            if idx + 1 >= len(args):
                log.error("missing_flag_value", flag="--expected-chapters")
                sys.exit(1)
            try:
                ec = int(args[idx + 1])
            except ValueError:
                log.error("invalid_flag_value", flag="--expected-chapters", value=args[idx + 1])
                sys.exit(1)
            args = [a for i, a in enumerate(args) if i not in (idx, idx + 1)]
        cmd_init(args[0], args[1] if len(args) > 1 else "T1", ec)
    elif cmd == "mark-done":
        note = None
        if "--note" in args:
            idx = args.index("--note")
            note = args[idx + 1] if idx + 1 < len(args) else "carry-forward"
            args = [a for i, a in enumerate(args) if i not in (idx, idx + 1)]
        cmd_mark_done(args[0], args[1], args[2], float(args[3]), note)
    elif cmd == "validate":
        cmd_validate(args[0])
    elif cmd == "rebuild-queues":
        cmd_rebuild_queues(args[0])
    else:
        log.error("unknown_command", command=cmd)
        sys.exit(1)


if __name__ == "__main__":
    main()
