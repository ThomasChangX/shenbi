"""契约层不可变基类型。PureInput 只含已读入内存数据，无 Path 写能力。
GateOutcome 是纯数据，门返回它而非修改文件系统。

v2: 命名为 GateOutcome 而非 GateResult，避与 shenbi.status.GateResult(TypedDict) 碰撞。
后续支柱二门改造时统一迁移 status.GateResult -> GateOutcome。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal


@dataclass(frozen=True)
class PureInput:
    """门的输入：已读入内存的技能输出。无 Path 写能力。"""

    skill: str
    round_dir: Path
    raw_outputs: dict[str, str]


@dataclass(frozen=True)
class GateOutcome:
    """门的输出：纯数据。passed/fail 是工厂方法。"""

    skill: str
    status: Literal["PASS", "FAIL", "SKIP", "WARN"]
    issues: tuple[str, ...] = ()
    checks: tuple[dict[str, object], ...] = ()

    @classmethod
    def passed(cls, skill: str) -> GateOutcome:
        return cls(skill=skill, status="PASS")

    @classmethod
    def fail(cls, skill: str, issues: list[str]) -> GateOutcome:
        return cls(skill=skill, status="FAIL", issues=tuple(issues))
