# 伏笔生命周期参考

## 五种状态（Phase 2 审计简化模型）

> Phase 2 审计用简化模型。Phase 3 的完整状态机（含 ABANDONED、EXPIRED、DEFER 操作）见 `skills/shenbi-foreshadowing-track/lifecycle-states.md`。

| 状态 | 含义 | 可执行操作 |
|------|------|----------|
| PLANTED | 已种植，读者尚未注意到 | REINFORCE, PROMOTE |
| RELEVANT | 已被提醒，读者开始注意 | TRIGGER |
| TRIGGERED | 已触发，准备兑现 | RESOLVE |
| RESOLVED | 已兑现 | ARCHIVE |
| ABANDONED | 已放弃 | — (不可恢复) |

> 注意：DEFER 操作不在 Phase 2 审计模型中。审计只检查伏笔是否按约定推进，不负责修改伏笔生命周期。DEFER 由 Phase 3 的 `foreshadowing-track` 执行。

## 培育规则

- `cultivation_interval`: 每 N 章需要一次强化
- `max_distance`: 最大种植到兑现距离（章）
- `last_reinforced`: 上次强化所在章
- 超过 `max_distance` 未兑现 → 警告

## 密度预算

- 每章最多 8 次伏笔操作（plant + reinforce + trigger + resolve）
- 超过 → 密度异常警告

> 这是 Phase 2 用于审计的简化版本。完整状态机（含 ABANDONED、ARCHIVED、DEFER）见 Phase 3 的 `skills/shenbi-foreshadowing-track/lifecycle-states.md`。
