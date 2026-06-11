# 触发测试：角色一致性审计

测试目标：验证 `using-shenbi` 在收到角色一致性相关的自然语言请求时，能否正确路由到 `shenbi-review-character`（角色一致性审计技能）。

## 用户输入

```
我刚把第12章改完了，麻烦你帮我看看这章里的角色说话做事是不是符合他们的人设？特别是林轩和苏婉。
```

## 期望的 Agent 行为

正确的 agent 必须：

1. 加载 `skills/using-shenbi/SKILL.md`
2. 识别关键词："角色说话做事"、"人设"、"符合" → 对应角色一致性审计
3. 路由到 `skills/shenbi-review-character/SKILL.md`
4. 读取 `characters/` 下的角色档案（林轩、苏婉）
5. 比对章节中角色的对话、行为、内心独白与档案是否一致

## 期望触发的技能

- **Primary:** `shenbi-review-character`（角色一致性审计）

## 通过条件

- [ ] Agent 加载 `using-shenbi`
- [ ] 路由到 `shenbi-review-character`（不是去加载 `shenbi-character-design`，那是创建/修改角色档案的技能）
- [ ] 报告格式包含：行为链合理性 / 性格一致性 / 声音档案匹配度 / 角色弧线符合度

## 失败条件

- 路由到 `shenbi-character-design`（那是设计阶段，不是审查阶段） → FAIL
- 路由到 `shenbi-style-polishing`（那是改文风，不是审角色） → FAIL
- Agent 直接回答"我读了，觉得没问题" → FAIL
