# 流水线 Runner 设计注意点（Pipeline Design Notes）

> 日期: 2026-06-29
> 状态: 设计注意点，待实现为完整 spec
> 目的: 基于 round test 001 的经验教训，为未来流水线 runner 提供设计约束和注意点

## 背景

Round test 001 暴露的核心问题是：框架有完整的设计（逐章循环、审计、评分、修正闭环、分层记忆），但**没有自动化的执行器**。所有步骤都需要人工编排器手动调用，导致大量治理步骤被跳过。

未来流水线 runner（`shenbi-pipeline`）应解决以下问题。以下是设计注意点。

## 1. 串行生成（非并行）

**决定**: 未来小说生成使用**串行**逐章顺序，不使用并行 worker。

**原因**: 并行 worker 之间无法共享 truth files 状态，导致角色名/设定/伏笔不一致。串行生成确保每章基于完整的 truth files 前序状态。

**设计约束**: runner 必须确保前一章的 state-settling + 审计 + 评分完成后，才开始下一章的 chapter-planning。

## 2. 逐章循环必须完整执行

runner 必须对每章执行完整的循环步骤，不可跳过任何一步：

```
for chapter N:
  1. intent-management（更新 current_focus）
  2. chapter-planning（生成 8 段式备忘）
  3. context-composing（按层组装 L5→L1，产出上下文包）
  4. chapter-drafting（读上下文包，产出章节正文）
  5. state-settling（提取事实变化，更新 truth files）← 不可跳过
  6. foreshadowing-recall（更新伏笔索引）
  7. 审计层（按 genre-config 激活规则运行审计技能）
  8. review-resonance（独立 agent，route A+C 评分）
  9. revision_routing（诊断分类 → spot-fix/regenerate）
  10. chapter-revision（如需修订/重生 + preserve_check + state-settling 重跑）
  11. snapshot-manage（创建快照）
  12. drift-guidance（生成纠偏指导）
  13. escalation_check（检查是否需要人工升级）
```

**关键约束**: 
- 步骤 5（state-settling）**必须在步骤 4 之后立即执行**。跳过 = truth files 过时 = 后续章节全部基于错误状态
- 步骤 7（审计）**不可跳过**。任何审计 BLOCKING → 进入步骤 9-10 修正闭环
- 步骤 8-10（评分-修正闭环）**不可跳过**。评分 < 阈值 → 必须修订/重生，不可"先放着后面再说"
- 步骤 13（escalation_check）在每章评分完成后调用

## 3. 分层记忆触发

runner 必须包含触发逻辑（不是 skill 内部触发，是 runner 外部触发）：

```
if chapter % 12 == 0:
    run memory-distill L2（弧段蒸馏）
    run score-arc（弧段级评分）
if chapter % 36 == 0:
    run memory-distill L4（大弧蒸馏）
    run score-stratum（大弧/书级评分）
if is_volume_boundary(chapter):
    run volume-consolidation L3（必须在 score-volume 之前）
    run review-arc-payoff（体验质量门）
    run score-volume（目标达成门）
    run memory-distill L5滚动复核（合并 author_intent）
    run drift-guidance 卷级
```

## 4. context-composing 不可绕过

**HARD-GATE**: chapter-drafting 的输入**必须**是 context-composing 产出的上下文包。

runner 必须调用 context-composing skill 产出 `context/chapter-N-context.md`，然后将此文件作为 chapter-drafting 的输入。不可直接给 chapter-drafting 扁平的 outline 文件。

**爬坡期处理**（章节 1-35）：context-composing 按层尝试加载，缺失层（L2/L4）跳过不报错。L1 取近 12 章补偿。

## 5. state-settling 不可跳过

**HARD-GATE**: 每章起草后必须执行 state-settling。更新以下 truth files：
- truth/current_state.md（位置/状态/情绪/冲突）
- truth/chapter_summaries.md（追加摘要）
- truth/character_matrix.md（关系/信息边界）
- truth/emotional_arcs.md（情感弧线）
- truth/pending_hooks.md（伏笔状态）← 需要先运行 foreshadowing-plant
- truth/particle_ledger.md（资源账本）
- truth/subplot_board.md（支线进度）

**注意**: truth/pending_hooks.md、particle_ledger.md、subplot_board.md 在 round test 001 中完全不存在。创世层（worldbuilding）应该初始化这些空模板（worldbuilding SKILL.md 已声明 `truth/*.md` 初始化），但 runner 必须验证它们存在。

## 6. 锚点处理

review-resonance 的 route A 需要 `benchmarks/anchors/AC-NNN.md`。锚点文件是**框架级资产**（在框架根目录的 `benchmarks/anchors/`），不复制到项目目录。

如果锚点目录为空或不存在，route A 降级为"无锚点参照"模式（评分报告标注 `anchor_calibration: unavailable`），不阻断但 flag。

## 7. 章节元数据格式

章节文件中 PRE_WRITE_CHECK 和 POST_WRITE_SELF_CHECK 用 `<!--META-BEGIN-->` / `<!--META-END-->` 包裹。下游解析器（字数统计、审计、评分）必须剥离 META 块后处理纯正文。

## 8. progress.json 跟踪

runner 必须在每步完成后调用 `shenbi-progress mark-done`：
- 每个 skill 的 generative/bug-hunt/clean 测试完成后
- progress.json 已在 init 时预填充所有 skill 为 pending 状态

## 9. Gate 执行

runner 必须在适当节点运行 gates：
- G0：round 创建时（已有 round-exec.sh）
- G2：每个 skill 产出后验证输出结构
- G4：每个 skill 产出后验证 skill-specific 结构
- G5：T2 phase 开始前
- G6：T3 pipeline 开始前
- G7：round 关闭时

gate marker 文件必须写入 `gate-markers/` 目录。

## 10. 错误处理与重试

- 审计 BLOCKING：自动进入修正闭环（spot-fix 或 regenerate），最多 3 次重试
- 评分 < 阈值：进入修正闭环
- 同一目标连续 3 次未兑现：escalation_check 触发人工升级
- state-settling 失败：该章标记为 `settling_failed`，暂停后续章节生成

## 11. 回退与恢复

runner 必须支持从中断点恢复：
- 读 progress.json 确定当前进度
- 读 novel.json current_chapter 确定章节进度
- 验证 truth files 的 chapter 字段与 novel.json 一致
- 如不一致，从 truth files 的最后已知正确状态恢复

## 12. 串行生成的性能考量

67 章 × 13 步/章 = ~871 步。每步可能需要 30-120 秒（LLM 调用）。
预计总时间：7-15 小时（取决于 LLM 速度和审计/评分复杂度）。

可接受的优化（不牺牲一致性）：
- 审计层内的 18 个审计可按 spec §7.5 的顺序串行执行（前一步 BLOCKING 则停止）
- review-resonance 与审计可并行（不同评估轴，不互相依赖）
- context-composing 与 intent-management 可合并为一步

