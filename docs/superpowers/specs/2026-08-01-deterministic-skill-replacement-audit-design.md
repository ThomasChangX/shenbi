# 确定性技能替换审计：何时把 skill 从 LLM 提升到 Python

> **Date:** 2026-08-01
> **Status:** Design
> **Severity:** 🟡 Medium（架构层优化，非阻塞；但单条候选 payoff 最高——消除 1 次不必要 dispatch = 省 100% 该调用 token）
> **方法:** [`systematic-debugging`](archive/2026-07-19-06-llm-context-engineering-design.md) skill 四阶段
> **系列:** Token 效率全栈 audit（子 spec 2/3，隶属总纲 [`...read-write-consistency-audit-design.md`](2026-08-01-pipeline-read-write-consistency-audit-design.md) §0 分工）
> **依赖:** 总纲 spec；`src/shenbi/skill_utils/`（9 个已存在的确定性助手）；`src/shenbi/pipeline/{context_assemble,truth_io,hook_planting,scr_extractor}.py`；archive `2026-07-19-01`（覆盖 vs 追加 postmortem）
> **范围:** 本 spec 只审 **"这个 LLM 调用本身是否必要"**——能否用确定性 Python 替代（部分或全部）。**不审** prompt 内容（总纲）、不审调用参数（推理控制 spec）、不审输出浪费（输出侧 spec）。
> **核心洞察（决定本 spec 框架）:** "确定性替换"不是假设性维度——**repo 已 9 次实现该模式**（`skill_utils/` + `pipeline/` 助手），且 repo 自有 postmortem 证明确定性写路径是最高严重缺陷（CN3 覆盖 bug）的根因修复。因此本 spec 不是"要不要引入"，是"把提升判据形式化 + 逐候选评估剩余 skill"。

---

## 1. 背景：repo 已有的三层架构与 9 个先例

### 1.1 三层架构（已半形式化）

archive `2026-06-22-positive-quality-gates.md:7` 定义了 repo 的 canonical 分层：

| 层 | 位置 | 职责 |
|---|---|---|
| L1 确定逻辑 | `src/shenbi/skill_utils/` + `src/shenbi/pipeline/` | 漂移触发、置信度校准、块路由、trope 匹配——tested Python |
| L2 skill 行为 | `skills/*/SKILL.md` | LLM 执行的技能指令 |
| L3 输出校验 | `gates/g4/` | 结构性后置校验 |

本 spec 审的是 **L2→L1 的提升判据**：何时一个 skill（L2）的核心功能应迁移到 Python（L1）。

### 1.2 已存在的 9 个确定性先例（证明模式成立）

| 助手 | 替代/包裹的 LLM 工作 | 文件 |
|---|---|---|
| `context_assemble.py` | context-composing 的 3 路检索+rerank+budget 组装 | `src/shenbi/pipeline/` |
| `scr_extractor.py` | 章节实体抽取（位置/对话/情绪关键词） | `src/shenbi/pipeline/` |
| `truth_io.py` `write_truth_file()` | truth 文件键值 upsert（替代 LLM 全量重发） | `src/shenbi/pipeline/` |
| `hook_planting.py` | 伏笔 ID 生成 + upsert | `src/shenbi/pipeline/` |
| `recall.py` | 伏笔召回阈值过滤 | `skill_utils/foreshadowing_recall/` |
| `compute_pattern.py` | 13 模式 + 熵 + 单调性统计（LLM 只做分类） | `skill_utils/chapter_pattern/` |
| `compute_stats.py` | 风格统计 | `skill_utils/style_learning/` |
| `triggers.py` | 记忆蒸馏触发条件（chapter%12==0） | `src/shenbi/pipeline/` |
| `decisions_validator.py` | decisions.json schema 校验 | `gates/g4/` |

### 1.3 关键先例：CN3 postmortem 证明确定性写路径是根因修复

archive `2026-07-19-01-truth-file-and-state-accumulation-design.md:42,176,283`：CN3（truth 文件覆盖 vs 追加）的根因是**写路径缺陷**（substring dedup），修复是 `truth_io.py:write_truth_file(mode="upsert_markdown_row")` 的键值 upsert——确定性路径**结构性消除**失败模式，而 prompt-only 守卫（"告诉 LLM 要追加"）被证明不够。这是"提升到 L1"的最强论据。

