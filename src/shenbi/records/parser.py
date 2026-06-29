"""pending_hooks.md record parser（判据 12）。

真实 fixture（tests/fixtures/truth-pending_hooks.md）同时含 ## 活跃伏笔 markdown 表
与 ## hooks YAML block，按 id 对应。本 parser 采用 spec New-F「检测」模型：
  - YAML block 为权威记录源；
  - 解析时只截 ## hooks 到下一个 ## 标题之间（naive 整段 yaml.safe_load 会把其后
    ## 伏笔统计 的 markdown 表行 | 维度 | 数量 | 误当 YAML 块标量而 ScannerError 崩溃）；
  - serialize 用排序键 YAML；语义 round-trip = parse(serialize(parse(x)))==parse(x)。
"""

from __future__ import annotations

import re
from typing import Any

import yaml

_HOOKS_HEADER_RE = re.compile(r"^## hooks\s*$", re.MULTILINE)
_NEXT_HEADER_RE = re.compile(r"^## ", re.MULTILINE)


def extract_yaml_block(text: str) -> str:
    """截取 ## hooks 标题到下一个 ## 标题（或文末）之间的 YAML 正文。

    必须停在下一个 ## 标题，否则后续 markdown 表的 | ... | 被 YAML 当块标量。无段返回 ""。
    """
    m = _HOOKS_HEADER_RE.search(text)
    if m is None:
        return ""
    start = m.end() + 1  # 跳过该行换行
    rest = text[start:]
    nxt = _NEXT_HEADER_RE.search(rest)
    body = rest[: nxt.start()] if nxt else rest
    return body.strip()


def _parse_body(body: str) -> list[dict[str, Any]]:
    if not body:
        return []
    data = yaml.safe_load(body)
    if data is None:
        return []
    if not isinstance(data, list):
        raise ValueError(f"## hooks block 必须解析为列表；实际 {type(data).__name__}")
    return [r for r in data if isinstance(r, dict)]


def parse_records(text: str) -> list[dict[str, Any]]:
    """解析 markdown 全文的 ## hooks YAML block → 记录列表（按出现顺序）。空块 → []。"""
    return _parse_body(extract_yaml_block(text))


def serialize_records(records: list[dict[str, Any]]) -> str:
    """序列化记录为规范 YAML（排序键、unicode）。语义 round-trip 的写侧。"""
    return yaml.safe_dump(
        records, sort_keys=True, allow_unicode=True, default_flow_style=False
    ).strip()


def is_idempotent(text: str) -> bool:
    """判据 12 语义 round-trip：parse(serialize(parse(x))) == parse(x)。"""
    once = parse_records(text)
    twice = _parse_body(serialize_records(once))
    return once == twice
