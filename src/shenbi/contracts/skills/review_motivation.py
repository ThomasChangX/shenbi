"""Auto-generated minimal contract model for shenbi-review-motivation."""

from __future__ import annotations

from pydantic import BaseModel, Field


class Report(BaseModel):
    """Minimal output contract for shenbi-review-motivation."""

    model_config = {"extra": "ignore"}
    kind: str = Field(default="artifact")
