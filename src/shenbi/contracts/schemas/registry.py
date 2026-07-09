"""Canonical model for docs/framework/truth-files.yaml (spec §5.3, fixes D1/D24).

Single source of truth for the file vocabulary. Adding a genuinely new file is
ONE edit to truth-files.yaml; this model guarantees every concept/pattern/glob
in the registry matches the declared shape (so silent synonym creation shows up
as a ValidationError at load).

Phase-0-verified facts reflected here:
- 16 kind values (the real yaml uses all 16).
- top-level keys: ``concepts`` (required), ``patterns`` / ``globs`` (optional,
  default empty); ``extra: forbid`` so undeclared keys surface as drift.
- the real file has NO ``version`` field — it defaults to 1 and the validator
  accepts only 1 (so a future bump is a loud, deliberate event).
- ``assert_non_empty`` (D24): an empty concepts list is structural drift.
- ``RegistryConcept.producer`` defaults to ``"skill"`` (Producer Registry). The
  real yaml does not carry this field yet (Task 17 adds it); the default lets
  loading succeed today.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, field_validator, model_validator

RegistryKind = Literal[
    "benchmark",
    "chapter",
    "character",
    "config",
    "context",
    "decisions",
    "import",
    "outline",
    "plan",
    "reference",
    "report",
    "short",
    "snapshot",
    "style",
    "truth",
    "world",
]

Producer = Literal["skill", "pipeline", "external", "shared"]


class RegistryConcept(BaseModel):
    """A single canonical file (matched verbatim)."""

    model_config = {"extra": "forbid"}
    name: str
    kind: RegistryKind
    producer: Producer = "skill"
    glob: str | None = None


class RegistryPattern(BaseModel):
    """A parametric concept -> its declared glob (generator lookup)."""

    model_config = {"extra": "forbid"}
    parametric: str
    glob: str


class RegistryGlob(BaseModel):
    """A declared wildcard that contracts may use verbatim."""

    model_config = {"extra": "forbid"}
    pattern: str


class TruthFilesRegistry(BaseModel):
    """Top-level shape of docs/framework/truth-files.yaml."""

    model_config = {"extra": "forbid", "populate_by_name": True}
    version: int = 1
    concepts: list[RegistryConcept]
    patterns: list[RegistryPattern] = []
    globs: list[RegistryGlob] = []

    @field_validator("version")
    @classmethod
    def _check_supported(cls, v: int) -> int:
        if v != 1:
            raise ValueError(f"unsupported registry version {v}, expected 1")
        return v

    @model_validator(mode="after")
    def _assert_non_empty(self) -> TruthFilesRegistry:
        if not self.concepts:
            raise ValueError("registry concepts empty — truth-files.yaml structural drift")
        return self
