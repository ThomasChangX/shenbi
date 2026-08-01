# 正向质量门设计 (Positive Quality Gates)

> **日期**: 2026-06-22
> **状态**: Draft — 待 human partner 审阅
> **范围**: 为 shenbi 新增正向质量评分层（逐章 + 卷/弧），并增强 `foundation-review` 的反套路维度
> **硬约束**: 忽略开发成本；追求产出小说的**最佳质量**与项目 **maintenance 最佳实践**
> **决策来源**: brainstorming 会话（2026-06-22），human partner 已确认全部决策点

---

## 1. 背景与动机

### 1.1 现状：质量的「U 形」缺口

正向质量**只在创世层门控一次**（`foundation-review` 总分 ≥80），逐章阶段**全部是负向/缺陷门**（`review-anti-ai`、`review-continuity`、`review-character` 等 18 个 review skill）。

```
创世层:  foundation-review (正向, 门) ──≥80──┐
                                              │  正向把关只发生在这里
逐章层:  review-* x18 (负向, 缺陷检测) ────────┘  之后只防缺陷，不复评正向
卷/弧层: (无正向门)
```

### 1.2 后果

小说可以以 85 分通过 `foundation-review`，然后**逐章漂向平庸**，中间没有任何机制抓它——因为每个逐章门问的都是「有没有缺陷」，不是「好不好」。这是「**规则干净但平庸**」的 B 类失败，是产出「高质量」小说的核心障碍。

### 1.3 反向教训

`foundation-review` 已证明「**加权 rubric + 证据引用 + 阈值门**」是可行的正向评分模式。本设计把这个模式扩展到**逐章层**与**卷/弧层**，并在创世层补一个反套路维度。

> **更正记录**：brainstorming 早期曾断言「系统没有正向门」。读 `foundation-review` 后更正——它**是**一个成熟的正向门。本设计的缺口定位因此从「没有正向门」修正为「正向只在创世层门控一次，逐章/卷层缺失」。

---

## 2. 设计目标

- **G1** 让「平庸但干净」可被**检测与阻断**。
- **G2** 让质量分数成为**跨章时间序列**，捕获「逐章下滑」漂移——这是二值门结构性看不到的信号。
- **G3** 维护最佳实践：复用现有 `audit_drift` 闭环、frontmatter 契约、DAG、G2/G4 gate、T1 测试框架；**不造并行系统**。
- **G4** 评分可信：**所有评分位置强制独立 agent**。

---

## 3. 设计原则（跨切，A/B/C 共用）

| # | 原则 | 说明 |
|---|------|------|
| P1 | **分数是原语，门是阈值** | 每个正向维度计算 `[0, 满分]` 分数；门 = 校准阈值；**分数恒记录**用于漂移检测。有分数总能派生门，反之不行。 |
| P2 | **上下文校准门** | 阈值由章节/卷的**计划角色**决定（读 plan/memo），不是扁平数字。解决「静章被误杀」。 |
| P3 | **置信度守护** | 评分员报置信度；低置信或分数近阈值（±5）→ **人机复核**，不自动进入重写循环。解决「主观信号噪声→假阻断/死循环」。 |
| P4 | **评分独立性（硬铁律）** | 任何产出分数或审核判断的 skill，**必须在 context-cleaned 独立 subagent 执行**；drafting/planning agent 不得评分。适用于测试**与生产**。 |
| P5 | **锚定校准** | 每维度 3 个参考锚点 fixture（高/中/低分样例），评分员对照锚点打分，压低 LLM 评分漂移。 |
| P6 | **单一数据源** | 套路清单等知识进 `genre-config.json`，不硬编码（呼应去 AI 味的教训）。 |
| P7 | **前向兼容** | 新 skill 在 frontmatter 声明 **field-level reads**（即便当前 DAG 生成器忽略字段），为字段级契约迁移铺路。 |

---

## 4. 架构总览

三层正向评分，分布在不同管线层：

