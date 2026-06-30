"""Chapter-planning contract with semantic validators (spec workflow A).

Rules from SKILL.md auto-check:
1. Chapter > 3: at least 1 change typed from {info, relation, physical, power}
2. Hook operations only: open / advance / resolve / defer
3. If defer with silent chapters >= 4, must have activation plan
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, model_validator

_VALID_OPS = {"open", "advance", "resolve", "defer"}
_VALID_CHANGE_TYPES = {"信息", "关系", "物理", "权力"}


class ChapterPlanning(BaseModel):
    model_config = {"extra": "ignore"}

    chapter_number: int = Field(ge=1)
    changes: list[dict[str, Any]] = Field(default_factory=list)
    hooks: list[dict[str, Any]] = Field(default_factory=list)

    @model_validator(mode="after")
    def _typed_change_when_ch3(self) -> ChapterPlanning:
        if self.chapter_number > 3:
            typed = [
                c
                for c in self.changes
                if c.get("type", "") in _VALID_CHANGE_TYPES and c.get("detail")
            ]
            if not typed:
                raise ValueError(f"chapter {self.chapter_number} > 3 but no typed change")
        return self

    @model_validator(mode="after")
    def _hook_ops_valid(self) -> ChapterPlanning:
        for h in self.hooks:
            op = h.get("operation", "")
            if op and op not in _VALID_OPS:
                raise ValueError(f"hook operation '{op}' not in {_VALID_OPS}")
        return self

    @model_validator(mode="after")
    def _defer_silence_warning(self) -> ChapterPlanning:
        for h in self.hooks:
            if h.get("operation") == "defer":
                silent = h.get("silent_chapters", 0)
                if isinstance(silent, (int, float)) and silent >= 4:
                    if not h.get("activation_plan") and not h.get("abandon"):
                        raise ValueError(
                            f"hook deferred with {silent} silent chapters "
                            f"but no activation plan or ABANDON"
                        )
        return self


Report = ChapterPlanning
