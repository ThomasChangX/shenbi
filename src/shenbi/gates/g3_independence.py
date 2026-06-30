"""G3.4 评分独立性纯函数（spec 支柱五；判据 6）。

gate_G3（g3.py:144-162）现状 fail-open：progress.json 存在但缺
current_scorer_agent 时返回 PASS（空转 bug）。本模块承载**正确**的 fail-closed
逻辑，供属性测试钉死；已接线进 gate_G3（g3.py G3.4 调用 scoring_independence_status）。

规则（AGENTS.md：评分必须用独立 subagent；dispatcher 自评无效）：
  - 无 current_scorer_agent 证据 → FAIL（fail-closed）
  - 生成 agent == 评分 agent（同源）→ FAIL
  - 否则 → PASS
"""

from __future__ import annotations

from typing import Any


def scoring_independence_status(progress: dict[str, Any], skill_name: str) -> tuple[str, str]:
    """返回 ("PASS","") 或 ("FAIL", reason)。fail-closed：缺评分证据即 FAIL。"""
    scorer = progress.get("current_scorer_agent")
    if not scorer:
        return "FAIL", "no independent scorer recorded (fail-closed)"
    agent_trace = progress.get("agent_trace")
    if isinstance(agent_trace, dict):
        gen = agent_trace.get(skill_name)
        if gen is not None and str(gen) == str(scorer):
            return "FAIL", "scorer agent same as generator"
    return "PASS", ""