| 层 | 交付物 | 类型 | 现状 | 本设计 |
|----|--------|------|------|--------|
| 创世 | `foundation-review` | 门 (≥80) | 已有（5 维 /100） | **C**: 增「反套路/原创性」维度，再平衡为 6 维 /100 |
| 逐章 | `shenbi-review-resonance` | 校准门 | ❌ 缺 | **A**: 新建，4 维 /100 |
| 卷/弧 | `shenbi-review-arc-payoff` | 门 (≥80) | ❌ 缺 | **B**: 新建，5 维 /100 |

**数据流**：

```
drafting/revision 产出 chapter
   │
   ▼
[review-resonance] (独立 agent) ── 分数 ──┬─→ truth/resonance_trend.md (新, 时间序列)
   │                                      └─→ truth/audit_drift.md (复用, 本章短板)
   │  校准门三路径(§5.4): 明确通过 / 明确失败(自动 revision) / 边界(人机复核)
   ▼
[chapter-planning 下一章] ← 读 audit_drift → PRE_WRITE_CHECK 补「共鸣短板」
   │
   ▼  (卷边界)
[review-arc-payoff] (独立 agent) ── 门 ≥80 ── 放行下一卷 / 阻断+处方；分数入 truth/arc_payoff_trend.md（跨卷漂移）
```

---

## 5. 交付物 A — `shenbi-review-resonance`（逐章正向评分）

### 5.1 数据契约（frontmatter）

```yaml
name: shenbi-review-resonance
description: "Use when a finished chapter needs a positive quality score on emotional landing, presence, prose craft, and reader reward — runs in an independent agent"
requires_independent_agent: true
contract:
  kind: report
  reads:
    - file: chapters/chapter-N.md
      fields: [prose, POST_WRITE_SELF_CHECK]
    - file: plans/chapter-N-plan.md
      fields: [chapter_role, core_task,兑现伏笔]   # chapter_role 驱动校准阈值
    - file: style/style_profile.md
      fields: [voice_fingerprint, sentence_rhythm]
    - file: tests/fixtures/calibration/resonance/*.md   # 锚点
  writes:
    - audits/chapter-N-resonance.md
  updates:
    - truth/audit_drift.md
    - truth/resonance_trend.md
```

> `updates` 表示 append/merge（非覆盖）。

**前置依赖（`chapter_role`）**：校准阈值依赖 `plans/chapter-N-plan.md` 声明 `chapter_role`（高潮/兑现 | 推进/转折 | 过渡/铺垫）。三条路径：
1. **首选**：扩展 `shenbi-chapter-planning` 的备忘模板，强制输出 `chapter_role` 字段（小改动，纳入实现计划）。
2. **回退**：若 plan 未声明，A 按「推进」阈值评 + 报告 flag human 补 role；不得静默降级或跳过。
3. **存量迁移**：现有 fixture（星火燃穹）与在写项目的 chapter plan 缺 `chapter_role` → 实现计划须含一次性回填（由 `chapter-planning` 对存量 plan 补评 role，或人工标注 fixture）。回填完成前回退路径生效；flag **聚合后批量处理**，不做逐章阻塞（避免全项目 mass-flagging 停摆）。

### 5.2 评分维度（/100）

| 维度 | 权重 | 评什么（读者反应信号，非美学判断） | 子地板 |
|------|------|------|--------|
| 情感落地 | 30 | 核心情绪节拍是 show 还是 tell；**命名最强情绪 + 触发行** | —（阈值按角色校准，见 5.3；不设绝对子地板，因角色校准已覆盖） |
| 场景临场感 | 25 | 感官具体性、是否「在场」而非概述 | — |
| 文笔质感 | 25 | 句子级工艺 vs `style_profile` 指纹（**正向**，补 anti-ai 的负向） | — |
| 读者回报 | 20 | 本章给了读者情绪/信息/推进的回报吗（「值不值得读」轴） | — |

### 5.3 校准门逻辑

