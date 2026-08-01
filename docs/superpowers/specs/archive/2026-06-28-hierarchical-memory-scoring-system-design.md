# 分层记忆与分层评分系统设计 (Hierarchical Memory & Scoring System)

> 日期: 2026-06-28
> 状态: 设计完成，待实现
> 版本: v1.4.0 (R1+R2+R3+R4: 设计修复 + 测试基建 + 集成接缝契约：10个运行时数据断裂点修复)
> 前置: docs/specs/2026-06-08-shenbi-design.md (原始框架), docs/superpowers/specs/2026-06-22-positive-quality-gates-design.md (正向质量门)

## 0. 背景与问题

Shenbi 框架当前在"防止写坏"上达到行业顶尖水平（33+审计维度、伏笔生命周期、多层反AI味），但存在三个根本性缺口：

1. **上下文长度不可扩展。** truth 文件扁平结构，`chapter_summaries.md` 到第3000章膨胀至60万字（200字/章 × 3000），`context-composing` 无法组装。框架无长程记忆压缩机制，千万字规模不可行。
2. **验证测的是合规而非质量。** 评分维度几乎全是结构合规指标，60% 分数塌缩到 95.0（评分通胀）。整个系统验证的是"对自身规则的合规性"而非"对外部文学标准的达标度"。
3. **生成-评分是开环。** 审计失败只能修工艺（AI味/OOC），修不了目标未达成。评分诊断不回流为本章重生的输入。

本设计通过四个子系统解决这三个缺口。

## 1. 设计目标

| 目标 | 衡量标准 |
|------|---------|
| 上下文与全书长度解耦 | 任何单章 skill 的上下文窗口大小有界（误差 ±20%），与全书总字数无关 |
| 评分锚定真实目标而非自证 | 章级对照卷目标、卷级对照书脊——从不自评同一层 |
| 评分有外部质量天花板 | route A 锚点库（诡秘之主+炮火弧线工艺分析）提供9类校准槽位 |
| 评分驱动优化（闭环） | 评分诊断结构化回流为重生/修订指令，本章失败的目标由本章重生修复 |
| 千万字规模可行 | 人工介入从每章6次降至异常升级时才出现 |

## 2. 核心设计决策

| 决策 | 选择 | 理由 |
|------|------|------|
| 记忆架构 | 路线3：分层蒸馏主干 + RAG辅助召回 | 蒸馏保证有界窗口，RAG解跨弧伏笔召回（见§3.6确定性处理） |
| 评分客观性 | route C（目标达成）主干 + route A（锚点校准）天花板 | C与"按目标优化"契合且二元/程度分列；A打破循环验证 |
| 评分载体 | 独立skill家族 | 职责清晰优先于skill数量精简 |
| 验证范围 | 全量，递进实证节点 | 不计成本，质量优先 |
| 审批模式 | 默认自动批 + 阻断级覆盖 + 升级触发 | 千万字 ≈ 3300章 × 6门禁 ≈ 2万决策点，全人工不可行 |

## 3. 子系统一：分层记忆架构

### 3.1 七层蒸馏树

```
L0 原文        chapters/chapter-N.md       ~3000字/章   不动
L1 章节拍点    truth/chapter_summaries.md  ~200字/章    现有，append-only
L2 弧段合成    truth/arcs/arc-N.md         ~1500字/弧   新增，每12章一篇（固定）
L3 卷摘要      truth/volume_summaries.md   ~2000字/卷   现有 volume-consolidation 扩展
L4 大弧层      truth/book_strata.md        ~3000字/大弧 新增，每36章一篇（固定，= 3个L2弧段）
L5 书脊        truth/book_spine.md         ~1页常青     新增，核心冲突/themes/主角弧/主线钩子
```

> **有界窗口的正确理由（非"每层压缩15×"）：** 章级上下文之所以有界，是因为每层只加载**当前实例**（1个书脊 + 1个当前大弧段 + 1个当前卷摘要 + 1个当前弧段 + 近8章拍点），而非累积全部历史。实测窗口大小 ≈ 600+3000+2000+1500+1600+2000 ≈ **10,700字**，在第3章和第3000章一致（误差±20%，源于弧段长度随12章微变）。

### 3.2 章级上下文组装公式

章级 skill 的上下文 = L5 + L4(当前大弧) + L3(当前卷) + L2(当前弧) + L1(近8章拍点) + 本章相关文件。不读历史全量。

### 3.2.1 爬坡期处理（章节 1-35）

前36章内，L2/L3/L4 尚未产出（首个L2弧段在第12章生成，首个L4大弧在第36章生成，首个L3卷摘要在卷边界生成）。爬坡期上下文组装规则：

- **缺失层不报错，跳过加载。** context-composing 按层逐层尝试加载，若该层文件不存在则跳过（不填充占位）。
- **爬坡期用 L1 近章拍点补偿。** 前12章无 L2 时，L1 取近章范围扩大到近12章（而非8章），部分补偿缺失的弧段合成。
- **爬坡期窗口较小（~3000-6000字），非缺陷。** 爬坡期信息总量本身就少（章节数少），较小的窗口是自然的。稳态窗口（~10,700字）从第36章起达成。

### 3.3 新增文件

#### truth/book_spine.md（L5 书脊）

常青文件，全书唯一、持续维护。随第一卷定稿产出，每卷/大弧边界滚动复核。

```markdown
---
updated: YYYY-MM-DD
total_chapters: N
---

# 书脊

## 核心冲突三层（从 story_frame.md 继承，滚动复核）
- surface_conflict: [外部矛盾，当前状态]
- personal_conflict: [主角困境，当前状态]
- deep_conflict: [主题问题，当前状态]

## 全书 themes（贯穿校验基准）
- [theme 1]: 当前已探索章节范围、探索深度
- [theme 2]: ...

## 主角弧（声明终点锚定）
- arc_type: GROWTH
- arc_starting → arc_turning（已过）→ arc_ending（声明终点）
- 当前位置相对终点的进度

## 主线钩子（master hooks，max_distance跨全书）
- MH01: [内容] | 状态: [PLANTED/ADVANCED/...] | 最后推进章: N | 声明兑现卷
- MH02: ...

## 世界铁律滚动快照（最高频引用的5条，从 world/rules.md 同步）
```

#### truth/book_strata.md（L4 大弧层）

每36章（= 3个L2弧段）一篇，append-only。

```markdown
---
stratum: 1
chapter_range: 1-36
generated_at: YYYY-MM-DD
generated_by: shenbi-memory-distill
---

# 第一大弧合成

## 弧范围
第1章 - 第36章

## 本弧主题推进
- [theme]: 本弧如何推进此主题（具体事件链）

## 跨弧伏笔账（跨卷级别的伏笔，L1拍点无法追踪的长程线）
- MH01: 第X章种植 → 第Y章推进 → 当前状态
- MH02: ...

## 角色弧弧段（每个主要角色在本弧的弧段变化）
- 主角: [弧段起点状态] → [弧段终点状态]，关键转折章: N
- 配角A: ...

## 未解决的张力悬置（带入下一大弧）
- [悬置项1]: 为何未解决，预期解决弧段
```

#### truth/arcs/arc-N.md（L2 弧段合成）

每12章一篇，append-only。

```markdown
---
arc: 3
chapter_range: 25-36
volume: 1
generated_at: YYYY-MM-DD
generated_by: shenbi-memory-distill
---

# 第三弧段合成

## 弧内事件链
[连续叙事摘要，~800字，可追溯到具体章节]

## 弧内伏笔兑现/推进
- H01: 第26章advance → 第32章resolve（兑现方式）
- H02: 第29章plant（新种）

## 角色状态变化（弧段粒度）
- 主角: [起点] → [终点]
- 配角: [起点] → [终点]

## 张力曲线本弧段
[本弧段张力走向，对照卷节奏原则]
```

### 3.4 层边界对齐规则

L2弧段（每12章）与L3卷（可变长）边界不一定对齐——一卷可能是15章或20章。处理规则：

