"""评分报告共享契约模型（spec M3 修复：评分标尺显式声明）。

聚合公式（Route C 硬二元门控 + 软分加权）：
  final_score = ROUTE_C_SOFT_WEIGHT * route_c_soft_score
                     + ROUTE_A_WEIGHT * route_a_score

阈值来源：AGENTS.md（>=90 单项通过，>=94 层进）。此前散落在散文/AGENTS.md，
现固化于此模型为单一真理之源。

三个评分 skill（arc/stratum/volume）共用本模型；各自 score_*.py 导出
Report = ScoreReport 供 REGISTRY 自动发现。本文件以 _ 前缀跳过发现。
"""

from __future__ import annotations

from pydantic import BaseModel, Field, computed_field, model_validator

# --- 显式阈值（M3 修复 + Kant I3：从 thresholds.py 单一源 import） ---

from shenbi.contracts.thresholds import T1_PASS as TIER_ADVANCE_THRESHOLD
from shenbi.contracts.thresholds import TEST_PASS as PASS_THRESHOLD

# --- 聚合权重 ---

ROUTE_C_SOFT_WEIGHT: float = 0.6
ROUTE_A_WEIGHT: float = 0.4

# --- 文档派生用公式描述 ---

AGGREGATION_FORMULA: str = (
    "# final_score = ROUTE_C_SOFT_WEIGHT * route_c_soft_score "
    "+ ROUTE_A_WEIGHT * route_a_score\n"
    "# passed requires final_score >= PASS_THRESHOLD AND hard_binary all pass"
)


class ScoreReport(BaseModel):
    """评分报告共享模型。Route C 硬二元门控 + Route A/C 软分加权聚合。"""

    model_config = {"extra": "ignore"}  # N7

    route_c_hard_binary_pass: int = Field(ge=0)
    route_c_hard_binary_total: int = Field(ge=1)
    route_c_soft_score: float = Field(ge=0, le=100)
    route_a_score: float = Field(ge=0, le=100)

    @model_validator(mode="after")
    def _hard_binary_pass_le_total(self) -> ScoreReport:
        if self.route_c_hard_binary_pass > self.route_c_hard_binary_total:
            raise ValueError(
                f"route_c_hard_binary_pass ({self.route_c_hard_binary_pass}) "
                f"> route_c_hard_binary_total ({self.route_c_hard_binary_total})"
            )
        return self

    @computed_field
    @property
    def hard_binary_gate_failed(self) -> bool:
        """True if any hard-binary check failed. Audit flag only."""
        return self.route_c_hard_binary_pass < self.route_c_hard_binary_total

    @computed_field
    @property
    def final_score(self) -> float:
        # Weighted average; hard_binary failure does NOT zero the score
        # (skill: 该检查项 0 分, not 全卷归零). Parfit round-1 fix.
        return ROUTE_C_SOFT_WEIGHT * self.route_c_soft_score + ROUTE_A_WEIGHT * self.route_a_score

    @computed_field
    @property
    def passed(self) -> bool:
        # Gate semantics (Poincare round-2): hard_binary failure blocks pass
        # even if weighted final_score >= 90. Matches scoring.py kill-switch.
        return self.final_score >= PASS_THRESHOLD and not self.hard_binary_gate_failed

    @computed_field
    @property
    def tier_advance_eligible(self) -> bool:
        # Same kill-switch as passed (Bernoulli round-3): hard_binary failure
        # blocks tier advancement even if final_score >= 94.
        return self.final_score >= TIER_ADVANCE_THRESHOLD and not self.hard_binary_gate_failed
