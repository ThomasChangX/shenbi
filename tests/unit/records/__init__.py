"""记录级解析测试包（判据 12）。
**v2 修订（round-1 审核 7→目标 9+，Singer reproduced）：** C1 cross-section drift 加 numeric-aware 比较（`_values_equal` try float() fallback，修 YAML `0.80`→0.8 vs md `0.80` 假阳性）；C2 `audit/__init__` 增量导出（Task 5 只导 snapshot，Task 9 组装全量，避免 import 未建模块 ImportError）。
"""
