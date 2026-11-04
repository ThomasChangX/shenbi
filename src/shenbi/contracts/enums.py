"""enums 域词表。全框架状态词表的唯一裁决依据是 docs/framework/status-vocab.md
(spec #34 T1/T901) — 新状态域必须先在登记表立域再落定义。
"""

from __future__ import annotations
from enum import StrEnum
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
class RevisionMode(StrEnum):
    """Revision mode domain — single source (spec #34 T910)."""

    SPOT_FIX = "spot-fix"
    REGENERATE = "regenerate"
    CONSTRAINED_REGENERATE = "constrained-regenerate"
    RECONSTRUCTION = "reconstruction"
    NO_REVISION = "no-revision"


# Legacy production value aliases (read-side normalization only, see registry)
REVISION_MODE_ALIASES: dict[str, str] = {"no_op": "no-revision"}
# spec #34 T9 行38/39 同键合一: revision-decisions 顶层 status
RevisionStatus = Literal[
    "preserved", "skipped", "delegated", "reconstructed_from_cross_source_evidence"
]
# spec #34 T909: genre-config approval 值域（与 pipeline ReviewDecision 命令域分立）
ApprovalDecision = Literal["approved", "rejected"]
# spec #34 T204: write-semantics mode 值域（G0.16 此前只查存在性不查合法性）
# spec #95 T6a: merge_prose 载体=场景级替换清单（`场景n: <全文>`；applier 见
# pipeline/prose_patch.py——确定性整体替换，未匹配场景键 fail-loud 拒收）
WriteMode = Literal["create_or_overwrite", "append_dedup", "merge_prose"]
# spec #34 T911: novel.json status（生产两文件持值，立域不删字段）
NovelStatus = Literal["worldbuilding", "worldbuilding_complete"]

# --- spec #95 T1: gate 词表 ⇄ prompt 单源（R1：SKILL 斜杠分组形教错模型） ---
# 值域只收单值；斜杠/多值在场由 gate 锚尾判定拒（G4.cp.invalid_chapter_role）。
CHAPTER_ROLE_VALUES: tuple[str, ...] = ("高潮", "兑现", "推进", "转折", "过渡", "铺垫")
GOLDEN_LINE_VALUES: tuple[str, ...] = ("燃", "静")

# 有枚举判定的检查 → (常量名, SKILL 仓库相对路径)；lint_gate_prompt_contract 从此
# 派生枚举检查清单，禁手列函数清单（r1.5：手列即计数腐化源）。
CHECK_ENUM_REGISTRY: dict[str, tuple[str, str, str]] = {
    # check_id -> (常量名, SKILL 仓库相对路径, 字段名)——lint 的正例检查按字段名派生
    "cp.chapter_role": (
        "CHAPTER_ROLE_VALUES",
        "skills/shenbi-chapter-planning/SKILL.md",
        "chapter_role",
    ),
}


# spec #47 C33 R1: dispatch 失败分类单源域（每层重试决策消费同一分类）。
class FailureClass(StrEnum):
    """Failure taxonomy domain — single source (spec #47 C33 R1).

    budget-exhausted is a routing OUTCOME (RetryExhaustedError → escalation),
    not a failure signature, so it is deliberately not a member. Unknown
    failures classify as TRANSIENT and remain guarded by the retry budget.
    """

    TRANSIENT = "transient"
    DETERMINISTIC_GATE = "deterministic_gate"
    DETERMINISTIC_CONTENT = "deterministic_content"


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
    "WriteMode": WriteMode,
    "FailureClass": FailureClass,
}

#: plan_format 版本集（spec #82 r7/F2——三处令牌比较消费常量（cp :247/:251/:259），
#: 另三处为正则形态（cp :124 / cd :920/:925——多行锚定语义，无令牌变量可判成员）；v4 ⊃ v3 ⊃ v2）。
#: v4 新增义务：章尾钩型七型词表行 + 章尾张力拍引句锚定形态（spec #82 T1/T4）。
PF_LEGAL: tuple[str, ...] = ("v1", "v2", "v3", "v4")
PF_GE_V2: frozenset[str] = frozenset({"v2", "v3", "v4"})
PF_GE_V3: frozenset[str] = frozenset({"v3", "v4"})
