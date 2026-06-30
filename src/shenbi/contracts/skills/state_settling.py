"""Auto-generated minimal contract model for shenbi-state-settling."""

from __future__ import annotations

from pydantic import BaseModel, Field


class Report(BaseModel):
    """Minimal output contract for shenbi-state-settling."""

    model_config = {"extra": "ignore"}
    kind: str = Field(default="artifact")
