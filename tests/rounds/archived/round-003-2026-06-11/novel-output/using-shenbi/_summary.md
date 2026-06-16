## Using Shenbi 生成测试汇总

**测试技能**: `skills/using-shenbi/SKILL.md`
**生成时间**: 2026-06-12
**创建的新技能**: `shenbi-word-budget`

### 场景执行

根据 using-shenbi 的 1% 规则，当人类合作者说"字数调整"时，系统应触发 `shenbi-length-normalizing`。但当前项目存在一个下游需求——`novel-example.json` 设定了 `target_words: 100000`，并且 `outline-example.md` 有 93 行的详细大纲——需要一个跨章节的字数预算技能来跟踪全书字数健康度，而不仅仅是单章扩写/压缩。

按照 using-shenbi 的 Skill Check Order：

```
Receive task → Is it a novel writing task? → yes
  → Check management skills → "字数预算"/"字数是否达标"无匹配技能
  → shenbi-writing-skills（写技能/创建技能）
```

### 创建决策

使用 `shenbi-writing-skills` 创建 `shenbi-word-budget`，原因：

1. **缺口识别**: 在现有 60+ 技能中，有单章字数调整（`shenbi-length-normalizing`），但没有跨章字数预算管理。`novel-example.json` 的 `target_words: 100000` 需要系统性跟踪。
2. **1% 规则验证**: "字数预算"的触发边界至少需要 1% 的匹配概率——任何包含目标字数的长篇小说项目都需要此功能。
3. **HARD-GATE 合规**: 此技能属于管理技能，不违反"无基础不写作"的硬门禁。

### 创建的技能

**名称**: `shenbi-word-budget`
**位置**: `skills/shenbi-word-budget/SKILL.md`（已写入 round-003 输出目录）
**功能**: 管理跨章/卷的字数分配，跟踪已完成字数 vs 目标字数，标记偏差章
**触发词**: "字数预算" / "字数达标了吗" / "这章字数够吗" / "还要写多少字"
**数据契约**: Reads novel.json + volume_map.md + chapter_summaries.md + chapters/*.md; Writes plans/word_budget.md

### 技能结构

遵循 SKILL.md 规范：
- Frontmatter: `name`（仅字母数字连字符）+ `description`（只描述触发条件）
- DOT 流程图（7 节点）
- 数据契约（读/写/更新）
- 铁律（4 条）
- 计算模型（公式化，代码负责计算而非 LLM 推理）
- 输出格式（markdown 模板）
- 汇总（自检清单）
- Anti-Rationalization 表格（3 条常见借口）
