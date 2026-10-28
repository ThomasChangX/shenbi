"""facts 域——规范事实库（spec #80）。

词表唯一信源 = ``shenbi.facts.enums``（StrEnum）；status-vocab.md 注册行、
docs/framework/invariants.md 普查表只引用不定义。
op 应用是有状态写侧（本模块 store.py）；门检（gates/g4/*）是纯读者。
"""
