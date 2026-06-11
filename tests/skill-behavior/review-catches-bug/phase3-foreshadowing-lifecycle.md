# 行为测试：伏笔生命周期 — 过期伏笔检测

测试目标：验证 `shenbi-foreshadowing-track` 能检测出超过 `max_distance` 的过期伏笔，并正确推进生命周期状态。

## 测试场景

`truth/pending_hooks.md` 中有一条伏笔已超过 max_distance 但状态仍为 RELEVANT，从未被强化。

## 准备

`truth/pending_hooks.md`:
```yaml
- id: hook-003
  content: "师姐脖子上的玉佩暗藏古族血脉"
  state: RELEVANT
  planted_chapter: 5
  last_reinforced: 8
  max_distance: 15
  cultivation_interval: 5
  subtlety: low
  core_hook: true
```

当前章节: 25

## 期望检测

| 检查项 | Hook | 计算 | 阈值 | 状态 |
|--------|------|------|------|------|
| 培育间隔 | hook-003 | 25 - 8 = 17 章 | cultivation_interval = 5 | OVERDUE |
| 距离上限 | hook-003 | 25 - 5 = 20 章 | max_distance = 15 | EXPIRED |
| 核心伏笔 | hook-003 | 过期 5 章 | core_hook=true, 过期>10章升级critical | WARNING (还未超10章) |

## 通过条件

- [ ] 检测出 hook-003 培育间隔超期（17 > 5）
- [ ] 检测出 hook-003 距离超期（20 > 15），标记为 EXPIRED
- [ ] 标记为 `error` 级别（铁律: 过期伏笔必须标记 error）
- [ ] 建议具体推进方案（在 25-27 章内 advance 或 resolve）

## 失败条件

- 未检测出过期 → FAIL
- 标记为 `warning` 而非 `error` → FAIL（铁律: 过期伏笔 = error）
- 计算距离错误（应从 planted_chapter 5 算起，不是 last_reinforced） → FAIL
