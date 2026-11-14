"""Spec #89 T6: G0.12 is falsifiable — injected no-checker skill turns it red."""

from __future__ import annotations

import pytest

import shenbi.gates.g0 as g0mod
from shenbi.gates.shared import all_skills
from shenbi.status import GateStatus


@pytest.mark.unit
def test_g012_fails_on_injected_fake_skill(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(g0mod, "all_skills", lambda: [*all_skills(), "shenbi-fake-skill"])
    g012 = g0mod.check_g4_checker_coverage()  # 提取的纯函数（-> dict[str, Any]）
    assert g012["s"] == GateStatus.FAIL
    assert "shenbi-fake-skill" in g012["note"]


@pytest.mark.unit
def test_g012_fails_on_registered_but_missing_skill(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        g0mod, "all_skills", lambda: [s for s in all_skills() if s != "using-shenbi"]
    )
    g012 = g0mod.check_g4_checker_coverage()
    assert g012["s"] == GateStatus.FAIL
    assert "using-shenbi" in g012["note"]


@pytest.mark.unit
def test_g012_passes_on_current_tree() -> None:
    g012 = g0mod.check_g4_checker_coverage()
    assert g012["s"] == GateStatus.PASS
    assert "roster reconciled" in g012["note"]
