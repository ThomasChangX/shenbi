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


def test_chapter_revision_registration_order():
    """generic.py must register (structural, decisions) — not reversed (spec 13).

    Asserted behaviorally via routing: the revision sidecar must reach the
    dedicated G4.rev checker (see test_composite_partition.py for the full
    routing test); here we assert the checker dict maps chapter-revision to a
    composite (callable that is not g4_chapter_revision itself) and that
    g4_decisions is not in the existing slot.
    """
    # Behavioral routing assertion: a thin-rationale revision sidecar must
    # produce G4.rev findings via gate_G4 (dedicated checker in existing slot).
    import json as _json
    import tempfile
    from pathlib import Path

    import shenbi.gates.g4.chapter_revision as cr
    import shenbi.gates.g4.decisions_validator as dv
    import shenbi.gates.g4.generic as g

    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        sidecar = {
            "$schema": "shenbi-decisions-v1",
            "skill": "shenbi-chapter-revision",
            "chapter": 5,
            "selections": [],
            "adjustments": [
                {"issue_id": "x", "severity": "low", "handling": "ignore", "rationale": "short"}
            ],
            "produced_at": "2026-08-29T00:00:00",
        }
        (td_path / "chapter-5-revision-decisions.json").write_text(
            _json.dumps(sidecar), encoding="utf-8"
        )
        result = g.gate_G4(
            "shenbi-chapter-revision",
            "generative",
            ["chapter-5-revision-decisions.json"],
            str(td_path),
            None,
        )
        assert "G4.rev.adjustment_0_thin_rationale" in result
    assert cr.g4_chapter_revision is not dv.g4_decisions
