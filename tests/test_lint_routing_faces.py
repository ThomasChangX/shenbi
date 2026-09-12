"""Routing-face DEPRECATED reconciliation lint tests (spec #59 T11; acceptance 4)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.lint_routing_faces import lint_routing_faces

REPO = Path(__file__).resolve().parents[1]


@pytest.mark.unit
def test_real_repo_baseline_zero() -> None:
    assert lint_routing_faces(REPO, REPO / "skills") == []


@pytest.mark.unit
def test_injected_deprecated_registration_fails(tmp_path: Path) -> None:
    skills = tmp_path / "skills"
    skills.mkdir()
    (skills / "shenbi-dead").mkdir()
    (skills / "shenbi-dead" / "SKILL.md").write_text("# DEPRECATED: gone\n", encoding="utf-8")
    deps = tmp_path / "tests" / "tiers"
    deps.mkdir(parents=True)
    (deps / "deps.json").write_text(
        json.dumps({"t2-phases": {"audit": {"prerequisites": ["shenbi-dead"]}}}),
        encoding="utf-8",
    )
    errs = lint_routing_faces(tmp_path, skills)
    assert any("shenbi-dead" in e for e in errs)


@pytest.mark.unit
def test_injected_table_ghost_name_fails(tmp_path: Path) -> None:
    """Spec T3.11(b) existence direction: a routed name without a skills/ dir."""
    skills = tmp_path / "skills"
    skills.mkdir()
    (skills / "using-shenbi").mkdir(parents=True)
    (skills / "using-shenbi" / "SKILL.md").write_text(
        "| phrase | shenbi-review-typoed |\n", encoding="utf-8"
    )
    errs = lint_routing_faces(tmp_path, skills)
    assert any("shenbi-review-typoed" in e for e in errs)