---

## 2. 提升判据（Phase 1 — 形式化何时提升）

一个 skill 的 LLM 调用应迁移到 Python，当且仅当其核心功能落入以下任一类别（且 `requires_independent_agent` 不为 true）：

| 判据 | 含义 | 确定性程度 |
|---|---|---|
| **纯文件操作** | cp/glob/列表/hash，无变换 | 100% |
| **键值 upsert** | 按自然键去重合并 | 100% |
| **计数/tally** | 跨文件统计 | 100% |
| **固定模板填充** | 从已知输入填固定模板 | 100% |
| **阈值比较** | 触发条件判定 | 100% |
| **结构字段聚合** | 从已有结构化文件聚合字段 | 100% |
| **语义抽取** | 从自由文本抽结构化事实 | ~30%（关键词命中部分，语义需 LLM） |
| **叙事综合** | 多源压缩成连贯叙述 | 0%（LLM 不可替代） |

**反判据（不提升）：** `requires_independent_agent: true` 的 skill（全部 review-* / score-* / drift-guidance / escalation-review / chapter-pattern）——其价值就是独立判断，确定性化即丧失存在意义。

---

## 3. 候选评估（Phase 2 — 逐 skill 6 字段 + 可行性）

### 3.1 `shenbi-snapshot-manage` —— 最干净的全替换候选

- **核心功能**：章节完成快照的 create/view/rollback/list——cp truth+章节到 `snapshots/chapter-NNN/` + manifest + SHA-256。
- **是否确定**：**100%**。每步机械：cp/glob/列表/hash。SKILL.md **自己禁止 LLM 算 checksum**（`:156-164`，要求 `python3 -c "import hashlib..."`）。
- **确定性 vs 创意**：100/0。无综合、无判断、无反合理化守卫依赖 LLM。
- **为何现用 LLM**：纯样板便利——一切 dispatch 为 LLM 调用，此 skill 无推理内容。
- **替换破坏什么**：无。人工确认 rollback 是策略门，非 LLM 能力。
- **token 成本**：每章 ~10-15K tokens（读 truth+章节 ~30-40KB 纯为 cp）——**纯 pass-through 浪费**。
- **可行性**：**立即**。SKILL.md 已近 Python spec。无 G4 checker（无 `gates/g4/snapshot*.py`），checksum 往返断言即可。
- **风险**：无（policy 不禁；`kind: artifact`，无 `requires_independent_agent`）。
- **验证**：`tests/pipeline/test_snapshot_diff.py` 已存在；加 checksum 往返属性测试。

### 3.2 `shenbi-context-composing` —— pipeline 模式下 85% 已确定

- **核心功能**：从 12 truth/plan/style 文件组装 9 节上下文包（P1-P7 + 结尾多样性 + 钩子债）供 drafting。
- **是否确定**：**~85%**。`context_assemble.py` **已实现** 3 路检索（Route A 实体索引 w=1.0 / Route B embedding w=sim×0.8 / Route C 固定文件 w=0.6）+ `rerank_results`（权重序 + content-hash 去重）+ budget 裁剪。SKILL.md 自认（`:109-118` Pipeline 集成模式）：pipeline 模式下此 skill 职责缩为"去重/冲突检测/budget 裁剪"。
- **确定性 vs 创意**：~85/15。机械：载 P1-P7、取近 8 章、hash 去重、数钩子沉默 `(current-last_reinforced)/max_distance`。唯一软点：判"哪 ≤5 世界规则最相关"（top-5-by-frequency 可替）+ 结尾 3 桶分类（hook/transition/cliffhanger，可启发式或 LLM 标一次缓存）。
- **为何现用 LLM**：样板 + 非 pipeline 直 dispatch 路径（无编排器预算装）。
- **替换破坏什么**：极少。9 节 markdown 格式化（模板填充）+ 钩子债表渲染都平凡可模板化。
- **token 成本**：~18K tokens/次 × 56 章 ≈ **~1.0M tokens——单 skill 最大浪费之一**。
- **可行性**：**强**。`context_assemble.py` 是 pipeline 主路径；LLM skill 是遗留直 dispatch 兜底 + 表面策展。auto-check 不变量（9 节、无 3 连续结尾、钩子有路径）将从 G4 后置检查变成生成保证。
- **风险**：低-中（结尾分类软点需验证）。
- **验证**：`tests/unit/gates/g4/test_context_composing.py` 验 9 节/计数不变量；`context_assemble.py` 由 `tests/pipeline/` 覆盖。