阈值由 `plans/chapter-N-plan.md` 的 `chapter_role` 决定：

| chapter_role | overall 阈值 | 维度子地板 |
|--------------|-------------|-----------|
| 高潮 / 兑现 | ≥75 | 情感落地 ≥20 |
| 推进 / 转折 | ≥65 | — |
| 过渡 / 铺垫 | ≥50 | 读者回报 ≥12（过渡章也必须给回报） |
| 未声明 | ≥65（默认推进） | + flag human 补 role |

> **子地板 rationale**：高潮章强制「情感落地≥20」（情感交付是高潮章的核心交付物）；过渡章强制「读者回报≥12」（过渡章也必须给读者增量，否则=水章）。推进章不设维度子地板——其主交付维度随情节而变（信息/转折/关系），固定子地板不合理，由 overall≥65 兜底。

**阻断规则**：overall 或任一子地板未达 → **阻断**，按 §5.4 三路径分流。

### 5.4 置信度守护与阻断分流

评分员对每维度报置信度（high/mid/low）+ overall。阻断时分三条路径（明确，消除「clear-fail 走哪」的歧义）：

| 情形 | 条件 | 路径 |
|------|------|------|
| 明确通过 | overall + 全子地板达标 | 放行 |
| 明确失败 | 高置信度 **且** overall 低于阈值 >5 | 自动进入 `chapter-revision`（评分报告 = 修订反馈） |
| 边界/不确定 | overall 置信度 = low，**或** 任一阻断维度分数在阈值 ±5 内 | **人机复核**：human 审阅 →「接受（覆盖阻断）」或「确认阻断 → `chapter-revision`」 |

> 设计意图：只有**边界/不确定**走人因（防主观噪声假阻断死循环）；**明确失败**直接修订（高置信度 + 大幅低于阈值 = 真实缺陷，无需人因把关）。人因只在噪声区介入，不作每章瓶颈。
>
> **修订循环上限（防死循环）**：同一章 resonance 驱动的 revision 最多 2 次。第 3 次重评仍 clear-fail → **升级人因复核**（不再自动 revision）。「评不出来」的章必须人因介入，不得无限重试。

### 5.5 输出格式

```markdown
## 共鸣评分报告

**章节**: 第N章 | **计划角色**: 高潮 | **结果**: 通过 (82/100) / 阻断 (XX/100) / 待人机复核

### 评分明细
| 维度 | 得分 | 满分 | 置信度 | 证据（行号+引述） | 裁判理由 |
|------|------|------|--------|------------------|----------|
| 情感落地 | 22 | 30 | high | `chapter-N.md` L45-52 > … | show，触发行 L48 |
| ... | | | | | |

### 校准门判定
- overall 82 ≥ 高潮阈值 75 ✓
- 情感落地 22 ≥ 子地板 20 ✓
- 判定: 通过

### 共鸣短板（写入 audit_drift）
- [维度] [短板描述] → 下章 PRE_WRITE_CHECK 防范建议

### 趋势（写入 resonance_trend）
- 第 N 章 情感落地 22 | 近 3 章均值 24 | 趋势: 持平
```

### 5.6 与现有负向门的边界（避免重复）

- resonance 只管**体验轴**（情绪/临场/文笔/回报）。
- 节奏**缺陷**（拖/赶）仍归 `review-pacing`；resonance 不单列张力维度（其正向面折进「读者回报」）。
- 伏笔**追踪**归 `review-foreshadowing`；**兑现质量**归 B。
- 遵守「暴露冲突别平均化」：不在多个门重复评同一关注点。

---

## 6. 交付物 B — `shenbi-review-arc-payoff`（卷/弧正向门）

### 6.1 触发

卷边界或弧完成时，由 `volume-consolidation` 调用（或新增 G-type gate 强制）。在卷内所有章节 resonance 通过、consolidation 完成后执行。

### 6.2 数据契约

