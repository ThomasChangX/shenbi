"""Unit tests for skill_utils/foreshadowing_recall/recall.py (spec §3.6)."""

from __future__ import annotations

import pytest

from shenbi.skill_utils.foreshadowing_recall.recall import recall_overdue_hooks


@pytest.mark.unit
def test_overdue_hook_returned() -> None:
    hooks = [
        {"id": "H01", "last_reinforced": 60, "max_distance": 20},  # silence=6 < 20, NOT overdue
        {"id": "H02", "last_reinforced": 50, "max_distance": 15},  # silence=16 > 15, overdue
    ]
    overdue = recall_overdue_hooks(hooks, current_chapter=66)
    assert "H02" in overdue
    assert "H01" not in overdue


@pytest.mark.unit
def test_non_overdue_hooks_excluded() -> None:
    hooks = [
        {"id": "H01", "last_reinforced": 60, "max_distance": 20},  # 66-60=6 < 20
        {"id": "H02", "last_reinforced": 55, "max_distance": 20},  # 66-55=11 < 20
    ]
    assert recall_overdue_hooks(hooks, current_chapter=66) == []


@pytest.mark.unit
def test_resolved_hooks_excluded() -> None:
    hooks = [
        {"id": "H01", "last_reinforced": 3, "max_distance": 20, "state": "RESOLVED"},
    ]
    assert recall_overdue_hooks(hooks, current_chapter=66) == []


@pytest.mark.unit
def test_multiple_overdue_returned() -> None:
    hooks = [
        {"id": "H01", "last_reinforced": 1, "max_distance": 10},
        {"id": "H02", "last_reinforced": 40, "max_distance": 15},
        {"id": "H03", "last_reinforced": 60, "max_distance": 20},
    ]
    overdue = recall_overdue_hooks(hooks, current_chapter=66)
    assert set(overdue) == {"H01", "H02"}


@pytest.mark.unit
def test_empty_hooks_returns_empty() -> None:
    assert recall_overdue_hooks([], current_chapter=100) == []


@pytest.mark.unit
def test_hook_without_max_distance_skipped() -> None:
    hooks = [{"id": "H01", "last_reinforced": 1}]  # no max_distance
    assert recall_overdue_hooks(hooks, current_chapter=100) == []
