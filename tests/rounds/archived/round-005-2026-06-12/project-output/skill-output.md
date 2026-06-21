## 新技能: POV 过渡管理

---
name: shenbi-pov-transition
description: Use when a scene requires switching between character viewpoints, managing information boundaries across POV changes, or auditing a chapter for unauthorized knowledge leakage
---

# POV 过渡管理

管理多角色叙事中的视点切换。

## 流程

```dot
graph pov_transition {
    "Identify current POV character" -> "Check knowledge boundary at exit point";
    "Check knowledge boundary" -> "Select transition type (hard cut / soft bridge / parallel)";
    "Select transition type" -> "Execute transition with explicit marker";
    "Execute transition" -> "Verify new POV character knowledge";
    "Verify new POV knowledge" -> "Flag any leakage";
}
```

## 铁律

1. **每一段有且只有一个视点角色** — NEVER 同一段内切换视点
2. **切换必须标记** — MUST 使用场景分隔符或章节断点
3. **新视点不知道旧视点的内心** — ALWAYS 验证知识获取渠道
4. **读者知道的 ≠ 角色知道的** — NEVER 让读者先于角色获得信息泄漏

## Anti-Rationalization

| Excuse | Reality |
|--------|---------|
| "读者已经知道了，角色知道也没关系" | 读者知道 ≠ 角色知道；信息泄漏 = 角色OOC |
| "过渡不重要，直接切就行" | 无标记切换 = 读者困惑 = 叙事信用破产 |
| "第一人称可以知道一切" | 第一人称也有认知边界；叙述者不能知道未经历的事 |

## 红旗检查清单

- [ ] 同段内出现两个角色的内心独白
- [ ] 角色A知道只有角色B在场时发生的事
- [ ] 场景切换无分隔符
- [ ] 叙述者用"他/她"指代不明
