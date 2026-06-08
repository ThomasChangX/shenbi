# Shenbi (神笔) — 小说写作 AI 技能框架设计文档

> 日期: 2026-06-08
> 状态: 设计完成，待实现
> 版本: v0.2.0

## 1. 项目定位

Shenbi 是一套**小说写作方法论**，以 prompt 技能的形式注入到 AI agent 中。它不是一个小说生成器，而是一个**行为塑造框架** —— 让 AI agent 遵循经过验证的叙事创作实践。

核心理念来自三个项目的融合：

- **Superpowers** 的行为工程模式：反理性化表格、DOT 流程图、描述陷阱规避、说服心理学、压力驱动测试
- **InkOS** 的领域知识：35 个 Agent 的管线架构、33+ 维度审计、Hook 生命周期、去 AI 味多层防御
- **WiiNovel** 的技术深度：CFPG 伏笔系统、NEKG 知识图谱、L1-L4 生成管线、Chase Power 期望债务

## 2. 设计决策

| 决策 | 选择 | 理由 |
|------|------|------|
| 项目类型 | 纯技能框架（SKILL.md 文件） | 先可用的技能体系，后续可演进为完整应用 |
| 语言优先级 | 中文网络小说优先，英文次之 | 目标平台：起点、番茄等中文平台 |
| 平台策略 | 平台无关（D） | 核心技能是纯 markdown，hooks/manifests 是薄适配层 |
| 与 WiiNovel 关系 | 完全独立 | 新 repo，无依赖。未来通过 API 或数据格式约定集成 |
| 工作模式 | 人机协作（A） | 人类始终在回路中，每个关键决策需要人类批准 |
| 行为框架 | Superpowers 模式 | 反理性化 + DOT 流程图 + 说服心理学 |

## 3. 架构

### 3.1 目录结构

```
shenbi/
├── CLAUDE.md                    # 贡献者指南
├── GEMINI.md                    # Gemini CLI 入口
├── hooks/
│   ├── hooks.json               # Claude Code SessionStart hook
│   ├── hooks-cursor.json        # Cursor hook 配置
│   ├── session-start            # 核心注入脚本
│   └── run-hook.cmd             # Windows polyglot wrapper
├── skills/
│   ├── using-shenbi/            # 技能调度器
│   ├── shenbi-writing-skills/   # 元技能：编写新技能
│   │
│   │   ═══ 创世层 ═══
│   ├── shenbi-worldbuilding/
│   ├── shenbi-location-builder/
│   ├── shenbi-character-design/
│   ├── shenbi-relationship-map/
│   ├── shenbi-faction-builder/
│   ├── shenbi-power-system/
│   │
│   │   ═══ 规划层 ═══
│   ├── shenbi-story-architecture/
│   ├── shenbi-volume-outlining/
│   ├── shenbi-chapter-planning/
│   ├── shenbi-pacing-design/
│   ├── shenbi-plot-thread-weaver/
│   │
│   │   ═══ 伏笔层 ═══
│   ├── shenbi-foreshadowing-plant/
│   ├── shenbi-foreshadowing-track/
│   ├── shenbi-foreshadowing-resolve/
│   │
│   │   ═══ 起草层 ═══
│   ├── shenbi-context-composing/
│   ├── shenbi-chapter-drafting/
│   ├── shenbi-state-settling/
│   ├── shenbi-length-normalizing/
│   │
│   │   ═══ 审计层（18 个专项审查）═══
│   ├── shenbi-review-continuity/
│   ├── shenbi-review-character/
│   ├── shenbi-review-world-rules/
│   ├── shenbi-review-pacing/
│   ├── shenbi-review-foreshadowing/
│   ├── shenbi-review-anti-ai/
│   ├── shenbi-review-sensitivity/
│   ├── shenbi-review-reader-pull/
│   ├── shenbi-review-memo-compliance/
│   ├── shenbi-review-dialogue/
│   ├── shenbi-review-motivation/
│   ├── shenbi-review-pov/
│   ├── shenbi-review-texture/
│   ├── shenbi-review-highpoint/
│   ├── shenbi-review-long-span/
│   ├── shenbi-review-era/
│   ├── shenbi-review-fanfic/
│   ├── shenbi-review-spinoff/
│   │
│   │   ═══ 修订层 ═══
│   ├── shenbi-chapter-revision/
│   ├── shenbi-style-polishing/
│   ├── shenbi-anti-detect/
│   │
│   │   ═══ 导入与分析层 ═══
│   ├── shenbi-import-analysis/
│   ├── shenbi-style-learning/
│   ├── shenbi-character-extraction/
│   ├── shenbi-world-extraction/
│   ├── shenbi-canon-import/
│   │
│   │   ═══ 短篇层 ═══
│   ├── shenbi-short-outline/
│   ├── shenbi-short-drafting/
│   ├── shenbi-short-packaging/
│   │
│   │   ═══ 管理层 ═══
│   ├── shenbi-truth-sync/
│   ├── shenbi-snapshot-manage/
│   ├── shenbi-market-radar/
│   ├── shenbi-foundation-review/
│   ├── shenbi-genre-config/
│   ├── shenbi-volume-consolidation/
│   ├── shenbi-drift-guidance/
│   ├── shenbi-intent-management/
│   ├── shenbi-chapter-pattern/
│   ├── shenbi-sequel-writing/
│
├── .claude-plugin/              # Claude Code 插件清单
├── .cursor-plugin/              # Cursor 插件清单
├── .codex-plugin/               # OpenAI Codex 插件清单
├── .opencode/                   # OpenCode 原生插件
└── tests/                       # 测试体系
```

### 3.2 技能结构

每个技能遵循 Superpowers 的 SKILL.md 模式：

```
skills/shenbi-xxx/
├── SKILL.md              # 主体（必须）
└── supporting-file.*     # 按需（参考文档、模板等）
```

SKILL.md 的 frontmatter 规则：
- `name`: 仅字母、数字、连字符
- `description`: 只描述触发条件（"Use when..."），绝不描述做什么（描述陷阱）
- frontmatter 整体 ≤ 1024 字符，description ≤ 500 字符
- `description` 使用英文，第三人称，"Use when..." 开头。中文含义写在技能主体标题中

