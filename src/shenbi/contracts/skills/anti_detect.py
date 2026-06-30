"""Auto-generated minimal contract model for shenbi-anti-detect."""

from __future__ import annotations

from pydantic import BaseModel, Field


class Report(BaseModel):
    """Minimal output contract for shenbi-anti-detect."""

    model_config = {"extra": "ignore"}
    kind: str = Field(default="artifact")
