"""Auto-generated minimal contract model for shenbi-short-packaging."""

from __future__ import annotations

from pydantic import BaseModel, Field


class Report(BaseModel):
    """Minimal output contract for shenbi-short-packaging."""

    model_config = {"extra": "ignore"}
    kind: str = Field(default="artifact")
