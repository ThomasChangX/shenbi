"""Auto-generated minimal contract model for shenbi-review-fanfic."""

from __future__ import annotations

from pydantic import BaseModel, Field


class Report(BaseModel):
    """Minimal output contract for shenbi-review-fanfic."""

    model_config = {"extra": "ignore"}
    kind: str = Field(default="artifact")
