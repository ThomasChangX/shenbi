"""Auto-generated minimal contract model for shenbi-short-outline."""

from __future__ import annotations

from pydantic import BaseModel, Field


class Report(BaseModel):
    """Minimal output contract for shenbi-short-outline."""

    model_config = {"extra": "ignore"}
    kind: str = Field(default="artifact")
