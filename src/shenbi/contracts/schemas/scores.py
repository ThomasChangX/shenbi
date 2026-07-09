"""ScoreReport: shape of a scoring/score-report doc (g5 consumer).

``extra: forbid`` so undeclared dimensions/provenance keys surface as drift.
The provenance block is serialized under the leading-underscore key
``_provenance`` (phase-0 fact), so it is exposed via ``Field(alias=...)`` with
``populate_by_name=True``.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ScoreDimension(BaseModel):
    model_config = {"extra": "forbid"}
    num: int
    name: str = ""
    weight: float = 0.0
    score: float


class ScoreProvenance(BaseModel):
    model_config = {"extra": "forbid"}
    scored_by: str = ""
    timestamp: str = ""
    gate_markers_verified: bool = False
    round_dir: str = ""
    scoring_tool: str = ""


class ScoreReport(BaseModel):
    model_config = {"extra": "forbid", "populate_by_name": True}
    dimensions: list[ScoreDimension] = []
    final_score: float = 0.0
    classification: str = ""
    kill_switch_triggered: bool = False
    kill_switches: list[str] = []
    provenance: ScoreProvenance | None = Field(default=None, alias="_provenance")
