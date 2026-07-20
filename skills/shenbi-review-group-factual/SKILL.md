---
name: shenbi-review-group-factual
description: Grouped audit for factual consistency -- continuity, world rules, and pacing in one call; dispatches as a parallel wave via parallel_dispatch.py
requires_independent_agent: true
contract:
  kind: report
  reads:
    - chapters/chapter-N.md
    - truth/current_state.md
    - truth/chapter_summaries.md
    - world/rules.md
    - world/power_system.md
    - world/locations.md
    - world/story_bible.md
    - genre-config.json
  writes:
    - file: audits/chapter-N-continuity.md
      mode: create_or_overwrite
    - file: audits/chapter-N-world-rules.md
      mode: create_or_overwrite
    - file: audits/chapter-N-pacing.md
      mode: create_or_overwrite
  updates: []
---
<!-- AUTO-CHECK-START -->

## auto-check (generated -- do not edit)

<!-- AUTO-CHECK-END -->

<!-- AUTO-GENERATED from frontmatter — do not edit -->

## 数据契约

- **Reads:** chapters/chapter-N.md, truth/current_state.md, truth/chapter_summaries.md, world/rules.md, world/power_system.md, world/locations.md, world/story_bible.md, genre-config.json
- **Writes:** audits/chapter-N-continuity.md, audits/chapter-N-world-rules.md, audits/chapter-N-pacing.md
- **Updates:** none

<!-- END AUTO-GENERATED -->

# Grouped Audit: Factual Consistency

This skill performs three independent factual-consistency audits in a **single LLM call**. Each dimension produces an independent audit report section using the standard defect evidence format. All three reports are written to their respective audit files.

> **Dispatch note:** This is a MERGE-2 grouped auditor. It dispatches as a parallel wave via `parallel_dispatch.py` (invoked at `chapter_loop.py:1090-1168`), preserving the existing two-wave parallel dispatch model. Do NOT run the three dimensions serially.

## Contract

```yaml
contract:
  reads:
    - {file: chapters/chapter-N.md}
    - {file: truth/current_state.md, fields: [主角状态, 当前世界局势, 活跃线索]}
    - {file: truth/chapter_summaries.md, fields: [已完成章节]}
    - {file: world/rules.md}
    - {file: world/power_system.md}
    - {file: world/locations.md}
    - {file: world/story_bible.md}
    - {file: genre-config.json, fields: [pacing, chapterTypes]}
  writes: []
  updates:
    - audits/chapter-N-continuity.md
    - audits/chapter-N-world-rules.md
    - audits/chapter-N-pacing.md
```

## Evaluation Dimensions

Evaluate the provided chapter from three independent dimensions. Score each separately. Produce three independent audit report sections.

### Dimension 1: Continuity (10 min)

This dimension supersedes the deprecated `shenbi-review-continuity` skill.

#### 铁律

1. **独立评分** -- 本 skill 产出评分/审核判断，必须在 context-cleaned 独立 subagent 执行；drafting/planning agent 不得执行本 skill
2. **时间线是单向不可逆的** -- 不能出现"太阳落山后又出现正午场景"类矛盾
3. **地点跳跃需要过渡** -- 角色不能从A地瞬移到B地除非有明确能力支撑
4. **事件因果链必须完整** -- 每个事件必须有前因后果，不能凭空出现
5. **物理规则一致** -- 本章的物理规则必须与前章一致（除非有明确的世界规则变更）

#### 检查执行

1. **时间线检查**: 提取本章所有时间标记，与 `truth/current_state.md` 和近3章摘要对比，检查是否有时间倒流或不合理跳跃
2. **地点检查**: 提取本章所有地点提及，与角色当前位置对比，检查地点跳跃是否有过渡段落或能力支撑
3. **事件时序**: 提取本章事件链，按文本顺序编号，检查事件间逻辑先后关系是否合理
4. **物理空间合理性**: 检查场景的空间描述是否一致，战斗/移动场景的空间逻辑

#### Arithmetic Consistency Verification

For each chapter, verify:
1. **Currency accumulation**: Copper/silver coin totals must be arithmetically consistent with previous chapters
2. **Date and count patterns**: Verify daily-increment patterns
3. **Inventory tracking**: Verify running totals for items acquired or expended

#### 输出格式

```markdown
### FILE: audits/chapter-N-continuity.md

## 连续性审计报告

**章节**: 第N章
**结果**: 通过 / 有瑕疵 / 不通过

### 时间线
| 标记 | 位置 | 推断时间 | 上一章末尾时间 | 状态 |
|------|------|---------|-------------|------|
| ... | ... | ... | ... | OK/MISMATCH |

### 地点
[地点流转记录，标注跳跃和过渡情况]

### 事件时序
[事件链编号与逻辑审查]

### 物理空间
[空间矛盾标注]

### 评分: X/10 通过

### 建议修复
- [ERROR] [具体段落] [问题描述]：[修复方案]
```

