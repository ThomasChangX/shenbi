---
name: shenbi-review-group-character
description: Grouped audit for character integrity -- character consistency, dialogue, motivation, and POV in one call; dispatches as a parallel wave via parallel_dispatch.py
requires_independent_agent: true
contract:
  kind: report
  reads:
    - chapters/chapter-N.md
    - characters/protagonist.md
    - characters/major/*.md
    - truth/character_matrix.md
    - truth/emotional_arcs.md
    - truth/current_state.md
    - genre-config.json
  writes:
    - file: audits/chapter-N-character.md
      mode: create_or_overwrite
    - file: audits/chapter-N-dialogue.md
      mode: create_or_overwrite
    - file: audits/chapter-N-motivation.md
      mode: create_or_overwrite
    - file: audits/chapter-N-pov.md
      mode: create_or_overwrite
  updates: []
---
<!-- AUTO-CHECK-START -->

## auto-check (generated -- do not edit)

<!-- AUTO-CHECK-END -->

<!-- AUTO-GENERATED from frontmatter — do not edit -->

## 数据契约

- **Reads:** chapters/chapter-N.md, characters/protagonist.md, characters/major/*.md, truth/character_matrix.md, truth/emotional_arcs.md, truth/current_state.md, genre-config.json
- **Writes:** audits/chapter-N-character.md, audits/chapter-N-dialogue.md, audits/chapter-N-motivation.md, audits/chapter-N-pov.md
- **Updates:** none

<!-- END AUTO-GENERATED -->

# Grouped Audit: Character Integrity

This skill performs four independent character-integrity audits in a **single LLM call**. Each dimension produces an independent audit report section using the standard defect evidence format. All four reports are written to their respective audit files.

> **Dispatch note:** This is a MERGE-2 grouped auditor. It dispatches as a parallel wave via `parallel_dispatch.py` (invoked at `chapter_loop.py:1090-1168`), preserving the existing two-wave parallel dispatch model. Do NOT run the four dimensions serially.

## Contract

```yaml
contract:
  reads:
    - {file: chapters/chapter-N.md}
    - {file: characters/protagonist.md}
    - {file: characters/major/*.md}
    - {file: truth/character_matrix.md}
    - {file: truth/emotional_arcs.md}
    - {file: truth/current_state.md}
    - {file: genre-config.json, fields: [povMode]}
  writes: []
  updates:
    - audits/chapter-N-character.md
    - audits/chapter-N-dialogue.md
    - audits/chapter-N-motivation.md
    - audits/chapter-N-pov.md
```

## Evaluation Dimensions

Evaluate the provided chapter from four independent dimensions. Score each separately. Produce four independent audit report sections.

### Dimension 1: Character Consistency (OOC Detection)

This dimension supersedes the deprecated `shenbi-review-character` skill.

#### 铁律

1. **独立评分** -- 本 skill 产出评分/审核判断，必须在 context-cleaned 独立 subagent 执行
2. **OOC = blocking error** -- 角色行为违反已建立的性格/动机/声音，视为最高严重级别
3. **一人一卡** -- 每个角色的行为只能与其自身角色档案对比，不能交叉污染
4. **配角降智是致命毒点** -- 为推进剧情让反派/配角降智 = 必须修订
5. **声音指纹是读者的识别锚** -- 角色说话方式突变会让读者感到陌生

#### 检查执行

1. BDI 可信度评估（信念/欲望/意图三元组）
2. 声音一致性检查（口头禅、句式、措辞偏好）
3. 配角降智检测
4. 配角工具人化检测
5. 弧线平坦检测
6. 关系动态检查

#### 输出格式

```markdown
### FILE: audits/chapter-N-character.md

## 角色一致性审计报告

**章节**: 第N章
**结果**: 通过 / 有瑕疵 / 不通过

### BDI 评估
| 角色 | 信念 | 欲望 | 意图 | 一致性 |
|------|------|------|------|--------|
| ... | ... | ... | ... | PASS/WARNING |

### OOC 检测
| 角色 | 维度 | 违规行为 | 预期行为 | 严重度 |
|------|------|---------|---------|--------|
| ... | ... | ... | ... | error/warning |

### 配角检查
| 配角 | 降智? | 工具人? | 独立动机? |
|------|-------|---------|----------|
| ... | ... | ... | ... |

### 声音一致性
[口头禅匹配 / 句式复杂度 / 措辞偏好]

### 弧线
[近3章情感变化曲线]

### 评分: X/10 通过

### 建议修复
- [ERROR] [具体段落] [问题描述]：[修复方案]
```

---

### Dimension 2: Dialogue Style Consistency

This dimension supersedes the deprecated `shenbi-review-dialogue` skill.

#### 铁律

1. **声音指纹 = 角色身份证** -- 角色说话方式与 `voice_profile` 严重不符 = error
2. **口头禅必须出现或显式缺席** -- 标志口头禅每5-8章至少出现1次，长时间消失 = warning
3. **对话标签单调 = 写作偷懒** -- 连续5段以上使用同一种对话标签 = warning
4. **了字密度需符合角色** -- 文言角色了字密度应低于白话角色，违反 = warning

#### 检查执行

1. **对白提取与说话人归属**: 提取所有对白行，通过上下文判定说话人
2. **逐角色声音匹配**: 比对句长分布、词汇偏好、句式偏好与角色 `voice_profile`
3. **口头禅匹配**: 检索角色 `catchphrases` 是否在本章出现
4. **对话标签多样性**: 统计"说""道""问""答"等标签，检查连续重复
5. **了字密度**: 统计每角色对白中"了"字密度，与基线对比

#### 输出格式

```markdown
### FILE: audits/chapter-N-dialogue.md

## 对白审计报告

**章节**: 第N章
**结果**: 通过 / 有瑕疵 / 不通过

### 声音匹配
| 角色 | 句长偏差 | 词汇偏差 | 句式偏差 | 综合 | 严重度 |
|------|---------|---------|---------|------|--------|
| ... | ... | ... | ... | ... | ... |

### 口头禅
| 角色 | 口头禅 | 本章出现 | 距上次 | 状态 |
|------|-------|---------|-------|------|
| ... | ... | ... | ... | ... |

### 对话标签分布
| 标签 | 出现次数 | 最长连续 |
|------|---------|---------|
| ... | ... | ... |

### 了字密度
| 角色 | 密度 | 基线 | 偏差 | 严重度 |
|------|-----|-----|------|--------|
| ... | ... | ... | ... | ... |

### 评分: X/10 通过

### 建议修复
- [ERROR] [段落] [角色] [声音偏差]：[修复方案]
- [WARNING] [段落] [问题描述]：[修复方案]
```

---

### Dimension 3: Motivation and Behavior Chain

This dimension supersedes the deprecated `shenbi-review-motivation` skill.

#### 铁律

1. **无利益驱动 = 无缘无故** -- 角色行为若无自身利益/恐惧/欲望/信念支撑 = error
2. **动机必须可推导** -- 读者能从已建立信息中推导出角色当下的动机，不能 = error
3. **行为链 = 因果链** -- 角色行为A->后果B->应对C，链中任一环节缺失 = warning
4. **不得为推进剧情制造动机** -- 角色动机必须源于已有欲望/恐惧，不能因"剧情需要"临时生成

#### 检查执行

1. **角色行为抽取**: 列出所有角色的主动行为（非被动反应）
2. **利益驱动检查**: 对每个行为回答角色"为什么"这么做，答案必须落到利益/恐惧/欲望/信念之一
3. **动机可信度**: 检验动机是否可从读者已知信息中推导，不可推导 = error
4. **行为链完整性**: 追踪每个主动行为的因果链（触发事件->角色判断->行为选择->后果）
5. **反派与配角动机**: 反派行为需有自身合理利益，不能仅为主角对立而存在

#### 输出格式

```markdown
### FILE: audits/chapter-N-motivation.md

## 动机与行为链审计报告

**章节**: 第N章
**结果**: 通过 / 有瑕疵 / 不通过

### 利益驱动
| 角色 | 行为 | 驱动类型 | 档案匹配 | 严重度 |
|------|------|---------|---------|--------|
| ... | ... | ... | ... | ... |

### 动机可信度
| 角色 | 行为 | 可推导性 | 严重度 |
|------|------|---------|--------|
| ... | ... | ... | ... |

### 行为链完整性
| 角色 | 行为 | 因果链 | 缺失环节 | 严重度 |
|------|------|-------|---------|--------|
| ... | ... | ... | ... | ... |

### 评分: X/10 通过

### 建议修复
- [ERROR] [段落] [角色] [动机缺失/不可信]：[具体补足方案]
- [WARNING] [段落] [行为链缺失]：[补足哪个环节]
```

---

### Dimension 4: POV and Information Boundary

This dimension supersedes the deprecated `shenbi-review-pov` skill.

#### 铁律

1. **POV 切换必须有分隔** -- 视点角色转换无空行/分隔符/章节断 = error
2. **信息边界 = 物理定律** -- 角色引用未在自己 POV 范围内获取的信息 = error
3. **感官边界不可逾越** -- 视点角色描述自己不在场/未目睹/未听见的事件 = error
4. **心理边界 = 密室** -- 视点角色展示他人内心独白 = error（全知模式除外）

#### 检查执行

1. **POV 模式识别**: 读取 `genre-config.json` 的 `povMode`（first-person/third-limited/third-omniscient/third-shifting）
2. **视点切换识别**: 提取每段视点角色，标注切换位置，third-shifting 模式章内切换 > 3 = warning
3. **切换过渡质量**: 检查每次切换是否有过渡（空行/小标题/视觉锚点）
4. **信息边界**: 验证"X知道Y"类陈述中X获取Y的渠道
5. **感官边界**: 视点角色描述的事件是否在该角色在场时空中

#### 输出格式

```markdown
### FILE: audits/chapter-N-pov.md

## 视点与信息边界审计报告

**章节**: 第N章
**POV 模式**: third-limited
**结果**: 通过 / 有瑕疵 / 不通过

### POV 切换
| 位置 | 从 -> 到 | 过渡方式 | 严重度 |
|------|--------|---------|--------|
| ... | ... | ... | ... |

### 信息边界
| 段落 | 角色 | 引用信息 | 获取渠道 | 严重度 |
|------|------|---------|---------|--------|
| ... | ... | ... | ... | ... |

### 感官边界
| 段落 | 角色 | 描述 | 是否在场 | 严重度 |
|------|------|------|---------|--------|
| ... | ... | ... | ... | ... |

### 评分: X/10 通过

### 建议修复
- [ERROR] [段落] [POV/信息/感官] [问题描述]：[修复方案]
```

## 缺陷证据格式

All four dimensions use the standard defect evidence format. Each defect report MUST follow the four-element format:

1. **位置** -- `文件路径` L行号-行号（如 `chapters/chapter-5.md` L23-27）
2. **原文引述** -- 用 `>` 标记引述原文，>=20 字上下文
3. **违反规则** -- 引用 SKILL.md 中的精确规则名（逐字匹配）
4. **严重度** -- BLOCKING | CRITICAL | MINOR

缺失任一要素的缺陷报告视为不合格。

## Anti-Rationalization

| Excuse | Reality |
|--------|---------|
| "配角降智是为剧情服务" | 配角降智是网文最大毒点之一，读者会直接弃书 |
| "声音差异不大，读者听不出" | 角色声音是读者识别角色的锚，相似声音 = 角色模糊 |
| "角色为剧情牺牲是合理的" | 角色是故事主人，剧情为角色服务 |
| "口头禅偶尔不出现没关系" | 口头禅是角色识别锚，消失 = 角色模糊 |
| "POV切换可以加快节奏" | 无过渡的切换 = 节奏断裂 |
| "信息泄漏只是叙事便利" | 信息泄漏 = 后续剧情可信度归零 |