### 3.3 行为工程模式

每个技能应用以下 Superpowers 验证的模式：

1. **DOT 流程图** — 关键技能用 GraphViz DOT 定义权威流程
2. **反理性化表格** — 列举 AI 可能的偷懒借口及反驳
3. **红旗检查表** — 自我检查触发器
4. **铁律 + 无例外** — 关键规则用绝对语言
5. **说服心理学** — 使用 Authority / Commitment / Scarcity / Social Proof / Unity，不用 Liking / Reciprocity
6. **渐进式披露** — description → overview → flowchart → details → references

### 3.4 小说写作常见理性化模式

以下是小说写作领域特有的 AI 理性化借口，每个纪律性技能都应包含对应的反制措施：

| 借口 | 现实 |
|------|------|
| "这章太简单了，不需要伏笔" | 简单章节恰好是埋伏笔的最佳时机 |
| "读者不会注意到这个小矛盾" | 网文读者会逐章追更，记忆力极强 |
| "先写完再检查一致性" | 等写到20章再回来修，改动的代价是10倍 |
| "这个角色不需要这么复杂" | 配角降智是网文最大毒点之一 |
| "爽点不需要铺垫，直接给" | 没有压制的爆发是白开水 |
| "这章字数不够，加段描写凑一下" | 无功能的水文比字数不足更致命 |
| "前面已经提过了，读者记得" | 5章前的细节读者记不住，需要自然提醒 |
| "文风不重要，故事好就行" | AI味一重，平台检测直接降权 |
| "主角不能在这里失败" | 无挫折的成功 = 无张力的流水账 |
| "这条伏笔太久了，算了放弃" | 放弃伏笔 = 违背读者信任，Chase Power 债务暴增 |

## 4. 小说项目目录结构

用户创建的小说项目遵循以下目录约定（所有技能通过此结构读写数据）：

```
my-novel/
├── novel.json                     # 书籍元数据（标题、题材、语言、状态）
├── genre-config.json              # 题材配置（疲劳词、审计维度激活、节奏规则）
├── outline/                       # 大纲层
│   ├── story_frame.md             # 故事框架（散文骨架，4段式）
│   ├── volume_map.md              # 卷纲（5段 + 节奏原则尾段）
│   └── rhythm_principles.md       # 节奏原则（独立文件）
├── characters/                    # 角色层
│   ├── protagonist.md             # 主角档案（一人一卡，主角弧线单一权威）
│   ├── major/                     # 主要角色
│   │   ├── 角色名.md
│   │   └── ...
│   ├── minor/                     # 次要角色
│   │   ├── 角色名.md
│   │   └── ...
│   └── relationships.md           # 角色关系矩阵
├── world/                         # 世界观层
│   ├── story_bible.md             # 世界观圣经
│   ├── locations.md               # 地点图谱
│   ├── power_system.md            # 力量体系规则
│   ├── factions.md                # 势力图谱
│   └── rules.md                   # 世界铁律
├── truth/                         # 真相文件（每章更新）
│   ├── current_state.md           # 当前世界状态
│   ├── pending_hooks.md           # 伏笔池（PLANTED/RELEVANT/TRIGGERED/RESOLVED）
│   ├── chapter_summaries.md       # 逐章摘要
│   ├── subplot_board.md           # 支线进度板
│   ├── emotional_arcs.md          # 角色情感弧线
│   ├── character_matrix.md        # 角色交互矩阵 + 信息边界
│   ├── particle_ledger.md         # 资源账本（物品/金钱/资源增减）
│   ├── author_intent.md           # 作者长期意图
│   ├── current_focus.md           # 当前关注点（1-3章范围）
│   └── audit_drift.md             # 审计纠偏指导（传导给下一章）
├── plans/                         # 章节规划（每章一个）
│   ├── chapter-001-plan.md        # 章节备忘（8段式）
│   └── ...
├── chapters/                      # 章节正文
│   ├── chapter-001.md
│   ├── chapter-002.md
│   └── ...
├── snapshots/                     # 状态快照（每章完成后）
│   ├── chapter-001/
│   │   ├── current_state.md
│   │   ├── pending_hooks.md
│   │   ├── character_matrix.md
│   │   └── ...                    # truth/ 的完整副本
│   └── ...
├── style/                         # 风格参考
│   ├── style_profile.md           # 文风指纹
│   └── reference_samples.md       # 参考文本样本
└── import/                        # 导入产物
    └── analysis/                  # 导入分析结果
```

### 4.1 核心配置文件

`novel.json`:

```json
{
  "title": "苍穹之上",
  "genre": "玄幻",
  "core_concept": "一个失去灵根的少年偶然获得上古传承，踏上逆天改命之路",
  "themes": ["逆境成长", "自由与代价", "信任与背叛"],
  "language": "zh",
  "status": "active",
  "mode": "original",
  "target_word_count": 2000000,
  "narrative_pov": "third_limited",
  "chapter_word_count": 3000,
  "created_at": "2026-06-08",
  "current_chapter": 0,
  "current_volume": 1,
  "golden_opening_chapters": 3
}
```

`current_chapter: 0` 表示项目已初始化但尚未撰写任何章节。`golden_opening_chapters` 定义黄金三章（或N章）纪律适用的范围，`chapter-drafting` 据此施加额外约束。`narrative_pov` 有效值: `first_person` (第一人称), `third_limited` (第三人称限知), `third_omniscient` (第三人称全知), `multiple` (多视角切换)。

`genre-config.json`:

