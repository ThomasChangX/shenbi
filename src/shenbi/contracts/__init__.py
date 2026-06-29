"""契约单源层（spec 支柱一）。单一真理之源：技能输出 schema、算法不变量、
跨技能关系以 Pydantic 模型声明。门/helpers/文档从此派生。
"""

from __future__ import annotations

from shenbi.contracts.base import GateOutcome, PureInput
from shenbi.contracts.enums import (
    ALL_ENUMS,
    ActorRole,
    CPZone,
    Severity,
    Verdict,
)
from shenbi.contracts.registry import (
    REGISTRY,
    bootstrap_registry,
    load_skill_contract,
)

__all__ = [
    "ALL_ENUMS",
    "REGISTRY",
    "ActorRole",
    "CPZone",
    "GateOutcome",
    "PureInput",
    "Severity",
    "Verdict",
    "bootstrap_registry",
    "load_skill_contract",
]
