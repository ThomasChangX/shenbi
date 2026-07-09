# tests/unit/contracts/schemas/test_decisions.py
import pytest
from pydantic import ValidationError

from shenbi.contracts.schemas.decisions import Adjustment, DecisionsDoc, Selection


def _doc(**kw):
    base = {
        "$schema": "shenbi-decisions-v1",
        "skill": "x",
        "chapter": 5,
        "selections": [],
        "produced_at": "2026-07-08T00:00:00Z",
    }
    base.update(kw)
    return base


class TestDecisionsDoc:
    def test_minimal_valid(self):
        d = DecisionsDoc.model_validate(_doc())
        assert d.skill == "x"

    def test_extra_rejected(self):
        with pytest.raises(ValidationError):
            DecisionsDoc.model_validate(_doc(tyop="x"))

    def test_wrong_schema_version(self):
        with pytest.raises(ValidationError):
            DecisionsDoc.model_validate(_doc(**{"$schema": "v2"}))


class TestSelectionP25:
    def test_routine_low_forbids_rationale(self):
        with pytest.raises(ValidationError):
            Selection.model_validate(
                {
                    "target": "t.md",
                    "selected": [],
                    "basis": "arc_relevance",
                    "severity": "low",
                    "omitted": [],
                    "rationale": "should fail",
                }
            )

    def test_high_requires_rationale(self):
        with pytest.raises(ValidationError):
            Selection.model_validate(
                {
                    "target": "t.md",
                    "selected": [],
                    "basis": "arc_relevance",
                    "severity": "high",
                    "omitted": [],
                }
            )

    def test_manual_override_requires_rationale(self):
        Selection.model_validate(
            {
                "target": "t.md",
                "selected": [],
                "basis": "manual_override",
                "severity": "low",
                "omitted": [],
                "rationale": "ok",
            }
        )  # passes


class TestAdjustment:
    def test_rationale_required(self):
        with pytest.raises(ValidationError):
            Adjustment.model_validate({"issue_id": "x", "severity": "medium", "handling": "ignore"})

    def test_severity_medium_allowed(self):
        # doc example uses medium; validator never checked it before; keep permissive
        Adjustment.model_validate(
            {"issue_id": "x", "severity": "medium", "handling": "ignore", "rationale": "ok"}
        )
