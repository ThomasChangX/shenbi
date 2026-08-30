"""全框架单一词表（收严重性词汇分裂）。所有 Literal 必须从此处 import。"""

from __future__ import annotations
from typing import Any, Literal

Severity = Literal["BLOCKING", "CRITICAL", "MINOR"]
Verdict = Literal["通过", "有瑕疵", "不通过"]
CPZone = Literal["GREEN", "ORANGE", "RED"]
ActorRole = Literal["GENERATOR", "SCORER", "GATE", "SKILL", "HUMAN", "SYSTEM"]
# spec #27 F353: trigger failure stage vocab (pipeline/triggers last_trigger_failure)
TriggerFailureStage = Literal["dispatch", "g4", "g3", "governance"]
# spec #31 T3 (F113): scoring provenance — who produced the score.
ScoredBy = Literal["file", "interactive", "subagent"]
# v2 C4: object 非 type——Literal 是 _LiteralGenericAlias 不是 type，mypy strict 拒 dict[str,type]
ALL_ENUMS: dict[str, Any] = {
    "Severity": Severity,
    "Verdict": Verdict,
    "CPZone": CPZone,
    "ActorRole": ActorRole,
    "TriggerFailureStage": TriggerFailureStage,
    "ScoredBy": ScoredBy,
}
