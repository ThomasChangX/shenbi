"""Single source of truth for decisions.json validation.
Replaces hand-rolled checks in g2.py, g4/decisions_validator.py, g4/_decisions_schema.py.
Field shapes from phase-0 investigation of tests/unit/gates/test_g4_decisions.py.
"""

from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, Field, model_validator

DECISIONS_SCHEMA_VERSION = "shenbi-decisions-v1"
VALID_BASIS = {"adjacent_to_target_chapter", "arc_relevance", "volume_scope", "manual_override"}
VALID_SEVERITY = {"low", "high"}
_RATIONALE_MAX_CHARS = 100

Basis = Literal["adjacent_to_target_chapter", "arc_relevance", "volume_scope", "manual_override"]
Severity = Literal["low", "high"]
Handling = Literal["compensate_via_pacing", "explicit_callout", "defer_to_next_chapter", "ignore"]
Trim = Literal["none", "oldest_first", "lowest_relevance", "manual"]


class Selection(BaseModel):
    model_config = {"extra": "forbid"}
    target: str
    selected: list[str]
    basis: Basis
    severity: Severity = "low"
    omitted: list[str] = []
    rationale: str | None = None

    @model_validator(mode="after")
    def _p25(self) -> Selection:
        rationale = self.rationale
        has = rationale is not None
        if rationale is not None and len(rationale) > _RATIONALE_MAX_CHARS:
            raise ValueError(f"rationale exceeds {_RATIONALE_MAX_CHARS} chars")
        requires = self.severity == "high" or self.basis == "manual_override"
        routine_low = (
            self.basis in {"arc_relevance", "volume_scope", "adjacent_to_target_chapter"}
            and self.severity == "low"
        )
        if routine_low and has:
            raise ValueError("rationale FORBIDDEN for routine+low")
        if requires and not has:
            raise ValueError("rationale REQUIRED for high/manual_override")
        return self


class Adjustment(BaseModel):
    model_config = {"extra": "forbid"}
    issue_id: str
    severity: str  # NOT enum: doc uses "medium", legacy validator never checked
    handling: Handling
    rationale: str

    @model_validator(mode="after")
    def _rationale(self) -> Adjustment:
        if len(self.rationale) > _RATIONALE_MAX_CHARS:
            raise ValueError(f"rationale exceeds {_RATIONALE_MAX_CHARS} chars")
        return self


class Budget(BaseModel):
    model_config = {"extra": "forbid"}
    context_tokens_estimate: int
    limit: int
    trim_applied: Trim


class DecisionsDoc(BaseModel):
    model_config = {"extra": "forbid"}
    schema_: str = Field(alias="$schema")
    skill: str
    chapter: int
    selections: list[Selection] = []
    adjustments: list[Adjustment] = []
    budget: Budget | None = None
    produced_at: str

    @model_validator(mode="after")
    def _version(self) -> DecisionsDoc:
        if self.schema_ != DECISIONS_SCHEMA_VERSION:
            raise ValueError(f"$schema must be {DECISIONS_SCHEMA_VERSION}")
        return self
