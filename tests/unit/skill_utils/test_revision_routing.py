"""Unit tests for skill_utils/revision_routing/route.py (spec §5.2)."""

from __future__ import annotations

import pytest

from shenbi.skill_utils.revision_routing.preserve_check import verify_preservation
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


@pytest.mark.unit
def test_preservation_pass_when_all_items_retained() -> None:
    original = {
        "chapter": 5,
        "hooks_advanced": ["H01", "H03"],
        "changes_realized": ["信息: 得知反派寻找玉佩"],
        "state_changes": ["林轩: 紧张→自信"],
    }
    regenerated = {
        "chapter": 5,
        "hooks_advanced": ["H01", "H03", "H04"],  # superset OK
        "changes_realized": ["信息: 得知反派寻找玉佩"],
        "state_changes": ["林轩: 紧张→自信"],
    }
    ok, violations = verify_preservation(original, regenerated)
    assert ok
    assert violations == []


@pytest.mark.unit
def test_preservation_fails_when_hook_lost() -> None:
    original = {
        "chapter": 5,
        "hooks_advanced": ["H01", "H03"],
        "changes_realized": [],
        "state_changes": [],
    }
    regenerated = {
        "chapter": 5,
        "hooks_advanced": ["H01"],  # H03 lost
        "changes_realized": [],
        "state_changes": [],
    }
    ok, violations = verify_preservation(original, regenerated)
    assert not ok
    assert any("H03" in v for v in violations)


@pytest.mark.unit
def test_preservation_fails_when_change_lost() -> None:
    original = {
        "chapter": 5,
        "hooks_advanced": [],
        "changes_realized": ["权力: 升入内门"],
        "state_changes": [],
    }
    regenerated = {
        "chapter": 5,
        "hooks_advanced": [],
        "changes_realized": [],  # change lost
        "state_changes": [],
    }
    ok, violations = verify_preservation(original, regenerated)
    assert not ok
    assert len(violations) == 1


@pytest.mark.unit
def test_preservation_fails_when_state_change_reverted() -> None:
    original = {
        "chapter": 5,
        "hooks_advanced": [],
        "changes_realized": [],
        "state_changes": ["苏晴: 观望→认可"],
    }
    regenerated = {
        "chapter": 5,
        "hooks_advanced": [],
        "changes_realized": [],
        "state_changes": [],  # reverted
    }
    ok, violations = verify_preservation(original, regenerated)
    assert not ok
    assert len(violations) == 1
