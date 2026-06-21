#!/usr/bin/env python3
"""State machine for T2/T3 phase execution.

Usage:
    phase-runner.py start <phase> --round-dir <dir> --project-dir <dir>
    phase-runner.py pre-skill <phase> <skill> --round-dir <dir>
    phase-runner.py post-skill <phase> <skill> --round-dir <dir> --project-dir <dir>
    phase-runner.py pre-score <phase> --round-dir <dir>
    phase-runner.py post-score <phase> <scores-file> --round-dir <dir>
    phase-runner.py finalize <phase> --round-dir <dir> --project-dir <dir>
"""

import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from shenbi.cli_utils import emit_json
from shenbi.contract import ContractError, load_contract
from shenbi.logging import configure_logging, get_logger
from shenbi.status import CommandStatus, GateStatus, PhaseState

log = get_logger(__name__)

TESTS = Path(__file__).resolve().parents[2] / "tests"
PROJECT = TESTS.parent


def load_deps() -> Any:
    return json.loads((TESTS / "tiers" / "deps.json").read_text(encoding="utf-8"))


def load_state(round_dir: str, phase: str) -> dict[str, Any]:
    state_file = Path(round_dir) / "phase-state" / f"{phase}.json"
    if state_file.exists():
        return cast(dict[str, Any], json.loads(state_file.read_text(encoding="utf-8")))
    return {"phase": phase, "state": PhaseState.CREATED, "steps": []}


def save_state(round_dir: str, state: dict[str, Any]) -> None:
    state_dir = Path(round_dir) / "phase-state"
    state_dir.mkdir(parents=True, exist_ok=True)
    state_file = state_dir / f"{state['phase']}.json"
    state_file.write_text(json.dumps(state, indent=2, ensure_ascii=False))


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def run_gate(gate: str, args: list[str]) -> dict[str, Any]:
    """Run a gate via validate-gate.py, return parsed JSON."""
    vg = str(TESTS / "validate-gate.py")
    r = subprocess.run(
        [sys.executable, vg, gate] + args,
        capture_output=True,
        text=True,
        timeout=60,
    )
    try:
        return cast(dict[str, Any], json.loads(r.stdout))
    except (json.JSONDecodeError, ValueError):
        return {"status": GateStatus.FAIL, "raw_stdout": r.stdout, "raw_stderr": r.stderr}


def require_state(state: dict[str, Any], expected: list[str], action: str) -> None:
    """Exit with error if state is not one of the expected states."""
    if state["state"] not in expected:
        emit_json(
            {
                "error": f"Cannot {action}: state is '{state['state']}', expected {expected}",
                "phase": state["phase"],
            }
        )
        sys.exit(1)


def cmd_start(phase: str, round_dir: str, project_dir: str | None) -> None:
    state = load_state(round_dir, phase)
    require_state(state, ["created"], "start")
    g5 = run_gate("G5", [phase, str(round_dir), str(project_dir)])
    step = {"action": "start", "timestamp": now_iso(), "g5_status": g5.get("status")}
    if g5.get("status") == "PASS":
        state["state"] = PhaseState.STARTED
        state["steps"].append(step)
        save_state(round_dir, state)
        emit_json(
            {"status": CommandStatus.OK, "phase": phase, "state": PhaseState.STARTED, "g5": "PASS"}
        )
    else:
        state["steps"].append({**step, "g5_must_fix": g5.get("must_fix", [])})
        save_state(round_dir, state)
        emit_json({"status": CommandStatus.BLOCKED, "phase": phase, "g5": g5})
        sys.exit(1)


def cmd_pre_skill(phase: str, skill: str, round_dir: str) -> None:
    state = load_state(round_dir, phase)
    require_state(state, ["started"], "pre-skill")
    # Validate skill exists
    skill_path = PROJECT / "skills" / skill / "SKILL.md"
    if not skill_path.exists():
        emit_json(
            {
                "status": CommandStatus.ERROR,
                "phase": phase,
                "skill": skill,
                "message": f"SKILL.md not found: {skill_path}",
            }
        )
        sys.exit(1)
    # Extract data contract via the single loader (spec D2 — no second parser).
    try:
        contract = load_contract(skill)
        read_files = list(contract["reads"])
        write_files = [*contract["writes"], *contract["updates"]]
    except ContractError:
        read_files, write_files = [], []
    step = {
        "action": "pre-skill",
        "skill": skill,
        "timestamp": now_iso(),
        "data_contract": {
            "reads": read_files,
            "writes": write_files,
        },
    }
    state["steps"].append(step)
    save_state(round_dir, state)
    emit_json(
        {
            "status": CommandStatus.OK,
            "phase": phase,
            "skill": skill,
            "action": "execute_skill",
            "reads": read_files,
            "writes": write_files,
        }
    )


def cmd_post_skill(phase: str, skill: str, round_dir: str, project_dir: str | None) -> None:
    state = load_state(round_dir, phase)
    require_state(state, ["started"], "post-skill")
    assert project_dir is not None
    proj = Path(project_dir)
    output_files = [str(f) for f in proj.rglob("*.md") if f.stat().st_size > 0][:20]
    g2_status = GateStatus.SKIP.value
    if output_files:
        g2 = run_gate("G2", [",".join(output_files), "chapter", str(round_dir)])
        g2_status = g2.get("status", GateStatus.FAIL.value)
    g4 = run_gate("G4", [skill, ",".join(output_files) if output_files else "", str(round_dir)])
    g4_status = g4.get("status", GateStatus.FAIL.value)
    step = {
        "action": "post-skill",
        "skill": skill,
        "timestamp": now_iso(),
        "g2": g2_status,
        "g4": g4_status,
    }
    state["steps"].append(step)
    save_state(round_dir, state)
    if g4_status == "FAIL":
        emit_json({"status": CommandStatus.BLOCKED, "phase": phase, "skill": skill, "g4": g4})
        sys.exit(1)
    emit_json(
        {
            "status": CommandStatus.OK,
            "phase": phase,
            "skill": skill,
            "g2": g2_status,
            "g4": g4_status,
        }
    )


