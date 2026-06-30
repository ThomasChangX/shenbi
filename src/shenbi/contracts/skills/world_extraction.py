"""Auto-generated minimal contract model for shenbi-world-extraction."""

from __future__ import annotations

from pydantic import BaseModel, Field


class Report(BaseModel):
    """Minimal output contract for shenbi-world-extraction."""

    model_config = {"extra": "ignore"}
    kind: str = Field(default="artifact")