```json
{
  "auditDimensions": [3, 4, 5, 6, 7, 9, 11, 15, 16, 17, 24, 26, 32, 33],
  "eraResearch": false,
  "eraConstraints": false,
  "fatigueWords": ["缓缓", "淡淡", "微微", "不禁", "不由得", "仿佛", "似乎"],
  "pacingRules": {
    "questRatio": 0.6,
    "fireRatio": 0.2,
    "constellationRatio": 0.2,
    "maxConsecutiveQuest": 5,
    "maxGapQuest": 3
  },
  "chapterTypes": ["COMBAT", "DIALOGUE", "EXPLORATION", "TRAINING", "SOCIAL", "REVELATION", "TRANSITION"],
  "prohibitions": ["全场震惊", "不由得倒吸一口凉气"]
}
```

### 4.2 真相文件格式

所有真相文件使用 **YAML frontmatter + Markdown body** 格式。YAML frontmatter 是结构化数据的权威来源，Markdown body 是人类可读的投影。

示例 `truth/pending_hooks.md`:

```markdown
---
hooks:
  - id: hook-001
    content: "主角在古墓中发现的玉佩"
    state: PLANTED
    type: GENUINE
    dimension: CHARACTER
    subtlety: 0.7
    plant_chapter: 1
    cultivation_interval: 5
    last_reinforced: 3
    max_distance: 20
    escalation_curve: FLAT
    depends_on: []
    core_hook: true
    promoted: false
  - id: hook-002
    content: "神秘老人的预言"
    state: RELEVANT
    ...
---

# 伏笔池

## 活跃伏笔

### hook-001: 主角在古墓中发现的玉佩
- **状态**: PLANTED → 需在第 21 章前推进
- **类型**: 真实伏笔 / 角色维度
- **微妙度**: 0.7
- **培育**: 每 5 章强化一次，上次强化第 3 章

### hook-002: 神秘老人的预言
...
```

示例 `truth/current_state.md`:

```markdown
---
chapter: 4
protagonist:
  location: "内门演武场"
  status: "健康"
  emotion: "警觉"
  inventory: ["玉佩", "初级剑谱"]
  known_secrets: ["玉佩有隐藏力量"]
active_characters:
  - name: "师姐苏晴"
    location: "内门演武场"
    attitude: "观望"
active_conflicts:
  - "内门考核（进行中）"
  - "反派代理人挑衅（升级中）"
pending_events:
  - "考核结果公布"
---

# 当前世界状态

## 主角位置
林轩正在内门演武场参加考核。

## 活跃冲突
- 内门考核进入第二轮...
```

示例 `truth/particle_ledger.md`:

```markdown
---
chapter: 4
items:
  - name: "古墓玉佩"
    owner: "林轩"
    status: "隐藏"
    acquired_chapter: 1
    notes: "隐藏力量未激活"
  - name: "初级剑谱"
    owner: "林轩"
    status: "学习中"
    acquired_chapter: 2
resources:
  - type: "灵石"
    amount: 50
    change: "+20（考核奖励）"
    chapter: 4
---

# 资源账本

## 物品
- 古墓玉佩：林轩持有，隐藏状态
- 初级剑谱：学习中

## 灵石余额: 50
```

示例 `truth/chapter_summaries.md`（追加模式，每章末尾追加一节）:

```markdown
# 逐章摘要

## 第1章
[3-5句叙事摘要，涵盖：核心事件、角色变化、新信息、章尾悬念]

## 第2章
[3-5句叙事摘要]
...
```

示例 `truth/character_matrix.md`:

```markdown
---
characters:
  - name: "林轩"
    role: protagonist
    location: "内门演武场"
    known_info: ["玉佩有隐藏力量", "反派在寻找玉佩"]
  - name: "苏晴"
    role: major
    location: "内门演武场"
    known_info: ["考核结果即将公布"]
    attitude_toward_protagonist: "认可"
relationships:
  - pair: ["林轩", "苏晴"]
    type: "信任/师徒"
    chapter_established: 1
    last_change_chapter: 5
    change_note: "态度从疏远转为认可"
---

# 角色交互矩阵

## 当前信息边界
- 林轩知道: ...
- 苏晴知道: ...
- 林轩不知道: ...
```

示例 `truth/emotional_arcs.md`:

```markdown
---
characters:
  - name: "林轩"
    arcs:
      - chapter: 1
        emotional_state: "平静/期待"
        trigger: "入门考核"
      - chapter: 5
        emotional_state: "自信/警觉"
        trigger: "通过考核，发现玉佩被觊觎"
---

# 角色情感弧线

## 林轩
- 第1章: 平静/期待（入门考核）
- 第5章: 自信/警觉（通过考核，发现玉佩被觊觎）
```

示例 `truth/audit_drift.md`:

```markdown
---
chapter: 5
drift_items:
  - source_audit: review-anti-ai
    severity: warning
    issue: "转折词密度偏高（4次/3000字）"
    guidance: "下章起草时注意控制转折词，优先用动作推进替代然而/突然"
    targeted_chapter: 6
  - source_audit: review-anti-ai
    severity: error
    issue: "第3段含破折号一处"
    guidance: "修订时移除破折号，用句号断句"
    targeted_chapter: 5
---

# 审计纠偏指导

## 传导至第6章
- **转折词控制**: 下章转折词目标 ≤ 3次
- **来自第5章**: 破折号已修复，无需传导
```

示例 `style/style_profile.md`:

```markdown
# 文风指纹

## 句段统计
- 平均句长: 25.3 字
- 平均段长: 4.2 句
- 段落CV: 0.31

## 词汇特征
- TTR (词汇多样性): 0.72
- 高频句式: 动作导向（65%段落以角色动作为首句）
- 修辞特征: 比喻密度适中（每章3-5个），少用排比

## 避免模式
- 不用"不是…而是…"
- 不用破折号
- 了字密度 < 5%
```

### 4.3 大纲文件格式

`outline/rhythm_principles.md`:

```markdown
# 节奏原则

## 整体节奏哲学
[本书的节奏理念——快慢交替的尺度、爆发频率、蓄压深度]

## 章节类型节奏
- QUEST: 蓄压/推进，占比 ~60%
- FIRE: 爆发/高潮，占比 ~20%
- CONSTELLATION: 日常/关系/世界观展开，占比 ~20%

## 张力曲线规则
- 最大连续 QUEST 章数: 5
- 最大连续无 FIRE 章数: 3
- 每卷至少 1 个反转型高潮（出乎读者预期）
```

