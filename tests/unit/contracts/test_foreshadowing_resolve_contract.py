"""foreshadowing_resolve 契约模型测试——根治 spec 的 CP 算术三 bug。"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from shenbi.contracts.registry import REGISTRY
from shenbi.contracts.skills.foreshadowing_resolve import (
    CP_THRESHOLDS,
    HookCP,
    Report,
)


def test_cp_thresholds_constants() -> None:
    assert CP_THRESHOLDS == {
        "GREEN_MAX": 50,
        "RED_NOW": 100,
        "FORCE_NEXT_CHAPTER": 200,
    }


def test_zone_computed_from_cp() -> None:
    assert HookCP(hook_id="h", cp=80, last_reinforced=1, current_chapter=10).zone == "ORANGE"
    assert HookCP(hook_id="h", cp=100, last_reinforced=1, current_chapter=10).zone == "RED"
    assert HookCP(hook_id="h", cp=49, last_reinforced=1, current_chapter=10).zone == "GREEN"
    assert (
        HookCP(hook_id="h", cp=50, last_reinforced=1, current_chapter=10).zone == "ORANGE"
    )  # GREEN_MAX boundary


def test_zone_ignores_hand_filled() -> None:
    """N7 + Bug 1: hand-filled zone=RED ignored by extra=ignore, recomputed."""
    h = HookCP.model_validate(
        {"hook_id": "h", "cp": 80, "zone": "RED", "last_reinforced": 1, "current_chapter": 1}
    )
    assert h.zone == "ORANGE"


def test_report_rejects_inconsistent_debt() -> None:
    with pytest.raises(ValidationError):
        Report(
            current_chapter=10,
            hooks=[HookCP(hook_id="h", cp=100, last_reinforced=1, current_chapter=10)],
            debt_level="GREEN",
        )


def test_report_rejects_dup_hook_three_cp() -> None:
    """v2 M3: three cp values (80/45/180) faithful to spec 'three CP'."""
    with pytest.raises(ValidationError):
        Report(
            current_chapter=10,
            hooks=[
                HookCP(hook_id="h1", cp=80, last_reinforced=1, current_chapter=10),
                HookCP(hook_id="h1", cp=45, last_reinforced=1, current_chapter=10),
                HookCP(hook_id="h1", cp=180, last_reinforced=1, current_chapter=10),
            ],
            debt_level="RED",
        )


def test_report_accepts_valid() -> None:
    r = Report(
        current_chapter=10,
        hooks=[HookCP(hook_id="h1", cp=80, last_reinforced=1, current_chapter=10)],
        debt_level="ORANGE",
    )
    assert r.debt_level == "ORANGE"


def test_must_resolve_threshold() -> None:
    assert (
        HookCP(hook_id="h", cp=201, last_reinforced=1, current_chapter=10).must_resolve_next_chapter
        is True
    )
    assert (
        HookCP(hook_id="h", cp=200, last_reinforced=1, current_chapter=10).must_resolve_next_chapter
        is False
    )


def test_must_resolve_serialized() -> None:
    """v2 M1: must_resolve uses computed_field to enter model_dump (pillar 6 doc derivation)."""
    h = HookCP(hook_id="h", cp=201, last_reinforced=1, current_chapter=10)
    assert h.model_dump()["must_resolve_next_chapter"] is True


def test_registry_includes_resolve() -> None:
    assert REGISTRY["shenbi-foreshadowing-resolve"] is Report
