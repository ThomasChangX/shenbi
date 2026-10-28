"""facts 域词表（spec #80 T1）。

值集唯一定义处（status-vocab.md 域清单注册行须与本文件集合相等，
tools/lint_status_strings.py 对账）。
"""

from __future__ import annotations

from enum import StrEnum


class FactsDim(StrEnum):
    """facts 维度文件名（truth/facts/<value>.json）。"""

    PROPS = "props"
    COUNTERS = "counters"
    IDENTITY = "identity"


class PropOp(StrEnum):
    """物象经手 op（spec #80 §4 F16：持有/传递/获得/遗失）。"""

    HOLD = "hold"
    TRANSFER = "transfer"
    ACQUIRE = "acquire"
    LOSE = "lose"


class CounterOp(StrEnum):
    """计数器 op（单调律：increment 仅正向；set 仅种子期 chapter=0）。"""

    INCREMENT = "increment"
    SET = "set"


class IdentityOp(StrEnum):
    """身份 op（narration_name 改名携带 from_ch 生效章界）。"""

    RENAME = "rename"
    SET_ALIAS = "set_alias"
