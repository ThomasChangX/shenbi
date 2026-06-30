"""Auto-generated minimal contract model for shenbi-memory-distill."""

from __future__ import annotations

from pydantic import BaseModel, Field


class Report(BaseModel):
    """Minimal output contract for shenbi-memory-distill."""

    model_config = {"extra": "ignore"}
    kind: str = Field(default="artifact")
