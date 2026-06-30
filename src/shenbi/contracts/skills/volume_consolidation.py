"""Auto-generated minimal contract model for shenbi-volume-consolidation."""

from __future__ import annotations

from pydantic import BaseModel, Field


class Report(BaseModel):
    """Minimal output contract for shenbi-volume-consolidation."""

    model_config = {"extra": "ignore"}
    kind: str = Field(default="artifact")