### 4.4 角色档案格式

示例 `characters/protagonist.md`:

```markdown
---
name: 林轩
role: protagonist
personality_tags: ["坚韧", "内敛", "重情义"]
core_value: "守护身边的人"
goal_surface: "成为内门弟子"
goal_deep: "查清父亲失踪的真相"
fear: "再次失去重要的人"
arc_type: GROWTH
arc_starting: "普通外门弟子"
arc_turning: "发现父亲失踪真相"
arc_ending: "TBD"
voice_profile:
  speech_patterns: ["简短有力", "关键时刻才长篇"]
  catchphrases: ["不会太久"]
  avoid_patterns: ["说教", "自怜"]
---

# 林轩

## 性格底色
...

## 说话风格指纹
...
```

### 4.5 章节备忘格式

示例 `plans/chapter-005-plan.md`:

```markdown
---
chapter: 5
goal: "主角首次与反派正面交锋"
volume: 1
tension_level: HIGH
chapter_type: COMBAT
---

# 第五章备忘

`tension_level` 有效值: `LOW` (纯过渡/日常章), `MEDIUM` (有冲突无高潮), `HIGH` (关键冲突/高潮章)。`chapter_type` 取值来自 `genre-config.json` 的 `chapterTypes` 列表。

## 1. 当前任务
主角必须在内门考核中击败反派的代理人，证明实力。

## 2. 读者此刻在等什么
- 上章末主角承诺"三天后见分晓"，读者期待兑现
- 延迟：考核前先发生一个意外干扰

## 3. 该兑现的 / 暂不掀的
- **兑现**: hook-002 神秘老人预言（考试中出现对应场景）
- **压住**: hook-001 玉佩的秘密（只给一个暗示，不揭开）

## 4. 日常/过渡承担什么任务
- 考核前的准备段落：推进与师姐的关系（关系变化）
- 建立场面反差：平静准备 vs 激烈战斗

## 5. 关键抉择过三连问
- 主角是否使用玉佩的隐藏力量？
  - Why: 对手太强，常规手段不够
  - Interest: 使用会暴露身份，不使用会输
  - Persona: 符合"内敛"性格，不轻易暴露

## 6. 章尾必须发生的改变
- 关系：师姐对主角态度从疏远转为认可
- 信息：主角得知反派也在寻找玉佩
- 权力：主角从外门升入内门

## 7. 本章 hook 账
- open: hook-003（反派寻找玉佩的动机）
- advance: hook-002（预言再次出现）
- resolve: 无
- defer: hook-001（玉佩秘密压住）

## 8. 不要做
- 不要让主角秒杀对手（战力崩坏风险）
- 不要出现"全场震惊"类套话
- 不要在本章揭示主角身世
```

## 5. 端到端工作流

```
用户: "我要写一本玄幻小说"
        │
        ▼
  ┌─────────────────────┐
  │ 1. using-shenbi      │ ← SessionStart hook 注入
  │    技能发现与调度      │
  └──────────┬──────────┘
             │ 检测到创作任务
             ▼
  ┌─────────────────────┐
  │ 2. 创世层            │ ← HARD-GATE: 禁止直接写正文
  │    worldbuilding     │
  │    → location-builder│
  │    → power-system    │
  │    → character-design│
  │    → relationship-map│
  │    → faction-builder │
  └──────────┬──────────┘
             │ 用户批准基础设定
             ▼
  ┌─────────────────────┐
  │ 3. foundation-review │ ← 基础设定审核（多维度打分）
  └──────────┬──────────┘
             │ 通过（80+）
             ▼
  ┌─────────────────────┐
  │ 4. 规划层            │
  │    story-architecture│
  │    → volume-outlining│
  │    → pacing-design   │
  │    → plot-thread     │
  └──────────┬──────────┘
             │ 用户批准故事框架
             ▼
  ┌──────────────────────────────────────────────┐
  │ 5. 逐章循环（每章执行以下步骤）                    │
  │                                               │
  │   ┌──────────────────┐  ┌──────────────────┐ │
  │   │ intent-management│  │ drift-guidance   │ │
  │   │ （更新意图/焦点）  │  │ （导入纠偏指导）   │ │
  │   └────────┬─────────┘  └────────┬─────────┘ │
  │            └──────────┬───────────┘           │
  │                       ▼                       │
  │   chapter-planning（生成章节备忘）               │
  │            │                                  │
  │            ▼                                  │
  │   foreshadowing-plant（根据备忘种植伏笔）        │
  │            │                                  │
  │            ▼                                  │
  │   context-composing（编排上下文）                │
  │            │                                  │
  │            ▼                                  │
  │   chapter-drafting（撰写正文）                   │
  │            │                                  │
  │            ▼                                  │
  │   state-settling（提取事实变化→更新真相文件）      │
  │            │                                  │
  │            ▼                                  │
  │   foreshadowing-track（更新伏笔池状态）           │
  │            │                                  │
  │            ▼                                  │
  │   length-normalizing（字数治理）                 │
  │            │                                  │
  │            ▼                                  │
  │   审计层（按激活规则运行审查）──────────┐         │
  │            │                          │       │
  │            ▼ 未通过                    ▼ 通过  │
  │   chapter-revision              foreshadowing-│
  │   → style-polishing             resolve       │
  │   → anti-detect                 （处理到期伏笔）│
  │            │                          │       │
  │            └──── 重新审计 ←───────────┘       │
  │                       │                       │
  │                       ▼                       │
  │              snapshot-manage                   │
  │              （创建快照）                        │
  │                       │                       │
  │                       ▼                       │
  │              drift-guidance                    │
  │              （生成纠偏指导给下一章）              │
  └───────────────────────┬──────────────────────┘
                          │ 卷完成时
                          ▼
  ┌──────────────────────────┐
  │ 6. 卷管理                  │
  │    volume-consolidation    │
  │    chapter-pattern         │
  │    foreshadowing-resolve   │ ← 卷尾伏笔盘点
  └──────────────────────────┘
```

