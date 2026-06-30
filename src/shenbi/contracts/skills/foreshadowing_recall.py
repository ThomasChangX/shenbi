"""Auto-generated minimal contract model for shenbi-foreshadowing-recall."""

from __future__ import annotations

from pydantic import BaseModel, Field


class Report(BaseModel):
    """Minimal output contract for shenbi-foreshadowing-recall."""

    model_config = {"extra": "ignore"}
    kind: str = Field(default="artifact")
