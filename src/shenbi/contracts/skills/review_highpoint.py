"""Auto-generated minimal contract model for shenbi-review-highpoint."""

from __future__ import annotations

from pydantic import BaseModel, Field


class Report(BaseModel):
    """Minimal output contract for shenbi-review-highpoint."""

    model_config = {"extra": "ignore"}
    kind: str = Field(default="artifact")