```yaml
name: shenbi-review-arc-payoff
description: "Use at a volume/arc boundary to gate advancement on arc emotional delivery, foreshadowing payoff quality, thread resolution, expectation-debt settlement, and character arc — runs in an independent agent"
requires_independent_agent: true
contract:
  kind: report
  reads:
    - file: chapters/chapter-(arc_start..arc_end).md
    - file: outline/volume_map.md
      fields: [volume_promise, arc_beats]
    - file: truth/pending_hooks.md
      fields: [resolved_this_arc, carried_forward]
    - file: truth/resonance_trend.md          # 复用 A 的时间序列
    - file: tests/fixtures/calibration/arc-payoff/*.md
  writes:
    - audits/volume-N-payoff.md
  updates:
    - truth/audit_drift.md
    - truth/arc_payoff_trend.md
```

### 6.3 评分维度（/100，门 ≥80）

| 维度 | 权重 | 评什么 | 子地板 |
|------|------|--------|--------|
| 弧情感交付 | 25 | 本卷承诺的情感高潮落地了吗 | — |
| 伏笔兑现质量 | 25 | resolved 的 hook 是惊喜/挣来的，还是敷衍（补 foreshadowing-track「追踪≠爽」缺口） | 15 |
| 线索收束 | 20 | 弧内线索闭合 or 有意携带（非遗忘） | — |
| 期待债务结算 | 15 | **Chase Power 落地点**：读者期待创建 vs 偿还的净债务 | — |
| 角色弧推进 | 15 | 角色有意义变化（非原地踏步） | — |

> **期待债务结算**吸收中优先级「读者期待债务模型」（借鉴 WiiNovel Chase Power），不单造 skill。判定：本章/本卷创建的读者期待（新 hook、新悬念）vs 偿还的期待（兑现、答疑）的净额；长期只创建不偿还 → 扣分。
>
> **`resonance_trend` 的用途**：B 读 `truth/resonance_trend.md` 用于「弧情感交付」维度——本卷逐章情感落地均分作为弧情感一致性的客观佐证（逐章高 → 弧交付可信；逐章大幅波动 → 扣弧情感交付分）。

### 6.4 门逻辑

- overall ≥80 **且** 伏笔兑现质量 ≥15 → 放行下一卷。
- 否则 → **阻断** + 处方（指向具体未交付的弧节拍/敷衍兑现），走人机复核后进入卷级修订。

---

## 7. 交付物 C — `foundation-review` 增「反套路/原创性」维度

### 7.1 动机

防 shenbi house style / 通用大纲——一个结构合规但套路堆砌的大纲会产出结构合规但套路堆砌的小说。

### 7.2 再平衡（保持 /100 与 ≥80 心智模型）

| 维度 | 现权重 | 新权重 | 子地板 |
|------|--------|--------|--------|
| 核心冲突 | 30（地板 18） | **25**（地板 15） | 比例不变 (60%) |
| 开篇节奏 | 20 | 20 | — |
| 世界一致性 | 20 | 20 | — |
| 角色区分度 | 20 | **15** | — |
| 伏笔潜力 | 10 | 10 | — |
| **反套路/原创性** | — | **10（新增）** | — |

> **再平衡 rationale**：新增 10 分从「核心冲突」(−5) 与「角色区分度」(−5) 匀出——核心冲突仍居最高权重（25），地板按比例降至 15（60% 不变）；角色区分度 20→15，因反套路维度已部分覆盖「角色塑造的原创性」，两者相邻、合并让出空间最自然。开篇/世界/伏笔与原创性正交，不动。

### 7.3 评什么

核心设定/弧节拍对照 `genre-config.json` 的 `tropeInventory`（见 8.4），识别过度依赖套路组合。**证据驱动**——指向具体被判定为套路的节拍 + 反套路改写建议。评分工作表与现有五维同构。

---

## 8. 跨切机制

### 8.1 评分独立性（项目级硬铁律）

