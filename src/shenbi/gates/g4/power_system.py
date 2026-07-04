"""G4 checker for shenbi-power-system."""

from __future__ import annotations
from typing import Any
import re

from shenbi.gates.shared import (
    fail,
    passed,
    resolve_g4_base,
)


def g4_power_system(fps: list[str], rd: str | None = None) -> str:
    """Power system: level table (>=5 rows), advancement rules, ability boundaries,
    cost mechanism, power ceiling, cross-level combat reference.
    """
    c: list[dict[str, Any]] = []
    mf = []
    pd = resolve_g4_base(rd)

    ps = pd / "world" / "power_system.md"
    if not ps.exists():
        mf.append("G4.ps.not_found")
    else:
        content = ps.read_text(encoding="utf-8")
        # 等级表: table with >= 5 rows
        table_rows = len(re.findall(r"^\s*\|.+\|\s*$", content, re.MULTILINE))
        if table_rows < 5:
            mf.append(f"G4.ps.level_table_rows:{table_rows}<5")
        else:
            c.append({"id": "G4.ps.level_table", "s": "PASS", "rows": table_rows})

        # 进阶规则
        if not re.search(r"进阶规则|## 进阶|进阶级", content):
            mf.append("G4.ps.advancement_rules")
        else:
            c.append({"id": "G4.ps.advancement", "s": "PASS"})

        # 能力边界
        if not re.search(r"能力边界|能做|不能做", content):
            mf.append("G4.ps.ability_boundaries")
        else:
            c.append({"id": "G4.ps.boundaries", "s": "PASS"})

        # 代价机制
        if not re.search(r"代价机制|## 代价|代价类型", content):
            mf.append("G4.ps.cost")
        else:
            c.append({"id": "G4.ps.cost", "s": "PASS"})

        # 力量天花板
        if not re.search(r"力量上限|力量天花板|顶端|最高境界", content):
            mf.append("G4.ps.ceiling")
        else:
            c.append({"id": "G4.ps.ceiling", "s": "PASS"})

        # 跨级战斗参考
        if not re.search(r"跨级战斗|越级", content):
            mf.append("G4.ps.cross_level")
        else:
            c.append({"id": "G4.ps.cross_level", "s": "PASS"})

    if mf:
        return fail("G4-power-system", c, "scoring", mf)
    return passed("G4-power-system", c)