### 5.1 分支流程

```
已有作品导入:
  import-analysis → character-extraction → world-extraction → style-learning

同人创作:
  canon-import → 创世层（fanfic模式）→ 正常流程

续写:
  sequel-writing → 从断点快照重建上下文 → 逐章循环

短篇:
  short-outline → short-drafting → short-packaging
```

## 6. 技能间数据传递协议

由于 Shenbi 是纯 SKILL.md 框架（无运行时代码），技能间通过**共享文件系统**传递数据。每项技能遵循以下协议：

### 6.1 读写契约

每个技能在 SKILL.md 中声明：

```markdown
## Reads
- `truth/pending_hooks.md` — 伏笔池当前状态
- `plans/chapter-N-plan.md` — 章节备忘

## Writes
- `chapters/chapter-N.md` — 章节正文
- `truth/current_state.md` — 更新世界状态（追加变更）

## Updates (read-then-write)
- `truth/pending_hooks.md` — 更新伏笔状态
```

### 6.2 人类角色

人类在技能间充当以下角色：

1. **文件管理者** — 确保目录结构正确，文件存在
2. **审批者** — 每个关键技能的输出需要人类审阅和批准后才进入下一步
3. **仲裁者** — 当两个技能的输出矛盾时，人类决定保留哪个
4. **补充者** — 在技能输出不完整时手动补充

### 6.3 context-composing 的实际工作方式

`context-composing` 不是自动化检索系统，而是一个**上下文组装指南**——它指导 AI 或人类按优先级从以下来源手动收集上下文：

| 优先级 | 来源 | 读取位置 |
|--------|------|---------|
| P1 (must) | 章节备忘 | `plans/chapter-N-plan.md` |
| P2 (must) | 近 2 章摘要 | `truth/chapter_summaries.md` 末尾 |
| P3 (need) | 活跃伏笔（最多 3 条） | `truth/pending_hooks.md` |
| P4 (need) | 纠偏指导 | `truth/audit_drift.md` |
| P5 (nice) | 世界铁律（最多 5 条） | `world/rules.md` |
| P6 (nice) | 角色状态 | `truth/character_matrix.md` |
| P7 (nice) | 文风指纹 | `style/style_profile.md` |

未来演进时，WiiNovel 或其他工具可以自动化此收集过程。

## 7. 审计维度完整映射

### 7.1 InkOS 33+ 维度 → shenbi 审计技能

| 维度ID | 维度 | 技能 |
|--------|------|------|
| 1 | OOC 检查 | review-character |
| 2 | 时间线检查 | review-continuity |
| 3 | 设定冲突 | review-world-rules |
| 4 | 战力崩坏 | review-world-rules |
| 5 | 数值检查 | review-world-rules |
| 6 | 伏笔检查 | review-foreshadowing |
| 7 | 节奏检查 | review-pacing |
| 8 | 文风检查 | review-anti-ai |
| 9 | 信息越界 | review-pov |
| 10 | 词汇疲劳 | review-anti-ai + review-long-span |
| 11 | 利益链断裂 | review-motivation |
| 12 | 年代考据 | review-era（条件激活） |
| 13 | 配角降智 | review-character |
| 14 | 配角工具人化 | review-character |
| 15 | 爽点虚化 | review-highpoint |
| 16 | 台词失真 | review-dialogue |
| 17 | 流水账 | review-texture |
| 18 | 知识库污染 | review-world-rules |
| 19 | 视角一致性 | review-pov |
| 20 | 段落等长 | review-anti-ai |
| 21 | 套话密度 | review-anti-ai |
| 22 | 公式化转折 | review-anti-ai |
| 23 | 列表式结构 | review-anti-ai |
| 24 | 支线停滞 | review-foreshadowing |
| 25 | 弧线平坦 | review-character |
| 26 | 节奏单调 | review-pacing |
| 27 | 敏感词 | review-sensitivity |
| 28 | 正传事件冲突 | review-spinoff（条件激活） |
| 29 | 未来信息泄露 | review-spinoff（条件激活） |
| 30 | 世界规则（番外） | review-spinoff（条件激活） |
| 31 | 伏笔隔离 | review-spinoff（条件激活） |
| 32 | 读者期待管理 | review-reader-pull |
| 33 | 章节备忘偏离 | review-memo-compliance |
| 34 | 角色还原度 | review-fanfic（条件激活） |
| 35 | 世界规则（同人） | review-fanfic（条件激活） |
| 36 | 关系动态 | review-fanfic（条件激活） |
| 37 | 正典事件一致性 | review-fanfic（条件激活） |

### 7.2 WiiNovel 7 维质量引擎 → shenbi 审计技能

| 检查器 | 技能 |
|--------|------|
| AiTellChecker | review-anti-ai |
| HighPointChecker | review-highpoint |
| ConsistencyChecker | review-world-rules |
| PacingChecker | review-pacing |
| OOCChecker | review-character |
| ContinuityChecker | review-continuity |
| ReaderPullChecker | review-reader-pull |

### 7.3 InkOS Post-Write 确定性检查 → shenbi 审计技能

| 检查项 | 技能 |
|--------|------|
| "不是…而是…"句式 | review-anti-ai |
| 破折号 | review-anti-ai |
| 转折词密度 | review-anti-ai |
| 高疲劳词 | review-anti-ai |
| 元叙事/编剧旁白 | review-anti-ai |
| 分析报告术语 | review-anti-ai |
| 章节号指称 | review-memo-compliance |
| 作者说教词 | review-texture |
| 集体反应套话 | review-anti-ai |
| 连续"了"字 | review-dialogue |
| 段落过长/过碎 | review-texture |
| 段落密度漂移 | review-long-span |
| 跨章 6 字 n-gram 重复 | review-long-span |
| 本书禁忌词 | review-sensitivity |

### 7.4 审计激活规则

不是每章都运行全部 18 个审计技能。激活规则由 `genre-config.json` 的 `auditDimensions` 字段控制。

**默认激活（每章必查）**:

