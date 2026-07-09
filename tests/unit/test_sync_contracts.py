"""Generator: expected_outputs (parametric->glob), DAG, index — from contracts."""

from __future__ import annotations

from typing import Any

import pytest

from shenbi.contracts.graph import normalize_to_glob
from shenbi.contracts.schemas.registry import TruthFilesRegistry
from shenbi.sync_contracts import (
    build_dag,
    derive_expected_outputs,
    verify_bijection,
)

# The functions under test read only ``patterns`` / ``globs`` (not ``concepts``),
# but ``TruthFilesRegistry`` forbids empty concepts (D24 structural-drift guard).
# Supply a harmless placeholder concept so unit fixtures stay minimal.
_PLACEHOLDER_CONCEPT = {"name": "novel.json", "kind": "config"}


def _reg(
    *,
    patterns: list[dict[str, Any]] | None = None,
    globs: list[dict[str, Any]] | None = None,
    concepts: list[dict[str, Any]] | None = None,
) -> TruthFilesRegistry:
    """Build a minimal ``TruthFilesRegistry`` for graph/DAG unit tests.

    Uses ``model_validate`` (accepts plain dicts) rather than the typed
    constructor so the static checker does not reject dict fixtures.
    """
    return TruthFilesRegistry.model_validate(
        {
            "concepts": concepts if concepts else [_PLACEHOLDER_CONCEPT],
            "patterns": patterns or [],
            "globs": globs or [],
        }
    )


@pytest.mark.unit
def test_parametric_normalizes_to_glob() -> None:
    reg = _reg(patterns=[{"parametric": "chapters/chapter-N.md", "glob": "chapters/chapter-*.md"}])
    assert normalize_to_glob("chapters/chapter-N.md", reg) == "chapters/chapter-*.md"


@pytest.mark.unit
def test_normalize_falls_back_to_declared_glob_for_per_dim_literal() -> None:
    """A per-dimension audit literal (audits/chapter-N-anti-ai.md) is not the
    registered parametric (audits/chapter-N-<dim>.md), so the patterns lookup
    misses. The globs fallback must resolve it to audits/chapter-*.md — without
    this, expected_outputs carries a literal N and G5.4 / cmd_pre_score never
    match real numbered files (regression for Copilot review on PR #6).
    """
    reg = _reg(
        patterns=[{"parametric": "audits/chapter-N-<dim>.md", "glob": "audits/chapter-*.md"}],
        globs=[{"pattern": "audits/chapter-*.md"}],
    )
    assert normalize_to_glob("audits/chapter-N-anti-ai.md", reg) == "audits/chapter-*.md"


@pytest.mark.unit
def test_parametric_glob_wins_over_broader_declared_glob() -> None:
    """A registered parametric (chapters/chapter-N.md) matches both its own
    pattern and the broad chapters/*.md glob; the specific parametric glob must
    win so the normalized output stays specific.
    """
    reg = _reg(
        patterns=[{"parametric": "chapters/chapter-N.md", "glob": "chapters/chapter-*.md"}],
        globs=[{"pattern": "chapters/*.md"}],
    )
    assert normalize_to_glob("chapters/chapter-N.md", reg) == "chapters/chapter-*.md"


@pytest.mark.unit
def test_load_all_contracts_emits_kind() -> None:
    """load_all_contracts() must include ``kind`` per contract — the
    contract-completeness lint (lint_contracts.find_completeness_violations)
    gates on ``c.get("kind") == "report"``; dropping kind made the lint dead.
    Regression for Copilot review on PR #6.
    """
    from shenbi.sync_contracts import load_all_contracts

    contracts = load_all_contracts()
    assert contracts, "expected migrated skills to load"
    for skill, c in contracts.items():
        assert "kind" in c, f"{skill} contract missing kind (completeness lint would skip it)"


@pytest.mark.unit
def test_declared_glob_passes_through() -> None:
    reg = _reg(globs=[{"pattern": "truth/*.md"}])
    assert normalize_to_glob("truth/*.md", reg) == "truth/*.md"


@pytest.mark.unit
def test_concrete_path_stays_concrete() -> None:
    reg = _reg(concepts=[{"name": "novel.json", "kind": "config"}])
    assert normalize_to_glob("novel.json", reg) == "novel.json"


@pytest.mark.unit
def test_dag_edge_from_producer_to_consumer() -> None:
    contracts = {
        "A": {"writes": ["chapters/chapter-N.md"], "updates": [], "reads": []},
        "B": {"writes": [], "updates": [], "reads": ["chapters/chapter-N.md"]},
    }
    reg = _reg(patterns=[{"parametric": "chapters/chapter-N.md", "glob": "chapters/chapter-*.md"}])
    dag = build_dag(contracts, reg)
    assert {"producer": "A", "consumer": "B", "file": "chapters/chapter-N.md"} in dag["edges"]


@pytest.mark.unit
def test_dag_connects_concrete_write_to_glob_read() -> None:
    """A concrete audit write must join a glob audit read (glob-aware matching)."""
    contracts = {
        "reviewer": {"writes": ["audits/chapter-N-anti-ai.md"], "updates": [], "reads": []},
        "drift": {"writes": [], "updates": [], "reads": ["audits/chapter-N-*.md"]},
    }
    reg = _reg(globs=[{"pattern": "audits/chapter-*.md"}])
    dag = build_dag(contracts, reg)
    assert any(e["producer"] == "reviewer" and e["consumer"] == "drift" for e in dag["edges"])


@pytest.mark.unit
def test_derive_expected_outputs_normalizes_and_dedups() -> None:
    """Two members writing the same glob -> one entry; parametric -> glob."""
    phase = {"prerequisites": ["A", "B"]}
    contracts = {
        "A": {"writes": ["chapters/chapter-N.md"], "updates": [], "reads": []},
        "B": {"writes": [], "updates": ["chapters/chapter-N.md"], "reads": []},
    }
    reg = _reg(patterns=[{"parametric": "chapters/chapter-N.md", "glob": "chapters/chapter-*.md"}])
    assert derive_expected_outputs(phase, contracts, reg) == ["chapters/chapter-*.md"]


@pytest.mark.unit
def test_bijection_self_check_passes_when_complete() -> None:
    """Every member write is emitted and every emitted entry traces to a member."""
    phase = {"prerequisites": ["A"]}
    contracts = {"A": {"writes": ["novel.json"], "updates": [], "reads": []}}
    reg = _reg(concepts=[{"name": "novel.json", "kind": "config"}])
    generated = derive_expected_outputs(phase, contracts, reg)
    # No raise == bijection holds (catches generator bugs, not curated drift).
    verify_bijection(generated, phase, contracts, reg)


@pytest.mark.unit
def test_bijection_self_check_rejects_dropped_member_write() -> None:
    """verify_bijection raises when a member write is missing from generated."""
    phase = {"prerequisites": ["A", "B"]}
    contracts = {
        "A": {"writes": ["novel.json"], "updates": [], "reads": []},
        "B": {"writes": ["genre-config.json"], "updates": [], "reads": []},
    }
    reg = _reg(
        concepts=[
            {"name": "novel.json", "kind": "config"},
            {"name": "genre-config.json", "kind": "config"},
        ]
    )
    # Drop B's write -> the bijection is broken (member output not emitted).
    with pytest.raises(AssertionError, match="genre-config"):
        verify_bijection(["novel.json"], phase, contracts, reg)
