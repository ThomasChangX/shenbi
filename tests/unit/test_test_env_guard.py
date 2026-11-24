"""Test-environment guard: the suite must never reach a real LLM.

Root cause of the "xdist probabilistic hang" (2026-11-24): ``just`` exports
``SHENBI_LLM_API_KEY`` from ``.env`` (justfile ``set dotenv-load``), so one
test that called ``dispatch_skill`` unpatched routed to the live API — billed
real tokens, ran 70-140s, crossed the pytest-timeout limit and killed its
xdist worker. pytest-xdist 3.8.0 ``--dist loadscope`` then deadlocked: the
replacement worker is handed one already-completed work unit and nothing
triggers the next reschedule.

``tests/conftest.py`` strips the key before any shenbi module import, and the
``test-ci`` recipe disables worker restart so a timeout fails once, visibly.
This file pins both halves of the contract.
"""

import os
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def test_api_key_is_not_visible_to_tests() -> None:
    assert "SHENBI_LLM_API_KEY" not in os.environ


def test_test_ci_disables_worker_restart() -> None:
    """A timed-out test must fail once — not hang, not retry 4 x workers."""
    justfile = (REPO / "justfile").read_text(encoding="utf-8")
    match = re.search(r"^test-ci:\n((?:[ \t]+.*\n?)+)", justfile, re.M)
    assert match, "test-ci recipe not found in justfile"
    first_leg = match.group(1).splitlines()[0]
    assert "-n auto" in first_leg
    assert "--max-worker-restart=0" in first_leg
