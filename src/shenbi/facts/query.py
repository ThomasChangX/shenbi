"""facts 查询面——现态紧凑投影（spec #80 §1.1 T3）。

planning 投影=token 有界紧凑文本（现态 owner/值，历史 events 不入）；
完备历史/``--as-of``=P2（审计/金丝雀消费方）。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from shenbi.facts.enums import FactsDim
from shenbi.facts.schemas import FactsFile
from shenbi.facts.store import load_facts


def current_state(file: FactsFile, dim: FactsDim, *, chapter: int | None = None) -> dict[str, Any]:
    """现态紧凑视图。

    props→``{entity: {owner}}``；counters→``{name: {value}}``；
    identity→平视图 ``{narration_name, from_ch, aliases}``（非嵌套——
    单实体约定）。
    ``chapter``：P1 相关性语义占位（全量返回；子集过滤=P2 实装，
    spec rev5 R4-M5 分期差注记）。
    """
    if dim is FactsDim.PROPS:
        return {k: {"owner": v.owner} for k, v in file.props().items()}
    if dim is FactsDim.COUNTERS:
        return {k: {"value": v.value} for k, v in file.counters().items()}
    fact = file.identity()
    if fact is None:
        return {}
    return {
        "narration_name": fact.narration_name,
        "from_ch": fact.from_ch,
        "aliases": list(fact.aliases),
    }


def planning_view(project_dir: Path, dim: FactsDim) -> str:
    """Planning 上下文装配消费的紧凑文本（facts 缺席返回空串，调用方 WARN）。"""
    file = load_facts(project_dir, dim)
    if file is None or file.is_empty:
        return ""
    view = current_state(file, dim)
    if dim is FactsDim.IDENTITY:
        lines = [
            f"叙事名: {view['narration_name']}（自 ch{view['from_ch']}）",
            f"别名（叙述段禁用）: {'、'.join(view['aliases']) or '无'}",
        ]
    else:
        lines = [f"{key}: {next(iter(val.values()))}" for key, val in view.items()]
    header = {
        "props": "物象现态（owner）",
        "counters": "计数器现态（值）",
        "identity": "身份现态（叙事名/别名）",
    }[dim.value]
    return header + "\n" + "\n".join(lines)
