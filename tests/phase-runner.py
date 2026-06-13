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
from datetime import datetime, timezone
from pathlib import Path

TESTS = Path(__file__).resolve().parent
PROJECT = TESTS.parent


def load_deps():
    return json.loads((TESTS / "tiers" / "deps.json").read_text(encoding="utf-8"))


def load_state(round_dir, phase):
    state_file = Path(round_dir) / "phase-state" / f"{phase}.json"
    if state_file.exists():
        return json.loads(state_file.read_text(encoding="utf-8"))
    return {"phase": phase, "state": "created", "steps": []}


def save_state(round_dir, state):
    state_dir = Path(round_dir) / "phase-state"
    state_dir.mkdir(parents=True, exist_ok=True)
    state_file = state_dir / f"{state['phase']}.json"
    state_file.write_text(json.dumps(state, indent=2, ensure_ascii=False))


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def run_gate(gate, args):
    """Run a gate via validate-gate.py, return parsed JSON."""
    vg = str(TESTS / "validate-gate.py")
    r = subprocess.run(
        [sys.executable, vg, gate] + args,
        capture_output=True, text=True, timeout=60,
    )
    try:
        return json.loads(r.stdout)
    except (json.JSONDecodeError, ValueError):
        return {"status": "FAIL", "raw_stdout": r.stdout, "raw_stderr": r.stderr}


def require_state(state, expected, action):
    """Exit with error if state is not one of the expected states."""
    if state["state"] not in expected:
        print(json.dumps({
            "error": f"Cannot {action}: state is '{state['state']}', expected {expected}",
            "phase": state["phase"],
        }))
        sys.exit(1)


def cmd_start(phase, round_dir, project_dir):
    state = load_state(round_dir, phase)
    require_state(state, ["created"], "start")
    g5 = run_gate("G5", [phase, str(round_dir), str(project_dir)])
    step = {"action": "start", "timestamp": now_iso(), "g5_status": g5.get("status")}
    if g5.get("status") == "PASS":
        state["state"] = "started"
        state["steps"].append(step)
        save_state(round_dir, state)
        print(json.dumps({"status": "ok", "phase": phase, "state": "started", "g5": "PASS"}))
    else:
        state["steps"].append({**step, "g5_must_fix": g5.get("must_fix", [])})
        save_state(round_dir, state)
        print(json.dumps({"status": "blocked", "phase": phase, "g5": g5}))
        sys.exit(1)


def cmd_pre_skill(phase, skill, round_dir):
    state = load_state(round_dir, phase)
    require_state(state, ["started"], "pre-skill")
    # Validate skill exists
    skill_path = PROJECT / "skills" / skill / "SKILL.md"
    if not skill_path.exists():
        print(json.dumps({"status": "error", "phase": phase, "skill": skill, 
                          "message": f"SKILL.md not found: {skill_path}"}))
        sys.exit(1)
    # Extract data contract for dispatcher guidance
    skill_md = skill_path.read_text(encoding="utf-8")
    import re as _re
    reads = _re.findall(r'\*\*Reads:\*\*\s*(.*)', skill_md)
    writes = _re.findall(r'\*\*Writes:\*\*\s*(.*)', skill_md)
    updates = _re.findall(r'\*\*Updates:\*\*\s*(.*)', skill_md)
    read_files = []
    for line in reads:
        read_files.extend(_re.findall(r'`([^`]+)`', line))
    write_files = []
    for line in writes + updates:
        write_files.extend(_re.findall(r'`([^`]+)`', line))
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
    print(json.dumps({
        "status": "ok", "phase": phase, "skill": skill,
        "action": "execute_skill",
        "reads": read_files,
        "writes": write_files,
    }))


