"""facts 域 pydantic schema（spec #80 T1）。

``FactsFile`` 按 ``dim`` 判 ``facts`` 值类型（model_validator 收口）——
props→PropFact、counters→CounterFact、identity→IdentityFact。事件 op
字段直接用枚举类型（``PropOp`` 等）——值集唯一信源在 enums.py。
"""

from __future__ import annotations

from typing import Any, cast

from pydantic import BaseModel, ConfigDict, Field, model_validator

from shenbi.facts.enums import CounterOp, FactsDim, IdentityOp, PropOp

FACTS_SCHEMA = "shenbi-facts-v1"


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class PropFact(StrictModel):
    entity: str
    owner: str
    events: list[str] = []


class CounterFact(StrictModel):
    name: str
    value: int
    history: list[str] = []


class IdentityFact(StrictModel):
    narration_name: str
    from_ch: int = 1
    aliases: list[str] = []


class PropTransferEvent(StrictModel):
    op: PropOp
    prop: str
    from_: str = Field(default="", alias="from")
    to: str = ""
    evidence: str = ""
    chapter: int = 0


class CounterEvent(StrictModel):
    name: str
    op: CounterOp
    delta: int
    chapter: int


class IdentityEvent(StrictModel):
    op: IdentityOp
    new_name: str | None = None
    alias: str | None = None
    from_ch: int = 0


_FACT_MODEL_BY_DIM: dict[str, type[PropFact | CounterFact | IdentityFact]] = {
    FactsDim.PROPS: PropFact,
    FactsDim.COUNTERS: CounterFact,
    FactsDim.IDENTITY: IdentityFact,
}


class FactsFile(StrictModel):
    schema_: str = Field(alias="$schema")
    dim: FactsDim
    facts: dict[str, PropFact | CounterFact | IdentityFact] = {}
    ops_log: list[dict[str, Any]] = []

    @model_validator(mode="before")
    @classmethod
    def _schema_literal(cls, data: Any) -> Any:
        if isinstance(data, dict):
            schema_val = data.get("$schema")
            if schema_val is not None and schema_val != FACTS_SCHEMA:
                raise ValueError(f"$schema must be {FACTS_SCHEMA!r}, got {schema_val!r}")
        return data

    @model_validator(mode="after")
    def _facts_match_dim(self) -> FactsFile:
        model = _FACT_MODEL_BY_DIM[self.dim]
        for key, value in self.facts.items():
            if not isinstance(value, model):
                raise ValueError(
                    f"dim={self.dim} but facts[{key!r}] is {type(value).__name__},"
                    f" expected {model.__name__}"
                )
        return self

    @property
    def is_empty(self) -> bool:
        """空种子语义（spec rev5 R4-M2）：键缺失 ≡ 维缺失 ⇒ 门检 WARN。"""
        return not self.facts

    def props(self) -> dict[str, PropFact]:
        """dim=props 专用类型化访问；其它 dim 调用即 ValueError。"""
        if self.dim is not FactsDim.PROPS:
            raise ValueError(f"props() on dim={self.dim}")
        return cast(dict[str, PropFact], self.facts)

    def counters(self) -> dict[str, CounterFact]:
        if self.dim is not FactsDim.COUNTERS:
            raise ValueError(f"counters() on dim={self.dim}")
        return cast(dict[str, CounterFact], self.facts)

    def identity(self) -> IdentityFact | None:
        """Identity 维单实体（主角）约定：取首个条目。"""
        if self.dim is not FactsDim.IDENTITY:
            raise ValueError(f"identity() on dim={self.dim}")
        for value in self.facts.values():
            return cast(IdentityFact, value)
        return None


__all__ = [
    "FACTS_SCHEMA",
    "CounterEvent",
    "CounterFact",
    "CounterOp",
    "FactsDim",
    "FactsFile",
    "IdentityEvent",
    "IdentityFact",
    "IdentityOp",
    "PropFact",
    "PropOp",
    "PropTransferEvent",
]
