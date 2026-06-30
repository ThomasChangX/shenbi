"""Context-composing contract with semantic validators (spec workflow A).

Rules from SKILL.md auto-check:
1. 9 section headers required
2. Hook debt briefing entries must have file paths
3. Near-chapter endings: <= 2 consecutive same type
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, model_validator


class ContextComposing(BaseModel):
    model_config = {"extra": "ignore"}

    section_count: int = Field(default=0)
    hook_debt_entries: list[dict[str, Any]] = Field(default_factory=list)
    chapter_endings: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _nine_sections(self) -> ContextComposing:
        if self.section_count != 9:
            raise ValueError(f"section count {self.section_count} != 9")
        return self

    @model_validator(mode="after")
    def _hook_debt_has_paths(self) -> ContextComposing:
        for entry in self.hook_debt_entries:
            if not entry.get("source_file"):
                raise ValueError(f"hook debt entry missing source_file: {entry.get('id', '?')}")
        return self

    @model_validator(mode="after")
    def _no_3_consecutive_endings(self) -> ContextComposing:
        if len(self.chapter_endings) >= 3:
            for i in range(len(self.chapter_endings) - 2):
                w = self.chapter_endings[i : i + 3]
                if len(set(w)) == 1:
                    raise ValueError(f"3 consecutive same-type endings: '{w[0]}' at position {i}")
        return self


Report = ContextComposing
