"""Closure check (spec §5.5 #3, Task 18): every ``reads:`` entry must have a
producer (skill writes/updates, pipeline-produced, or an external seed).

ORPHAN_READ → CI FAIL (exit 1, block PR). DANGLING_WRITE → stderr WARN.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
LINT = REPO / "tools" / "lint_contract_graph.py"

# Imported lazily in tests so the clean-repo subprocess can run the tool as-is
# without first importing the module under test (which would load contracts).


@pytest.mark.unit
def test_clean_repo_has_zero_orphan_reads() -> None:
    """Phase-0 found 0 orphan reads; the lint should pass (exit 0) on the real
    contract set. A regression that introduces a dangling read into a real
    skill turns this red — the marquee CI guard.
    """
    r = subprocess.run([sys.executable, str(LINT)], capture_output=True, text=True, cwd=REPO)
    assert r.returncode == 0, f"orphan reads:\n{r.stdout}\n{r.stderr}"


@pytest.mark.unit
def test_detects_injected_orphan(monkeypatch: pytest.MonkeyPatch) -> None:
    """Canary #1: a contract with a read no skill produces → ORPHAN_READ detected.

    ``load_all_contracts`` is monkeypatched so the real skills are replaced by a
    synthetic contract set with a single orphan read. ``find_closure_violations``
    imports ``load_all_contracts`` from ``shenbi.sync_contracts`` by name, so the
    patch on that module attribute is seen.
    """
    from tools.lint_contract_graph import find_closure_violations

    fake_contracts = {
        "shenbi-test": {
            "reads": ["truth/does-not-exist.md"],
            "writes": [],
            "updates": [],
        },
    }
    monkeypatch.setattr("shenbi.sync_contracts.load_all_contracts", lambda: fake_contracts)
    orphan, _dangling = find_closure_violations()
    assert any(skill == "shenbi-test" and "truth/does-not-exist.md" in f for skill, f in orphan)