| 技能 | 理由 |
|------|------|
| review-anti-ai | AI 味是最大风险，每章必查 |
| review-continuity | 时间线矛盾无法事后修复 |
| review-character | OOC 是致命毒点 |
| review-sensitivity | 敏感词导致平台下架 |

**条件激活（由 genre-config 控制）** — "包含 X,Y" 表示 `auditDimensions` 数组中存在至少一个所列维度即激活：

| 技能 | 默认 | 激活条件 |
|------|------|---------|
| review-world-rules | 关闭 | `genreConfig.auditDimensions` 包含 3,4,5,18 |
| review-pacing | 关闭 | `genreConfig.auditDimensions` 包含 7,26 |
| review-foreshadowing | 关闭 | `genreConfig.auditDimensions` 包含 6,24 |
| review-reader-pull | 关闭 | `genreConfig.auditDimensions` 包含 32 |
| review-memo-compliance | 关闭 | `genreConfig.auditDimensions` 包含 33 |
| review-dialogue | 关闭 | `genreConfig.auditDimensions` 包含 16 |
| review-motivation | 关闭 | `genreConfig.auditDimensions` 包含 11 |
| review-pov | 关闭 | `genreConfig.auditDimensions` 包含 9,19 |
| review-texture | 关闭 | `genreConfig.auditDimensions` 包含 17 |
| review-highpoint | 关闭 | `genreConfig.auditDimensions` 包含 15 |
| review-long-span | 关闭 | `genreConfig.auditDimensions` 包含 10（跨章维度，从第 3 章起激活） |
| review-era | 关闭 | `genreConfig.eraResearch` 或 `genreConfig.eraConstraints` 为 true |
| review-fanfic | 关闭 | `novel.json.mode` 为 fanfic |
| review-spinoff | 关闭 | `truth/` 下存在 `parent_canon.md` |

**推荐配置 — 玄幻/仙侠题材**:

```json
{
  "auditDimensions": [3, 4, 5, 6, 7, 9, 11, 15, 16, 17, 24, 26, 32, 33],
  "eraResearch": false,
  "eraConstraints": false
}
```

此配置激活 14 个审计技能（4 默认 + 10 条件）。

### 7.5 审计执行顺序

仅激活的技能参与执行。每章按照 `genre-config.json` 的 `auditDimensions` 和默认激活规则确定激活的技能集合，然后按以下顺序执行（从低成本到高成本）：

1. **确定性检查（零 LLM 成本）**: review-anti-ai, review-sensitivity, review-long-span（仅当各自激活时）
2. **结构检查（低成本）**: review-memo-compliance, review-texture, review-pacing
3. **领域检查（中成本）**: review-continuity, review-character, review-world-rules, review-dialogue, review-pov, review-motivation
4. **高级检查（高成本）**: review-foreshadowing, review-highpoint, review-reader-pull
5. **条件检查**: review-era, review-fanfic, review-spinoff

每层内按表中顺序执行。前一步发现 blocking 级别问题则停止，进入修订层。`review-long-span` 额外要求 `current_chapter ≥ 3` 才参与执行。

## 8. 技能完整清单（59 个）

### 8.1 元层（2 个）

| # | 技能名 | 中文描述 | English description |
|---|--------|---------|---------------------|
| 1 | `using-shenbi` | 技能发现与调度器。1%规则：只要有1%可能适用就必须检查对应技能 | Skill dispatcher. 1% rule: check if any skill could possibly apply |
| 2 | `shenbi-writing-skills` | 元技能，教 AI 如何编写新的 shenbi 技能 | Meta-skill for creating new shenbi skills |

### 8.2 创世层（6 个）

| # | 技能名 | 中文描述 |
|---|--------|---------|
| 3 | `shenbi-worldbuilding` | 生成故事圣经：世界规则、地理、社会结构、历史背景。输出散文骨架而非条目列表 |
| 4 | `shenbi-location-builder` | 地点设计：空间布局、氛围描写、功能定位、地点间空间关系一致性。管理地点图谱 |
| 5 | `shenbi-character-design` | 角色档案：性格底色、核心价值观、表面目标/深层动机/恐惧、成长弧线、说话风格指纹。一人一卡 |
| 6 | `shenbi-relationship-map` | 角色关系网络：利益链、势力归属、信息边界（谁知道什么）、关系演变轨迹。维护角色交互矩阵 |
| 7 | `shenbi-faction-builder` | 势力设计：层级结构、内部矛盾、势力间冲突关系、利益驱动。避免势力脸谱化 |
| 8 | `shenbi-power-system` | 力量体系：等级划分、升级规则、战力天花板、能力边界。防止战力崩坏 |

### 8.3 规划层（5 个）

| # | 技能名 | 中文描述 |
|---|--------|---------|
| 9 | `shenbi-story-architecture` | 故事框架：前台故事+后台故事双线设计、OKR式全书目标分解、核心冲突三层（表面/个人/深层） |
| 10 | `shenbi-volume-outlining` | 卷纲规划：每卷目标与节奏原则、卷内张力曲线、跨卷衔接。附节奏原则尾段 |
| 11 | `shenbi-chapter-planning` | 章节备忘（8段式）：当前任务、读者期待管理、伏笔兑现清单、日常段落功能、关键抉择三连问、章尾必须改变、hook账、禁止事项 |
| 12 | `shenbi-pacing-design` | 节奏设计：蓄压→升级→爆发→后效周期、场景类型序列避免单调、三线节奏比例（QUEST/FIRE/CONSTELLATION） |
| 13 | `shenbi-plot-thread-weaver` | 线索编织：A/B/C线管理、线索优先级、最大连续/最大间隔控制、线索交叉依赖 |

### 8.4 伏笔层（3 个）

