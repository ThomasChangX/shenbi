"""Auto-generated minimal contract model for shenbi-review-dialogue."""

from __future__ import annotations

from pydantic import BaseModel, Field


class Report(BaseModel):
    """Minimal output contract for shenbi-review-dialogue."""

    model_config = {"extra": "ignore"}
    kind: str = Field(default="artifact")
