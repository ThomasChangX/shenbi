"""Generator: expected_outputs (parametric->glob), DAG, index — from contracts."""

from __future__ import annotations

import pytest

from shenbi.sync_contracts import (
    build_dag,
    derive_expected_outputs,
    normalize_to_glob,
    verify_bijection,
)


@pytest.mark.unit
def test_parametric_normalizes_to_glob() -> None:
    reg = {"patterns": [{"parametric": "chapters/chapter-N.md", "glob": "chapters/chapter-*.md"}]}
    assert normalize_to_glob("chapters/chapter-N.md", reg) == "chapters/chapter-*.md"


@pytest.mark.unit
def test_declared_glob_passes_through() -> None:
    reg = {"globs": [{"pattern": "truth/*.md"}], "patterns": []}
    assert normalize_to_glob("truth/*.md", reg) == "truth/*.md"


@pytest.mark.unit
def test_concrete_path_stays_concrete() -> None:
    reg = {"concepts": [{"name": "novel.json"}], "patterns": [], "globs": []}
    assert normalize_to_glob("novel.json", reg) == "novel.json"


@pytest.mark.unit
def test_dag_edge_from_producer_to_consumer() -> None:
    contracts = {
        "A": {"writes": ["chapters/chapter-N.md"], "updates": [], "reads": []},
        "B": {"writes": [], "updates": [], "reads": ["chapters/chapter-N.md"]},
    }
    reg = {
        "patterns": [{"parametric": "chapters/chapter-N.md", "glob": "chapters/chapter-*.md"}],
        "globs": [],
        "concepts": [],
    }
    dag = build_dag(contracts, reg)
    assert {"producer": "A", "consumer": "B", "file": "chapters/chapter-N.md"} in dag["edges"]


@pytest.mark.unit
def test_dag_connects_concrete_write_to_glob_read() -> None:
    """A concrete audit write must join a glob audit read (glob-aware matching)."""
    contracts = {
        "reviewer": {"writes": ["audits/chapter-N-anti-ai.md"], "updates": [], "reads": []},
        "drift": {"writes": [], "updates": [], "reads": ["audits/chapter-N-*.md"]},
    }
    reg = {"concepts": [], "patterns": [], "globs": [{"pattern": "audits/chapter-*.md"}]}
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
    reg = {
        "patterns": [{"parametric": "chapters/chapter-N.md", "glob": "chapters/chapter-*.md"}],
        "globs": [],
        "concepts": [],
    }
    assert derive_expected_outputs(phase, contracts, reg) == ["chapters/chapter-*.md"]


@pytest.mark.unit
def test_bijection_self_check_passes_when_complete() -> None:
    """Every member write is emitted and every emitted entry traces to a member."""
    phase = {"prerequisites": ["A"]}
    contracts = {"A": {"writes": ["novel.json"], "updates": [], "reads": []}}
    reg = {"concepts": [{"name": "novel.json"}], "patterns": [], "globs": []}
    generated = derive_expected_outputs(phase, contracts, reg)
    # No raise == bijection holds (catches generator bugs, not curated drift).
    verify_bijection(generated, phase, contracts, reg)
