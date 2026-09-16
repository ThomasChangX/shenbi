"""C26 / F002+F003+F1013+F1014+F1035+T1203+T1205 (spec #64): run_pipeline.sh
must be a smoke tool — loud failure on hostile paths, zero state writes,
never auto-approving checkpoints. Offline: a fake ``uv`` on PATH replays
canned `pipeline resume` output (stubbing ``pipeline`` itself is useless —
``uv run`` prepends the venv bin to PATH).
"""

import json
import os
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "run_pipeline.sh"

# T1205 replay: balanced-paren Python breakout payload in PROJECT_DIR.
HOSTILE_DIRS = [
    "x') and __import__('os').system('touch pwned-by-rp') and ('1",
    "dir with space",
    "dir( paren )",
]
# F1014/F002: an error message containing the over-broad grep words must NOT
# be auto-approved (canned output replays a fake "error" status whose text
# mentions escalation/gate/dispatch).
CANNED_ERROR = json.dumps(
    {"status": "error", "error": "dispatch failed inside gate escalation path"}
)
CANNED_ESCALATION_BLOCKED = json.dumps(
    {"status": "blocked", "checkpoint": "ESCALATION", "phase": "chapter_loop"}
)


def _run_script(tmp_path: Path, project_dir: str, canned: str) -> subprocess.CompletedProcess[str]:
    bin_dir = tmp_path / "stub-bin"
    bin_dir.mkdir(exist_ok=True)
    canned_file = tmp_path / "canned.txt"
    canned_file.write_text(canned + "\n", encoding="utf-8")
    # Stub records EVERY invocation first (incl. `pipeline review`), replays
    # canned output only for `resume` — record-after-replay would make the
    # "no review issued" assertion vacuous.
    (bin_dir / "uv").write_text(
        "#!/usr/bin/env bash\n"
        'printf \'%s\\n\' "$@" >> "${STUB_UV_OUT:?}"\n'
        '[ "$3" = "resume" ] && cat "$STUB_UV_CANNED"\n'
        "exit 0\n",
        encoding="utf-8",
    )
    (bin_dir / "uv").chmod(0o755)
    env = os.environ.copy()
    env.update(
        PATH=f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
        STUB_UV_CANNED=str(canned_file),
        STUB_UV_OUT=str(tmp_path / "uv.args"),
    )
    return subprocess.run(
        ["bash", str(SCRIPT), project_dir, "1"],
        capture_output=True,
        text=True,
        timeout=60,
        cwd=REPO_ROOT,
        env=env,
    )


@pytest.mark.unit
@pytest.mark.parametrize("dirname", HOSTILE_DIRS)
def test_hostile_project_dir_loud_failure_no_python_breakout(tmp_path: Path, dirname: str) -> None:
    # Vacuity guard (precedent tests/test_round_exec_injection.py): the
    # and-form breakout payload needs a literal `<tmp>/x` for open() to
    # succeed before the and-chain reaches os.system — without it the
    # pre-fix script silently takes the inert path and the test is vacuous.
    (tmp_path / "x").write_text("{}", encoding="utf-8")
    proc = _run_script(tmp_path, str(tmp_path / dirname), CANNED_ERROR)
    marker = REPO_ROOT / "pwned-by-rp"
    try:
        assert not marker.exists(), "T1205 python breakout executed"
    finally:
        marker.unlink(missing_ok=True)
    # F1035: not a silent death — some diagnostic reached stderr/stdout.
    assert proc.returncode != 0
    assert "FATAL" in proc.stdout + proc.stderr or "error" in (proc.stdout + proc.stderr).lower()


@pytest.mark.unit
def test_escalation_blocked_stops_without_approve_or_state_write(tmp_path: Path) -> None:
    proj = tmp_path / "proj"
    proj.mkdir()
    state = proj / "pipeline-state.json"
    state.write_text(json.dumps({"chapter_loop": {"step_index": 3}}), encoding="utf-8")
    before = state.read_text(encoding="utf-8")
    proc = _run_script(tmp_path, str(proj), CANNED_ESCALATION_BLOCKED)
    assert proc.returncode == 3
    assert "manual review required" in proc.stdout
    # F002: no `pipeline review` invocation ever issued...
    calls = (
        (tmp_path / "uv.args").read_text(encoding="utf-8")
        if (tmp_path / "uv.args").exists()
        else ""
    )
    assert "review" not in calls, "auto-approve survived"
    # ...and no state JSON mutation (step_index bump / retry clear gone).
    assert state.read_text(encoding="utf-8") == before


@pytest.mark.unit
def test_error_with_gate_words_is_fatal_not_approved(tmp_path: Path) -> None:
    proc = _run_script(tmp_path, str(tmp_path / "proj2"), CANNED_ERROR)
    assert proc.returncode == 1
    calls = (
        (tmp_path / "uv.args").read_text(encoding="utf-8")
        if (tmp_path / "uv.args").exists()
        else ""
    )
    assert "review" not in calls, "F1014 over-broad grep still auto-approving"
