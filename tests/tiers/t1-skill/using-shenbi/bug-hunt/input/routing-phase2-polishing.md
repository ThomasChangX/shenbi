# 触发测试：文风润色

测试目标：验证 `using-shenbi` 在收到"润色文风但不改剧情"请求时，能否正确路由到 `shenbi-style-polishing`（文风润色技能）。

## 用户输入

```
这章的情节我都满意，但读起来有点涩。你能不能帮我润色一下文字，让它读起来更顺，但剧情和人物对话别动。
```

## 期望的 Agent 行为

正确的 agent 必须：

1. 加载 `skills/using-shenbi/SKILL.md`
2. 识别关键词："润色"、"读起来更顺"、"剧情和人物对话别动" → 对应文风润色
3. 路由到 `skills/shenbi-style-polishing/SKILL.md`（不是 anti-detect，不是 chapter-revision）
4. 明确**不改**情节、对话、人物行为
5. 只在表层文笔（句式、词汇、节奏、视角一致性）上优化

## 期望触发的技能

- **Primary:** `shenbi-style-polishing`（文风润色）

## 通过条件

- [ ] Agent 加载 `using-shenbi`
- [ ] 路由到 `shenbi-style-polishing`
- [ ] 不路由到 `shenbi-anti-detect`（那是去 AI 化检测的修复，不是文风润色）
- [ ] 不路由到 `shenbi-chapter-revision`（那是按审计反馈改内容的）
- [ ] Agent 明确说明："不动情节、对话、人物行为"

## 失败条件

- 路由到 `shenbi-anti-detect` → FAIL
- 路由到 `shenbi-chapter-revision` → FAIL
- Agent 修改了对话或情节 → FAIL（违反"剧情和人物对话别动"的明确约束）
- Agent 重新整章重写而不是局部润色 → FAIL
