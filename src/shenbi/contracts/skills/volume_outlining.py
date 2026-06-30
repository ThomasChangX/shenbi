"""Volume-outlining contract with semantic validators (spec workflow A).

Rules from SKILL.md auto-check:
1. KR count must be 3-5
2. Tension curve 4-segment percentages sum = 100
3. At least 3 entity hooks with >= 2 types
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, model_validator


class VolumeOutlining(BaseModel):
    model_config = {"extra": "ignore"}

    key_results: list[dict[str, Any]] = Field(default_factory=list)
    tension_curve: dict[str, float] = Field(default_factory=dict)
    entity_hooks: list[str] = Field(default_factory=list)
    entity_hook_types: set[str] = Field(default_factory=set)

    @model_validator(mode="after")
    def _kr_count(self) -> VolumeOutlining:
        n = len(self.key_results)
        if not 3 <= n <= 5:
            raise ValueError(f"KR count {n} not in [3, 5]")
        return self

    @model_validator(mode="after")
    def _tension_sum(self) -> VolumeOutlining:
        if self.tension_curve:
            total = sum(self.tension_curve.values())
            if abs(total - 100.0) > 0.01:
                raise ValueError(f"tension curve sum {total} != 100")
        return self

    @model_validator(mode="after")
    def _entity_hooks(self) -> VolumeOutlining:
        if len(self.entity_hooks) < 3:
            raise ValueError(f"entity hooks {len(self.entity_hooks)} < 3")
        if len(self.entity_hook_types) < 2:
            raise ValueError(f"entity hook types {len(self.entity_hook_types)} < 2")
        return self


Report = VolumeOutlining
