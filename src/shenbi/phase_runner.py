#!/usr/bin/env python3
"""State machine for T2/T3 phase execution.

Usage:
    phase-runner.py start <phase> --round-dir <dir> --project-dir <dir>
    phase-runner.py pre-skill <phase> <skill> --round-dir <dir>
    phase-runner.py post-skill <phase> <skill> --round-dir <dir> --project-dir <dir> [--chapter <n>]
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
from shenbi.contracts import ContractError, load_contract
from shenbi.logging import configure_logging, get_logger
from shenbi.safe_write import safe_write
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
    safe_write(state_file, json.dumps(state, indent=2, ensure_ascii=False))


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _record_gate_manifest(
    project_dir: Path,
    phase: str,
    chapter: int,
    skill: str,
    gate: str,
    result: dict[str, Any],
) -> None:
    """Record a gate result into the pipeline manifest (best-effort, never raises)."""
    try:
        from shenbi.gates.gate_manifest import record_gate_result

        record_gate_result(
            gate_manifest_dir=project_dir,
            phase=phase,
            chapter=chapter,
            skill=skill,
            gate=gate,
            result=result,
        )
    except Exception:
        log.warning("gate_manifest_record_failed", gate=gate, skill=skill, exc_info=True)


def run_gate(gate: str, args: list[str]) -> dict[str, Any]:
    """Run a gate via the live ``shenbi.gates.cli`` module, return parsed JSON.

    Gate logic was extracted from the legacy ``tests/validate-gate.py`` into
    ``src/shenbi/gates/`` (PR-19). This function targets the module directly
    via ``python -m shenbi.gates.cli``, matching ``dispatch_helper.run_gate_g3/g4``.
    """
    r: subprocess.CompletedProcess[str] | None = None
    try:
        r = subprocess.run(
            [sys.executable, "-m", "shenbi.gates.cli", gate] + args,
            capture_output=True,
            text=True,
            timeout=60,
        )
        return cast(dict[str, Any], json.loads(r.stdout))
    except (json.JSONDecodeError, ValueError, OSError):
        return {
            "status": GateStatus.FAIL,
            "raw_stdout": r.stdout if r is not None else "",
            "raw_stderr": r.stderr if r is not None else "",
        }


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


def cmd_post_skill(
    phase: str,
    skill: str,
    round_dir: str,
    project_dir: str | None,
    chapter: int | None = None,
) -> None:
    state = load_state(round_dir, phase)
    require_state(state, ["started"], "post-skill")
    assert project_dir is not None
    proj = Path(project_dir)
    from shenbi.dispatcher.executor import derive_file_type, derive_output_files

    # M5: use contract-declared outputs instead of rglob heuristic.
    # chapter must be provided for chapter-parametric skills; when None
    # (non-pipeline T2), derive_output_files returns [] for parametric paths.
    output_files = [
        p
        for p in derive_output_files(skill, chapter, proj)
        if Path(p).exists() and Path(p).stat().st_size > 0
    ]
    # M8: use derived file_type instead of hardcoded "chapter".
    file_type = derive_file_type(skill)
    # Safety fallback: when chapter is unknown (non-pipeline T2), fall back to
    # rglob. CRITICAL: the fallback file_type must match what rglob finds (.md).
    # If derive_file_type returns "decisions" but rglob only finds .md files,
    # G2's decisions branch would json.loads() markdown → crash. So the fallback
    # must use file_type="chapter" (the type for .md files).
    if not output_files and chapter is None:
        output_files = [str(f) for f in proj.rglob("*.md") if f.stat().st_size > 0][:20]
        file_type = "chapter"  # override: rglob finds .md, not decisions.json
    g2_status = GateStatus.SKIP.value
    if output_files:
        g2 = run_gate("G2", [",".join(output_files), file_type, str(round_dir)])
        g2_status = g2.get("status", GateStatus.FAIL.value)
        _record_gate_manifest(proj, phase, chapter or 0, skill, "G2", g2)
    g4 = run_gate("G4", [skill, ",".join(output_files) if output_files else "", str(round_dir)])
    g4_status = g4.get("status", GateStatus.FAIL.value)
    _record_gate_manifest(proj, phase, chapter or 0, skill, "G4", g4)
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
    chapter_str = find_flag("--chapter", required=False)
    chapter = int(chapter_str) if chapter_str else None

    if cmd == "start":
        phase = args[0]
        cmd_start(phase, round_dir, project_dir)
    elif cmd == "pre-skill":
        phase, skill = args[0], args[1]
        cmd_pre_skill(phase, skill, round_dir)
    elif cmd == "post-skill":
        phase, skill = args[0], args[1]
        cmd_post_skill(phase, skill, round_dir, project_dir, chapter=chapter)
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
