# 修订模式参考

## 6种修订模式

| 模式 | 使用场景 | 输出格式 |
|------|---------|---------|
| auto | 默认模式，自动路由到最佳策略 | 根据问题类型决定 |
| spot-fix | 局部措辞/用词问题 | PATCHES（靶向替换） |
| polish | 表达/节奏微调，不涉及情节 | REVISED_CONTENT（全文替换） |
| rewrite | 结构问题，需重组段落 | REVISED_CONTENT（全文替换） |
| rework | 重大问题，可重构场景推进 | REVISED_CONTENT（全文替换） |
| anti-detect | 降低 AI 可检测性 | REVISED_CONTENT（全文替换） |

## auto 模式路由规则

根据问题类型自动选择：

| 问题类型 | 路由到 | 触发审计技能 | Phase |
|---------|--------|------------|-------|
| 时间线错 / 地点矛盾 / 事件时序 / 物理空间 | rewrite | `shenbi-review-continuity` | 2 |
| OOC / 声音不一致 / 配角降智 / 弧线平坦 | rewrite | `shenbi-review-character` | 2 |
| 蓄压-爆发缺失 / 连续无 FIRE / 日常无功能 / 序列单调 | rewrite | `shenbi-review-pacing` | 2 |
| 伏笔过期 / 培育间隔超 / 支线停滞 / 密度异常 / 备忘不符 | rewrite | `shenbi-review-foreshadowing` | 2 |
| 措辞 / 段落形状 / 疲劳词 / 信息越界 / 知识污染 | spot-fix | `shenbi-review-anti-ai` | 1 |
| 混合 / 未知 | rewrite（保守策略） | — | — |

> Phase 2 起：`shenbi-review-continuity`、`shenbi-review-character`、`shenbi-review-pacing`、`shenbi-review-foreshadowing` 四个审计技能均已就绪，auto 模式的 rewrite 路由全部可用。Phase 1 仅有 `shenbi-review-anti-ai`，因此部分 rewrite 路由在 Phase 1 不可用。

## PATCHES 格式

```
--- PATCH 1 ---
TARGET_TEXT: "他感到一股强烈的愤怒涌上心头"
REPLACEMENT_TEXT: "他捏碎了茶杯"
--- END PATCH ---

--- PATCH 2 ---
TARGET_TEXT: "突然间，整个广场都安静了下来"
REPLACEMENT_TEXT: "李长老停下了手中的茶杯"
--- END PATCH ---
```

## REVISED_CONTENT 格式

直接输出修订后的完整章节正文。总长变化不超过 ±15%。

## 修订接受条件

修订必须满足以下所有条件才能应用：

1. blocking 级别问题数量未增加
2. critical 级别问题数量未增加
3. AI 痕迹数量未增加
4. 至少有一项改善（blocking 或 AI 痕迹）
