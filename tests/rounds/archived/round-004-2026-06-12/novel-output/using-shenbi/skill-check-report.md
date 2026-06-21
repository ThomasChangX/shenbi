---
skill: using-shenbi
test_type: generative
test_round: round-004
---
# Using Shenbi: 技能路由报告

**分析时间**: 2026-06-12
**请求数**: 20
**覆盖类别**: 小说创建、章节写作、审计、修订、管理、导入、短篇、市场研究、边界案例
**适用技能数**: 涉及 20+ 个 shenbi 技能

---

## 请求 1: "我要写一本玄幻小说"

**分类**: 小说创建
**1%规则**: 适用（99%概率涉及到创建/规划技能）
**Red Flag**: "I know what they want" and "I'll just start writing" → 必须先检查技能

**技能路由**:
- `shenbi-worldbuilding` — 世界观创建
- `shenbi-character-design` — 角色设计
- `shenbi-story-architecture` — 故事框架
- `shenbi-genre-config` — 题材配置

**检查顺序**: creation skills → planning skills
**HARD-GATE**: 在 `novel.json`, `outline/story_frame.md`, `characters/protagonist.md` 存在之前，不得开始写章节

**路由结果**: 加载 `shenbi-worldbuilding` → 创建 novel.json 和世界规则 → 加载 `shenbi-character-design` → 加载 `shenbi-story-architecture`

---

## 请求 2: "帮我设计几个主要角色"

**分类**: 角色创建
**1%规则**: 适用

**技能路由**:
- `shenbi-character-design` — 主角+配角设计
- `shenbi-relationship-map` — 角色关系矩阵（依赖触发："关系"/"角色关系"）
- `shenbi-faction-builder` — 如果角色属于组织/势力（条件触发）

**路由结果**: 加载 `shenbi-character-design` → 输出角色档案 → 若角色间存在复杂关系网，加载 `shenbi-relationship-map`

---

## 请求 3: "写下一章"（项目已有 novel.json + story_frame.md + protagonist.md）

**分类**: 章节写作
**1%规则**: 适用

**技能路由**:
- `shenbi-chapter-planning` — 章节规划（先决条件）
- `shenbi-context-composing` — 上下文组装
- `shenbi-chapter-drafting` — 正文起草
- `shenbi-state-settling` — 状态结算（章节后）

**HARD-GATE 检查**:
- [x] `novel.json` 存在 ✓
- [x] `outline/story_frame.md` 存在 ✓
- [x] `characters/protagonist.md` 存在 ✓
- [ ] `plans/chapter-N-plan.md` 存在 — **必须先生成**

**Red Flag**: "I'll just start writing" → 写作前必须有 chapter plan

**路由结果**: 加载 `shenbi-chapter-planning` → `shenbi-context-composing` → `shenbi-chapter-drafting` → `shenbi-state-settling`

---

## 请求 4: "写下一章"（项目仅存在 novel.json，无 story_frame.md）

**分类**: 章节写作（前置条件不满足）
**1%规则**: 适用

**HARD-GATE 检查**:
- [x] `novel.json` 存在 ✓
- [ ] `outline/story_frame.md` 存在 ✗ → **HARD-GATE 阻挡**
- [ ] `characters/protagonist.md` 存在 ✗

**Red Flag**: "I'll just start writing" → **HARD-GATE 阻拦**

**路由结果**: 拒绝直接写作。加载 `shenbi-story-architecture` 和 `shenbi-character-design` 先创建基础文件。回复人类合作者："在开始写章节之前，需要先完成故事框架和主角档案。我先启动 shenbi-story-architecture 来建立三幕结构。"

---

## 请求 5: "检查这章有没有AI味"

**分类**: 审计
**1%规则**: 适用

**技能路由**:
- `shenbi-review-anti-ai` — 默认审计，每次自动运行
- 依据 `genre-config.json` 中的 `auditDimensions` 决定是否同时运行其他审计

**默认审计激活**（始终运行）:
- `shenbi-review-anti-ai`
- `shenbi-review-continuity`
- `shenbi-review-character`
- `shenbi-review-sensitivity`

**路由结果**: 加载 `shenbi-review-anti-ai` + 默认审计套件 → 输出审计报告

---

## 请求 6: "检查角色一致性，主角好像人设崩了"

**分类**: 审计（角色一致性）
**1%规则**: 适用

**技能路由**:
- `shenbi-review-character` — 主要匹配（"角色一致性"/"人设崩了"/"OOC"）
- `shenbi-review-continuity` — 作为默认审计同时运行
- `shenbi-drift-guidance` — 如果发现偏差，生成纠偏指导（"纠偏"/"下一章注意"）

**路由结果**: 加载 `shenbi-review-character` → 对比当前章节与角色档案 → 如发现偏差，加载 `shenbi-drift-guidance` → 输出纠偏建议

---

## 请求 7: "修改这章，节奏太拖了"

**分类**: 修订
**1%规则**: 适用