### 3.3 `shenbi-state-settling` —— 写半路径已落地，抽取留 LLM

- **核心功能**：章节后抽 9 类变化（位置/资源/关系/情绪/信息流/情节线/时间/身体/行为）写 6 truth 文件。
- **是否确定**：**写半 100%，抽取半 ~30%**。
  - 写（upsert）半：**完全确定**。给定抽取记录 + 自然键（章号/hook_id），合并是纯键去重——`truth_io.py:write_truth_file()` 已实现（433 行测试 `tests/unit/pipeline/test_truth_io.py`）。
  - 抽取半：**不确定**。自由文本（"师姐苏晴: 观望→认可"）→ 结构化关系态增量需阅读理解。`scr_extractor.py` 试过确定性抽取但**显式放弃语义类**——只抽位置/对话关键词/情绪标记，`confidence: 0.7`、`character: "unknown"` 频繁。
- **确定性 vs 创意**：~50/50。写 100% 确定；抽取 30% 机械（名/hook ID/位置，scr_extractor 覆盖）+ 70% 语义。
- **为何现用 LLM**：(a) 语义抽取真需推理；(b) 历史 dispatch 路径强求全量发文。CN3 postmortem（§1.3）：失败是 prompt-only 守卫无程序强制。
- **替换破坏什么**：纯 Python 抽取会漏 9 类大多数（`scr_extractor.py` 已证明）。人工审批门（逐项 checkbox + 原文引用）是反合理化守卫，确定路径会绕过。
- **根因裁定（关键）**："覆盖 vs 追加"有两诊断：(1) 上下文工程 spec §2.3 说"上下文不足"→补上下文；(2) accumulation postmortem 说"写路径缺陷"→确定性 upsert。**哪个治根因？** 确定性写路径**结构性消除**失败（即使 LLM 发全文件，`write_truth_file(mode="upsert_markdown_row")` 按键去重保历史）；补上下文只**降概率**。**repo 已选确定性路径**——`truth_io.py` 已落地，`dispatch_helper.py:1030-1037` 文档说 append_dedup 是 caller 责任。故 state-settling 现实替换范围 = **写半（已落地），非全抽取（不可行）**。
- **token 成本**：~9K tokens/次 × 56 ≈ 504K tokens。
- **可行性**：写半已完成；抽取留 LLM 是正确定位。
- **风险**：全抽取替换被 `scr_extractor.py` 的局限证伪——不可行。

### 3.4 `shenbi-memory-distill` —— 结构字段聚合确定，800 字叙事留 LLM

- **核心功能**：每 12 章蒸馏 `chapter_summaries.md` → 弧综合（`truth/arcs/arc-N.md`）；每 36 章 → 层综合；卷边界 → book spine 前滚。
- **是否确定**：**否（整体）**，但**可拆**。
  - 结构字段（钩子兑现表、角色态表、未解悬置列表）：**确定可聚合**——从 `pending_hooks.md`/`character_matrix.md` 直接聚合。
  - ~800 字事件链叙述：**LLM 不可替**——压缩 12 章摘要成可溯源叙述正是 LLM 所长（铁律 #1：每条合成结论可溯源）。
- **确定性 vs 创意**：~30/70。
- **可行性**：**部分替换**——拆成"确定性聚合结构字段"+"LLM 只写叙述段"。
- **token 成本**：每 12/36 章跑一次，56 章 ~5-9 次——频率低，绝对 payoff 小于 context-composing/state-settling。

### 3.5 不提升（反判据示范）

全部 `review-*`（24）、`score-*`（3）、`chapter-drafting`、`chapter-revision`、`drift-guidance`、`escalation-review`、语义抽取核——价值就是独立判断/创意生成，`requires_independent_agent: true` 或本质需推理。

---

## 4. 模式分析（Phase 3）—— 跨候选规律

