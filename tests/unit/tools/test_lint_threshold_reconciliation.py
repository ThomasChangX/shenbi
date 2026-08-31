"""Tests for the allowlist-driven threshold reconciliation lint (spec #35 T5)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "tools" / "lint_threshold_reconciliation.py"


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )


def test_lint_warns_on_mismatch_but_exits_zero(tmp_path: Path) -> None:
    allow = tmp_path / "allow.json"
    allow.write_text(
        json.dumps(
            {
                "entries": [
                    {
                        "skill": "shenbi-pacing-design",
                        "pattern": "CONSTELLATION",
                        "file": "skills/shenbi-pacing-design/SKILL.md",
                        "checker": "src/shenbi/contracts/skills/pacing_design.py",
                        "bounds": [999, 1000],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    r = _run("--allowlist", str(allow))
    assert r.returncode == 0  # WARN-only first cycle
    assert "WARN" in r.stdout


def test_lint_warns_on_missing_files(tmp_path: Path) -> None:
    allow = tmp_path / "allow.json"
    allow.write_text(
        json.dumps(
            {
                "entries": [
                    {
                        "skill": "shenbi-ghost",
                        "pattern": "X",
                        "file": "skills/shenbi-ghost/SKILL.md",
                        "checker": "src/none.py",
                        "bounds": [1, 2],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    r = _run("--allowlist", str(allow))
    assert r.returncode == 0
    assert "WARN" in r.stdout


def test_lint_clean_on_repo_allowlist() -> None:
    r = _run()
    assert r.returncode == 0
