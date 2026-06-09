# 触发测试：作者意图管理

测试目标：验证 `using-shenbi` 在收到关于作者意图/长期目标的请求时，能否正确路由到 `shenbi-intent-management`。

## 用户输入

```
我觉得接下来5章应该集中写门派大比，主角要在第30章拿到第一。帮我把这个长期目标更新一下，下一章规划的时候参考这个方向。
```

## 期望的 Agent 行为

正确的 agent 必须：

1. 加载 `skills/using-shenbi/SKILL.md`
2. 识别关键词："长期目标"、"更新" → 对应意图管理
3. 路由到 `skills/shenbi-intent-management/SKILL.md`
4. 更新 `truth/author_intent.md`（长期意图）
5. 更新 `truth/current_focus.md`（1-3章范围的短期焦点）

## 期望触发的技能

- **Primary:** `shenbi-intent-management`（意图管理）

## 通过条件

- [ ] Agent 加载 `using-shenbi`
- [ ] 路由到 `shenbi-intent-management`
- [ ] 同时更新 author_intent.md 和 current_focus.md
- [ ] 短期焦点反映"门派大比"方向

## 失败条件

- 路由到 `shenbi-chapter-planning`（那是规划下一章，不是管理意图） → FAIL
- 只更新 author_intent.md 不更新 current_focus.md → FAIL
