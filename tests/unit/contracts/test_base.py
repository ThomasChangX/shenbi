"""base.py PureInput + GateOutcome frozen 基类型测试。"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from shenbi.contracts.base import GateOutcome, PureInput
from shenbi.status import GateStatus


def test_pure_input_frozen() -> None:
    pi = PureInput(skill="x", round_dir=Path("/tmp"), raw_outputs={"a.md": "..."})
    with pytest.raises(FrozenInstanceError):
        pi.skill = "y"  # type: ignore[misc]


def test_gate_outcome_frozen() -> None:
    gr = GateOutcome(skill="x", status=GateStatus.PASS, issues=(), checks=())
    with pytest.raises(FrozenInstanceError):
        gr.status = "FAIL"  # type: ignore[misc]


def test_gate_outcome_factories() -> None:
    assert GateOutcome.passed("x").status == "PASS"
    f = GateOutcome.fail("x", ["e1", "e2"])
    assert f.status == "FAIL"
    assert f.issues == ("e1", "e2")


class TestFrontmatterAnchoringSpec16:
    def test_midline_dashes_not_frontmatter_delimiter(self, tmp_path, monkeypatch):
        """F263: a `---` inside frontmatter values must not end the block."""
        import sys

        sys.path.insert(0, "src")
        from shenbi.contracts.legacy import read_frontmatter_contract

        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text(
            "---\nname: shenbi-x\ndescription: uses a---b token\ncontract:\n  reads: []\n  writes: []\n---\nbody\n",
            encoding="utf-8",
        )
        contract = read_frontmatter_contract("shenbi-x", skill_md)
        assert contract == {"reads": [], "writes": []}

    def test_closing_fence_at_eof_accepted(self, tmp_path):
        """F263: closing `---` with no trailing newline is still valid."""
        from shenbi.contracts.legacy import read_frontmatter_contract

        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text(
            "---\nname: shenbi-x\ncontract:\n  reads: []\n  writes: []\n---",
            encoding="utf-8",
        )
        contract = read_frontmatter_contract("shenbi-x", skill_md)
        assert contract == {"reads": [], "writes": []}
