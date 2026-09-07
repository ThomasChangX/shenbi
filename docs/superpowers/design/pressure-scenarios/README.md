# 压力场景设计材料（2026-08-15 审计期）

这 6 份 markdown 是审计期间设计的压力场景 prompt（state-drift / chapter-writing /
snapshot-skip / import-shortcut / foreshadowing-fatigue / audit-skipping），
**不是可执行的测试 harness**——它们没有 runner，也不在 pytest 收集范围内。

按 spec #55（C17 / T1101）的「激活或下线」裁决：接 harness 需要真实 LLM
dispatch（被 SDD 成本纪律禁止），故从 `tests/pressure-tests/` 移入本目录，
降级为设计材料。历史迁移映射见 `tests/ARCHIVE-MIGRATED.md`。