**规则**：任何产出分数或审核判断的 skill（含全部 `review-*`、`foundation-review`、A、B、T1/T2/T3 评分），**必须在 context-cleaned 独立 subagent 执行**。drafting/planning/consolidation agent **不得**给自己的产出评分。

**现状缺口**：独立性目前在**测试框架**内强制（`dispatch-subagent.sh` + `shenbi-score._provenance`）；**生产 review 未显式强制**。本设计把它上升为项目级铁律。

**落实机制**：
- **frontmatter 标记驱动（确定性判定）**：任何产出评分/审核判断的 skill 在 frontmatter 声明 `requires_independent_agent: true`（A、B、`foundation-review`、全部 `review-*` 均须标记）。dispatcher 据此标记强制判定，**不**依赖对 report 内容的启发式猜测。
- dispatcher 对带 `requires_independent_agent: true` 的 skill 强制走独立 subagent dispatch（清空生成上下文，只传入 reads 文件路径 + rubric + 锚点）。
- 每份评分报告带 `_provenance`（scored_by + 是否独立 dispatch），复用现有 provenance 机制。
- 新 skill 的 SKILL.md「铁律」段显式写明独立性要求。
- **校验**：G2/gate 增加 frontmatter 检查——产出评分的 report 类 skill 必须带 `requires_independent_agent: true`，缺失则 G2 不通过。

### 8.2 锚定校准系统

- 每个正向维度配 3 个锚点 fixture（高/中/低分样例），存 `tests/fixtures/calibration/<dimension>/`。
- 每个 fixture = 短散文摘录 + 期望分数段 + 评判理由。
- **hash 纳入 G0.11 一致性检查**——锚点改动可检测。
- **校准漂移检测**：周期性用当前模型重评锚点；若得分偏离记录的期望段 → flag 校准漂移（模型升级后尤其重要）。这是新增的测试能力。
- **bootstrap 与校验（破鸡生蛋）**：
  - 初始锚点集由 human partner **策展**——从目标题材的优秀/平庸真实文本中选取，人因判定其分数段与理由（人因判断 = 基准）。
  - 评分员（独立 agent）对照锚点打分；与人因基准的偏差即校准信号。
  - 模型升级后重评锚点：若独立评分员与人因基准**系统性偏离** → 更新锚点理由，或 flag 模型不适配。
  - 锚点 fixture 本身纳入 T1 clean 测试（强锚点不得被评低分、弱锚点不得被评高分），保证锚点可被正确识别。
- **锚点数量与方法论（open question）**：3 锚点（低/中/高）对**排序型**判断（高于/低于锚点）可靠；对**精确区间分**存在不确定度。实现计划须验证 3 锚点是否足够——必要时增至 5（加低中/中高）或改用 pair-wise 排序校准。不在此预判。
- **置信度校准**：LLM 评分员自报置信度系统性偏高，不可裸信。以「锚点命中准确率」校验——若评分员对 high 置信判断的锚点命中率 < 阈值（如 80%），降级其后续置信度报告（high→mid）。置信度报告必须经过该校验才用于 §5.4 分流。

### 8.3 跨章漂移检测（resonance_trend.md）

- 新 truth 文件 `truth/resonance_trend.md`：每章 append 一行（章节号 + 各维度分数 + 置信度）。
- 由 `review-resonance` 写入（updates）。
- 漂移检测由 `drift-guidance`（主）或 `chapter-planning` 读取趋势执行，**精确触发条件见下「触发参数与降噪」**（不在此复述模糊定义）。
- **这是分数优于门的核心价值**：门只在踩地板时响，看不见逐章下滑；时间序列能。
- **记录语义（明确，关系漂移检测可信度）**：
  - 记录**最终采纳分**（阻断→修订→重评后通过的分）；被拒绝的修订前低分**不入库**（已拒绝，非真实交付质量）。
  - 人因覆盖放行的弱章：低分**照记**，并附 `human_overridden: true` flag——这是真实质量信号，漂移检测必须看见。
  - `human_overridden` 章节在「下滑/低于均值」统计中**单独标注**：不触发自动纠偏，但进入人因复审队列，避免覆盖数据污染自动判定。
