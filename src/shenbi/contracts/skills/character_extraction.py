"""Auto-generated minimal contract model for shenbi-character-extraction."""

from __future__ import annotations

from pydantic import BaseModel, Field


class Report(BaseModel):
    """Minimal output contract for shenbi-character-extraction."""

    model_config = {"extra": "ignore"}
    kind: str = Field(default="artifact")