- **L2弧段是硬性固定间隔**（每12章，与卷无关），保证蒸馏触发确定性
- **"当前弧"定义**：包含当前章号的那个L2弧段（chapter_range 覆盖当前章号）
- **"当前卷"定义**：outline/volume_map.md 中 chapter_range 覆盖当前章号的卷
- 两者独立确定，不强求对齐。context-composing 分别加载当前弧和当前卷，允许重叠
- **L4大弧 = 3×L2 = 36章固定**，与卷无关。一个L4大弧可能横跨1-3个卷

### 3.5 新增/改造 skill

#### 新增: shenbi-memory-distill（记忆蒸馏）

泛化现有 volume-consolidation。职责：产出 L2（弧段合成）、L4（大弧合成）、维护 L5（书脊滚动复核）。

```
触发（固定章数，确定性）:
- chapter % 12 == 0 → L2 弧段蒸馏（产出 truth/arcs/arc-(chapter//12).md）
- chapter % 36 == 0 → L4 大弧蒸馏（产出 truth/book_strata.md 的第 (chapter//36) 段）
- 卷边界（volume_map.md 声明的卷末章）→ L3 卷摘要（复用 volume-consolidation 逻辑）
- 大弧边界 → L5 书脊滚动复核

reads:
- L1: truth/chapter_summaries.md（本弧段/大弧覆盖的章范围）
- L3: truth/volume_summaries.md（L4蒸馏时）
- 现有 truth/*.md（伏笔池、角色矩阵等）
writes:
- truth/arcs/arc-N.md (L2)
- truth/book_strata.md (L4, append)
updates:
- truth/book_spine.md (L5, 滚动复核)
```

铁律：
1. **蒸馏可溯源** — 每条合成结论必须可追溯到具体章节（引用章号）
2. **增量产出** — 只追加本弧/本大弧的合成，不重写历史层
3. **信息损失显式标注** — 蒸馏必然损失信息，损失的关键项（如未兑现的伏笔）必须在"未解决悬置"显式列出
4. **L5滚动复核不破坏声明** — 书脊的核心冲突/themes/主角弧终点是 author_intent 声明的，复核只更新"当前位置/进度"，不改声明本身

#### 改造: shenbi-context-composing

P1-P7 优先级重写为按层组装：

| 优先级 | 层 | 来源 | 裁剪规则 |
|--------|----|------|---------|
| P1 | - | plans/chapter-N-plan.md | 不裁剪 |
| P2 | L5 | truth/book_spine.md | 不裁剪（常青，~1页） |
| P3 | L4 | truth/book_strata.md（当前大弧段） | 不裁剪 |
| P4 | L3 | truth/volume_summaries.md（当前卷） | 不裁剪 |
| P5 | L2 | truth/arcs/arc-N.md（当前弧） | 不裁剪 |
| P6 | L1 | truth/chapter_summaries.md（近8章拍点） | 仅取近8章 |
| P7 | - | world/rules.md（最多5条）+ style/style_profile.md | nice，先裁剪 |

### 3.6 RAG 辅助召回层

蒸馏树保证有界窗口。RAG **仅用于跨弧伏笔召回**这类需全库扫描但低频的检查。

**确定性处理（解决LLM非确定性）：** RAG 召回不进入上下文组装主干。召回结果作为**候选列表**输出，由确定性代码过滤（如 max_distance 超期检查是纯数值比较，不受嵌入不确定性影响）。嵌入模型固定版本、查询固定模板，召回结果即使有微小波动，最终判定（超期/未超期）由确定性阈值决定。

**最小契约：**
- 索引对象：truth/pending_hooks.md 全部条目（向量化 hook.content + hook.id + hook.plant_chapter + hook.last_reinforced + hook.max_distance）
- 索引存储：`benchmarks/index/` 下 SQLite + 向量列（本地运行，bge-large-zh 模型，不依赖外部API）
- 索引维护：由 foreshadowing-recall skill 在每章 state-settling 后增量更新（append/update hook 条目）
- 查询接口：`recall_overdue_hooks(current_chapter) -> list[hook_id]`，返回 max_distance 超期的 hook 列表
- 使用场景：review-foreshadowing 跨数百章检查伏笔 max_distance 超期；弧段/书级评分检查长程钩子

新增 skill: `shenbi-foreshadowing-recall`（伏笔召回，封装RAG查询+确定性过滤，对调用方透明）。

## 4. 子系统二：分层评分体系

### 4.1 四层评分金字塔

评分不再是一个扁平0-100，而是四层金字塔，每层目标由上一层定义——这是打破循环验证的关键。

| 评分层 | 触发 | route C：目标达成（主干） | route A：锚点校准（天花板） | 新增/现有 skill |
|--------|------|------|------|------|
| 章级 | 每章定稿后 | 硬二元检查 + 软程度评分（见§4.2） | 叙事工艺维度对照锚点定相对位置 | 强化 review-resonance |
| 弧段级 | 每12章 | 弧内伏笔兑现/推进、张力曲线遵卷节奏、角色弧有可测变化 | 对照伏笔纪律/信息张力锚点 | 新增 score-arc |
| 卷级 | 卷边界 | 卷Objective达成度、跨卷钩子≥3过境、长程主线钩子未死 | 对照规模管理锚点 | 新增 score-volume |
| 大弧/书级 | 每36章+滚动 | themes被真正探索、master hook在max_distance内推进、主角弧仍指向声明终点 | 对照战役节奏/氛围质感锚点 | 新增 score-stratum |

### 4.2 route C 客观性来源：硬二元 vs 软程度

route C 检查项分为两类，客观性来源不同：

**硬二元检查（纯客观，确定性可验）：**
- hook H01 在本章是否 advance → 对照 hook 账§7声明 → 二元（是/否）
- §6 章尾改变是否发生 → 对照章计划§6声明 → 二元（是/否）
- master hook 是否在 max_distance 内推进 → 纯数值比较 → 二元

**软程度评分（半客观，需LLM判断但锚定上级目标）：**
- "卷Objective: 主角从外门升内门"达成度 → 事件发生=已达成（二元），但"完成质量"需程度评分
- chapter_role=高潮 的"情感高潮兑现" → 是否发生高潮是事实判断（二元），但"高潮强度"需程度评分

route C 输出格式：硬二元项 → `已达成/未达成`；软程度项 → `已达成/部分达成/未达成 + 程度分(0-100)`。**硬二元项的"未达成"直接触发重生路由（§5），不接受程度评分。**

### 4.3 route A 锚点库系统

#### 锚点来源工艺分析

基于文学批评（非原文复制）提炼两部作品的卓越工艺：

**《诡秘之主》（爱潜水的乌贼，446万字）**：第一卷《小丑》/第二卷《无面人》公认封神。工艺强项：信息差驱动悬念层叠、序列体系内部自洽、跨数百章长程伏笔兑现、克苏鲁氛围质感、扮演法绑定角色成长与力量体系。

**《炮火弧线》（康斯坦丁伯爵，262万字，830章）**：工艺强项：大场面战役节奏控制、战略-战术层级叠加、群像场面调度、赌注阶梯升级、单场与战略弧关系。

#### 9类锚点槽位

| 锚点类别 | 工艺来源 | 校准的评分维度（均归一化到0-100） | 参考章节（本地语料，仅供工艺分析） |
|---------|---------|--------------|------|
| 情感落地/角色弧兑现 | 诡秘·小丑消化场景 | 章级.情感落地, 章级.角色弧兑现 | 诡秘 第一卷末 |
| 氛围质感/日常段功能 | 诡秘·羔羊肉场景 | 章级.文笔质感, 章级.日常段功能 | 诡秘 克莱恩做羔羊肉 |
| 规模管理/高光/信息张力 | 诡秘·乌托邦偷袭战 | 弧段/卷级.高光, 卷级.伏笔纪律 | 诡秘 第七卷末 |
| 战役节奏/场景临场感 | 炮火·燃烧的原野 | 章级.节奏, 章级.场景临场 | 炮火 第50章 |
| 高光设计/爽点阶梯 | 炮火·我炮多 | 章级.爽点, 章级.读者牵引 | 炮火 第67章 |
| 规模管理/群像调度 | 炮火·突袭莫哈 | 弧段.群像, 卷级.规模 | 炮火 第453章 |
| 情感落地/主题升华 | 炮火·以我残躯化烈火 | 大弧级.主题贯穿, 章级.情感 | 炮火 第670章 |
| 战役节奏/张力曲线 | 炮火·装甲对决 | 卷级.张力曲线, 弧段.节奏 | 炮火 第696章 |
| 伏笔纪律/世界规则自洽 | 诡秘·序列体系 | 卷级.世界规则, 卷级.伏笔 | 诡秘 序列体系全局 |