- **触发参数与降噪（明确，否则漂移检测无法实现）**：
  - 逐章信号先做**平滑**：某维度分 = 该章原始分与前后各 1 章的移动均值（3 点窗），平滑后才用于趋势判定，压低单章评分噪声。
  - **边界**：首/末章用 2 点窗（自身 + 唯一邻居）；卷首章**不跨卷**借用上卷末章（跨卷节奏不同），卷首降级为「无前置→自身 + 后置邻居」。
  - **触发条件**（满足任一即写 `audit_drift` 纠偏项）：(a) 某维度平滑分**连续 ≥3 章单调下滑**且累计降幅 ≥3；(b) **本卷已评 ≥6 章时启用**（小样本 σ 不稳定）：某维度平滑分 < 历史均值 − 2σ（历史 = 本卷已评章节），持续 ≥2 章。
  - 人因覆盖（`human_overridden`）章节排除在触发统计外（§记录语义）。
- **跨卷漂移（macro，本设计核心增量）**：
  - 新 truth 文件 `truth/arc_payoff_trend.md`：每卷 append 一行（卷号 + B 的各维度分 + overall）。
  - 由 `review-arc-payoff` 写入（updates）。
  - **触发条件**：连续 2 卷 overall 下滑，或某维度跨卷持续低于首卷均值 − 5 → 写入 `audit_drift` 卷级纠偏，并**阻断下一卷推进**（`volume-outlining` 与章节生成）直至人因介入。
  - **为何 macro 必要**：逐章趋势回答「这章是否在滑」；跨卷趋势回答「**整本小说是否在走向平庸**」——后者是产出「高质量 20 万字」的最终信号，逐章信号无法替代。

### 8.4 套路清单数据源

- `genre-config.json` 新增 `tropeInventory` 段，schema 明确：
  - `trope`：套路名（如「废柴逆袭」「天降系统」）
  - `signatures`：**可识别特征列表**——情节节拍描述 + 关键词/短语（如 `["主角开局被退婚", "获得金手指=系统/老爷爷", "首次展示实力打脸"]`），供评分员做语义 + 关键词匹配
  - `overuse_threshold`：**每大纲/每卷最大命中数**（整数；超出即判过度依赖）
  - `rewrite_hint`：反套路改写方向（字符串）
- **检测机制**：评分员（独立 agent）将大纲节拍对照 `signatures` 做语义匹配，命中数 > `overuse_threshold` → 该维度扣分，并在报告中列出命中的具体节拍 + 对应套路 + `rewrite_hint`。匹配为 LLM 语义判断（非纯正则），因套路是节拍级语义模式。
- 单一数据源（呼应去 AI 味：疲劳词在 `genre-config.fatigueWords`，套路在 `tropeInventory`），不硬编码。

### 8.5 既有 skill 的联动改动（横切，纳入实现计划）

本设计除新增 A/B 外，对既有 skill 有以下支持性联动改动（小改，非行为重写）：

| 既有 skill | 改动 | 服务于 |
|------------|------|--------|
| `shenbi-chapter-planning` | 备忘模板增 `chapter_role` 字段 | A 的校准阈值（§5.1） |
| `shenbi-chapter-drafting` | PRE_WRITE_CHECK 增「共鸣短板」项（读 `audit_drift`） | A 的反馈闭环（§4 数据流） |
| `foundation-review` + 全部 `review-*` | frontmatter 加 `requires_independent_agent: true` | §8.1 独立性铁律 |
| dispatcher | 按 `requires_independent_agent` 强制独立 dispatch | §8.1 |
| G2/gate | 校验评分类 skill 带独立性标记 | §8.1 |
| `shenbi-drift-guidance` / `shenbi-chapter-planning` | 读取 `resonance_trend.md` + `arc_payoff_trend.md`，执行漂移检测（§8.3 触发条件）并写入 `audit_drift.md` | §8.3 |

