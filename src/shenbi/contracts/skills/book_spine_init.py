"""Auto-generated minimal contract model for shenbi-book-spine-init."""

from __future__ import annotations

from pydantic import BaseModel, Field


class Report(BaseModel):
    """Minimal output contract for shenbi-book-spine-init."""

    model_config = {"extra": "ignore"}
    kind: str = Field(default="artifact")