> **作用域限定：** 锚点仅校准**叙事工艺维度**（情感/节奏/质感/伏笔/规模等）。结构合规维度（指令遵从、输出完整性、G4段标题等）不依赖锚点——这些是确定性检查，无需外部校准。

#### 版权边界

锚点库 `benchmarks/anchors/` 存储：锚点ID + 工艺维度标签 + 工艺分析（2-3句文学批评）+ 指纹哈希。**不存储大段原文。** 原文样本仅在本地（~/Downloads/）用于一次性工艺分析提取，不进入版本库。评分 rubric 引用锚点ID，要求评分员定相对位置（更好/相当/更差），不引用原文。

#### 锚点文件格式（维度分0-100，与现有rubric一致）

```markdown
# benchmarks/anchors/AC-001.md

---
id: AC-001
category: 情感落地/角色弧兑现
source_work: 诡秘之主
source_ref: 第一卷末，小丑魔药消化
fingerprint: sha256:...
calibrates: [章级.情感落地, 章级.角色弧兑现]
---

## 工艺分析

[2-3句文学批评：为什么这个场景在情感落地/角色弧兑现维度上是卓越的。分析手法，不复制原文。]

## 评分校准基准（0-100，归一化到各维度）

- 产出达到此工艺水平 → 章级情感落地 88-97
- 产出接近但未及 → 75-87
- 产出远不及 → <75
- 禁止默认 95。95是"未认真区分"的信号。
```

### 4.4 新增评分 skill 家族

#### shenbi-anchor-curate（锚点策展）

从授权样本生成入库。输入：本地语料路径 + 章节定位。输出：`benchmarks/anchors/AC-NNN.md`。每类槽位3-5个锚点（总计27-45个）。

#### shenbi-score-arc（弧段级评分）

触发：每12章（与memory-distill L2对齐）。

```
requires_independent_agent: true
reads:
- truth/arcs/arc-N.md（被评弧段）
- truth/book_strata.md（上级目标：本弧应推进的themes/master hooks）
- truth/volume_summaries.md（上级目标：本弧在卷Objective中的定位）
- benchmarks/anchors/（route A 校准）
writes:
- audits/arc-N-score.md
updates:
- truth/audit_drift.md（弧段级漂移指导）
```

route C 硬二元检查：弧段声明的伏笔是否兑现/推进（对照弧段合成§伏笔）
route C 软程度：弧段张力曲线遵循卷节奏原则的程度；主要角色弧段变化的程度
route A：伏笔纪律/信息张力维度对照 AC-003/AC-009 锚点定相对位置

#### shenbi-score-volume（卷级评分）

触发：卷边界。**与现有 arc-payoff 分工（见§4.5）。**

```
requires_independent_agent: true
reads:
- truth/volume_summaries.md（被评卷）
- outline/volume_map.md（上级目标：卷Objective + Key Results）
- truth/book_spine.md（上级目标：主线钩子状态）
- benchmarks/anchors/
writes:
- audits/volume-N-score.md
```

route C 硬二元检查：卷Objective二元判定（达成/未达成）；本卷Key Results全部有章节覆盖；跨卷钩子≥3且已过境
route C 软程度：Objective达成质量程度
route A：规模管理维度对照 AC-003/AC-006 锚点

#### shenbi-score-stratum（大弧/书级健康）

触发：每36章 + 滚动（每卷后增量复核）。

```
requires_independent_agent: true
reads:
- truth/book_strata.md（被评大弧）
- truth/book_spine.md（上级目标：全书themes/主角弧终点）
- benchmarks/anchors/
writes:
- audits/stratum-N-score.md
updates:
- truth/book_spine.md（漂移诊断结果回流）
```

route C 硬二元：master hooks 是否在 max_distance 内推进；主角弧是否仍指向声明终点（arc_ending 未被偏移）
route C 软程度：全书 themes 被真正探索的程度；跨数百章疲劳/套路复发诊断
route A：战役节奏/氛围质感维度对照 AC-004/AC-008 锚点

#### 强化: shenbi-review-resonance（章级，注入锚点对照）

保留4维度（情感落地/场景临场/文笔质感/读者回报），注入 route A 锚点对照逻辑。route C 硬二元检查：chapter_role兑现（对照§1声明）、§6改变发生（对照§6声明）、hook账履行（对照§7声明）。

### 4.5 score-volume 与现有 arc-payoff 的分工

两者都是卷/弧边界触发，但**评估轴不同，不合并**：

| skill | 评估轴 | 输出 | 阈值 |
|-------|--------|------|------|
| review-arc-payoff（现有） | 体验交付轴：弧情感交付、伏笔兑现质量、线索解决、期望债务、角色弧 | audits/volume-N-payoff.md → arc_payoff_trend.md | overall≥80 且 伏笔兑现≥15 |
| score-volume（新增） | 目标达成轴：卷Objective达成、KR覆盖、跨卷钩子过境、长程主线钩子 | audits/volume-N-score.md | Objective达成=硬二元门 |

**执行顺序**：卷边界先跑 arc-payoff（体验质量），再跑 score-volume（目标达成）。两者都通过才能推进到下一卷。arc-payoff 不通过 → 卷级情感修订；score-volume 不通过 → 卷级目标重写。

## 5. 子系统三：生成-评分-修正闭环

### 5.1 四 prompt 闭环

```
1. 生成 prompt
   输入: 分层记忆切片(L5-L1按context-composing) + 章计划 + 文风指纹
   输出: 章节草稿 chapters/chapter-N.md

2. 评分 prompt（独立 agent，context-cleaned）
   输入: 章节 + 计划 + 相关锚点ID + 目标达成 rubric
   输出: 各维分数(0-100) + 结构化诊断
   诊断输出格式（统一schema，见§5.2）:
     {
       "issues": [
         {
           "category": "unmet_goal" | "craft",
           "id": "goal-H01-advance" | "craft-ai-tell-L23",
           "evidence": "chapters/chapter-5.md L23-27",
           "severity": "BLOCKING" | "CRITICAL" | "MINOR"
         }
       ]
     }

3. 路由（确定性 helper: revision_routing）
   分类诊断:
     - 纯工艺问题（无 BLOCKING unmet_goal）→ spot-fix 修订
     - 目标未达成（≥1个 BLOCKING unmet_goal）→ 重生（诊断作为重写指令）
     - 两者皆有 → 带工艺约束的重生

4. 重生/修订 prompt → v2 → 重评
   接受条件: 必须在失败维度上具体改善（不只总分升）
   kill switch: 同一目标连续3次未兑现 → 升级人工，禁止无限循环
```

### 5.2 诊断 schema 与路由 helper（一致性已对齐）

诊断输出统一 schema（§5.1 定义的 JSON）：

```python
# src/shenbi/skill_utils/revision_routing/route.py

def route_revision(diagnosis: dict) -> str:
    """分类诊断 → 路由到 spot-fix / regenerate / constrained-regenerate。

    diagnosis schema:
      {"issues": [{"category": "unmet_goal"|"craft", "id": str,
                    "evidence": str, "severity": "BLOCKING"|"CRITICAL"|"MINOR"}]}

    返回值:
      - "spot-fix": 纯工艺问题（无 BLOCKING unmet_goal）
      - "regenerate": 有 BLOCKING unmet_goal，无 craft 问题
      - "constrained-regenerate": 有 BLOCKING unmet_goal + craft 问题
    """
    issues = diagnosis.get("issues", [])
    has_unmet_blocking = any(
        i.get("category") == "unmet_goal" and i.get("severity") == "BLOCKING"
        for i in issues
    )
    has_craft = any(i.get("category") == "craft" for i in issues)
    if has_unmet_blocking and has_craft:
        return "constrained-regenerate"
    if has_unmet_blocking:
        return "regenerate"
    return "spot-fix"
```

> **schema 一致性**：§5.1 的诊断输出 JSON 与 §5.2 的路由读取字段（category/severity）完全对齐。评分 skill 必须按此 schema 输出，否则 revision_routing 报错。

