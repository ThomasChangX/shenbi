---
name: shenbi-review-group-craft
description: Grouped audit for writing craft -- texture, reader-pull, and anti-AI patterns in one call; dispatches as a parallel wave via parallel_dispatch.py
requires_independent_agent: true
contract:
  kind: report
  reads:
    - chapters/chapter-N.md
    - genre-config.json
    - plans/chapter-N-plan.md
    - truth/pending_hooks.md
  writes:
    - file: audits/chapter-N-texture.md
      mode: create_or_overwrite
    - file: audits/chapter-N-reader-pull.md
      mode: create_or_overwrite
    - file: audits/chapter-N-anti-ai.md
      mode: create_or_overwrite
  updates: []
---
<!-- AUTO-CHECK-START -->

## auto-check (generated -- do not edit)

<!-- AUTO-CHECK-END -->

<!-- AUTO-GENERATED from frontmatter — do not edit -->

## 数据契约

- **Reads:** chapters/chapter-N.md, genre-config.json, plans/chapter-N-plan.md, truth/pending_hooks.md
- **Writes:** audits/chapter-N-texture.md, audits/chapter-N-reader-pull.md, audits/chapter-N-anti-ai.md
- **Updates:** none

<!-- END AUTO-GENERATED -->

# Grouped Audit: Writing Craft

This skill performs three independent writing-craft audits in a **single LLM call**. Each dimension produces an independent audit report section using the standard defect evidence format. All three reports are written to their respective audit files.

> **Dispatch note:** This is a MERGE-2 grouped auditor. It dispatches as a parallel wave via `parallel_dispatch.py` (invoked at `chapter_loop.py:1090-1168`), preserving the existing two-wave parallel dispatch model. Do NOT run the three dimensions serially.

## Contract

```yaml
contract:
  reads:
    - {file: chapters/chapter-N.md}
    - {file: genre-config.json}
    - {file: plans/chapter-N-plan.md}
    - {file: truth/pending_hooks.md}
  writes: []
  updates:
    - audits/chapter-N-texture.md
    - audits/chapter-N-reader-pull.md
    - audits/chapter-N-anti-ai.md
```

## Evaluation Dimensions

Evaluate the provided chapter from three independent dimensions. Score each separately. Produce three independent audit report sections.

### Dimension 1: Writing Texture

This dimension supersedes the deprecated `shenbi-review-texture` skill.

> Activation: conditioned on `genre-config.json` `auditDimensions` including dimension 17.

> Distinction from pacing: pacing checks "chapter type sequence" and "buildup-release cycle periodicity"; texture checks "paragraph-level" quality.
> Distinction from anti-ai: texture checks **extreme** segment lengths (>500/<20 chars) and **breathing** (readability); anti-ai checks segment length **regularity/uniformity** (low CV = AI generation signal).

#### 铁律

1. **流水账 = 写作致命伤** -- 单纯按时间罗列事件而无功能/冲突/变化的段落 = error
2. **作者说教 = 越界** -- 叙事者跳出情节直接对读者输出观点/教训 = error
3. **段长极端 = 节奏病** -- 单段 > 500 字或 < 20 字（无特殊修辞目的）= warning
4. **日常段必须有功能** -- 备忘第4段标注的功能必须在对应段落实

#### 检查执行

1. **流水账检测**: 扫描连续段落是否仅按时序罗列而无变化/冲突/选择
2. **作者说教检测**: 检测叙事者直接发表观点/教训的句子
3. **段落呼吸检查**: 统计每段字数，检查长段和短段模式
4. **段长极端检查**: 段落字数极差、单段超800字且非高潮 = error
5. **日常段功能验证**: 读取备忘第4段，验证功能是否兑现

#### 输出格式

```markdown
### FILE: audits/chapter-N-texture.md

## 写作质感审计报告

**章节**: 第N章
**结果**: 通过 / 有瑕疵 / 不通过

### 流水账检测
| 段落范围 | 流水账特征 | 严重度 |
|---------|----------|--------|
| ... | ... | ... |

### 作者说教
| 段落 | 触发词/模式 | 严重度 |
|------|--------------|--------|
| ... | ... | ... |

### 段长分布
- 最短段: X 字
- 最长段: Y 字
- 平均段长: Z 字
- 极端段: N 段

### 段长极端
| 段落 | 字数 | 判定 | 严重度 |
|------|-----|------|--------|
| ... | ... | ... | ... |

### 日常段功能
| 备忘声明 | 对应段落 | 是否兑现 |
|---------|---------|---------|
| ... | ... | ... |

### 评分: X/10 通过

### 建议修复
- [ERROR] [段落] [流水账/说教]：[具体改写方向]
- [WARNING] [段落] [段长/功能]：[具体修改方案]
```

