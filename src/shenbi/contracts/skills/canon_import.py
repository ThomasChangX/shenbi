"""Auto-generated minimal contract model for shenbi-canon-import."""

from __future__ import annotations

from pydantic import BaseModel, Field


class Report(BaseModel):
    """Minimal output contract for shenbi-canon-import."""

    model_config = {"extra": "ignore"}
    kind: str = Field(default="artifact")