def cmd_post_skill(phase, skill, round_dir, project_dir):
    state = load_state(round_dir, phase)
    require_state(state, ["started"], "post-skill")
    proj = Path(project_dir)
    output_files = [str(f) for f in proj.rglob("*.md") if f.stat().st_size > 0][:20]
    g2_status = "SKIP"
    if output_files:
        g2 = run_gate("G2", [",".join(output_files), "chapter", str(round_dir)])
        g2_status = g2.get("status", "UNKNOWN")
    g4 = run_gate("G4", [skill, ",".join(output_files) if output_files else "", str(round_dir)])
    g4_status = g4.get("status", "UNKNOWN")
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
        print(json.dumps({"status": "blocked", "phase": phase, "skill": skill, "g4": g4}))
        sys.exit(1)
    print(json.dumps({"status": "ok", "phase": phase, "skill": skill, "g2": g2_status, "g4": g4_status}))


def cmd_pre_score(phase, round_dir):
    state = load_state(round_dir, phase)
    require_state(state, ["started"], "pre-score")
    deps = load_deps()
    phase_data = deps.get("t2-phases", {}).get(phase, {})
    marker_dir = Path(round_dir) / "gate-markers"
    missing = []
    for skill in phase_data.get("prerequisites", []):
        marker = marker_dir / f"G4-{skill}-generative.json"
        if not marker.exists():
            missing.append(skill)
    if missing:
        print(json.dumps({
            "status": "blocked",
            "phase": phase,
            "missing_markers": [f"G4-{s}-generative" for s in missing],
        }))
        sys.exit(1)
    proj_dir = Path(round_dir) / "project-output"
    for pattern in phase_data.get("expected_outputs", []):
        if "*" in pattern:
            if not list(proj_dir.rglob(pattern)):
                print(json.dumps({"status": "blocked", "phase": phase, "missing_output": pattern}))
                sys.exit(1)
        else:
            if not (proj_dir / pattern).exists():
                print(json.dumps({"status": "blocked", "phase": phase, "missing_output": pattern}))
                sys.exit(1)
    state["state"] = "skills_done"
    save_state(round_dir, state)
    print(json.dumps({"status": "ok", "phase": phase, "state": "skills_done"}))


def cmd_post_score(phase, scores_file, round_dir):
    state = load_state(round_dir, phase)
    require_state(state, ["skills_done"], "post-score")
    if not Path(scores_file).exists():
        print(json.dumps({"status": "error", "phase": phase, "message": f"Scores file not found: {scores_file}"}))
        sys.exit(1)
    scores_data = json.loads(Path(scores_file).read_text(encoding="utf-8"))
    step = {
        "action": "post-score",
        "timestamp": now_iso(),
        "scores_file": str(scores_file),
    }
    state["steps"].append(step)
    state["state"] = "scored"
    save_state(round_dir, state)
    print(json.dumps({"status": "ok", "phase": phase, "state": "scored"}))


def cmd_finalize(phase, round_dir, project_dir):
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
        print(json.dumps({"status": "blocked", "phase": phase, "g5": g5}))
        sys.exit(1)
    deps = load_deps()
    marker_dir = Path(round_dir) / "gate-markers"
    for skill in deps.get("t2-phases", {}).get(phase, {}).get("prerequisites", []):
        if not (marker_dir / f"G4-{skill}-generative.json").exists():
            print(json.dumps({"status": "error", "phase": phase, "missing_marker": f"G4-{skill}-generative"}))
            sys.exit(1)
    state["state"] = "finalized"
    state["steps"].append(step)
    save_state(round_dir, state)
    print(json.dumps({"status": "ok", "phase": phase, "state": "finalized"}))


def main():
    if len(sys.argv) < 2:
        print("Usage: phase-runner.py <command> [args...] --round-dir <dir> [--project-dir <dir>]")
        print("Commands: start pre-skill post-skill pre-score post-score finalize")
        sys.exit(1)

    cmd = sys.argv[1]
    args = sys.argv[2:]

    def find_flag(flag, required=True):
        if flag in args:
            idx = args.index(flag)
            if idx + 1 < len(args):
                return args[idx + 1]
        if required:
            print(f"Missing required flag: {flag}")
            sys.exit(1)
        return None

    round_dir = find_flag("--round-dir")
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
        print(f"Unknown command: {cmd}")
        sys.exit(1)


if __name__ == "__main__":
    main()