### 5.3 改造: shenbi-chapter-revision

增加重生模式路由。当前只有 spot-fix / rewrite 两种模式，新增"目标未达成→重生"路径。

**重生保留核验（确定性 helper 强制执行）：**

```python
# src/shenbi/skill_utils/revision_routing/preserve_check.py

def verify_preservation(original: dict, regenerated: dict) -> tuple[bool, list[str]]:
    # original/regenerated 结构: {"chapter": int, "hooks_advanced": [str], "changes_realized": [str], "state_changes": [str]}
    # hooks_advanced: 原稿中已 advance/resolve 的 hook_id 列表（从章计划§7 + state-settling 提取）
    # changes_realized: 原稿中已发生的§6改变列表
    # state_changes: 原稿中已发生的角色状态变更列表
    """重生后强制核验已兑现项未被破坏。

    检查项:
      - 已 advance/resolve 的 hook 在重生稿中仍存在对应剧情
      - 章计划§6声明的已发生改变在重生稿中仍发生
      - 角色状态变更（来自state-settling）未被回退

    返回 (all_preserved, violations)
    """
    violations = []
    # 对照 hook 账: 原稿 advance 的 hook，重生稿是否仍 advance
    # 对照 §6 改变: 原稿实现的改变，重生稿是否仍实现
    # 对照 character_matrix: 原稿的关系/状态变化，重生稿是否保留
    return (len(violations) == 0, violations)
```

铁律补充：
6. **重生不是润色** — 目标未达成不能用 spot-fix 修复，必须重生对应段落/整章
7. **重生保留已兑现项** — 重生后必须通过 verify_preservation 核验，违反 = 重生无效，重做

### 5.4 反塌缩三道补丁

#### 补丁1: 评分 dispatch 指令强制离散化

评分 subagent 的 dispatch 指令增加约束：

```
评分约束:
- 若你认为质量达标，必须在 88-97 间给出有区分度的分数
- 禁止默认 95。95 是"未认真区分"的信号，将触发复核
- 必须能解释每个维度分数相对锚点的位置（更好/相当/更差）
```

#### 补丁2: 双评员一致性（分层触发）

双评员**按评分层分触发**（已解决与成本矛盾）：

| 评分层 | 双评员触发条件 | 理由 |
|--------|--------------|------|
| 章级 | 总是双评（每章两个独立subagent） | 章级是最高频、最高杠杆，双评防塌缩价值最大 |
| 弧段级 | 总是双评 | 12章一次，成本可控 |
| 卷级 | 总是双评 | 卷边界低频，质量门槛高 |
| 大弧/书级 | 总是双评 | 36章一次，全书主轴，必须双评 |

差异 >5 分（任一维度）→ 触发第三 subagent 仲裁。scoring.py 增加 `check_scorer_agreement` 函数。

> 注：全量（千万字 ≈ 3300章）双评成本可控——章级双评仅每章多一次评分调用，不涉及双倍生成。评分调用成本远低于生成成本。

#### 补丁3: 锚点相对定位抑制塌缩

route A 要求对照锚点定相对位置。锚点是固定参考，天然抑制全体向中位塌缩——评分员必须回答"比锚点好/差/相当"，而非孤立打分。

### 5.5 改造: src/shenbi/scoring.py

增加：
- `check_scorer_agreement(scores_a, scores_b, threshold=5)`: 双评员一致性校验
- `flag_score_collapse(scores)`: 检测塌缩信号（如全体=95的精确值，标记为低置信度）
- 评分输出增加 `anti_collapse_flags` 字段

## 6. 子系统四：自动审批与人工升级

### 6.1 默认自动批 + 阻断级覆盖

**默认规则**：所有创作/审计/状态 skill 的输出默认自动通过，不等待人工。

**阻断级覆盖（确定性，优先于默认）**：审计 skill 输出含 BLOCKING 级问题时，自动批不生效——该输出标记为 `blocked`，触发升级（§6.2）。这是"自动批"的例外机制：BLOCKING 是确定性信号，不是主观判断。

> 敏感性审计 blocking → 自动标记 blocked → 召唤人工。§6.1 的"默认自动通过"不含 BLOCKING 级输出。

### 6.2 升级触发条件（确定性判定）

| 触发条件 | 精确定义 | 判定来源 | 升级动作 |
|---------|---------|---------|---------|
| 章级评分连续3章下滑 | 近5章 overall 的线性回归斜率 < -2（每章降>2分趋势） | truth/resonance_trend.md | 暂停自动批，召唤人工审查趋势 |
| 卷级Objective未达成 | score-volume 硬二元判定=未达成 | audits/volume-N-score.md | 召唤人工决定卷级重写还是接受 |
| 同一目标连续3次未兑现 | 章级重生循环计数对该目标≥3 | 章级重生计数器 | 升级人工，禁止无限循环 |
| 敏感性审计 blocking | severity=BLOCKING | audits/chapter-N-sensitivity.md | 召唤人工处理 |
| 弧段评分 <70 | score-arc overall < 70 | audits/arc-N-score.md | 召唤人工审查弧段级问题 |
| 书级主轴偏移 | score-stratum 判定主角弧偏离声明终点 | audits/stratum-N-score.md | 召唤人工复核书脊声明 |

### 6.3 新增确定性 helper: escalation_check

```python
# src/shenbi/skill_utils/escalation/check.py

def check_escalation(round_dir: Path, chapter: int) -> list[EscalationSignal]:
    """在每章评分完成后调用。检查是否需要人工升级。返回升级信号列表。"""
    signals = []
    # 1. 章级评分连续下滑: 读 resonance_trend 近5章, 线性回归斜率 < -2
    # 2. 卷级Objective未达成: 读最近 audits/volume-*-score.md
    # 3. 同一目标连续3次未兑现: 读章级重生计数器
    # 4. 敏感性 blocking: 读最近 audits/chapter-*-sensitivity.md
    # 5. 弧段评分 <70: 读最近 audits/arc-*-score.md
    # 6. 书级主轴偏移: 读最近 audits/stratum-*-score.md
    return signals
```

**集成点**：escalation_check 在每章 review-resonance 评分完成后立即调用（逐章循环的固定步骤）。若返回非空信号 → 该章标记为 `escalation_required`，召唤人工。

### 6.4 改造各 skill 的审批节点

统一改为"默认auto + 阻断覆盖 + 升级判定"。现有 skills 中所有 `Human reviews → Revise/Write` 的 DOT 节点改为：

```dot
"Generate output" -> "Has BLOCKING issues?";
"Has BLOCKING issues?" -> "Write to disk" [label="no"];
"Has BLOCKING issues?" -> "Mark blocked" [label="yes"];
"Write to disk" -> "Escalation check (post-score)";
"Escalation check (post-score)" -> "Done" [label="no escalation"];
"Escalation check (post-score)" -> "Human review" [label="escalation"];
"Mark blocked" -> "Human review";
"Human review" -> "Revise" [label="rejected"];
"Human review" -> "Write to disk" [label="approved"];
```

## 7. 数据流总览（概要，精确接缝见 §11.10）

```
创世层 → story_frame.md + volume_map.md
       → shenbi-book-spine-init → book_spine.md(L5初始化)
                ↓
逐章循环（每章）:
  intent-management → current_focus.md
  chapter-planning → plans/chapter-N-plan.md
       ↓
  context-composing（L5+L4+L3+L2+L1近8章+本章文件）→ 上下文包
       ↓
  chapter-drafting → chapters/chapter-N.md
       ↓
  state-settling → truth/*.md 更新 → foreshadowing-recall 更新RAG索引
       ↓
  审计层(现有18个，含BLOCKING阻断覆盖) + review-resonance(route A+C)
       ↓
  评分(双评员) → 诊断(schema统一)
       ↓
  revision_routing(spot-fix/regenerate) → 重生/修订 → preserve_check核验 → 重评
       ↓
  escalation_check → 无升级则继续 / 有升级则召唤人工
       ↓
  [chapter % 12 == 0] memory-distill L2 → truth/arcs/arc-N.md
       ↓
  [chapter % 36 == 0] memory-distill L4 + score-stratum → book_spine.md滚动复核
       ↓
  [卷边界] volume-consolidation L3 + arc-payoff(体验) + score-volume(目标)
```

