---
name: shenbi-context-composing
description: "Use when assembling context before drafting a chapter, collecting truth files, or preparing the writing context package"
contract:
  kind: ephemeral
  reads:
    - plans/chapter-N-plan.md
    - truth/chapter_summaries.md
    - truth/pending_hooks.md
    - truth/audit_drift.md
    - world/rules.md
    - truth/character_matrix.md
    - style/style_profile.md
    - chapters/chapter-N.md
  writes: []
  updates: []
---
<!-- AUTO-GENERATED from frontmatter — do not edit -->

## 数据契约

- **Reads:** plans/chapter-N-plan.md, truth/chapter_summaries.md, truth/pending_hooks.md, truth/audit_drift.md, world/rules.md, truth/character_matrix.md, style/style_profile.md, chapters/chapter-N.md
- **Writes:** none
- **Updates:** none

<!-- END AUTO-GENERATED -->

# 上下文组装

## 流程

```dot
digraph context_composing {
    "Read chapter plan" -> "Collect P1: plan";
    "Collect P1: plan" -> "Collect P2: recent summaries";
    "Collect P2: recent summaries" -> "Collect P3: active hooks [Phase 3] (max 3)";
    "Collect P3: active hooks [Phase 3] (max 3)" -> "Collect P4: drift guidance";
    "Collect P4: drift guidance" -> "Collect P5: world rules (max 5)";
    "Collect P5: world rules (max 5)" -> "Collect P6: character states";
    "Collect P6: character states" -> "Collect P7: style profile";
    "Collect P7: style profile" -> "Check near-chapter endings (avoid repetition)";
    "Check near-chapter endings (avoid repetition)" -> "Present context to human";
    "Present context to human" -> "Proceed to chapter-drafting";
}
```

## 铁律

1. **优先级严格递减** — P1 不可省略，P7 最先被裁剪
2. **近章结尾轨迹** — 收集近 3 章的结尾方式（从 `chapters/chapter-(N-3).md` 到 `chapters/chapter-(N-1).md` 的末段），避免连续相同结尾结构（如连续3个崩塌式结尾）。此检查独立于 P2 摘要收集——摘要提供叙事脉络，结尾轨迹检查章尾模式多样性
3. **不自动检索** — 这是手动组装指南，由 AI 或人类按优先级从文件读取
4. **结尾分析必读原文** — 近章结尾多样性检查必须读取实际章节文件（`chapters/chapter-(N-3).md` 到 `chapters/chapter-(N-1).md`）的末段文本，严禁以摘要（`chapter_summaries.md`）作为结尾分析的代理。摘要不包含结尾结构信息，无法判断连续闭环/开放型结尾模式
5. **伏笔数据溯源** — Hook 债务简报的内容必须来自 `truth/pending_hooks.md`，不得从章节计划（`plans/chapter-N-plan.md`）中提取伏笔信息。章节计划中的伏笔引用可能已过期，只有 pending_hooks.md 是伏笔状态的权威数据源

## 上下文优先级

| 优先级 | 来源 | 文件位置 | 裁剪规则 |
|--------|------|---------|---------|
| P1 (must) | 章节备忘 | `plans/chapter-N-plan.md` | 不裁剪 |
| P2 (must) | 近 2 章摘要 | `truth/chapter_summaries.md` 末尾 | 不裁剪。第 1 章跳过此项，第 2 章只取近 1 章 |
| P3 (need) | 活跃伏笔 | `truth/pending_hooks.md` | 最多 3 条，按紧迫度排序 |
| P4 (need) | 纠偏指导 | `truth/audit_drift.md` | 不裁剪 |
| P5 (nice) | 世界铁律 | `world/rules.md` | 最多 5 条 |
| P6 (nice) | 角色状态 | `truth/character_matrix.md` | 仅本章出场角色 |
| P7 (nice) | 文风指纹 | `style/style_profile.md` | 仅摘要部分 |

## Hook 债务简报

从 pending_hooks.md 提取以下信息，以简报形式呈现：

```markdown
## Hook 债务简报

| Hook ID | 内容 | 状态 | 沉默章数 | 操作建议 |
|---------|------|------|---------|---------|
| hook-001 | 玉佩秘密 | PLANTED | 4/20 | advance |
| hook-002 | 老人预言 | RELEVANT | 2/15 | advance |
| hook-005 | 师姐身世 | PLANTED | 8/12 | URGENT advance |
```

紧迫度 = (current_chapter - last_reinforced) / max_distance

## 输出格式

输出上下文组装结果，必须使用以下 EXACT 节标题。缺少任意一节 = 不合格。

### EXACT 节标题（9/9 必须）

输出的 markdown 必须包含以下 H2 标题，按此顺序：

1. `## P1 章节备忘`
2. `## P2 近期摘要`
3. `## P3 活跃伏笔`
4. `## P4 纠偏指导`
5. `## P5 世界铁律`
6. `## P6 角色状态`
7. `## P7 文风指纹`
8. `## 近章结尾多样性`
9. `## Hook 债务简报`

### ## P3 活跃伏笔 模板

每条伏笔必须附带"数据来源"字段（文件路径 + 行号）。

| Hook ID | 内容 | 状态 | 紧迫度 | 数据来源 |
|---------|------|------|--------|---------|
| hook-001 | ... | PLANTED | 0.4 | `truth/pending_hooks.md` L12-15 |

紧迫度 = (current_chapter - last_reinforced) / max_distance

### ## 近章结尾多样性 模板

必须读取实际章节文件末段（铁律 4），不得以摘要替代。

| 章节 | 文件路径 | 结尾方式 | 末段首句（前 20 字） |
|------|---------|---------|-------------------|
| N-3 | `chapters/chapter-(N-3).md` | hook | ... |
| N-2 | `chapters/chapter-(N-2).md` | transition | ... |
| N-1 | `chapters/chapter-(N-1).md` | cliffhanger | ... |

**不合格条件**：连续 ≥ 3 章同结尾方式，或数据来源未引用实际章节文件。

### ## Hook 债务简报 模板

| Hook ID | 内容 | 状态 | 沉默章数 | 操作建议 | 数据来源 |
|---------|------|------|---------|---------|---------|
| hook-001 | 玉佩秘密 | PLANTED | 4/20 | advance | `truth/pending_hooks.md` L12-15 |

**数据来源列**：每行必须包含文件路径 + 行号。缺失 = 不合格。

### 可自动检查的计数规则

| 检查项 | 规则 | 不合格条件 |
|--------|------|----------|
| 节标题数 | = 9 | < 9 |
| P3 伏笔条目数据来源 | 每条有文件路径+行号 | 任意条目缺失 |
| Hook 债务简报数据来源 | 每条有文件路径+行号 | 任意条目缺失 |
| 近章结尾来源 | 引用 chapters/chapter-*.md 原文 | 使用摘要文件替代 |
| P3 伏笔来源文件 | `truth/pending_hooks.md` | 使用章节计划文件 |
| 近章结尾连续同类型 | ≤ 2 | ≥ 3 |

## Anti-Rationalization

| Excuse | Reality |
|--------|---------|
| "不需要收集这么多上下文" | 上下文不足 = 每章都在重新发明设定 |
| "近章结尾不需要检查" | 不检查 = 连续3个"轰然崩塌"式结尾 |
| "hook 债务简报可以省略" | 不看债务 = 过期伏笔 = 读者信任流失 |