def cmd_pre_score(phase: str, round_dir: str) -> None:
    state = load_state(round_dir, phase)
    require_state(state, ["started"], "pre-score")
    deps = load_deps()
    phase_data = deps.get("t2-phases", {}).get(phase, {})
    marker_dir = Path(round_dir) / "gate-markers"
    missing: list[str] = []
    for skill in phase_data.get("prerequisites", []):
        marker = marker_dir / f"G4-{skill}-generative.json"
        if not marker.exists():
            missing.append(skill)
    if missing:
        emit_json(
            {
                "status": CommandStatus.BLOCKED,
                "phase": phase,
                "missing_markers": [f"G4-{s}-generative" for s in missing],
            }
        )
        sys.exit(1)
    proj_dir = Path(round_dir) / "project-output"
    for pattern in phase_data.get("expected_outputs", []):
        if "*" in pattern:
            if not list(proj_dir.rglob(pattern)):
                emit_json(
                    {"status": CommandStatus.BLOCKED, "phase": phase, "missing_output": pattern}
                )
                sys.exit(1)
        elif not (proj_dir / pattern).exists():
            emit_json({"status": CommandStatus.BLOCKED, "phase": phase, "missing_output": pattern})
            sys.exit(1)
    state["state"] = PhaseState.SKILLS_DONE
    save_state(round_dir, state)
    emit_json({"status": CommandStatus.OK, "phase": phase, "state": PhaseState.SKILLS_DONE})


def cmd_post_score(phase: str, scores_file: str, round_dir: str) -> None:
    state = load_state(round_dir, phase)
    require_state(state, ["skills_done"], "post-score")
    if not Path(scores_file).exists():
        emit_json(
            {
                "status": CommandStatus.ERROR,
                "phase": phase,
                "message": f"Scores file not found: {scores_file}",
            }
        )
        sys.exit(1)
    _scores_data = json.loads(Path(scores_file).read_text(encoding="utf-8"))
    step = {
        "action": "post-score",
        "timestamp": now_iso(),
        "scores_file": str(scores_file),
    }
    state["steps"].append(step)
    state["state"] = PhaseState.SCORED
    save_state(round_dir, state)
    emit_json({"status": CommandStatus.OK, "phase": phase, "state": PhaseState.SCORED})


def cmd_finalize(phase: str, round_dir: str, project_dir: str | None) -> None:
    state = load_state(round_dir, phase)
    require_state(state, ["scored"], "finalize")
    g5 = run_gate("G5", [phase, str(round_dir), str(project_dir)])
    step = {
        "action": "finalize",
        "timestamp": now_iso(),
        "g5_status": g5.get("status"),
    }
    if g5.get("status") != "PASS":
        state["steps"].append({**step, "g5_must_fix": g5.get("must_fix", [])})
        save_state(round_dir, state)
        emit_json({"status": CommandStatus.BLOCKED, "phase": phase, "g5": g5})
        sys.exit(1)
    deps = load_deps()
    marker_dir = Path(round_dir) / "gate-markers"
    for skill in deps.get("t2-phases", {}).get(phase, {}).get("prerequisites", []):
        if not (marker_dir / f"G4-{skill}-generative.json").exists():
            emit_json(
                {
                    "status": CommandStatus.ERROR,
                    "phase": phase,
                    "missing_marker": f"G4-{skill}-generative",
                }
            )
            sys.exit(1)
    state["state"] = PhaseState.FINALIZED
    state["steps"].append(step)
    save_state(round_dir, state)
    emit_json({"status": CommandStatus.OK, "phase": phase, "state": PhaseState.FINALIZED})


def main() -> None:
    configure_logging()
    if len(sys.argv) < 2:
        log.info(
            "usage",
            message="Usage: phase-runner.py <command> [args...] --round-dir <dir> [--project-dir <dir>]\nCommands: start pre-skill post-skill pre-score post-score finalize",
        )
        sys.exit(1)

    cmd = sys.argv[1]
    args = sys.argv[2:]

    def find_flag(flag: str, required: bool = True) -> str | None:
        if flag in args:
            idx = args.index(flag)
            if idx + 1 < len(args):
                return args[idx + 1]
        if required:
            log.error("missing_required_flag", flag=flag)
            sys.exit(1)
        return None

    round_dir = find_flag("--round-dir")
    assert round_dir is not None
    project_dir = find_flag("--project-dir", required=False)

    if cmd == "start":
        phase = args[0]
        cmd_start(phase, round_dir, project_dir)
    elif cmd == "pre-skill":
        phase, skill = args[0], args[1]
        cmd_pre_skill(phase, skill, round_dir)
    elif cmd == "post-skill":
        phase, skill = args[0], args[1]
        cmd_post_skill(phase, skill, round_dir, project_dir)
    elif cmd == "pre-score":
        phase = args[0]
        cmd_pre_score(phase, round_dir)
    elif cmd == "post-score":
        phase, scores_file = args[0], args[1]
        cmd_post_score(phase, scores_file, round_dir)
    elif cmd == "finalize":
        phase = args[0]
        cmd_finalize(phase, round_dir, project_dir)
    else:
        log.error("unknown_command", command=cmd)
        sys.exit(1)


if __name__ == "__main__":
    main()
