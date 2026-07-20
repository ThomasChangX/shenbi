"""全框架单一词表（收严重性词汇分裂）。所有 Literal 必须从此处 import。"""

from __future__ import annotations
from typing import Any, Literal

Severity = Literal["BLOCKING", "CRITICAL", "MINOR"]
Verdict = Literal["通过", "有瑕疵", "不通过"]
CPZone = Literal["GREEN", "ORANGE", "RED"]
ActorRole = Literal["GENERATOR", "SCORER", "GATE", "SKILL", "HUMAN", "SYSTEM"]
# v2 C4: object 非 type——Literal 是 _LiteralGenericAlias 不是 type，mypy strict 拒 dict[str,type]
ALL_ENUMS: dict[str, Any] = {
    "Severity": Severity,
    "Verdict": Verdict,
    "CPZone": CPZone,
    "ActorRole": ActorRole,
}
