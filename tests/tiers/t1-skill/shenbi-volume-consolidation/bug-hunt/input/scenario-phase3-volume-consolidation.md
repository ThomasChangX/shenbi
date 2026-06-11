# 行为测试：卷总结 — 数据归档完整性

测试目标：验证 `shenbi-volume-consolidation` 在卷完成后能正确归档数据、生成卷摘要、更新 volume_summaries.md。

## 测试场景

第一卷（第1-15章）全部完成，需要执行卷总结。

## 准备

- 第一卷: chapter-001 到 chapter-015
- `outline/volume_map.md`: 第一卷 objective + 3 个 key results
- `truth/chapter_summaries.md`: 15 章摘要
- `truth/pending_hooks.md`: 5 条伏笔（2 PLANTED, 2 RELEVANT, 1 TRIGGERED）
- `truth/volume_summaries.md`: 不存在（第一卷）

## 期望行为

1. 读取 volume_map.md 第一卷定义
2. 总结本卷核心冲突进展
3. 统计本卷伏笔状态（2 PLANTED / 2 RELEVANT / 1 TRIGGERED）
4. 生成卷摘要（含关键事件、角色弧线变化、跨卷衔接点）
5. 追加到 `truth/volume_summaries.md`（创建文件）
6. 建议下卷起点的关注点

## 通过条件

- [ ] 卷摘要包含核心冲突进展
- [ ] 卷摘要包含伏笔盘点
- [ ] `truth/volume_summaries.md` 被创建并追加
- [ ] 提供跨卷衔接点

## 失败条件

- 不创建 volume_summaries.md → FAIL
- 只写摘要不盘点伏笔 → FAIL
- 删除 truth/ 中的逐章摘要 → FAIL（铁律: 归档不是删除）