> **范围说明（M3）**：§8.1 的项目级独立性规则改变**全部现有 review skill** 的生产运行时契约，比「加 A/B/C」范围更广。已确认（决策 #6），但列为横切变更——建议在实现计划中作为**独立子任务**推进，便于回归与回滚。

---

## 9. 错误处理与边界

| 情形 | 处理 |
|------|------|
| 主观信号噪声 → 假阻断 | 置信度守护（5.4）：低置信/近阈值走人机复核，不自动重写 |
| `chapter_role` 未声明 | 默认「推进」阈值 + flag human 补 role |
| 锚点缺失 | 评分降置信度 + flag；不得跳过维度 |
| 评分 agent 非独立（被检测到） | provenance 标记 → 评分作废，重 dispatch |
| 弧内章节未全部 resonance 通过（人因覆盖放行的弱章计为「通过」，带 flag） | B 不执行（前置不满足），flag |
| 评分 dispatch 失败（独立 agent 超时/错误） | 重试（复用 provider 重试）→ 仍失败则该章标 `resonance_pending`，**不阻断 drafting 继续**，入待评队列；**严禁**主 agent 补评 |
| 跨门维度重复（如张力） | 已在 5.6 划界；spec review 时再核一遍 |

---

## 10. 测试策略（适配 T1，不另造框架）

| 测试类型 | 适配方式 |
|----------|----------|
| **generative** | 对 fixture 章节跑 A/B → 产出合规评分报告（全维度有分、证据引述、置信度、门判定正确）。由独立 subagent 按 rubric 打分。 |
| **bug-hunt** | 取 generative 的强章副本，注入 **resonance 专属缺陷**（**非** anti-ai 可抓）：(a) 情绪 show 了但相对备忘「欠交付」（备忘要求震撼，文本只给平淡反应）；(b) 高潮节拍被压平（信息齐备但张力曲线塌）；(c) 读者回报缺失（整章无情绪/信息/推进增量）。**不**注入「他感到愤怒」类 tell（那是 `review-anti-ai` 的 bug-hunt 职责，混淆 = 测试无效）。验证：目标维度跌破角色阈值 **且** 缺陷被定位（行号+证据）。kill switch：未检出 → 0；误判为 anti-ai 缺陷 → 扣分。 |
| **clean** | 强章 → 高分、零幻觉扣分、全维度 PASS。kill switch：任何幻觉扣分 → 0。 |
| **校准锚点测试**（新） | 重评锚点 fixture → 必须落在期望分数段。检测评分模型漂移。 |
| **独立性测试** | 验证评分报告 `_provenance.scored_by` ≠ drafting agent；同 session 评分 → 判废。 |
| **漂移触发单元测试**（新） | 对 `resonance_trend` / `arc_payoff_trend` fixture 序列验证触发逻辑：正例（连续 3 章降 ≥3、低于均值−2σ 持续 ≥2 章、连续 2 卷降）+ 负例（平稳序列），断言**仅正例**写 `audit_drift`。属确定性代码逻辑，必须有单测（非 LLM 评判）。 |
| **置信度校准测试**（新） | 构造 high 置信但锚点命中率 <80% 的评分员 fixture → 断言其后续置信度被降级（high→mid），且 §5.4 分流路径随之从「自动 revision」变「人机复核」。 |
| **套路检测测试**（新） | 对 `tropeInventory` fixture + 含/不含套路节拍的大纲 → 断言命中数正确、超 `overuse_threshold` 扣分、报告列出命中的具体节拍 + 对应套路 + `rewrite_hint`。 |
| **阻断分流与循环上限测试**（新） | 对 §5.4 三路径 + 2 次修订上限的确定性逻辑做单测：构造 (明确通过 / 明确失败 / 边界) 评分 fixture → 断言分流正确；构造连续 3 次 clear-fail → 断言第 3 次升级人因、不再自动 revision。 |

