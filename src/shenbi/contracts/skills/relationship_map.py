"""Auto-generated minimal contract model for shenbi-relationship-map."""

from __future__ import annotations

from pydantic import BaseModel, Field


class Report(BaseModel):
    """Minimal output contract for shenbi-relationship-map."""

    model_config = {"extra": "ignore"}
    kind: str = Field(default="artifact")