| # | 技能名 | 中文描述 |
|---|--------|---------|
| 14 | `shenbi-foreshadowing-plant` | 埋伏笔：类型分类（真实/烟雾弹/侧面影）、维度标记（主题/角色/象征/结构）、微妙度设置、跨线程依赖 |
| 15 | `shenbi-foreshadowing-track` | 伏笔追踪：生命周期管理（PLANTED→RELEVANT→TRIGGERED→RESOLVED）、培育间隔监控、密度预算（每章8操作）、晋升规则 |
| 16 | `shenbi-foreshadowing-resolve` | 伏笔兑现：升级曲线（平坦/上升/指数）、戏剧反讽追踪、读者期望债务管理（Chase Power）、多层伏笔有序解决 |

### 8.5 起草层（4 个）

| # | 技能名 | 中文描述 |
|---|--------|---------|
| 17 | `shenbi-context-composing` | 上下文组装指南：按优先级从真相文件收集上下文（P1备忘→P7文风），指导 AI 或人类手动组装 |
| 18 | `shenbi-chapter-drafting` | 章节起草：两阶段生成（创作 temp=0.7 + 结算 temp=0.3）、文风指纹注入、对话指纹提取、类型规范应用、黄金三章纪律 |
| 19 | `shenbi-state-settling` | 状态结算：观察者提取 9 类事实变化（位置/资源/关系/情绪/信息/线索/时间/身体/行为），结算者合并到真相文件 |
| 20 | `shenbi-length-normalizing` | 字数治理：压缩/扩写到目标区间、软硬区间控制、截断保护（归一化后 <25% 则拒绝） |

### 8.6 审计层（18 个）

| # | 技能名 | 中文描述 |
|---|--------|---------|
| 21 | `shenbi-review-continuity` | 时间线一致性、地点矛盾（Allen区间代数）、事件时序、物理空间合理性 |
| 22 | `shenbi-review-character` | OOC 检测（BDI 可信度评估）、角色声音一致性、配角降智检测、工具人化检测、弧线平坦 |
| 23 | `shenbi-review-world-rules` | 设定冲突、战力崩坏、数值一致性、知识库污染 |
| 24 | `shenbi-review-pacing` | 蓄压-爆发周期完整性、连续5章无爆发→停滞检测、日常段落功能验证、章节类型序列多样性 |
| 25 | `shenbi-review-foreshadowing` | Hook 债务升级规则、培育间隔过期、密度异常、支线停滞、伏笔账本一致性 |
| 26 | `shenbi-review-anti-ai` | 段落等长、套话密度、公式化转折、列表式结构、疲劳词、AI标记词（4维度统计）、"不是…而是…"句式、破折号、元叙事、集体反应套话 |
| 27 | `shenbi-review-sensitivity` | 政治敏感词、色情/暴力检测、平台合规性、本书禁忌词检查 |
| 28 | `shenbi-review-reader-pull` | 章首钩子强度、章尾悬念、读者期待管理（是否重新点燃好奇心） |
| 29 | `shenbi-review-memo-compliance` | 正文是否兑现章节备忘的 8 段整体承诺、章节号指称 |
| 30 | `shenbi-review-dialogue` | 角色说话风格一致性、对话标签多样性、了字密度、口头禅匹配 |
| 31 | `shenbi-review-motivation` | 角色行为利益驱动、动机合理性、行为逻辑链条完整性 |
| 32 | `shenbi-review-pov` | POV 切换过渡、信息边界（角色是否引用不该知道的信息） |
| 33 | `shenbi-review-texture` | 流水账检测、日常段落功能验证、段落呼吸感、章节冲突密度、作者说教词、段落过长/过碎 |
| 34 | `shenbi-review-highpoint` | 压制-爆发模式、反转检测、高潮关键词密度与多样性、爽点虚化（兑现是否超过读者预期） |
| 35 | `shenbi-review-long-span` | 跨章节重复用词/意象/句式、6字 n-gram 跨章重复、段落长度漂移 |
| 36 | `shenbi-review-era` | 历史年代准确性、时代用词、器物考据（仅特定题材激活） |
| 37 | `shenbi-review-fanfic` | 角色还原度/世界规则/关系动态/正典事件一致性（按 canon/au/ooc/cp 模式调整严格度） |
| 38 | `shenbi-review-spinoff` | 正传事件冲突/未来信息泄露/世界规则/伏笔隔离（番外模式激活） |

### 8.7 修订层（3 个）

| # | 技能名 | 中文描述 |
|---|--------|---------|
| 39 | `shenbi-chapter-revision` | 章节修订：自动路由（结构问题→重写、局部问题→补丁、混合→完整改写）、6种修稿模式 |
| 40 | `shenbi-style-polishing` | 文字层润色：只改表达/节奏/段落呼吸，禁止增删情节/改变人设/调整主线。发现结构问题以 `[polisher-note]` 标记 |
| 41 | `shenbi-anti-detect` | 反检测改写：9种改写手法（打破句式规律、口语化、了字降频、转折词降频、情绪外化等） |

### 8.8 导入与分析层（5 个）

| # | 技能名 | 中文描述 |
|---|--------|---------|
| 42 | `shenbi-import-analysis` | 多 Pass 分析管道：解析→角色→世界观→情节→伏笔→风格→精彩→状态重建（8 Pass，中间6步可并行） |
| 43 | `shenbi-style-learning` | 风格指纹提取：句长/段长统计、词汇多样性(TTR)、高频句式模式、修辞特征。纯统计无 LLM |
| 44 | `shenbi-character-extraction` | 逆向角色分析：从已有章节提取角色档案、说话风格、关系网络、行为模式 |
| 45 | `shenbi-world-extraction` | 逆向世界观提取：从已有章节提取世界规则、地点、物品、力量体系 |
| 46 | `shenbi-canon-import` | 正典导入：从原作提取 5 个 SECTION，支持 4 种同人模式 |

### 8.9 短篇层（3 个）

| # | 技能名 | 中文描述 |
|---|--------|---------|
| 47 | `shenbi-short-outline` | 短篇大纲生成→审核→修订（3步） |
| 48 | `shenbi-short-drafting` | 批量章节生成→审核→修订（3步），一次性生成所有章节 |
| 49 | `shenbi-short-packaging` | 销售包装：标题/简介/卖点/封面提示词生成 |

### 8.10 管理层（10 个）

