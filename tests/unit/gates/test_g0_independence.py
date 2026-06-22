"""Unit tests for G0.13: report-kind skills must declare independence.

Function contract (verified against src/shenbi/gates/g0.py):

- check_independence_markers(skills: dict[str, dict[str, Any]]) -> list[str]
    G0 sub-check: every report-kind skill must declare
    ``requires_independent_agent: true``. Caller assembles
    ``skills[skill] = {"kind": OutputKind, "has_marker": bool}`` via
    ``load_contract`` + ``requires_independent_agent``. Returns a list of
    issue strings (empty list == all OK).
"""

from __future__ import annotations

from typing import Any

import pytest

from shenbi.gates.g0 import check_independence_markers


@pytest.mark.unit
def test_report_skill_without_marker_fails() -> None:
    """A report-kind skill lacking the marker surfaces an issue."""
    skills: dict[str, dict[str, Any]] = {
        "shenbi-review-foo": {"kind": "report", "has_marker": False}
    }
    issues = check_independence_markers(skills)
    assert any("shenbi-review-foo" in i for i in issues)


@pytest.mark.unit
def test_artifact_skill_without_marker_ok() -> None:
    """Artifact-kind skills are exempt from the independence requirement."""
    skills: dict[str, dict[str, Any]] = {
        "shenbi-chapter-drafting": {"kind": "artifact", "has_marker": False}
    }
    assert check_independence_markers(skills) == []


@pytest.mark.unit
def test_report_skill_with_marker_ok() -> None:
    """A report-kind skill declaring the marker passes cleanly."""
    skills: dict[str, dict[str, Any]] = {
        "shenbi-review-resonance": {"kind": "report", "has_marker": True}
    }
    assert check_independence_markers(skills) == []
