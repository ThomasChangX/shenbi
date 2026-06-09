# 触发测试：伏笔审计

测试目标：验证 `using-shenbi` 在收到伏笔相关请求时，能否正确路由到 `shenbi-review-foreshadowing`（伏笔审计技能）。

## 用户输入

```
我已经写到第30章了，前面埋了好多伏笔。我现在担心这些伏笔是不是都还记得、是不是在合适的位置揭开了。能不能帮我检查一下伏笔的处理情况？
```

## 期望的 Agent 行为

正确的 agent 必须：

1. 加载 `skills/using-shenbi/SKILL.md`
2. 识别关键词："伏笔"、"记得"、"揭开" → 对应伏笔审计
3. 路由到 `skills/shenbi-review-foreshadowing/SKILL.md`（注意：是审计，不是 plan/track/resolve）
4. 读取 `truth/pending_hooks.md`（伏笔池）
5. 比对章节中触发的伏笔与池中条目是否一致
6. 检查是否有 PLANTED 后长期未 TRIGGERED 的"遗失伏笔"

## 期望触发的技能

- **Primary:** `shenbi-review-foreshadowing`（伏笔审计）

## 通过条件

- [ ] Agent 加载 `using-shenbi`
- [ ] 路由到 `shenbi-review-foreshadowing`，**不是** `shenbi-foreshadowing-plant/track/resolve`（那三个是状态变更技能，review 才是审计）
- [ ] 报告格式包含：伏笔池清单 / 已触发但未解决 / 已解决 / 长期未触发（潜在遗失）

## 失败条件

- 路由到 `shenbi-foreshadowing-track`（那是状态评估，不是审计） → FAIL
- 路由到 `shenbi-foreshadowing-resolve`（那是揭伏笔的创作技能） → FAIL
- Agent 没有读取 `truth/pending_hooks.md` 就直接审计 → FAIL