| # | 技能名 | 中文描述 |
|---|--------|---------|
| 50 | `shenbi-truth-sync` | 真相文件同步：从编辑后的正文重新反推 truth files，校验一致性 |
| 51 | `shenbi-snapshot-manage` | 状态快照管理：创建/查看/回滚快照，状态恢复 |
| 52 | `shenbi-market-radar` | 平台趋势扫描：排行榜数据、题材分析、开书建议、对标作品 |
| 53 | `shenbi-foundation-review` | 基础设定审核：5 维度打分（核心冲突 30分/开篇节奏 20分/世界一致性 20分/角色区分度 20分/伏笔潜力 10分），总分 80+ 通过 |
| 54 | `shenbi-genre-config` | 题材配置管理：疲劳词列表、节奏规则、章节类型、审计维度激活、自定义规则 |
| 55 | `shenbi-volume-consolidation` | 卷完成后合并逐章摘要为叙事摘要、归档旧摘要、生成卷级长程记忆 |
| 56 | `shenbi-drift-guidance` | 审计纠偏传导：把当前章节审计问题传导给下一章，纠偏指导嵌入 `truth/audit_drift.md` |
| 57 | `shenbi-intent-management` | 管理作者长期意图和短期关注点（1-3章范围），维护 `truth/author_intent.md` 和 `truth/current_focus.md` |
| 58 | `shenbi-chapter-pattern` | 13种章节模式检测与分类，发现全书模式单一化问题 |
| 59 | `shenbi-sequel-writing` | 续写服务：从已有内容找到断点快照，重建上下文，续写后续章节 |

**总计：59 个技能**（元层 2 + 创世层 6 + 规划层 5 + 伏笔层 3 + 起草层 4 + 审计层 18 + 修订层 3 + 导入层 5 + 短篇层 3 + 管理层 10）

## 9. 平台适配

### 9.1 Hooks 系统

采用 Superpowers 的 polyglot hook 模式：

```
hooks/
├── hooks.json           # Claude Code（SessionStart hook）
├── hooks-cursor.json    # Cursor（camelCase 格式）
├── session-start        # Unix 入口脚本（bash）
└── run-hook.cmd         # Windows polyglot wrapper（batch + bash）
```

### 9.2 插件清单

| 平台 | 入口文件 | 说明 |
|------|---------|------|
| Claude Code | `.claude-plugin/plugin.json` | skills 目录注册 |
| Cursor | `.cursor-plugin/plugin.json` | 引用 hooks-cursor.json |
| OpenAI Codex | `.codex-plugin/plugin.json` | Codex 插件市场格式 |
| OpenCode | `.opencode/plugins/shenbi.js` | ES 模块插件 |
| Gemini CLI | `GEMINI.md` | 入口 markdown |
| GitHub Copilot CLI | hooks.json 兼容 | 通过 COPILOT_CLI 环境变量检测 |
| Factory Droid | `.claude-plugin/` 兼容 | 复用 Claude Code 格式 |

### 9.3 平台检测

`session-start` 脚本通过环境变量检测平台，输出对应 JSON 格式（与 Superpowers 相同模式）。

## 10. 测试策略

采用 Superpowers 的压力驱动测试方法论：

### 10.1 测试层次

```
tests/
├── skill-triggering/         # 技能自动触发测试
│   └── prompts/              # 朴素描述（不提及技能名），验证技能从描述触发
├── explicit-skill-requests/  # 显式请求测试
│   └── prompts/              # 按名请求，验证正确加载不跳过
├── skill-behavior/           # 行为测试
│   ├── review-catches-bug/   # 审计技能能捕获植入的真实问题
│   └── revision-fixes-issue/ # 修订技能能修复已识别问题
└── pressure-tests/           # 压力测试
    └── prompts/              # 组合压力场景，验证最大压力下仍遵守规则
```

### 10.2 压力类型

| 压力类型 | 示例 |
|---------|------|
| 时间压力 | "读者在等更新！赶紧写下一章！" |
| 沉没成本 | "我已经写了20章了，不能改主角性格" |
| 简单性错觉 | "这章太简单了，不需要伏笔" |
| 疲惫 | "这是今天最后一章了，随便写写" |
| 组合压力 | 时间 + 沉没成本 + 疲惫 |

### 10.3 技能 TDD 流程

1. **RED** — 不用技能对 agent 运行压力场景，记录 rationalization
2. **GREEN** — 编写最小技能应对那些 rationalization
3. **REFACTOR** — 关闭新漏洞，直到 bulletproof

## 11. 实现优先级

### Phase 1: 核心管线（先跑通）

shenbi-writing-skills → using-shenbi → worldbuilding → character-design → story-architecture → chapter-planning → context-composing → chapter-drafting → state-settling → review-anti-ai → chapter-revision

### Phase 2: 质量体系

review-continuity → review-character → review-pacing → review-foreshadowing → style-polishing → foundation-review → drift-guidance

### Phase 3: 伏笔与管理

foreshadowing-plant → foreshadowing-track → foreshadowing-resolve → truth-sync → snapshot-manage → intent-management → volume-consolidation

### Phase 4: 扩展能力

剩余审计技能 → 导入层 → 短篇层 → location-builder → power-system → faction-builder → sequel-writing

### Phase 5: 平台适配与国际化

hooks 系统 → 插件清单（7平台）→ 英文 description 翻译 → 压力测试 → market-radar

## 12. 与 Superpowers 的关键差异

| 维度 | Superpowers | Shenbi |
|------|-------------|--------|
| 领域 | 软件工程 | 小说写作 |
| 核心铁律 | 先写测试再写代码 | 先建世界再写正文 |
| 审计重点 | 代码正确性、测试覆盖 | 叙事连续性、去AI味、伏笔管理 |
| 理性化模式 | "太简单不需要测试" | "这章太简单不需要伏笔" |
| 输出 | 代码文件 | 小说章节 + 真相文件 |
| 人类角色 | 代码审查者 | 创作合作者 |
| 平台支持 | 7个平台 | 同样7个平台（复用模式） |