**技能路由**:
- `shenbi-chapter-revision` — 章节修订（"修改这章"/"修订"）
- `shenbi-review-pacing` — 节奏审计先行（"节奏不对"/"太拖"）
- `shenbi-pacing-design` — 若节奏原则文件不存在，先生成（"节奏设计"）

**路由结果**: 加载 `shenbi-review-pacing`（诊断当前问题）→ 加载 `shenbi-chapter-revision`（执行修改）→ 可能需要先确认 `outline/rhythm_principles.md` 存在

---

## 请求 8: "这章字数不够，需要扩写到5000字"

**分类**: 修订（字数调整）
**1%规则**: 适用

**技能路由**:
- `shenbi-length-normalizing` — 字数调整/扩写/压缩

**路由结果**: 加载 `shenbi-length-normalizing` → 分析当前字数 → 执行扩写操作

---

## 请求 9: "更新世界状态，刚结算完第5章"

**分类**: 管理
**1%规则**: 适用

**技能路由**:
- `shenbi-state-settling` — 状态结算
- `shenbi-truth-sync` — 同步 truth 文件（"同步状态"/"重新提取"）
- `shenbi-volume-consolidation` — 若第5章为卷末（"卷完成"/"卷总结"）

**路由结果**: 加载 `shenbi-state-settling` → 更新 `truth/current_state.md`, `truth/chapter_summaries.md`, `truth/emotional_arcs.md` → 加载 `shenbi-truth-sync`（确保所有 truth 文件一致）

---

## 请求 10: "把鲁迅的《狂人日记》导入，分析风格"

**分类**: 导入
**1%规则**: 适用

**技能路由**:
- `shenbi-import-analysis` — 分析已有作品（"导入"/"分析已有作品"）
- `shenbi-style-learning` — 风格学习（"文风"/"风格学习"）
- `shenbi-character-extraction` — 提取角色（"提取角色"/"反推角色"）
- `shenbi-world-extraction` — 提取世界观（"提取世界"/"反推世界"）

**路由结果**: 加载 `shenbi-import-analysis`（整体分析结构）→ 加载 `shenbi-style-learning`（统计风格指纹）→ 如需要角色信息，加载 `shenbi-character-extraction`

---

## 请求 11: "导入《三体》作为同人原作基础"

**分类**: 导入（同人）
**1%规则**: 适用

**技能路由**:
- `shenbi-canon-import` — 原作导入（"原作导入"/"同人原作"）
- `shenbi-character-extraction` — 提取原有角色
- `shenbi-world-extraction` — 提取原有世界观
- `shenbi-review-fanfic` — 同人一致性审计（后续写作时激活）

**路由结果**: 加载 `shenbi-canon-import` → `shenbi-character-extraction` + `shenbi-world-extraction` → 建立 canon 基线 → 标记 `shenbi-review-fanfic` 为后续写作的默认审计

---

## 请求 12: "写一个5000字短篇，主题是AI觉醒"

**分类**: 短篇
**1%规则**: 适用

**技能路由**:
- `shenbi-short-outline` — 短篇大纲（"短篇"）
- `shenbi-short-drafting` — 短篇写作（"批量写短篇"/"短篇写作"）
- `shenbi-short-packaging` — 短篇包装（"短篇包装"/"短篇上架"）

**路由结果**: 加载 `shenbi-short-outline` → 输出短篇大纲 → 加载 `shenbi-short-drafting` → 起草5000字短篇 → 如需发布，加载 `shenbi-short-packaging`

---

## 请求 13: "批量写10个短篇，每个3000字"

**分类**: 短篇（批量）
**1%规则**: 适用

**技能路由**:
- `shenbi-short-outline` — 先为每个短篇做大纲
- `shenbi-short-drafting` — 批量写作
- `shenbi-short-packaging` — 最终包装

**路由结果**: 加载 `shenbi-short-outline`（10次）→ 加载 `shenbi-short-drafting`（10次，顺序执行或使用 dispatching-parallel-agents 并行）→ `shenbi-short-packaging`

---

## 请求 14: "分析当前网文市场趋势，玄幻和都市哪个更火"

**分类**: 市场研究
**1%规则**: 适用

**技能路由**:
- `shenbi-market-radar` — 平台趋势/市场（"平台趋势"/"市场"）
- `shenbi-genre-config` — 如果决定改题材（"改题材配置"）

**路由结果**: 加载 `shenbi-market-radar` → 分析市场数据 → 输出趋势报告 → 如人类合作者决定切换题材，加载 `shenbi-genre-config`

---

## 请求 15: "续写我之前写的修真小说，停在主角渡劫失败那里"

**分类**: 续写
**1%规则**: 适用

**技能路由**:
- `shenbi-sequel-writing` — 续写（"续写"）
- `shenbi-import-analysis` — 先分析已有作品
- `shenbi-truth-sync` — 重建 truth 文件

**路由结果**: 加载 `shenbi-import-analysis`（分析已有章节）→ `shenbi-character-extraction`（重建角色档案）→ 加载 `shenbi-sequel-writing` → 从渡劫失败处续写