## 8. 全量验证路径（递进实证节点）

全量是最终目标，拆成递进节点，每个可验证、失败能定位。

### 节点1: 单卷跑通（~15章/4.5万字，星火燃穹第一卷）

验证：分层记忆 L0-L3 全链路、章级+弧段级评分（route A+C）、生成-评分-修正闭环（含重生路径）、自动批+升级触发。

通过标准：
- 卷级Objective达成评分 ≥85
- 章级评分稳定，近5章线性回归斜率 ≥ -2（无连续下滑）
- 闭环内重生成功率（失败目标在3次内修复）≥80%
- 无评分塌缩信号（双评员一致性通过，无anti_collapse_flags）

### 节点2: 单大弧跑通（~36章/10.8万字，跨2-3卷）

验证：L4蒸馏、卷级评分、跨卷钩子过境、RAG跨弧伏笔召回。

通过标准：
- 大弧级 themes 贯穿评分 ≥80
- 跨卷记忆一致性零冲突（book_strata 与 volume_summaries 交叉校验）
- master hooks 在 max_distance 内推进（RAG 召回验证）

### 节点3: 全量（目标字数，全书）

验证：L5书脊滚动维护、书级健康诊断、千万字规模下窗口有界性。

通过标准：
- 书级主轴未偏移（主角弧仍指向声明终点）
- 全书套路/疲劳无复发（chapter-pattern 全书数据）
- **窗口有界性验证**：context-composing 输出的上下文字符数在第36章、第100章、第1000章、第3000章均在 8,500-12,900字区间（10,700±20%）。第1-35章为爬坡期（§3.2.1），窗口较小（~3000-6000字），属正常

每个节点失败时，定位到具体评分层的具体维度，修复后重跑该节点，不回退到更早节点。

## 9. 新增/改造清单与测试基础设施改造

本设计的测试基建改动是**第一优先级**——框架是测试驱动的（G0-G7 gate 链 + 工具哈希锁定 + T1/T2/T3 三层），任何 skill/helper 变动不经测试基建同步，会直接被 G0 阻断或产生幻影数据。

### 9.1 新增 skill（8个）

| skill | 职责 | G4 checker | T1测试 |
|-------|------|-----------|--------|
| shenbi-memory-distill | 记忆蒸馏（L2/L4/L5） | 新建 generic checker（溯源校验：每条结论引用章号） | 新建3类 |
| shenbi-anchor-curate | 锚点策展 | 新建（工艺分析完整性校验） | 新建3类 |
| shenbi-score-arc | 弧段级评分 | 新建（报告型 generic） | 新建3类 |
| shenbi-score-volume | 卷级评分 | 新建（报告型 generic） | 新建3类 |
| shenbi-score-stratum | 大弧/书级评分 | 新建（报告型 generic） | 新建3类 |
| shenbi-foreshadowing-recall | RAG伏笔召回 | 新建（召回结果完整性） | 新建3类 |
| shenbi-book-spine-init | 书脊初始化 | 新建（frontmatter字段校验） | 新建3类 |
| shenbi-escalation-review | 人工升级审查 | 新建（报告型 generic） | 新建3类 |

### 9.2 改造 skill（6个）

| skill | 改造内容 |
|-------|---------|
| shenbi-context-composing | P1-P7 重写为按层组装；G4 checker 更新校验 9 节标题→按层节标题 |
| shenbi-chapter-revision | 增加重生模式路由 + preserve_check；G4 checker 更新校验重生保留核验区块 |
| shenbi-review-resonance | 注入 route A 锚点对照 + route C 目标达成检查；rubric 新增锚点对照维度 |
| shenbi-volume-consolidation | 对接 memory-distill 的 L3 产出 |
| 各创作/审计 skill（统一模式） | 审批节点改为默认auto + 阻断覆盖 + 升级条件 |
| shenbi-intent-management | 维护 book_spine.md（与 author_intent 同步） |
| shenbi-review-foreshadowing | 大规模时调用 foreshadowing-recall（§11.9） |

### 9.3 新增确定性 helper（4个）

| helper | 职责 |
|--------|------|
| skill_utils/revision_routing | 诊断分类→路由（spot-fix/regenerate）+ preserve_check |
| skill_utils/escalation | 升级条件判定（含线性回归斜率计算） |
| scoring.py 扩展 | 双评员一致性 + 塍缩检测 |
| skill_utils/foreshadowing_recall | RAG查询 + 确定性阈值过滤 |

### 9.4 Gate 代码改动（Critical，不修改则 G0 阻断）

#### G0.10 — skill 计数硬编码修复

`src/shenbi/gates/g0.py:419` 硬编码 `count < 59` 和 `total: 59` 两处。新增 8 个 skill 后总数为 67。

**修复**：将字面量 `59` 替换为 `len(ALL_SKILLS)`（动态从 skills/ 目录扫描），或读取 `tests/tiers/deps.json` 中的计数。G0.10 改为动态基数，不依赖硬编码。

```python
# 修复前
if count < 59:
    ... "total": 59 ...

# 修复后
total_skills = len(ALL_SKILLS)  # 动态扫描 skills/ 目录
if count < total_skills:
    ... "total": total_skills ...
```

#### G0.4 — 已是动态（无需修改）

G0.4 用 `len(ALL_SKILLS)` 动态扫描，新增 skill 自动纳入。但需确认 `ALL_SKILLS` 的扫描路径包含新增的 benchmarks/ 目录下的 skill（若有）。

#### G0.13/G0.14 — 工具哈希锁定范围扩展

`tests/lock-tool-hashes.sh` 当前只锁定 5 个文件（cli.py/shared.py/scoring.py/phase_runner.py/summarize_round.py）。新增 4 个 helper（revision_routing/escalation/foreshadowing_recall + scoring.py 扩展本身）需纳入锁定。

**修复方案**：lock-tool-hashes.sh 改为扫描 `src/shenbi/` 全树（排除 `__pycache__`），自动纳入所有 src/ 下的 .py 文件。这样未来新增 helper 自动被锁定，不依赖手动维护文件列表。

```bash
# 修复前：手动列举 5 个文件
tool_paths = ['src/shenbi/gates/cli.py', ...]

# 修复后：扫描全树
tool_paths = [str(p.relative_to(project)) for p in
              (project / 'src/shenbi').rglob('*.py')
              if '__pycache__' not in str(p)]
```

#### G2 — 文件类型分类扩展

`shenbi-validate G2 <files> <type>` 的 `<type>` 需新增分类：

| 新文件 | G2 type |
|--------|---------|
| truth/arcs/arc-N.md | `truth`（复用现有 truth 校验） |
| truth/book_strata.md | `truth` |
| truth/book_spine.md | `truth` |
| audits/arc-N-score.md | `audit`（复用现有 audit 校验，需新增） |
| audits/volume-N-score.md | `audit` |
| audits/stratum-N-score.md | `audit` |
| benchmarks/anchors/AC-NNN.md | `anchor`（新增类型，校验 frontmatter + 工艺分析完整性） |

### 9.5 deps.json 改动（Critical，不修改则 T2/T3 链断裂）

#### T2 phases — prerequisites 扩展

| phase | 新增 prerequisites | 理由 |
|-------|-------------------|------|
| genesis | + shenbi-book-spine-init | 创世层末尾必须初始化书脊（L5） |
| drafting | + shenbi-score-arc（每12章）, shenbi-foreshadowing-recall（每章） | 起草循环含弧段评分 + RAG召回 |
| management | + shenbi-memory-distill, shenbi-score-volume, shenbi-score-stratum | 卷/大弧管理含记忆蒸馏 + 分层评分 |

新增评分/记忆 skill **不新建独立 T2 phase**——它们作为评分层和记忆层，附加到现有 drafting/management phase。但它们各自有独立 T1 测试（§9.1）。

#### T3 pipelines — prerequisites 扩展

| pipeline | 新增 phase 依赖 | 理由 |
|----------|----------------|------|
| long-form | drafting + management（已含，但需确认含新评分技能） | 长篇必须跑通分层评分全链路 |

#### _out_of_pipeline 调整

