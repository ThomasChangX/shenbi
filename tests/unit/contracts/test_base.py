"""base.py PureInput + GateOutcome frozen 基类型测试。"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from shenbi.contracts.base import GateOutcome, PureInput


def test_pure_input_frozen() -> None:
    pi = PureInput(skill="x", round_dir=Path("/tmp"), raw_outputs={"a.md": "..."})
    with pytest.raises(FrozenInstanceError):
        pi.skill = "y"  # type: ignore[misc]


def test_gate_outcome_frozen() -> None:
    gr = GateOutcome(skill="x", status="PASS", issues=(), checks=())
    with pytest.raises(FrozenInstanceError):
        gr.status = "FAIL"  # type: ignore[misc]


def test_gate_outcome_factories() -> None:
    assert GateOutcome.passed("x").status == "PASS"
    f = GateOutcome.fail("x", ["e1", "e2"])
    assert f.status == "FAIL"
    assert f.issues == ("e1", "e2")