---

## 请求 16: "回滚到第5章完成后的状态，第6-10章写崩了"

**分类**: 管理（快照回滚）
**1%规则**: 适用

**技能路由**:
- `shenbi-snapshot-manage` — 回滚/快照（"回滚"/"快照"）

**路由结果**: 加载 `shenbi-snapshot-manage` → 列出可用快照 → 恢复到第5章完成后的快照 → 验证 truth 文件一致性

---

## 请求 17: "帮我计算一下最近10章的伏笔兑现率"

**分类**: 审计（伏笔）
**1%规则**: 适用

**技能路由**:
- `shenbi-foreshadowing-track` — 伏笔追踪（"伏笔追踪"/"hook状态"）
- `shenbi-foreshadowing-resolve` — 伏笔兑现（"伏笔兑现"/"收线"）

**路由结果**: 加载 `shenbi-foreshadowing-track`（扫描最近10章的伏笔状态）→ 计算兑现率 → 标记超期未兑现的伏笔 → 加载 `shenbi-foreshadowing-resolve`（处理到期伏笔）

---

## 请求 18: "把这章润色一下，文字太糙了"

**分类**: 修订（润色）
**1%规则**: 适用

**技能路由**:
- `shenbi-style-polishing` — 润色（"润色"/"打磨"/"文字"）
- `shenbi-anti-detect` — 如果润色后需要降低AI检测概率（"去AI味"/"反检测"）
- `shenbi-review-texture` — 质感审计（"质感"/"沉浸感"/"画面感"）

**路由结果**: 加载 `shenbi-style-polishing` → 参照 `style/style_profile.md` 进行统计导向润色 → 可选加载 `shenbi-anti-detect`

---

## 请求 19: "我是一个写小说的，想问问有什么好用的工具"（非小说写作任务）

**分类**: 边界案例 — 非小说写作任务
**1%规则**: 检查后不适用
**Red Flag**: "This is just a simple question about the novel" → 实际上这不是小说创作任务

**技能路由**:
- 先检查是否为小说写作任务 → **否**（这是一个关于写作工具的通用问题）
- 不触发 shenbi 技能
- 可以一般性回答

**路由结果**: 以普通助手模式回答。如果用户后续转向"帮我分析我的小说"，则重新触发技能检查。

---

## 请求 20: "我小说里有个角色说不清为什么这么做，帮我分析动机"

**分类**: 审计（动机分析）
**1%规则**: 适用

**技能路由**:
- `shenbi-review-motivation` — 动机审计（"动机不合理"/"为什么这么做"/"角色动机"）
- `shenbi-review-character` — 作为默认审计同时检查角色一致性
- `shenbi-intent-management` — 如果涉及作者长期意图（"作者意图"/"长期目标"）

**路由结果**: 加载 `shenbi-review-motivation` → 对比角色档案中的动机定义与当前行为 → 如人物设定中缺少独立动机，建议补充到角色档案 → 如涉及长期弧线，加载 `shenbi-intent-management`

---

## 综合路由统计

| 类别 | 请求数 | 主要触发技能 |
|------|--------|------------|
| 小说创建 | 1 | worldbuilding, character-design, story-architecture |
| 角色设计 | 1 | character-design, relationship-map |
| 章节写作 | 2 | chapter-planning, context-composing, chapter-drafting, state-settling |
| 审计 | 4 | review-anti-ai, review-character, review-motivation, foreshadowing-track |
| 修订 | 3 | chapter-revision, review-pacing, length-normalizing, style-polishing |
| 管理 | 3 | state-settling, truth-sync, snapshot-manage, volume-consolidation |
| 导入 | 2 | import-analysis, canon-import, character-extraction, style-learning |
| 短篇 | 2 | short-outline, short-drafting, short-packaging |
| 市场研究 | 1 | market-radar, genre-config |
| 边界案例 | 1 | 无 — 非小说写作任务 |

### HARD-GATE 触发情况

| 请求 | 触发 | 结果 |
|------|------|------|
| #3 写下一章（前置完备） | 检查通过 | 放行 |
| #4 写下一章（缺 story_frame） | **阻挡** | 拒绝，先加载 creation skills |

### Red Flag 检测

| 请求 | 触发 Red Flag | 处理 |
|------|-------------|------|
| #1 我要写玄幻小说 | "I know what they want" | 拒绝直接写，先检查创建技能 |
| #3 写下一章 | "I'll just start writing" | 确保 chapter plan 存在 |
| #19 非写作工具问题 | "This is just a simple question" | 确认非小说任务后正常回答 |

### 技能触发频率排名

1. `shenbi-state-settling` — 2次
2. `shenbi-chapter-planning` — 2次
3. `shenbi-review-character` — 2次
4. `shenbi-character-design` — 2次
5. `shenbi-style-learning` — 2次
6. `shenbi-character-extraction` — 2次
7. 其余18个技能各1次
