"""Auto-generated minimal contract model for shenbi-foreshadowing-track."""

from __future__ import annotations

from pydantic import BaseModel, Field


class Report(BaseModel):
    """Minimal output contract for shenbi-foreshadowing-track."""

    model_config = {"extra": "ignore"}
    kind: str = Field(default="artifact")
