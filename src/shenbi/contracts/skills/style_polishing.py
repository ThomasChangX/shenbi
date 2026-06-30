"""Auto-generated minimal contract model for shenbi-style-polishing."""

from __future__ import annotations

from pydantic import BaseModel, Field


class Report(BaseModel):
    """Minimal output contract for shenbi-style-polishing."""

    model_config = {"extra": "ignore"}
    kind: str = Field(default="artifact")
