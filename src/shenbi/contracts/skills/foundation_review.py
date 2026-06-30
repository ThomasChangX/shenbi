"""Auto-generated minimal contract model for shenbi-foundation-review."""

from __future__ import annotations

from pydantic import BaseModel, Field


class Report(BaseModel):
    """Minimal output contract for shenbi-foundation-review."""

    model_config = {"extra": "ignore"}
    kind: str = Field(default="artifact")
