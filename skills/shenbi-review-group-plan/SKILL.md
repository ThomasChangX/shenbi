---
name: shenbi-review-group-plan
description: Grouped audit for plan compliance -- memo compliance and foreshadowing consistency in one call; dispatches as a parallel wave via parallel_dispatch.py
requires_independent_agent: true
contract:
  kind: report
  reads:
    - chapters/chapter-N.md
    - plans/chapter-N-plan.md
    - truth/pending_hooks.md
    - truth/subplot_board.md
  writes:
    - file: audits/chapter-N-memo-compliance.md
      mode: create_or_overwrite
    - file: audits/chapter-N-foreshadowing.md
      mode: create_or_overwrite
  updates: []
---
<!-- AUTO-CHECK-START -->

## auto-check (generated -- do not edit)

<!-- AUTO-CHECK-END -->

<!-- AUTO-GENERATED from frontmatter — do not edit -->

## 数据契约

- **Reads:** chapters/chapter-N.md, plans/chapter-N-plan.md, truth/pending_hooks.md, truth/subplot_board.md
- **Writes:** audits/chapter-N-memo-compliance.md, audits/chapter-N-foreshadowing.md
- **Updates:** none

<!-- END AUTO-GENERATED -->

# Grouped Audit: Plan Compliance

This skill performs two independent plan-compliance audits in a **single LLM call**. Each dimension produces an independent audit report section using the standard defect evidence format. Both reports are written to their respective audit files.

> **Dispatch note:** This is a MERGE-2 grouped auditor. It dispatches as a parallel wave via `parallel_dispatch.py` (invoked at `chapter_loop.py:1090-1168`), preserving the existing two-wave parallel dispatch model. Do NOT run the two dimensions serially.

## Contract

```yaml
contract:
  reads:
    - {file: chapters/chapter-N.md}
    - {file: plans/chapter-N-plan.md}
    - {file: truth/pending_hooks.md}
    - {file: truth/subplot_board.md}
  writes: []
  updates:
    - audits/chapter-N-memo-compliance.md
    - audits/chapter-N-foreshadowing.md
```

## Evaluation Dimensions

Evaluate the provided chapter from two independent dimensions. Score each separately. Produce two independent audit report sections.

### Dimension 1: Memo Compliance

This dimension supersedes the deprecated `shenbi-review-memo-compliance` skill.

> Activation: conditioned on `genre-config.json` `auditDimensions` including dimension 33.

> Relationship with `shenbi-chapter-planning`: the memo is generated during planning; this audit only checks "was it delivered" -- it does NOT modify the memo itself.

#### 铁律

1. **备忘是承诺，必须兑现** -- 备忘第1段"当前任务"未在正文中出现 = error
2. **章尾改变 = 必现** -- 备忘第6段列出的1-3条改变必须发生，少一条 = error
3. **禁止事项 = 必避** -- 备忘第8段列出的事项一旦在正文中出现 = error
4. **Hook账本必须与正文一致** -- 备忘第7段声明的hook操作必须能在正文中找到对应动作

#### 检查执行

1. **当前任务交付检查（第1段）**: 读取备忘第1段"当前任务"，在正文中检索关键动作词
2. **Hook兑现/压住检查（第3段）**: 兑现项是否出现，压住项是否被意外掀出
3. **章尾改变检查（第6段）**: 列出的1-3条改变必须在章尾可验证
4. **Hook账本匹配（第7段）**: 声明的hook操作是否与 `truth/pending_hooks.md` 同步
5. **禁止事项检查（第8段）**: 逐条在正文中检索"不要做"的事项
6. **读者等待/日常功能（第2、4段）**: 第2段读者等待是否有回应，第4段日常功能是否兑现

#### 输出格式

```markdown
### FILE: audits/chapter-N-memo-compliance.md

## 章节备忘合规审计报告

**章节**: 第N章
**结果**: 通过 / 有瑕疵 / 不通过

### 备忘兑现度
| 备忘段 | 承诺 | 兑现状态 | 严重度 |
|--------|------|---------|--------|
| 第1段 当前任务 | ... | OK/MISSING | error/warning |
| 第3段 兑现 | hook-XXX | OK/MISSING | ... |
| 第6段 章尾改变 | ... | OK/MISSING | ... |
| 第7段 Hook账 | ... | OK/MISMATCH | ... |
| 第8段 禁止 | ... | OK/VIOLATED | ... |

### 读者等待/日常功能
[第2段与第4段的核对结果]

### 评分: X/10 通过

### 建议修复
- [ERROR] [段落位置] [备忘段引用] [问题描述]：[修复方案]
- [WARNING] [段落位置] [备忘段引用] [问题描述]：[修复方案]
```

