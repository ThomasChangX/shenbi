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
from shenbi.contracts.ownership import (
    OWNERSHIP,
    FileChange,
    FileOwnership,
    check_write_ownership,
    get_ownership,
)

__all__ = [
    "ALL_ENUMS",
    "OWNERSHIP",
    "REGISTRY",
    "ActorRole",
    "CPZone",
    "FileChange",
    "FileOwnership",
    "GateOutcome",
    "PureInput",
    "Severity",
    "Verdict",
    "bootstrap_registry",
    "check_write_ownership",
    "get_ownership",
    "load_skill_contract",
]


# Legacy contract.py re-exports (criterion 3: contracts/ is the unified import surface).
# New code should import from shenbi.contracts, not shenbi.contract.
from shenbi.contract import (
    ContractError as ContractError,
    Contract as Contract,
    OutputKind as OutputKind,
    load_contract as load_contract,
    load_registry as load_registry,
    requires_independent_agent as requires_independent_agent,
)
