"""Hand-maintained minimal contract model for shenbi-worldbuilding (provenance claim corrected: no generator exists; spec60 T206)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class Report(BaseModel):
    """Minimal output contract for shenbi-worldbuilding."""

    model_config = {"extra": "ignore"}
    kind: str = Field(default="artifact")
