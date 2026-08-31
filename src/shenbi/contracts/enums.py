"""enums 域词表。全框架状态词表的唯一裁决依据是 docs/framework/status-vocab.md
(spec #34 T1/T901) — 新状态域必须先在登记表立域再落定义。
"""

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
# spec #34 T902: resonance 判定词表（原 g4/review_resonance._VERDICTS 裸 tuple 收编）
ResonanceVerdict = Literal["通过", "阻断", "待人机复核"]
# spec #34 T903: revision-decisions severity 生产域（容错映射见 status-vocab.md）
RevisionSeverity = Literal["low", "medium", "high"]
# spec #34 T910: 修订 mode 单一域（route.py/revision_router.py 双域合一；旧值 no_op 读侧归一 no-revision）
RevisionMode = Literal[
    "spot-fix", "regenerate", "constrained-regenerate", "reconstruction", "no-revision"
]
# spec #34 T9 行38/39 同键合一: revision-decisions 顶层 status
RevisionStatus = Literal[
    "preserved", "skipped", "delegated", "reconstructed_from_cross_source_evidence"
]
# spec #34 T909: genre-config approval 值域（与 pipeline ReviewDecision 命令域分立）
ApprovalDecision = Literal["approved", "rejected"]
# spec #34 T911: novel.json status（生产两文件持值，立域不删字段）
NovelStatus = Literal["worldbuilding", "worldbuilding_complete"]
# v2 C4: object 非 type——Literal 是 _LiteralGenericAlias 不是 type，mypy strict 拒 dict[str,type]
ALL_ENUMS: dict[str, Any] = {
    "Severity": Severity,
    "Verdict": Verdict,
    "CPZone": CPZone,
    "ActorRole": ActorRole,
    "TriggerFailureStage": TriggerFailureStage,
    "ScoredBy": ScoredBy,
    "ResonanceVerdict": ResonanceVerdict,
    "RevisionSeverity": RevisionSeverity,
    "RevisionMode": RevisionMode,
    "RevisionStatus": RevisionStatus,
    "ApprovalDecision": ApprovalDecision,
    "NovelStatus": NovelStatus,
}
