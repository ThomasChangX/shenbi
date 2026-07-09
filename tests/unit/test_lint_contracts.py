"""Contract lints: every in-pipeline skill loads; report consumed => persisted."""

from __future__ import annotations

import pytest

from shenbi.contracts.schemas.registry import TruthFilesRegistry
from tools.lint_contracts import find_completeness_violations

# Only ``globs`` is exercised by the completeness check; concepts must be
# non-empty per the TruthFilesRegistry D24 structural-drift guard.
_REG = TruthFilesRegistry.model_validate(
    {
        "concepts": [{"name": "novel.json", "kind": "config"}],
        "patterns": [],
        "globs": [{"pattern": "audits/chapter-*.md"}],
    }
)


@pytest.mark.unit
def test_report_consumed_downstream_without_writes_is_flagged() -> None:
    dag = {"edges": [{"producer": "R", "consumer": "X", "file": "audits/chapter-N-anti-ai.md"}]}
    contracts = {
        "R": {"kind": "report", "reads": [], "writes": [], "updates": []},
        "X": {
            "kind": "artifact",
            "reads": ["audits/chapter-N-anti-ai.md"],
            "writes": [],
            "updates": [],
        },
    }
    vios = find_completeness_violations(contracts, dag, _REG)
    assert any(v["skill"] == "R" for v in vios)


@pytest.mark.unit
def test_report_with_persisted_writes_is_clean() -> None:
    dag = {"edges": [{"producer": "R", "consumer": "X", "file": "audits/chapter-N-anti-ai.md"}]}
    contracts = {
        "R": {
            "kind": "report",
            "reads": [],
            "writes": ["audits/chapter-N-anti-ai.md"],
            "updates": [],
        },
        "X": {
            "kind": "artifact",
            "reads": ["audits/chapter-N-anti-ai.md"],
            "writes": [],
            "updates": [],
        },
    }
    assert find_completeness_violations(contracts, dag, _REG) == []


@pytest.mark.unit
def test_glob_read_satisfied_by_concrete_report_write() -> None:
    """The completeness check is glob-aware: a concrete audit write satisfies
    a glob audit read (the real drift-guidance → review-* case).
    """
    dag = {
        "edges": [{"producer": "reviewer", "consumer": "drift", "file": "audits/chapter-N-*.md"}]
    }
    contracts = {
        "reviewer": {
            "kind": "report",
            "reads": [],
            "writes": ["audits/chapter-N-anti-ai.md"],
            "updates": [],
        },
        "drift": {
            "kind": "report",
            "reads": ["audits/chapter-N-*.md"],
            "writes": ["truth/drift_guidance.md"],
            "updates": [],
        },
    }
    assert find_completeness_violations(contracts, dag, _REG) == []
