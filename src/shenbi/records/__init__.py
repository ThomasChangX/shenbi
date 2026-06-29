"""记录级解析（spec 支柱四 Tier B 判据 12）。pending_hooks.md 的 ## hooks YAML block
为权威记录源；本包解析、序列化、检测 cross-section drift。纯函数，无 trace 依赖。
"""

from shenbi.records.parser import (
    extract_yaml_block,
    is_idempotent,
    parse_records,
    serialize_records,
)

__all__ = ["extract_yaml_block", "is_idempotent", "parse_records", "serialize_records"]