> foundation-review 的现有 T1 测试设置是模板——它已解决「怎么给正向 rubric 写 T1」。

---

## 11. 维护实践

- **复用清单**：audit_drift 闭环、frontmatter 契约、DAG、G2/G4 gate、T1 三类测试、`shenbi-score._provenance`、`dispatch-subagent.sh`、G0.11 hash 检查。**不引入并行基础设施。**
- **单一数据源**：套路 → `genre-config.tropeInventory`；锚点 → `tests/fixtures/calibration/`；逐章趋势 → `truth/resonance_trend.md`；跨卷趋势 → `truth/arc_payoff_trend.md`。
- **field-level reads 前向兼容**：A/B 的 frontmatter 声明字段级 reads，为中优先级「字段级契约」迁移建立先例（当前 DAG 生成器可忽略字段，不阻塞）。
- **版本与 hash**：锚点 fixture hash 入 G0.11；评分报告带 `_provenance`；`resonance_trend.md` 是 append-only 时间序列，可回放。
- **独立性铁律文档化**：写入 `using-shenbi` 与各 review skill 的铁律段。

---

## 12. 非目标（scope 纪律）

本 spec **不**做：

- 字段级契约的**全量迁移**（中优先级 #4）——只通过 A/B 的 frontmatter 建立模式。
- 独立 Chase Power skill——折进 B 的「期待债务结算」维度。
- 替换任何现有负向门——只**加**正向层。
- 定义 T4「作品质量」rubric——但校准机制与人机复核路径是 T4 兼容的雏形。
- LLM 成本/耗时埋点（独立优化项）。

---

## 13. 风险与未决

| 风险 | 缓解 |
|------|------|
| 正向评分天然比确定性门噪声大 | 置信度守护 + 锚点校准 + 人机复核（不消除，但可控） |
| 锚点按题材/风格定制，换题材需重制 | 接受（忽略成本）；锚点 fixture 可版本化、可复用 |
| 独立性要求增加编排复杂度（每次 review 都 dispatch） | 接受（忽略成本，换可信度）；复用现有 dispatch 机制 |
| 评分模型升级导致校准漂移 | 校准锚点重评测试（8.2）检测 |
| `resonance_trend.md` 无限增长 | append-only；卷边界由 `volume-consolidation` 将本卷趋势快照（均值/最低分/下滑章号）写入卷总结，原始逐章行归档到 `truth/archive/resonance_trend-volume-N.md`；主文件只保留最近 2 卷逐章明细 |
| 主观正向门能否在 T1 稳定 ≥94（foundation-review 模式可迁移性的前提） | open question；实现计划先验证 foundation-review 现有 T1 分数稳定性，再决定 A/B rubric 粒度。若主观 rubric 难达 ≥94，下调该类 skill 的 tier 门槛或改用相对评分 |

---

## 14. 决策记录（traceability）

| # | 决策 | 选择 | 来源 |
|---|------|------|------|
| 1 | 逐章正向用门还是分 | **上下文校准的门**（计划高潮章高阈值、过渡章低阈值）+ 置信度守护 + 分数恒记录用于漂移检测 | human 确认（原 advisory 方案被驳回，改为校准门）|
| 2 | 期待债务(Chase Power) 形态 | 折进 B「期待债务结算」维度，不单造 skill | human 确认 |
| 3 | foundation-review 维度调整 | 再平衡为 25/20/20/15/10/10，新增「反套路/原创性」10 | human 确认 |
| 4 | 套路清单位置 | 进 `genre-config.json` 新 `tropeInventory` 段 | human 确认 |
| 5 | 校准锚点 | 存 `tests/fixtures/calibration/` + hash 入 G0.11 | human 确认 |
| 6 | 评分独立性 | **所有评分位置强制独立 agent**（测试 + 生产），主 agent 评分不可信 | human 确认（升级为项目级铁律）|

---

## 15. 后续

本 spec 经 human partner 审阅通过后，转入 `writing-plans` skill 产出实现计划。
