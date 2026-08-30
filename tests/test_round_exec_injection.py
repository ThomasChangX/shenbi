"""T12-03 (round-exec.sh half, spec #22 R2): malicious directory names must
never execute shell/python payloads through the ``python3 -c`` interpolation
sites in tests/round-exec.sh (--validate mode reaches lines 19/29).

Injection class = Python string breakout: bash does not re-scan parameter
expansion results, so ``$( )``/backticks inside ``${VAR}`` values are inert
literals; the genuinely reachable vector pre-fix is ``'`` escaping the python
string literal inside the double-quoted ``python3 -c`` command.

The payload command must not contain ``/`` (it lives inside a directory
name, which cannot embed a path separator), so the marker is created as
``touch pwned-by-injection`` relative to the shell's working directory. The
subprocess must NOT set cwd= (round-exec.sh:18 does a CWD-relative ``ls``;
changing cwd would abort the script early and make the test vacuous), so the
marker lands at Path.cwd() == repo root, asserted and cleaned up.
"""

import json
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]

PAYLOAD = "pwned-by-injection"
PWN = f"touch {PAYLOAD}"

# Reachable rows (and-form): open() consumes the pre-created literal file
# <tmp>/x first, then the ``and`` chain evaluates os.system → pre-fix the
# payload really executes (red light is satisfiable).
REACHABLE = [f"x') and __import__('os').system('{PWN}') and ('1"]

# Defense-in-depth rows: the or-form short-circuits via the open() exception
# and $()/backtick values are never re-expanded by bash — they pass pre-fix
# by design (payload unreachable) and must keep passing post-fix; regression
# anchors only.
DEFENSE_IN_DEPTH = [
    "x') or __import__('os').system('id') and ('",
    'x"d',  # spec sample fidelity: double quote (inert inside single-quoted literal)
    "x$(touch y)",
    "x`touch z`",
]
MALICIOUS = REACHABLE + DEFENSE_IN_DEPTH


@pytest.mark.parametrize("name", MALICIOUS, ids=lambda n: n[:12])
def test_validate_rejects_malicious_dirname(tmp_path: Path, name: str) -> None:
    evil = name
    round_dir = tmp_path / evil
    round_dir.mkdir()
    # Vacuity guard: summary.json presence keeps --validate from failing at
    # the early check (round-exec.sh:13-16) before reaching the parameterized
    # calls; the and-form payload needs the literal <tmp>/x to exist (open()
    # success is what lets the and-chain reach os.system; content is never
    # consumed by json.load).
    (tmp_path / "x").write_text("{}", encoding="utf-8")
    (round_dir / "summary.json").write_text(json.dumps({"t1_scores": {}}), encoding="utf-8")
    (round_dir / "meta.json").write_text(json.dumps({"tier_target": "T1"}), encoding="utf-8")

    assert not (Path.cwd() / PAYLOAD).exists(), "pre-existing marker file collision"

    proc = subprocess.run(
        ["bash", str(REPO_ROOT / "tests" / "round-exec.sh"), "--validate", str(round_dir)],
        capture_output=True,
        text=True,
        timeout=30,
    )

    try:
        assert not (Path.cwd() / PAYLOAD).exists(), "injection payload executed!"
    finally:
        marker = Path.cwd() / PAYLOAD
        if marker.exists():
            marker.unlink()
    assert proc.returncode != 0
