# 触发测试：连续性审计

测试目标：验证 `using-shenbi` 在收到自然语言请求时，能否正确路由到 `shenbi-review-continuity`（连续性审计技能）。

## 用户输入

```
我刚写完第6章。能不能帮我检查一下这章有没有时间线上的问题？比如角色出现的时间点、事件发生的顺序这些。
```

## 期望的 Agent 行为

正确的 agent 必须：

1. 加载 `skills/using-shenbi/SKILL.md` 并执行其 skill-check 流程
2. 识别关键词："检查"、"时间线"、"事件顺序" → 对应连续性审计
3. 路由到 `skills/shenbi-review-continuity/SKILL.md`
4. 按连续性审计的流程执行：读章节内容 → 读 `truth/current_state.md` → 读 `truth/chapter_summaries.md` (last 3) → 输出审计报告

## 期望触发的技能

- **Primary:** `shenbi-review-continuity`（连续性审计）
- **可能附带:** `shenbi-review-character`（如果时间线问题牵涉角色一致性）

## 通过条件

- [ ] Agent 主动加载 `using-shenbi` SKILL.md
- [ ] 路由到 `shenbi-review-continuity`（不是直接回答"没问题"或自行猜测问题）
- [ ] 报告使用连续性审计的输出格式（时间线 / 地点 / 事件时序 / 物理空间 / 评分 / 修复建议）

## 失败条件

- Agent 直接说"看起来没问题" → FAIL
- Agent 路由到无关技能（如 `shenbi-chapter-revision`） → FAIL
- Agent 跳过 `using-shenbi` 直接调用某个审计技能 → FAIL
- Agent 同时加载所有审计技能而不是按需选择 → FAIL（这违反 using-shenbi 的 skill-check 顺序）
