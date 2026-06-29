"""foreshadowing_resolve 契约模型。spec 展示案例：根治 CP 算术三 bug。

zone/must_resolve 是 computed_field 只读派生；debt 一致性 + hook 单 cp 是
model_validator 运行时校验。字段以 fixture 为准（state 非 status）。

v2 M1: must_resolve_next_chapter 用 computed_field（非 @property）以进 model_dump。
"""

from __future__ import annotations

from pydantic import BaseModel, Field, computed_field, model_validator

from shenbi.contracts.enums import CPZone

# 单一阈值真理（spec：铁律、zone 表、示例数值全部从此读）
CP_THRESHOLDS: dict[str, int] = {
    "GREEN_MAX": 50,
    "RED_NOW": 100,
    "FORCE_NEXT_CHAPTER": 200,
}


class HookCP(BaseModel):
    """单 hook 紧迫度记录。zone/must_resolve 只读派生。"""

    model_config = {"extra": "ignore"}  # N7: computed_field round-trip 前提

    hook_id: str
    cp: int = Field(ge=0)
    last_reinforced: int = Field(ge=1)
    current_chapter: int = Field(ge=1)

    @computed_field
    @property
    def zone(self) -> CPZone:
        if self.cp >= CP_THRESHOLDS["RED_NOW"]:
            return "RED"
        if self.cp >= CP_THRESHOLDS["GREEN_MAX"]:
            return "ORANGE"
        return "GREEN"

    @computed_field  # v2 M1: computed_field 非 property，进 model_dump
    @property
    def must_resolve_next_chapter(self) -> bool:
        return self.cp > CP_THRESHOLDS["FORCE_NEXT_CHAPTER"]


class Report(BaseModel):
    """foreshadowing_resolve 完整输出契约。门做 model_validate()。"""

    model_config = {"extra": "ignore"}

    current_chapter: int = Field(ge=1)
    hooks: list[HookCP]
    debt_level: CPZone

    @model_validator(mode="after")
    def _debt_consistent_with_hooks(self) -> Report:
        max_cp = max((h.cp for h in self.hooks), default=0)
        expected: CPZone = (
            "RED"
            if max_cp >= CP_THRESHOLDS["RED_NOW"]
            else "ORANGE"
            if max_cp >= CP_THRESHOLDS["GREEN_MAX"]
            else "GREEN"
        )
        if self.debt_level != expected:
            raise ValueError(
                f"debt_level={self.debt_level} 与 hooks 最大 cp={max_cp} "
                f"推导的 zone={expected} 矛盾"
            )
        return self

    @model_validator(mode="after")
    def _hook_cp_single_value(self) -> Report:
        seen: dict[str, int] = {}
        for h in self.hooks:
            if h.hook_id in seen and seen[h.hook_id] != h.cp:
                raise ValueError(
                    f"hook {h.hook_id} 在同一报告内有多个 cp: {seen[h.hook_id]} vs {h.cp}"
                )
            seen[h.hook_id] = h.cp
        return self
