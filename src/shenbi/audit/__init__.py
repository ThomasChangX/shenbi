"""Tier B 写所有权审计包（spec 支柱四）。

C2 增量导出：本文件随各 task 落地逐步组装。Task 5 仅导 snapshot；Task 9 组装全量
（write_audit / record），避免 eager-import 尚未存在的模块。
"""

from shenbi.audit.snapshot import compute_file_change, parametric_globs, snapshot_tree

__all__ = ["compute_file_change", "parametric_globs", "snapshot_tree"]
