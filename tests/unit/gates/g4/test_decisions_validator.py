from __future__ import annotations

import json
import tempfile
from pathlib import Path

from shenbi.gates.g4.decisions_validator import _check_adjacent_budget


def test_budget_comparison_detects_copy():
    """Identical budgets in adjacent chapters trigger WARN."""
    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)
        chapters = project_dir / "chapters"
        chapters.mkdir()

        budget = {"token_planning": 5000, "token_drafting": 8000}

        prev = chapters / "chapter-5-decisions.json"
        curr = chapters / "chapter-6-decisions.json"
        prev.write_text(json.dumps({"budget": budget}))
        curr.write_text(json.dumps({"budget": budget}))

        issues = _check_adjacent_budget(project_dir, chapter=6)
        assert len(issues) > 0
        assert "budget_unchanged" in issues[0]


def test_budget_comparison_passes_different_budgets():
    """Different budgets do not trigger WARN."""
    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)
        chapters = project_dir / "chapters"
        chapters.mkdir()

        prev = chapters / "chapter-5-decisions.json"
        curr = chapters / "chapter-6-decisions.json"
        prev.write_text(json.dumps({"budget": {"token_planning": 5000}}))
        curr.write_text(json.dumps({"budget": {"token_planning": 6000}}))

        issues = _check_adjacent_budget(project_dir, chapter=6)
        assert len(issues) == 0


def test_budget_comparison_skips_when_prev_missing():
    """No error when previous chapter decisions file does not exist."""
    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)
        chapters = project_dir / "chapters"
        chapters.mkdir()

        curr = chapters / "chapter-1-decisions.json"
        curr.write_text(json.dumps({"budget": {"token_planning": 5000}}))

        issues = _check_adjacent_budget(project_dir, chapter=1)
        assert len(issues) == 0  # No previous chapter


def test_emission_ids_byte_stable_via_finding(tmp_path):
    """Spec #88 T1d characterization: composed G4.dec.* strings unchanged."""
    import json

    from shenbi.gates.g4.decisions_validator import g4_decisions

    bad = tmp_path / "x-decisions.json"
    bad.write_text(json.dumps({"skill": "shenbi-x", "not_schema": 1}), encoding="utf-8")
    result = g4_decisions([str(bad)])
    assert '"status": "FAIL"' in result
    # parse/pydantic path composes G4.dec.<id>:<file>:<reason> byte-stable
    assert "G4.dec." in result and str(bad) in result