| 规律 | 成员 | 含义 |
|---|---|---|
| **纯 pass-through 浪费** | snapshot-manage | LLM 读文件只为 cp——零变换，纯浪费 |
| **"helper 已存在，skill 是遗留兜底"** | context-composing | pipeline 主路径已确定，skill 降为表面策展 |
| **"写半已落地，抽取半不可行"** | state-settling, truth-sync | 确定性写路径治根因；语义抽取是 LLM 不可替核心 |
| **"结构字段确定，叙述留 LLM"** | memory-distill, foreshadowing-lifecycle | 可拆——确定性聚合结构 + LLM 写叙述 |

---

## 5. 假设与验证（Phase 3）

| 候选 | 假设 | 验证 |
|---|---|---|
| snapshot-manage | Python 替换后 checksum 往返一致，G4 无需 | 加属性测试；跑 round 对比快照完整性 |
| context-composing | pipeline 模式下 LLM 只做表面策展，去掉后 G4 仍 PASS | 关 LLM 策展层，跑 G4 对 9 节不变量 |
| state-settling 写半 | `truth_io.py` 已消除覆盖 bug | `test_truth_io.py` 433 行已验 |
| memory-distill 拆分 | 结构字段聚合 + LLM 叙述 = 全功能 | 拆分跑 round 对比弧文件完整度 |

---

## 6. 修复方案（Phase 4）

### 6.1 P0（纯浪费，立即）

| 候选 | 修复 | payoff |
|---|---|---|
| snapshot-manage | 提升为 `src/shenbi/pipeline/snapshot.py` CLI；dispatch 改调 Python；skill 标 deprecated 或保留仅非 pipeline 兜底 | 省每章 ~10-15K pass-through token |

### 6.2 P1（helper 已存在，接主线）

| 候选 | 修复 | 风险 |
|---|---|---|
| context-composing | pipeline 模式下 context_assemble.py 产出直接用；LLM skill 只在非 pipeline 兜底；auto-check 不变量转生成保证 | 低-中（结尾分类软点） |

### 6.3 P2（拆分，需验证）

| 候选 | 修复 | 风险 |
|---|---|---|
| state-settling | 显式化"写半确定（truth_io.py）+ 抽取半 LLM"分层；文档 + 契约反映 | 低（写半已落地） |
| memory-distill | 拆"确定性结构字段聚合"+"LLM 800 字叙述"两半 | 中（需保证铁律 #1 可溯源） |

### 6.4 显式不提升（反判据）

review-* / score-* / drafting / revision / 语义抽取核——见 §3.5。

---

## 7. 验证标准（数值化）

| 标准 | 当前 | 目标 |
|---|---|---|
| snapshot-manage dispatch 次数/章 | 1 LLM | 0 LLM（Python） |
| context-composing pipeline 模式 LLM 调用 | 1（含表面策展） | 0 或仅非 pipeline 兜底 |
| 被 `requires_independent_agent` 保护的 skill 误替换数 | — | 0 |
| `just check` | PASS | PASS |

---

## 8. 铁律（4 条）

1. **纯文件操作不调 LLM。** cp/glob/hash/列表类 skill 必须是 Python；LLM 读文件仅为 cp 是 100% 浪费。
2. **确定性写路径是覆盖 bug 的根因修复。** prompt-only 守卫（"告诉 LLM 要追加"）不够；键值 upsert（`truth_io.py`）结构性消除失败。
3. **语义抽取是 LLM 不可替核心。** `scr_extractor.py` 的局限证明纯 Python 抽不全；state-settling 的正确分层是"写半确定 + 抽取半 LLM"。
4. **`requires_independent_agent` 的 skill 不确定性化。** review/score 的价值是独立判断；确定性化即丧失存在意义。

---

## 9. 依赖关系图

```
总纲 spec（决策原则、Cluster B 契约脱节归口）
    │
    ├─ §1.2 先例（9 助手）──► 证明模式成立
    ├─ §1.3 CN3 postmortem ──► 证明确定性写路径治根因
    ├─ 3.1 snapshot-manage ──► P0 提升到 snapshot.py
    ├─ 3.2 context-composing ──► P1 context_assemble.py 接主线
    ├─ 3.3 state-settling ──► P2 写半已落地（truth_io.py）
    └─ 3.4 memory-distill ──► P2 拆结构字段/叙述

P0/P1 实施前需另写 plan 并批准
```
