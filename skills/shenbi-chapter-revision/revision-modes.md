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

| 问题类型 | 路由到 | Phase 1 可用 |
|---------|--------|------------|
| OOC / 主线偏离 / 冲突缺失 / 时间线错 / 伏笔未收 | rewrite | Phase 2+（Phase 1 无对应审计技能） |
| 措辞 / 段落形状 / 疲劳词 / 信息越界 / 知识污染 | spot-fix | 部分可用（anti-ai 覆盖措辞/疲劳词） |
| 混合 / 未知 | rewrite（保守策略） | |

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