---

### Dimension 2: Reader Pull

This dimension supersedes the deprecated `shenbi-review-reader-pull` skill.

> Activation: conditioned on `genre-config.json` `auditDimensions` including dimension 32.

#### 铁律

1. **章头 200 字 = 生死线** -- 章节开头无钩子/拖沓/信息密度低 = error
2. **章尾必须留悬念** -- 章尾无悬念/无信息落差/无改变 = error
3. **期待必须被回应或被管理** -- 备忘第2段"读者此刻在等什么"必须有明确回应
4. **中段必须有牵引点** -- 章中每800-1200字需有牵引点（冲突/揭示/转折），否则 = warning

#### 检查执行

1. **开头钩子强度**: 读取前200字，检测钩子类型（紧急情境/信息落差/直接冲突/反常情境/强气氛）
2. **章尾悬念**: 读取最后300字，检测悬念类型（揭示未完/决策未决/威胁升级/信息缺口/反转钩）
3. **期待管理**: 读取备忘第2段，在正文中追踪兑现/延迟/转方向
4. **中段牵引点**: 每800-1200字一块，每块需有至少一个牵引点
5. **钩子池压力平衡**: 对比"施加压力 vs 释放压力"，连续净施加 > 5章 = warning

#### 输出格式

```markdown
### FILE: audits/chapter-N-reader-pull.md

## 读者牵引力审计报告

**章节**: 第N章
**结果**: 通过 / 有瑕疵 / 不通过

### 开头钩子
- 钩子类型: ...
- 强度: 强/中/弱
- 判定: PASS/error

### 章尾悬念
- 悬念类型: ...
- 强度: 强/中/弱
- 判定: PASS/error

### 期待管理
| 备忘承诺 | 实际处理 | 状态 |
|---------|---------|------|
| ... | ... | MATCH/HELD/MISSING |

### 中段牵引点
| 段落块 | 牵引类型 | 状态 |
|--------|---------|------|
| ... | ... | OK/warning |

### 钩子池压力
- 施加: N
- 释放: N
- 净压力: +/-N
- 累计: 第N章连续+

### 评分: X/10 通过

### 建议修复
- [ERROR] [位置] [钩子/悬念/期待问题]：[修复方案]
- [WARNING] [段落块] [牵引点缺失]：[补足方案]
```

---

### Dimension 3: Anti-AI Detection

This dimension supersedes the deprecated `shenbi-review-anti-ai` skill.

> Default-activated (every chapter).

> Distinction from texture: texture checks segment length extremes and breathing (quality); anti-ai checks segment length uniformity/low CV (detectability).

#### 铁律

1. **不信任"看起来还行"** -- 每条检查必须逐一执行，不允许跳步
2. **先确定性后判断** -- 确定性检查（零LLM成本）先跑，发现问题就不需要继续
3. **error 级别 = 必须修复** -- error 级别问题不通过修订不能放过
4. **warning 级别 = 建议修复** -- 3+ warning也需要修订

#### 检查执行

Execute checks in order:

1. 段落等长检测 (Coefficient of Variation)
2. "不是...而是..."句式检测
3. 破折号检测
4. 转折词密度
5. AI 标记词
6. 疲劳词（from `genre-config.json`）
7. 元叙事/编剧旁白
8. 分析报告术语
9. 集体反应套话
10. 禁忌词（from `genre-config.json`）

#### 输出格式

```markdown
### FILE: audits/chapter-N-anti-ai.md

## Anti-AI 审计报告

**章节**: 第N章
**字数**: XXXX
**结果**: 通过 / 有瑕疵 / 不通过

### 检查结果
| # | 检查项 | 结果 | 详情 |
|---|--------|------|------|
| 1 | 段落等长 | PASS/ERROR | CV=X.XX |
| 2 | 不是...而是... | PASS/ERROR | N occurrences |
| ... | ... | ... | ... |

### 评分: X/10 通过

### 建议修复
- [ERROR] [段落] [问题描述]：[修复方案]
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
| "流水账是交代背景的必要手段" | 交代背景可以通过一个冲突场景或一个对话瞬间完成，流水账是懒惰写法 |
| "开篇可以从背景讲起" | 网文读者给每章30秒判断去留 |
| "AI味读者看不出来" | 平台AIGC检测算法看得很清楚，降权直接影响收入 |
| "章尾可以平静收束" | 平静章尾 = 没有下一章理由 = 读者合上书 |
