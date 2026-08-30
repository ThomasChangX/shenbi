"""F212/F431 (spec #30 T5): the P2.5 rationale matrix must name medium in the
error message and in both doc sources (schema doc + AGENTS.md) — code already
enforces rationale on medium severity; the sources drifted.
"""

import re
from pathlib import Path

import pytest
from pydantic import ValidationError

from shenbi.contracts.schemas.decisions import DecisionsDoc

REPO = Path(__file__).parent.parent


def _doc(selections: list[dict[str, object]]) -> dict[str, object]:
    return {
        "$schema": "shenbi-decisions-v1",
        "skill": "shenbi-chapter-drafting",
        "chapter": 5,
        "produced_at": "2026-08-31T00:00:00Z",
        "selections": selections,
    }


def test_medium_without_rationale_error_names_medium():
    doc = _doc([{"target": "t", "selected": ["a"], "basis": "arc_relevance", "severity": "medium"}])
    with pytest.raises(ValidationError, match="REQUIRED for medium"):
        DecisionsDoc.model_validate(doc)


def test_medium_with_rationale_passes():
    doc = _doc(
        [
            {
                "target": "t",
                "selected": ["a"],
                "basis": "arc_relevance",
                "severity": "medium",
                "rationale": "ok",
            }
        ]
    )
    DecisionsDoc.model_validate(doc)


def test_schema_doc_has_medium_row():
    text = (REPO / "docs" / "framework" / "decisions-schema.md").read_text(encoding="utf-8")
    assert re.search(r"medium.*rationale required", text), "P2.5 severity table missing medium row"


def test_agents_md_names_medium():
    text = (REPO / "AGENTS.md").read_text(encoding="utf-8")
    assert "medium" in text, "AGENTS.md P2.5 clause missing medium"
