"""Auto-generated minimal contract model for shenbi-chapter-pattern."""

from __future__ import annotations

from pydantic import BaseModel, Field


class Report(BaseModel):
    """Minimal output contract for shenbi-chapter-pattern."""

    model_config = {"extra": "ignore"}
    kind: str = Field(default="artifact")