新增的 8 个 skill 中，anchor-curate 和 escalation-review 是辅助/触发型，归入 `t1_only_auxiliary`：

```json
"_out_of_pipeline": {
  "t1_only_auxiliary": [
    "shenbi-market-radar",
    "shenbi-sequel-writing",
    "shenbi-anchor-curate",
    "shenbi-escalation-review"
  ],
  "t1_only_meta": ["shenbi-writing-skills", "using-shenbi"],
  "_note": "anchor-curate 和 escalation-review 是辅助/触发型，T1 通过即可，不进 T2 phase prerequisites"
}
```

### 9.6 Rubric 改动（Critical，不修改则评分维度不覆盖 route A+C）

#### 改造的 6 个 skill — rubric 新增维度

每个被改造 skill 的 rubric.md 必须同步新增 route A/C 维度。以 review-resonance 为例：

```markdown
## 新增 Bespoke Dimensions（route A + route C，权重从现有维度拆分）

| # | Dimension | Weight | Standard | route |
|---|-----------|--------|----------|-------|
| N | Anchor calibration | 15% | 每维度分数必须对照 benchmarks/anchors/ 相关锚点定相对位置（更好/相当/更差），禁止无锚点孤立打分 | A |
| N+1 | Goal attainment (hard-binary) | 15% | chapter_role兑现/§6改变发生/hook账履行——每项二元判定，任一未达成=该维度0分 | C |
```

权重从现有 bespoke 维度按比例拆分（如从"4-dim scoring quality"40%拆出15%给 anchor calibration），总权重保持100%。

#### 新增的 8 个 skill — 全新 rubric

每个新增 skill 需新建完整 rubric.md（Universal 15% + Bespoke 85%），维度覆盖其 route A/C 职责。例如 score-arc 的 rubric：

```markdown
## Bespoke Dimensions（score-arc）

| # | Dimension | Weight | Standard | route |
|---|-----------|--------|----------|-------|
| 3 | 弧段伏笔兑现检查（硬二元） | 30% | 弧段声明的伏笔是否兑现/推进，对照弧段合成§伏笔，二元判定 | C |
| 4 | 张力曲线遵循卷节奏（软程度） | 20% | 弧段张力走向对照卷节奏原则的程度 | C |
| 5 | 角色弧段变化（软程度） | 15% | 主要角色在本弧是否有可测弧段变化 | C |
| 6 | 锚点对照（伏笔纪律/信息张力） | 20% | 对照 AC-003/AC-009 锚点定相对位置 | A |
```

### 9.7 Fixture 改动（Important，不补充则 G0.9 fixture 纯度检查阻断）

每个新增 skill 的 T1 scenario 必须引用 `tests/fixtures/` 下的真实输入。需新建的 fixtures：

| fixture | 服务的 skill | 内容 |
|---------|------------|------|
| fixtures/arc-example.md | score-arc, memory-distill | 一个完整的 L2 弧段合成样本 |
| fixtures/book-strata-example.md | score-stratum, memory-distill | 一个完整的 L4 大弧合成样本 |
| fixtures/book-spine-example.md | score-stratum, book-spine-init | 一个完整的书脊样本 |
| fixtures/volume-summary-example.md | score-volume | 卷摘要样本 |
| fixtures/anchors/AC-00X.md | score-arc/volume/stratum, review-resonance | 锚点样本（从诡秘/炮火工艺分析生成，非原文） |
| fixtures/diagnosis-example.json | chapter-revision (重生路由) | 结构化诊断样本（含 unmet_goal + craft） |

所有 fixture 必须是真实 skill 产出的样本或上游生成副本（遵循 G0.9 禁止手写 mock）。

### 9.8 summarize_round.py 改动（Important，不修改则新评分层分数不入 summary）

`summarize_round.py` 当前只读 `t1_scores`/`t2_scores`/`t3_scores`。分层评分（score-arc/volume/stratum）是新的评分维度——它们不是单项 T1 skill 测试，也不完全是 T2 phase 测试。

**修复方案**：summary.json 新增分层评分桶：

```json
{
  "t1_scores": {...},
  "t2_scores": {...},
  "t3_scores": {...},
  "hierarchical_scores": {
    "arc_scores": {"arc-1": 88.0, "arc-2": 91.5},
    "volume_scores": {"volume-1": 85.0},
    "stratum_scores": {"stratum-1": 82.0}
  }
}
```

summarize_round.py 增加读取 `hierarchical_scores` 的逻辑，G7 审计纳入分层分数验证。

### 9.9 command-to-give.md 改动（Important，不修改则执行协议不反映新闭环）

`command-to-give.md` 第三步（按 skill 列表执行）需补充：

- 评分必须含 route A 锚点对照（dispatch 指令注入锚点ID）
- 评分必须含双评员（两个独立 subagent）
- 评分诊断输出必须按 §5.2 统一 schema（category/severity/evidence）
- chapter-revision 失败后按 revision_routing 分流（spot-fix/regenerate），不再只有 spot-fix
- 重生后必须通过 preserve_check 核验

第六步（T2 phase 执行）需补充：drafting phase 含 score-arc（每12章）；management phase 含 memory-distill + score-volume + score-stratum。

### 9.10 acceptance.json — 无需修改

`{"t1":94,"t2":94,"t3":94}` 的阈值适用于所有层。分层评分沿用 ≥94 阈值。

### 9.11 测试基建改动清单（执行顺序）

与 §10 实施顺序对齐，测试基建改动分波进行：

**波1（与 helpers 同步）：**
- lock-tool-hashes.sh 改为扫描全树（§9.4）
- scoring.py 扩展 + 重锁哈希

**波2（与记忆层同步）：**
- G0.10 硬编码59→动态（§9.4）
- G2 新增 truth/audit/anchor 类型（§9.4）
- 新增 fixtures（§9.7）：arc/book-strata/book-spine/volume-summary
- deps.json：genesis + book-spine-init（§9.5）

**波3（与评分层同步）：**
- 新增 fixtures（§9.7）：anchors/AC-00X、diagnosis
- deps.json：drafting + score-arc/recall；management + memory-distill/score-volume/stratum（§9.5）
- 6 个改造 skill 的 rubric 新增 route A/C 维度（§9.6）
- 8 个新增 skill 的全新 rubric + T1 目录（§9.6）
- summarize_round.py + hierarchical_scores（§9.8）

**波4（与闭环同步）：**
- command-to-give.md 更新执行协议（§9.9）
- chapter-revision rubric 更新（重生路由维度）
- _out_of_pipeline 调整（§9.5）
- 全量重锁哈希 + G0 全检通过

### 9.12 每个新增/改造 skill 必须同步交付（硬性）

1. **G4 checker**（`src/shenbi/gates/g4/<skill>.py`）
2. **T1测试目录**（`tests/tiers/t1-skill/<skill>/`）：rubric.md + generative/bug-hunt/clean + scenario.md + fixtures
3. **deps.json注册**：加入对应T2 phase prerequisites 或 _out_of_pipeline
4. **fixtures**：真实输入样本（遵循G0.9）
5. **重锁哈希**：`bash tests/lock-tool-hashes.sh`（修改任何 src/shenbi/ 代码后）

> 现有5个T2 phase 的 `g4_checker: null`（audit/management/import/foundation/short-story）是已知缺口。新增评分skill不进T2 phase（它们是评分层），但仍需独立G4 checker。

### 9.13 genre-config 激活模型

新增评分/记忆 skill 不走 genre-config.auditDimensions 激活模型（那是审计层的条件激活）。它们的触发规则：

| skill类型 | 触发方式 |
|----------|---------|
| 评分 skill（score-arc/volume/stratum） | 固定触发（章数/卷边界），always-on |
| review-resonance（强化） | 保留现有 always-on |
| memory-distill | 固定触发（chapter%12==0 / %36==0 / 卷边界），always-on |
| foreshadowing-recall | 每章 state-settling 后触发，always-on |
| escalation-review | 仅升级信号触发时 |

## 10. 实施顺序（依赖拓扑）

按依赖拓扑分4波实施，每波可独立验证：

**波1（基础设施 + helpers，无外部依赖）：**
1. revision_routing helper（含 preserve_check）
2. escalation helper
3. scoring.py 扩展（双评员 + 塌缩检测）
4. foreshadowing_recall helper（RAG查询）