---

### Dimension 2: Foreshadowing Consistency

This dimension supersedes the deprecated `shenbi-review-foreshadowing` skill.

> Default-activated (every chapter).

> Distinction from `shenbi-reader-pull`: foreshadowing checks "hook ledger cultivation and resolution"; reader-pull checks "immediate stimulation for continued reading."
> Distinction from `shenbi-foreshadowing-lifecycle`: the lifecycle skill performs recall-track-plant operations on `pending_hooks.md`; this audit dimension checks whether the foreshadowing outcomes align with the chapter plan and hook ledger.

#### 铁律

1. **伏笔池中每颗伏笔都有生命周期状态** -- 未标注状态 = error
2. **伏笔不可同时处于培育期和未标注** -- 培育中伏笔必须有触发条件
3. **伏笔兑现期超期 = 读者焦虑** -- 超过声明兑现窗口未兑现 = error
4. **新植伏笔必须有钩子描述** -- 无钩子描述 = warning

#### 检查执行

1. **伏笔池完整性**: 读取 `truth/pending_hooks.md`，检查每颗伏笔的生命周期状态
2. **兑现期检查**: 声明本应兑现但未兑现的伏笔 = error
3. **培育期检查**: 培育中伏笔是否有触发条件标注
4. **新植伏笔验证**: 备忘第7段新植伏笔是否有钩子描述和排版位置
5. **伏笔与副线板对齐**: 伏笔池中的伏笔是否与 `truth/subplot_board.md` 的副线一致

#### 输出格式

```markdown
### FILE: audits/chapter-N-foreshadowing.md

## 伏笔一致性审计报告

**章节**: 第N章
**结果**: 通过 / 有瑕疵 / 不通过

### 伏笔池状态
| 伏笔ID | 状态 | 兑现期 | 本章操作 | 严重度 |
|--------|------|-------|---------|--------|
| hook-XXX | ACTIVE | Ch+3 | advance | PASS |
| hook-YYY | DORMANT | Ch-2 | — | error (超期) |

### 兑现期检查
| 伏笔ID | 声明兑现章 | 当前章 | 状态 | 严重度 |
|--------|----------|-------|------|--------|
| ... | ... | ... | pending/overdue/resolved | ... |

### 新植伏笔
| 伏笔ID | 钩子描述 | 触发条件 | 状态 |
|--------|---------|---------|------|
| ... | ... | ... | OK/MISSING |

### 副线板对齐
[伏笔与subplot_board的交叉验证]

### 评分: X/10 通过

### 建议修复
- [ERROR] [伏笔ID] [问题类型]：[修复方案]
- [WARNING] [伏笔ID] [问题描述]：[修复方案]
```

## 缺陷证据格式

Both dimensions use the standard defect evidence format. Each defect report MUST follow the four-element format:

1. **位置** -- `文件路径` L行号-行号（如 `chapters/chapter-5.md` L23-27）
2. **原文引述** -- 用 `>` 标记引述原文，>=20 字上下文
3. **违反规则** -- 引用 SKILL.md 中的精确规则名（逐字匹配）
4. **严重度** -- BLOCKING | CRITICAL | MINOR

缺失任一要素的缺陷报告视为不合格。

## Anti-Rationalization

| Excuse | Reality |
|--------|---------|
| "备忘是计划，可以灵活调整" | 灵活调整 = 推翻承诺 = 读者信任崩塌。改备忘前先回规划阶段 |
| "章尾改变太小读者不会注意" | 章节必须推进状态，小改变也是改变；缺席 = 静止章 = 弃书信号 |
| "伏笔超期没事，后面补" | 超期伏笔 = 读者悬空太久 = 忘了 = 伏笔失效 |
| "禁止事项偶尔碰一下没事" | 禁止事项是写作者主动设立的护栏，碰护栏 = 偏离自己定的边界 |
| "Hook账本可以下次再同步" | 账本与正文脱节 = 伏笔系统失效 |
