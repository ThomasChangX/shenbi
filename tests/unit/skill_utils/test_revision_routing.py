"""Unit tests for skill_utils/revision_routing/route.py (spec §5.2)."""

from __future__ import annotations

import pytest

from shenbi.skill_utils.revision_routing.route import route_revision


@pytest.mark.unit
def test_pure_craft_issues_route_to_spot_fix() -> None:
    diagnosis = {
        "issues": [
            {
                "category": "craft",
                "id": "craft-ai-tell-L23",
                "evidence": "ch5.md L23",
                "severity": "CRITICAL",
            },
        ]
    }
    assert route_revision(diagnosis) == "spot-fix"


@pytest.mark.unit
def test_unmet_blocking_goal_routes_to_regenerate() -> None:
    diagnosis = {
        "issues": [
            {
                "category": "unmet_goal",
                "id": "goal-H01-advance",
                "evidence": "ch5.md",
                "severity": "BLOCKING",
            },
        ]
    }
    assert route_revision(diagnosis) == "regenerate"


@pytest.mark.unit
def test_unmet_blocking_plus_craft_routes_to_constrained_regenerate() -> None:
    diagnosis = {
        "issues": [
            {
                "category": "unmet_goal",
                "id": "goal-H01-advance",
                "evidence": "ch5.md",
                "severity": "BLOCKING",
            },
            {
                "category": "craft",
                "id": "craft-fatigue-L40",
                "evidence": "ch5.md L40",
                "severity": "MINOR",
            },
        ]
    }
    assert route_revision(diagnosis) == "constrained-regenerate"


@pytest.mark.unit
def test_unmet_non_blocking_goal_routes_to_spot_fix() -> None:
    diagnosis = {
        "issues": [
            {
                "category": "unmet_goal",
                "id": "goal-soft",
                "evidence": "ch5.md",
                "severity": "MINOR",
            },
        ]
    }
    assert route_revision(diagnosis) == "spot-fix"


@pytest.mark.unit
def test_empty_diagnosis_routes_to_spot_fix() -> None:
    assert route_revision({"issues": []}) == "spot-fix"
