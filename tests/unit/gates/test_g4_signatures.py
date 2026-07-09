"""Task 15a: gate_G4 must accept project_dir/repo_root (additive, no behavior change).

These params are threaded but not yet consumed by the checkers (that is 15b).
They MUST be accepted without error so the 4 call sites (cli/g5/g6/g7) can pass
them today and so RoundPaths migration in 15b has a stable entry point.

Spec §4.2 invariant: no silent CWD fallback. When neither round_dir nor
project_dir is provided, the per-skill checkers raise ValueError instead of
silently defaulting to CWD.
"""

from __future__ import annotations

import json

import pytest

from shenbi.gates.g4.generic import gate_G4


def test_gate_g4_accepts_project_dir_and_repo_root(tmp_path):
    # Must accept the new params without error (even if it doesn't use them yet).
    result = gate_G4(
        "shenbi-worldbuilding",
        "generative",
        [],
        str(tmp_path),
        project_dir=str(tmp_path),
        repo_root=str(tmp_path),
    )
    data = json.loads(result)
    # ran, didn't crash on signature — the worldbuilding checker ran (FAIL is
    # expected: tmp_path has no project files). What matters is the call
    # returned a valid gate result, not that it passed.
    assert data["gate"] == "G4-worldbuilding"
    assert "status" in data


def test_gate_g4_project_dir_repo_root_default_none():
    # Spec §4.2: omitting BOTH round_dir and project_dir must raise ValueError
    # (no silent CWD fallback). All 4 live callers pass round_dir positionally.
    with pytest.raises(ValueError, match="round_dir or project_dir required"):
        gate_G4("shenbi-worldbuilding", "generative", [])


def test_gate_g4_threads_params_to_generic_bug_hunt(tmp_path):
    # bug-hunt / clean routes call the generic checkers directly; ensure the new
    # params are threaded there too without error.
    result = gate_G4(
        "bug-hunt",
        "bug-hunt",
        [],
        str(tmp_path),
        project_dir=str(tmp_path),
        repo_root=str(tmp_path),
    )
    data = json.loads(result)
    assert "skill" in data or "status" in data
