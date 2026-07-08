"""Glob-aware DAG key normalization (extracted to contracts/graph.py).

These functions live in their own module so G5.2 (runtime WARN), the
lint_contract_graph CI gate, and sync_contracts (DAG generation) all use
IDENTICAL matching semantics by importing from one place.
"""

from __future__ import annotations

import pytest

from shenbi.contracts.graph import dag_key, normalize_to_glob
from shenbi.contracts.schemas.registry import TruthFilesRegistry

REGISTRY = TruthFilesRegistry.model_validate(
    {
        "concepts": [{"name": "truth/current_state.md", "kind": "truth"}],
        "patterns": [{"parametric": "chapters/chapter-N.md", "glob": "chapters/chapter-*.md"}],
        "globs": [{"pattern": "truth/*.md"}, {"pattern": "chapters/chapter-*.md"}],
    }
)


@pytest.mark.unit
def test_exact_concept_folds_to_declared_glob() -> None:
    # A concrete truth file matches the declared glob ``truth/*.md``, so
    # ``dag_key`` returns that glob (globs are checked first — verbatim
    # behavior preserved from sync_contracts.py). NOTE: the task brief's
    # original assertion here expected ``truth/current_state.md`` passthrough,
    # which contradicts the verbatim dag_key (globs-first) and the "behavior
    # IDENTICAL / move verbatim" constraint. See task-3-report.md.
    assert dag_key("truth/current_state.md", REGISTRY) == "truth/*.md"


@pytest.mark.unit
def test_glob_match_folds_to_glob() -> None:
    # A path matching a declared glob folds to that glob pattern
    key = dag_key("truth/other.md", REGISTRY)
    assert key == "truth/*.md"


@pytest.mark.unit
def test_parametric_resolves_to_glob() -> None:
    # chapters/chapter-N.md (parametric) -> its declared glob chapters/chapter-*.md
    assert normalize_to_glob("chapters/chapter-N.md", REGISTRY) == "chapters/chapter-*.md"
