"""cross-section drift 检测（判据 12）。pending_hooks.md 的 ## 活跃伏笔 markdown 表是
YAML 记录的派生视图。spec New-F「检测」模型：YAML 权威；派生表必须与 YAML 一致；
不一致即 drift（YAML 在冲突时胜出 → 报告 drift → ship 失败 → 人工修）。
"""

from __future__ import annotations

import re
from typing import Any

import structlog

log = structlog.get_logger(__name__)

# markdown 表头列 → YAML 记录键（亲手核对 fixture L14 表头顺序）
_MD_HEADER_TO_KEY: dict[str, str] = {
    "Hook ID": "id",
    "类型": "type",
    "维度": "dimension",
    "微妙度": "subtlety",
    "升级曲线": "escalation_curve",
    "种植章": "plant_chapter",
    "操作": "operation",
    "状态": "state",
}

_ACTIVE_HEADER_RE = re.compile(r"^## 活跃伏笔\s*$", re.MULTILINE)

# Public alias: records/writer.py derives the canonical table column set from
# this map (R5/F637) — private-name access across modules is a lint error.
MD_HEADER_TO_KEY: dict[str, str] = _MD_HEADER_TO_KEY


def parse_markdown_table(
    text: str, stats: dict[str, int] | None = None
) -> dict[str, dict[str, str]]:
    """解析 ## 活跃伏笔 markdown 表 → {id: {key: str_value}}。无表/空表 → {}。

    F649 (spec #32) 畸形行披露：
    - 短行（cell 少于 header）：缺失的 cell 补空串 —— 下游 ``_values_equal``
      会看到显式 "" 并报出真实 drift（旧行为静默保留部分行，缺键不比较）。
    - 溢出行（cell 多于 header）：溢出 cell 丢弃并计入
      ``stats["discarded_cells"]``（可选 out-param；旧行为静默丢弃）。
    """
    if stats is not None:
        stats["discarded_cells"] = 0
    m = _ACTIVE_HEADER_RE.search(text)
    if m is None:
        return {}
    lines = text[m.end() + 1 :].splitlines()
    header: list[str] | None = None
    out: dict[str, dict[str, str]] = {}
    for ln in lines:
        s = ln.strip()
        if not s:
            continue
        if not s.startswith("|"):
            break  # 表结束
        cells = [c.strip() for c in s.strip("|").split("|")]
        if header is None:
            header = cells
            continue
        if all(set(c) <= set("-: ") for c in cells):  # 分隔行 |---|---|
            continue
        assert header is not None
        if len(cells) < len(header):
            # 短行：补齐空 cell，保证行的键集合与 header 一致（可比较）。
            cells += [""] * (len(header) - len(cells))
        elif len(cells) > len(header):
            # 溢出行：丢弃溢出 cell 并披露计数（不再静默丢弃）。
            overflow = len(cells) - len(header)
            cells = cells[: len(header)]
            if stats is not None:
                stats["discarded_cells"] += overflow
            log.warning("markdown_table_overflow_cells_discarded", count=overflow, row=s)
        row: dict[str, str] = {}
        for i, val in enumerate(cells):
            if i < len(header):
                key = _MD_HEADER_TO_KEY.get(header[i], header[i])
                row[key] = val
        rid = row.get("id")
        if rid and rid in out:
            # duplicate id: first row wins (F658); F607 (spec #39 T9) discloses.
            log.warning("duplicate_id_first_wins", id=rid)
        if rid and rid not in out:
            out[rid] = row
    return out


def _values_equal(yaml_val: Any, md_val: str) -> bool:
    """Numeric-aware comparison.

    YAML parses 0.80 -> float 0.8; markdown keeps literal "0.80".
    str(0.8)="0.8" != "0.80" -> false drift on real fixture.
    Try float() both sides first; fall back to str() comparison.
    """
    if str(yaml_val) == md_val:
        return True
    try:
        return float(yaml_val) == float(md_val)
    except (TypeError, ValueError):
        return False


def detect_cross_section_drift(
    yaml_records: list[dict[str, Any]], md_rows: dict[str, dict[str, str]]
) -> list[str]:
    """Return drift descriptions (empty=consistent). YAML authoritative.

    Numeric-aware comparison via _values_equal: YAML parses 0.80 -> 0.8 (float);
    markdown keeps literal "0.80". Compare floats when both parse.
    """
    by_id: dict[str, dict[str, Any]] = {str(r.get("id")): r for r in yaml_records}
    issues: list[str] = []
    for rid, row in md_rows.items():
        if rid not in by_id:
            issues.append(f"drift: markdown table id={rid} not in YAML")
            continue
        rec = by_id[rid]
        for key, md_val in row.items():
            if key == "id":
                continue
            yaml_val = rec.get(key)
            if not _values_equal(yaml_val, md_val):
                issues.append(f"drift: id={rid} key={key} md={md_val!r} != YAML={yaml_val!r}")
    # F606 (spec #39 T9): reverse direction — YAML-only ids were never
    # reported (single-direction scan blind spot).
    for rid in by_id:
        if rid not in md_rows:
            issues.append(f"drift: YAML id={rid} not in markdown table")
    return issues
