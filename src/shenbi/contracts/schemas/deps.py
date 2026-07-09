"""DepsDoc: matches real tests/tiers/deps.json shape (phase-0 verified).

D19 resolution: G3.1's per-skill prerequisite check was a dead function
(deps.json never stored per-skill prereq data — ``prerequisites`` is a phase
member roster, not per-skill). The model exposes :func:`phase_of` for
skill->phase lookup; the G3.1 prerequisite logic is deleted in a later task.

Phase-0-verified facts reflected here:
- top-level keys are hyphenated and several carry leading underscores
  (``t2-phases``, ``t3-pipelines``, ``_tool_hashes``, ``_out_of_pipeline``,
  ``_calibration_hashes``). Each maps to a snake_case python attribute via
  ``Field(alias=...)`` and ``populate_by_name=True``.
- ``t2-phases`` is a DICT keyed by phase name (NOT a list). Each value is a
  :class:`PhaseDeps` with ``{prerequisites, expected_outputs, g4_checker,
  _g4_note}``. Five real phases carry ``_g4_note``.
- ``_out_of_pipeline`` is a nested DICT ``{t1_only_auxiliary, t1_only_meta,
  t1_only_drafting_phase, _note}`` (NOT a list).
- leading-underscore keys MUST use ``Field(alias=...)``: pydantic v2 treats
  attributes named ``_foo`` as private attrs and would silently drop them.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class PhaseDeps(BaseModel):
    """A single T2 phase: member roster, outputs, and optional G4 checker."""

    model_config = {"extra": "forbid", "populate_by_name": True}
    prerequisites: list[str] = []
    expected_outputs: list[str] = []
    g4_checker: str | None = None
    g4_note: str | None = Field(default=None, alias="_g4_note")


class PipelineDeps(BaseModel):
    """A single T3 pipeline: phase roster and the chapter-ratio floor."""

    model_config = {"extra": "forbid", "populate_by_name": True}
    min_chapter_ratio: float = 0.0
    expected_outputs: list[str] = []
    prerequisites: list[str] = []


class OutOfPipeline(BaseModel):
    """``_out_of_pipeline`` block: T1 skills no T2 phase requires."""

    model_config = {"extra": "forbid", "populate_by_name": True}
    t1_only_auxiliary: list[str] = []
    t1_only_meta: list[str] = []
    t1_only_drafting_phase: list[str] = []
    note: str = Field(default="", alias="_note")


class DepsDoc(BaseModel):
    """Top-level shape of tests/tiers/deps.json."""

    model_config = {"extra": "forbid", "populate_by_name": True}
    t2_phases: dict[str, PhaseDeps] = Field(default_factory=dict, alias="t2-phases")
    t3_pipelines: dict[str, PipelineDeps] = Field(default_factory=dict, alias="t3-pipelines")
    tool_hashes: dict[str, str] = Field(default_factory=dict, alias="_tool_hashes")
    out_of_pipeline: OutOfPipeline = Field(default_factory=OutOfPipeline, alias="_out_of_pipeline")
    calibration_hashes: dict[str, str] = Field(default_factory=dict, alias="_calibration_hashes")


def phase_of(deps: DepsDoc, skill: str) -> str | None:
    """Return the name of the T2 phase whose member roster contains ``skill``.

    ``prerequisites`` is a phase's MEMBER ROSTER (sync_contracts calls it
    "members"), so this is the lookup that locates which phase a skill belongs
    to. Returns ``None`` if the skill is not a member of any phase
    (e.g. it lives in ``out_of_pipeline`` or is unknown).
    """
    for pname, p in deps.t2_phases.items():
        if skill in p.prerequisites:
            return pname
    return None