**波2（记忆层，依赖波1的确定性基座）：**
5. book-spine-init（L5初始化，创世层末尾）
6. memory-distill（L2/L4/L5，依赖L1现有产出）
7. context-composing 改造（按层组装，依赖L2/L4/L5存在）
8. foreshadowing-recall skill（封装波1 helper）

**波3（评分层，依赖波2的记忆产出）：**
9. anchor-curate（锚点库，依赖本地语料）
10. review-resonance 强化（注入锚点+route C）
11. score-arc（依赖L2弧段产出）
12. score-volume（依赖L3卷摘要 + 现有arc-payoff分工）
13. score-stratum（依赖L4大弧产出）

**波4（闭环 + 审批，依赖波2+3）：**
14. chapter-revision 改造（重生路由 + preserve_check，依赖波1 helper）
15. 各 skill 审批节点改造（默认auto + 阻断覆盖 + 升级）
16. escalation-review skill（依赖波3评分产出 + 波1 escalation helper）

## 11. 集成接缝规范（Integration Seam Contract）

本节逐个组件声明它与现有链条的精确接合点。每个新增/改造组件必须回答三个问题：读谁、被谁读、什么时序。违反接缝 = 运行时数据断裂。

### 11.1 book-spine-init — 创世层末尾

**问题**：book-spine-init 需读 `truth/author_intent.md`，但该文件由 intent-management（逐章循环第1步）填充。book-spine-init 在创世层运行（逐章循环之前），此时 author_intent.md 是 worldbuilding 创建的空模板。

**接缝契约**：
- **初始化阶段（book-spine-init，创世层末尾）**：只读 `outline/story_frame.md` + `outline/volume_map.md`（两者均在创世层由 story-architecture / volume-outlining 产出）。书脊的 themes 从 novel.json 读取（worldbuilding 产出）。author_intent 字段初始化为空，标记 `status: pending_intent`。
- **滚动合并阶段（memory-distill 每卷/大弧边界）**：读 `truth/author_intent.md`（此时已由 intent-management 填充），合并到书脊的 themes/主角弧进度字段。
- **deps.json 顺序约束**：genesis phase 内，book-spine-init 必须在 story-architecture 和 volume-outlining **之后**运行。deps.json 的 prerequisites 列表是有序的，book-spine-init 排在两者之后。

```json
"genesis": {
  "prerequisites": [
    "shenbi-worldbuilding", "shenbi-power-system", "shenbi-faction-builder",
    "shenbi-location-builder", "shenbi-character-design", "shenbi-relationship-map",
    "shenbi-story-architecture", "shenbi-volume-outlining", "shenbi-genre-config",
    "shenbi-pacing-design", "shenbi-book-spine-init"
  ]
}
```

### 11.2 score-arc — L4 缺失处理

**问题**：score-arc 触发于每12章（chapter%12==0），但读取的 `truth/book_strata.md`（L4）首次产出在第36章（chapter%36==0）。第12、24章时 L4 不存在。

**接缝契约**：
- **主题/master hooks 上级目标**：从 `truth/book_spine.md`（L5，第1章起可用）读取，**不从** book_strata.md 读取。L5 始终存在（book-spine-init 产出）。
- **跨弧伏笔账**：从 `truth/book_strata.md`（L4）读取，但**允许缺失**。L4 缺失时（chapter < 36），score-arc 仅评弧内伏笔（从 `truth/arcs/arc-N.md` §伏笔），跳过跨弧维度并标记 `cross_arc_data: unavailable (pre-stratum)`。
- **修正 score-arc 契约**：
  ```
  reads:
    - truth/arcs/arc-N.md          # 被评弧段（必需）
    - truth/book_spine.md          # 上级目标: themes/master hooks（必需，L5）
    - truth/volume_summaries.md    # 上级目标: 卷Objective定位（若当前卷已完结）
    - truth/book_strata.md         # 跨弧伏笔（可选，chapter≥36 才存在）
    - benchmarks/anchors/
  ```

### 11.3 重生后 state-settling 重跑（闭环完整性）

**问题**：现有逐章循环时序是 drafting → state-settling → 审计 → revision。chapter-revision（含重生）修改 `chapters/chapter-N.md`，但不 update truth files。重生后 chapter_summaries.md / pending_hooks.md / character_matrix.md 反映的是重生前的旧章节，memory-distill（chapter%12触发）会读到过时数据。

**接缝契约 — 闭环必须含 state-settling 重跑**：

四 prompt 闭环修正为五步（§5.1 更新）：
```
1. 生成 → chapters/chapter-N.md
2. state-settling（首次）→ truth/*.md 初版
3. 评分 → 诊断
4. 路由 → spot-fix / regenerate
5a. spot-fix → 改章节，truth 影响小（工艺修订不改事实），跳过重跑
5b. regenerate → 重生章节 → state-settling（重跑）→ 更新 truth/*.md → 重评
```

**重生后 state-settling 重跑规则**：
- regenerate 路径完成后，强制重跑 state-settling（输入重生后的 chapter-N.md）
- state-settling 重跑是**覆盖更新**（不是追加），因为同一章的状态变化被重生的章节内容替代
- preserve_check 在 state-settling 重跑**之后**执行——它验证重生稿的 state-settling 输出是否保留了原稿的关键变更

### 11.4 chapter-revision 契约扩展 — 读取评分诊断

**问题**：revision_routing 需要"未达成目标"诊断（来自评分），但 chapter-revision 现有契约只读 `audits/chapter-N-*.md`（审计报告），不读评分诊断。

**接缝契约 — chapter-revision reads 扩展**：
```
reads:
  - chapters/chapter-N.md
  - audits/chapter-N-*.md           # 审计问题（现有）
  - audits/chapter-N-resonance.md   # 评分诊断（新增，含 route C unmet_goal）
  - plans/chapter-N-plan.md         # 章计划（新增，用于 preserve_check 的原始项提取）
  - truth/state_snapshot-pre-rev.md # 重生前状态快照（新增，由 chapter-revision 在重生前自动创建）
updates:
  - chapters/chapter-N.md
```

revision_routing 在 chapter-revision **内部**调用（chapter-revision 已有模式路由逻辑，新增 regenerate 路径）。评分诊断通过 `audits/chapter-N-resonance.md` 传入（review-resonance 的输出已含 route C 诊断）。

### 11.5 preserve_check — 原始项组装

**问题**：preserve_check 比较原始（已兑现项）与重生稿。原始项字典在重生前由谁组装？

**接缝契约 — chapter-revision 在重生前组装原始项**：

chapter-revision 在执行 regenerate 前：
1. 读 `plans/chapter-N-plan.md` §7（hook 账）提取已 advance/resolve 的 hook_id → `hooks_advanced`
2. 读 `plans/chapter-N-plan.md` §6（章尾改变）提取已实现的改变 → `changes_realized`
3. 读当前 `truth/character_matrix.md`（重生前的状态）提取角色关系/状态变更 → `state_changes`
4. 组装 `original` 字典，创建 `truth/state_snapshot-pre-rev.md` 快照
5. 执行重生
6. 重跑 state-settling（§11.3）
7. 调用 preserve_check(original, 重生后 state-settling 输出)

```python
# chapter-revision 内部流程
def regenerate_with_preservation(chapter_path, diagnosis):
    original = assemble_original_items(plan_path, current_truth)  # §7 hooks + §6 changes + matrix
    save_snapshot(original, "truth/state_snapshot-pre-rev.md")
    regenerated = execute_regenerate(chapter_path, diagnosis)
    new_truth = rerun_state_settling(regenerated)  # §11.3
    ok, violations = verify_preservation(original, new_truth)
    if not ok:
        return "regeneration_failed_preservation", violations
    return "ok", None
```

### 11.6 卷边界顺序约束

**问题**：score-volume 读 `truth/volume_summaries.md`（L3，volume-consolidation 产出），但 §7 数据流未指定 volume-consolidation 必须先于 score-volume 运行。

**接缝契约 — 卷边界执行顺序（§7 数据流修正）**：

