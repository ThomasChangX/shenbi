"""Auto-generated minimal contract model for shenbi-character-design."""

from __future__ import annotations

from pydantic import BaseModel, Field


class Report(BaseModel):
    """Minimal output contract for shenbi-character-design."""

    model_config = {"extra": "ignore"}
    kind: str = Field(default="artifact")