---

### Dimension 2: World Rules (8 min)

This dimension supersedes the deprecated `shenbi-review-world-rules` skill.

#### 铁律

1. **战力体系 = 不可逾越的天花板** -- 角色表现超出 `world/power_system.md` 定义的等级上限 = error
2. **世界规则 = 物理定律** -- 违反 `world/rules.md` 中声明的规则 = error
3. **数值一致性 = 不可调和** -- 同一数值在不同章节矛盾 = error
4. **知识库污染零容忍** -- 角色使用未建立的术语/概念/技术 = error

#### 检查执行

1. **设定冲突检查**: 提取本章所有"能做/不能做"类陈述，与 `world/rules.md` 对比
2. **战力体系完整性**: 检查角色等级上限、能力使用代价、跨等级对决规则
3. **数值一致性**: 提取所有数值陈述，与近5章摘要和 `truth/current_state.md` 对比
4. **知识库污染**: 识别新出现的术语/概念，检查是否在 `world/` 目录已建立

#### 输出格式

```markdown
### FILE: audits/chapter-N-world-rules.md

## 世界规则审计报告

**章节**: 第N章
**结果**: 通过 / 有瑕疵 / 不通过

### 设定冲突
| 段落 | 本章陈述 | 世界规则 | 冲突类型 | 严重度 |
|------|---------|---------|---------|--------|
| ... | ... | ... | ... | error/warning |

### 战力体系
| 段落 | 角色 | 表现 | 等级上限 | 严重度 |
|------|------|------|---------|--------|
| ... | ... | ... | ... | ... |

### 数值一致性
| 数值 | 本章值 | 之前记录 | 矛盾章 | 严重度 |
|------|-------|---------|-------|--------|
| ... | ... | ... | ... | ... |

### 知识库污染
| 段落 | 新术语 | 知识库状态 | 严重度 |
|------|-------|----------|--------|
| ... | ... | ... | ... |

### 评分: X/10 通过

### 建议修复
- [ERROR] [段落] [冲突类型] [规则引用]：[修复方案]
```

---

### Dimension 3: Pacing (5 min)

This dimension supersedes the deprecated `shenbi-review-pacing` skill.

#### 铁律

1. **蓄压必须有释放** -- 连续超过 `genre-config.json` 的 `maxConsecutiveQuest` 章 QUEST 无 FIRE = warning
2. **爆发后必须有缓冲** -- FIRE 章后不能直接进入下一个 FIRE
3. **日常段落必须有功能** -- CONSTELLATION 段落不能只是"日常描写"
4. **章节类型序列需多样** -- 单一类型 > 50% 警告

#### 检查执行

1. **蓄压-爆发周期**: 统计近5章章节类型（QUEST/FIRE/CONSTELLATION），检查规则违规
2. **本章节奏分析**: 识别本章类型，与章节备忘的 `chapter_type` 对比
3. **日常段落功能验证**: CONSTELLATION 章/段需承担关系推进/信息传递/伏笔铺垫
4. **序列多样性**: 检查近10章类型分布

#### 输出格式

```markdown
### FILE: audits/chapter-N-pacing.md

## 节奏审计报告

**章节**: 第N章
**本章类型**: QUEST
**结果**: 通过 / 有瑕疵 / 不通过

### 近5章类型序列
| 章节 | 类型 | 蓄压/爆发状态 |
|------|------|-------------|
| ... | ... | ... |

### 规则检查
- maxConsecutiveQuest: X/Y
- maxGapFIRE: X/Y
- 序列多样性: ...

### 评分: X/10 通过

### 建议修复
- [WARNING] [具体章节] [问题描述]：[修复方案]
```

## 缺陷证据格式

All three dimensions use the standard defect evidence format. Each defect report MUST follow the four-element format:

1. **位置** -- `文件路径` L行号-行号（如 `chapters/chapter-5.md` L23-27）
2. **原文引述** -- 用 `>` 标记引述原文，>=20 字上下文
3. **违反规则** -- 引用 SKILL.md 中的精确规则名（逐字匹配）
4. **严重度** -- BLOCKING | CRITICAL | MINOR

缺失任一要素的缺陷报告视为不合格。

## Anti-Rationalization

| Excuse | Reality |
|--------|---------|
| "读者记不住三天前的事件" | 网文读者逐章追更，时间线矛盾是最容易被发现的bug |
| "战力崩坏是为剧情服务" | 战力崩坏 = 体系失效 = 后续所有对决失去意义 |
| "连续几章蓄压没问题" | 现代网文3章无爆点读者开始流失 |
| "数值差一点没关系" | 数值差 = 长篇叙事的硬伤，读者一旦发现即弃书 |