```
[卷边界]:
  1. volume-consolidation → 产出 truth/volume_summaries.md (L3)     【必须最先】
  2. memory-distill L3（复用 volume-consolidation 产出）
  3. arc-payoff（读 chapters/* + volume_map，不依赖 L3）              【可与4并行】
  4. score-volume（读 volume_summaries L3 + book_spine + volume_map）【必须等1完成】
  5. drift-guidance 卷级（读所有 trend + arc_payoff_trend + volume_score_trend）
```

arc-payoff 和 score-volume 评估轴不同（§4.5），可并行，但 score-volume 必须在 volume-consolidation 之后。

### 11.7 book_spine.md 多写入者 — 字段所有权

**问题**：memory-distill 和 score-stratum 都 update `truth/book_spine.md`。字段所有权未指定，可能覆盖。

**接缝契约 — 字段分区所有权**：

| 字段区 | 拥有者 | 更新时机 | 其他 skill 权限 |
|--------|--------|---------|----------------|
| 核心冲突三层（声明值） | author_intent → book-spine-init 初始化 | 初始化 + 滚动合并 | 只读 |
| 核心冲突三层（当前状态） | memory-distill | 每卷/大弧滚动复核 | 只读 |
| themes（声明值） | novel.json → book-spine-init 初始化 | 初始化 | 只读 |
| themes（探索进度） | memory-distill | 每大弧滚动复核 | 只读 |
| 主角弧（声明终点） | author_intent → book-spine-init 初始化 | 初始化 | 只读 |
| 主角弧（当前位置/进度） | memory-distill | 每卷滚动复核 | 只读 |
| **主角弧（漂移诊断）** | **score-stratum** | 每大弧评分后 | 只读 |
| **themes（达成诊断）** | **score-stratum** | 每大弧评分后 | 只读 |
| 主线钩子状态 | memory-distill | 每卷滚动复核 | 只读 |
| 世界铁律快照 | memory-distill | 每卷同步 | 只读 |

**规则**：声明值（author_intent/novel.json 来源）只由 book-spine-init 写入；数据值（进度/状态）由 memory-distill 写入；诊断值（漂移/达成）由 score-stratum 写入。三者在 YAML frontmatter 中用不同字段，不共享写权。

### 11.8 score-volume 输出 → drift-guidance 消费

**问题**：drift-guidance 读 `resonance_trend.md` + `arc_payoff_trend.md`。新增 score-volume 产生卷级评分，但其输出未接入 drift-guidance，下一卷无法消费卷级目标达成信号。

**接缝契约**：
- **score-volume 新增 writes**：`truth/volume_score_trend.md`（append，每卷一行：卷号 + Objective达成度 + 跨卷钩子数 + 主线钩子推进状态）
- **drift-guidance reads 扩展**：增加 `truth/volume_score_trend.md`
- drift-guidance 的 drift_detection helper 增加"卷级目标未达成"触发器

```
# drift-guidance 修正后 reads
reads:
  - truth/resonance_trend.md
  - truth/arc_payoff_trend.md
  - truth/volume_score_trend.md    # 新增
  - truth/audit_drift.md
```

### 11.9 review-foreshadowing 改造 — 调用 foreshadowing-recall

**问题**：review-foreshadowing 需跨数百章检查伏笔 max_distance 超期，但现有契约只读扁平 `truth/pending_hooks.md`。大规模下扁平读取不可行，需调用 foreshadowing-recall（RAG）。review-foreshadowing 未列入 §9.2 改造清单。

**接缝契约 — review-foreshadowing 加入改造清单（§9.2 更新）**：

```
reads:
  - chapters/chapter-N.md
  - truth/pending_hooks.md          # 小规模直接读（现有）
  - plans/chapter-N-plan.md
  - truth/subplot_board.md
  # 新增：大规模时调用 foreshadowing-recall
  # when current_chapter > 50: 调用 shenbi-foreshadowing-recall 获取超期 hook 列表
```

改造规则：当 `current_chapter > 阈值`（建议50），review-foreshadowing 调用 foreshadowing-recall 获取 `recall_overdue_hooks(current_chapter)` 结果，替代全量读取 pending_hooks.md。阈值以下仍用扁平读取。

### 11.10 端到端数据流修正（§7 更新）

```
创世层 → story_frame.md + volume_map.md
       → book-spine-init（读 story_frame + volume_map，author_intent 暂空）
       → book_spine.md(L5, status: pending_intent)
                ↓
逐章循环（每章）:
  intent-management → current_focus.md + author_intent.md
  chapter-planning → plans/chapter-N-plan.md
  context-composing（L5+L4+L3+L2+L1近8章）→ 上下文包
  chapter-drafting → chapters/chapter-N.md
  state-settling → truth/*.md 初版
  foreshadowing-recall → 更新RAG索引
  审计层（含BLOCKING阻断覆盖）+ review-resonance(route A+C, 双评员)
  → 诊断(schema统一)
  → revision_routing(spot-fix / regenerate)
     spot-fix: chapter-revision 改章节 → 重评
     regenerate: 组装原始项 → 重生 → state-settling重跑 → preserve_check → 重评
  escalation_check → 无升级则继续 / 有升级则召唤人工
       ↓
  [chapter%12==0] memory-distill L2 → truth/arcs/arc-N.md → score-arc(读L5,非L4)
       ↓
  [chapter%36==0] memory-distill L4 → truth/book_strata.md → score-stratum → book_spine诊断字段
       ↓
  [卷边界] volume-consolidation L3（最先）→ arc-payoff(体验) ∥ score-volume(目标,等L3)
       ↓
  [卷边界] drift-guidance 卷级（读 resonance + arc_payoff + volume_score trend）
       ↓
  [卷/大弧边界] memory-distill L5滚动复核（合并 author_intent 到 book_spine）
```

### 11.11 集成完整性检查表

实现时每个新增/改造 skill 必须通过以下检查：

- [ ] reads 中每个文件有明确的产出者（谁 writes/updates 它）
- [ ] writes/updates 中每个文件有明确的消费者（谁 reads 它）
- [ ] 时序正确：被读文件在读取时已产出（无"读未来文件"）
- [ ] 多写入者有字段分区所有权（无写冲突）
- [ ] 缺失文件场景已处理（爬坡期、L4未产出等）

## 12. 与现有框架的兼容性

- **不破坏现有 truth 文件体系** — L1（chapter_summaries）、L3（volume_summaries）复用现有文件，L2/L4/L5 是新增
- **不破坏现有审计层** — 18个审计 skill 保留，分层评分是增量
- **不破坏现有 gate 体系** — G0-G7 保留。新增评分/记忆skill各自有独立G4 checker（§9.4）。现有report型skill的g4_checker=null缺口不因本设计恶化
- **可靠性边界** — RAG不进入上下文组装主干（§3.6），蒸馏固定触发（确定性触发时机）。LLM生成本身的非确定性是框架既有特征（所有generative skill共享），不因本设计引入新风险
- **渐进迁移** — 审批节点改造是可选的逐skill迁移，不需要一次性全改

## 13. 风险与缓解

| 风险 | 缓解 |
|------|------|
| 蒸馏信息损失导致长程失忆 | L4/L5 显式标注"未解决悬置"；RAG 辅助召回关键伏笔 |
| 锚点选取主观性 | 9类槽位基于社区共识（诡秘一二卷封神、炮火名场面）；锚点工艺分析可追溯 |
| 自动批导致质量问题积累 | 阻断级覆盖 + 升级触发条件覆盖趋势恶化/目标未达成/敏感性 |
| 重生循环不收敛 | kill switch：同一目标连续3次→升级人工 |
| RAG 破坏确定性 | RAG 仅用于低频跨弧检查，不参与上下文组装主干；最终判定由确定性阈值 |
| 双评员成本 | 章级双评仅多一次评分调用（远低于生成成本）；全量可控 |
| L2固定12章与卷长不对齐 | §3.4 层边界对齐规则：L2/L4按固定章数，卷按volume_map，独立确定 |

## 14. 开放问题（实现阶段解决）

1. **锚点库初始规模** — 9类槽位每类3-5个（总计27-45个），实现时按每类首批3个启动，运行中补充
2. **RAG 向量化模型** — bge-large-zh（本地运行），具体版本实现时锁定到 deps.json
3. **重生成功率度量** — 节点1验证时需收集重生成功率数据，若 <80% 需调整重生prompt质量
