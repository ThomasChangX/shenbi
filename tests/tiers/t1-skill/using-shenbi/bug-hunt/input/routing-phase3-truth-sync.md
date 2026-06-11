# 触发测试：真相同步

测试目标：验证 `using-shenbi` 在收到手动编辑后同步请求时，能否正确路由到 `shenbi-truth-sync`。

## 用户输入

```
我手动改了第8章的正文，把主角去北城改成去南城了。帮我重新提取一下这章的状态，把truth文件同步一下。
```

## 期望的 Agent 行为

正确的 agent 必须：

1. 加载 `skills/using-shenbi/SKILL.md`
2. 识别关键词："重新提取"、"同步"、"truth文件" → 对应真相同步
3. 路由到 `skills/shenbi-truth-sync/SKILL.md`
4. 从修改后的 chapters/chapter-008.md 重新提取状态变化
5. 更新受影响的 truth 文件（current_state.md 的位置信息、chapter_summaries.md 等）

## 期望触发的技能

- **Primary:** `shenbi-truth-sync`（真相同步）

## 通过条件

- [ ] Agent 加载 `using-shenbi`
- [ ] 路由到 `shenbi-truth-sync`（不是 `shenbi-state-settling`——state-settling 是起草后自动触发，truth-sync 是手动编辑后的重新提取）
- [ ] 识别出北城→南城的位置变化
- [ ] 更新 `truth/current_state.md` 中的位置信息

## 失败条件

- 路由到 `shenbi-state-settling`（那个用于起草后，不是手动编辑后） → FAIL
- 不读取修改后的章节正文就更新 → FAIL
