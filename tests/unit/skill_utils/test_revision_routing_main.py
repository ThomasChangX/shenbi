"""Coverage for revision_routing __main__ main() (F613, spec #53 C15).

Runs the module as a subprocess (`python -m`) so argparse/stdout/json error
paths are exercised exactly as a CLI caller would.
"""

from __future__ import annotations

import json
import subprocess
import sys


def run_module(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "shenbi.skill_utils.revision_routing", *args],
        capture_output=True,
        text=True,
    )


def test_main_routes_valid_diagnosis() -> None:
    diagnosis = {"issues": [{"category": "unmet_goal", "severity": "BLOCKING"}]}
    p = run_module(["--diagnosis", json.dumps(diagnosis)])
    assert p.returncode == 0
    assert json.loads(p.stdout)["mode"] == "regenerate"


def test_main_invalid_json_exits_nonzero() -> None:
    p = run_module(["--diagnosis", "not-json"])
    assert p.returncode != 0


def test_main_requires_diagnosis_flag() -> None:
    p = run_module([])
    assert p.returncode != 0


def test_main_in_process_covers_entry(tmp_path, monkeypatch, capsys) -> None:
    """In-process call (coverage-recordable; the subprocess tests above are
    the black-box CLI view).
    """
    from shenbi.skill_utils.revision_routing.__main__ import main

    monkeypatch.setattr(
        "sys.argv",
        ["revision_routing", "--diagnosis", json.dumps({"issues": []})],
    )
    main()
    out = capsys.readouterr().out
    assert json.loads(out)["mode"] == "spot-fix"
