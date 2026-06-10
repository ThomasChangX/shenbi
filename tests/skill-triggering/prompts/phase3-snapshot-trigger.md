# 触发测试：快照管理

测试目标：验证 `using-shenbi` 在收到快照相关请求时，能否正确路由到 `shenbi-snapshot-manage`。

## 用户输入

```
第15章写完了，帮我创建一个快照。另外能看看之前第10章的快照还在不在？
```

## 期望的 Agent 行为

正确的 agent 必须：

1. 加载 `skills/using-shenbi/SKILL.md`
2. 识别关键词："快照"、"创建" → 对应快照管理
3. 路由到 `skills/shenbi-snapshot-manage/SKILL.md`
4. 先执行"创建快照"操作（copy truth/ + chapters/chapter-015.md）
5. 再执行"查看快照"操作（列出 snapshots/ 目录）

## 期望触发的技能

- **Primary:** `shenbi-snapshot-manage`（快照管理）

## 通过条件

- [ ] Agent 加载 `using-shenbi`
- [ ] 路由到 `shenbi-snapshot-manage`（不是 `shenbi-state-settling`）
- [ ] 创建快照时复制全部 11 个 truth 文件 + chapters/chapter-015.md
- [ ] 写入 manifest（含 type/chapter/created/trigger/files）

## 失败条件

- 路由到 `shenbi-state-settling`（那是结算状态，不是快照管理） → FAIL
- 只复制部分 truth 文件 → FAIL
- 不创建 manifest → FAIL
