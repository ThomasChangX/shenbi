"""Auto-generated minimal contract model for shenbi-pacing-design."""

from __future__ import annotations

from pydantic import BaseModel, Field


class Report(BaseModel):
    """Minimal output contract for shenbi-pacing-design."""

    model_config = {"extra": "ignore"}
    kind: str = Field(default="artifact")
    # TODO: add @model_validator for auto-check rules
