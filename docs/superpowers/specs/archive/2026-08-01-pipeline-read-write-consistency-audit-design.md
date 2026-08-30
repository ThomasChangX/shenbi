# Pipeline 读写一致性与 Token 效率审核：全栈 audit 总纲

> **Date:** 2026-08-01
> **Status:** Design（总纲）
> **Severity:** 🟠 High（系统性效率与契约一致性缺陷，非 P0 阻塞）
> **方法:** [`systematic-debugging`](../archive/2026-07-19-06-llm-context-engineering-design.md) skill 的四阶段方法论（Root Cause → Pattern → Hypothesis → Implementation）—— 先定位根因，再谈修复
> **系列:** Token 效率全栈 audit（第三轮，承接 archive `2026-07-17-reduce-token-waste` / `2026-07-18-optimize-llm-context` / `2026-07-19-06-llm-context-engineering`）
> **依赖:** 上述 3 归档 spec；G4 结构校验门；`src/shenbi/pipeline/dispatch_helper.py` / `audit_layer.py` / `src/shenbi/cost/`
> **决策原则:** 质量 > token > 速度，但不应有浪费。即——能砍的只有"砍掉后 G4/gate 仍 PASS"的部分；凡是 gate FAIL 的上下文，无论多冗余都是必要保留或待去冗。
> **Purpose（总纲）:** 本 spec 是 Token 效率全栈 audit 的**总纲**——定义全局决策原则、四 spec 分工边界、跨 spec 根因簇图；并保留**输入侧（读/写/system prompt）的 10 条 findings**（§3）。三个子 spec 各自极致专注一个独立维度：[推理控制](2026-08-01-inference-control-audit-design.md)（采样/模型/重试）、[确定性替换](2026-08-01-deterministic-skill-replacement-audit-design.md)（skill→Python）、[输出侧浪费](2026-08-01-output-side-waste-audit-design.md)（重试放大/审计冗余/revision raw glob）。

---

## 0. 全局决策原则与四 spec 分工

### 0.1 决策原则（全栈共用）

质量 > token > 速度，但不应有浪费。**G4/gate 是唯一质量裁判**：

| 砍某项后 G4/gate | 分类 | 处置 |
|---|---|---|
| 仍 PASS | 真浪费（P0） | 直接砍 |
| FAIL，内容可由他处覆盖 | 冗余待去重（P1） | 去重前验证覆盖成立 |
| FAIL，无替代 | 必要上下文 | 保留，登记"不砍" |

### 0.2 四 spec 分工边界

| spec | 维度 | 核心问题 | findings 数 |
|---|---|---|---|
| **本总纲** | 输入侧（reads/writes/system prompt） | prompt **内容**里有什么浪费？ | 10（§3） |
| [推理控制](2026-08-01-inference-control-audit-design.md) | 调用方式（采样/模型/重试/截断） | 模型**怎么被调**？ | 10 |
| [确定性替换](2026-08-01-deterministic-skill-replacement-audit-design.md) | 调用必要性（LLM→Python） | **这个调用本身是否必要**？ | 4 候选 + 判据 |
| [输出侧浪费](2026-08-01-output-side-waste-audit-design.md) | 输出 token（重试放大/审计冗余） | LLM **产出**什么浪费？ | 4 |

### 0.3 折叠维度（证据不足独立成 spec，归此）

3 个待审维度经 deep-dive 证明**不够格**独立成 spec，折叠归入相关 spec：

| 维度 | 归属 | 理由 |
|---|---|---|
| provider prompt-cache | 本总纲 §3.9（已含）+ 推理 spec 无独立 | 仅"无显式 cache_control 标记"是新颖点；DeepSeek 自动缓存兜底；余与 §3.9 重叠 |
| 并行效率 | 推理 spec §2.10（折叠段） | SharedAuditContext 省 disk-IO 不省 token（误解澄清，1 段）；n=1 正确；semaphore 是吞吐非 token |
| 审计器去冗余 | 输出侧 spec §2.2（F9） | 已在输出侧 spec 内覆盖 |

---

## 1. 背景与方法

### 1.1 三轮承接关系

archive 中已有三轮 Token 效率设计：

| 轮次 | spec | 侧重 | 已落地 |
|---|---|---|---|
| 第一轮 | `2026-07-17-reduce-token-waste-design.md` | 量化浪费（~35%/章）+ 可观测性 | 部分（TokenLedger 类存在） |
| 第二轮 | `2026-07-18-optimize-llm-context-design.md`（782 行） | 逐 skill 上下文审查 + 13 项行业实践修复 | 多数落地，2 项 dead-wire |
| 第二轮.实施 | `2026-07-19-06-llm-context-engineering-{design,plan}.md` | 修 3 bug + 4 架构缺陷，目标 −40%/章 | 7/13 落地（见 §2） |

本 spec **不复述**上述设计的论证，只做两件它们都没做的事：

1. **审计审计者** —— 逐项复核前两轮 13 项提议的**实际代码落地状态**，用 `file:line` 落证。这是本 spec 的核心新贡献：前两轮都是"设计 + 计划"，从未做过一次"事后核验哪些真接进派发路径了"。
2. **补 5 类前两轮漏掉的根因** —— 全部来自本轮 7 个并行 Explore agent 的新证据（详见 §3）。

前两轮 spec 的设计论证仍作参考；本 spec 在 §2 用"落地状态表"接管它们的跟踪职责。

### 1.2 决策原则的工程含义

"质量 > token > 速度，但不应有浪费"翻译成可执行判据：

| 砍掉某上下文后 G4/gate 表现 | 分类 | 处置 |
|---|---|---|
| 仍 PASS | **真浪费**（P0） | 直接砍，零质量风险 |
| FAIL，但内容可由其它 read 覆盖 | **冗余待去重**（P1） | 去重前必须验证"覆盖"成立 |
| FAIL，且无替代来源 | **必要上下文** | 保留，显式登记为"不砍" |

G4/gate 是唯一裁判；spec 不主观判断"质量"。

### 1.3 证据来源

7 个并行 Explore agent（"very thorough"），全部 `file:line` 落证（Agent-1–4 为核心审计组，Agent-5/6/7 为全栈扩展，撑起三子 spec）：

- Agent-1：dispatcher 派发 I/O 路径（`dispatch_helper.py` / `audit_context_cache.py`）
- Agent-2：73 个 `shenbi-*` skills 的 `reads:` / `writes:` 契约面（268 reads / ~140 writes）
- Agent-3：prompt 体量与 boilerplate（73 SKILL.md body 度量）
- Agent-4：前两轮 13 项提议的实现态复核（grep + 读源码核验）
- Agent-5/6/7（全栈扩展）：推理控制层 / 确定性替换可行性 / 输出侧 + provider cache + 并行的 deep-dive（撑起三子 spec + 折叠决策）

### 1.4 跨 spec 根因簇图（全栈视图）

本 audit 跨四 spec 共发现 **28 条 findings**（总纲 10 + 推理 10 + 确定性 4 候选 + 输出 4）。它们归为 **5 个跨 spec 根因簇**——单点修不如修模式：

```
Cluster A "dead wiring"（infra 写了，派发路径漏接/绕过）
  ├─ 总纲 §3.1  TokenLedger.record() 零 caller
  ├─ 总纲 §3.2  SharedAuditContext 漏接 serial audit_layer
  ├─ 推理 §2.9  finish_reason=length 完全未检测（截断输出当成功写盘）
  └─ 输出 §2.1  重试预算无计量（依赖总纲 §3.1 接线）

Cluster B "契约↔正文脱节"（codegen/契约与 body 演进不同步，无一致性门）
  ├─ 总纲 §3.5  5/7 dead decisions sidecar 违反 AGENTS.md §73
  ├─ 总纲 §3.6  escalation-review 3 dead reads
  ├─ 总纲 §3.8  auto-gen 数据契约+AUTO-CHECK 块重复 frontmatter
  └─ 推理 §2.5  pro↔flash doc drift（plan 写 pro，代码 flash）

Cluster C "重复传输"（无跨调用缓存/聚合层）
  ├─ 总纲 §3.3  跨 dispatch 无缓存，同章 truth 重发 5+ 次
  ├─ 总纲 §3.7  字段级 reads 覆盖 13%，大文件全发
  ├─ 总纲 §3.9  system prompt 每次 dispatch 全文重发
  ├─ 推理 §2.6  G4 重试全量重发 prompt
  ├─ 输出 §2.2  审计器交叉冗余（同缺陷 5 份报告）
  └─ 输出 §2.3  revision 读 raw glob 无去重 ~60-120KB/次

Cluster D "调用方式浪费"（推理 spec 专属）
  ├─ 推理 §2.1  判别任务跑创意温度（21 review + 3 score 默认 0.7）
  ├─ 推理 §2.2  max_tokens 双向错（review 头部空 / drafting 撑满截断）
  └─ 推理 §2.4  单点模型服务全部 task type

Cluster E "输出放大"（输出 spec 专属）
  ├─ 输出 §2.1  坏章最坏 ~6 章等价输出 + 3 审计波
  └─ 输出 §2.4  dead sidecar 产出 completion token
```

**簇分析价值**：Cluster A 全靠"补派发路径接线"修；Cluster B 全靠"加契约一致性 gate"修；Cluster C 全靠"引入跨调用缓存/聚合层"修。跨 spec 看簇 = 修模式而非修单点。

### 1.5 确定性替换的独立位置

[确定性替换 spec](2026-08-01-deterministic-skill-replacement-audit-design.md) 不归上述 5 簇——它是**正交维度**：不问"prompt/调用有什么浪费"，而问"这个 LLM 调用本身是否必要"。其 4 候选（snapshot-manage/context-composing/state-settling/memory-distill）的 payoff 是 **100% 消除该调用 token**，是单条 payoff 最高的方向。

---

## 2. 实现态审计（Phase 1 — 前两轮 13 项落地复核）★ 核心新贡献

### 2.1 已落地（7 项，简表）

| # | 提议来源 | 内容 | 落地证据 |
|---|---|---|---|
| 1 | 07-18 §3.7 | 优先级加权截断 | `dispatch_helper.py:210` `_FILE_PRIORITY_WEIGHTS` / `:232` `_get_priority` / `:251` `_budgeted_truncate` / `:577` 调用 |
| 2 | 07-18 §3.7 | 每文件 + 总字符上限 | `dispatch_helper.py:194-195`（`_INPUT_MAX_CHARS_PER_FILE=32000` / `_INPUT_MAX_CHARS_TOTAL=128000`）/ `:570,577,583-590` 强制（总预算门 `:570`、截断调用 `:577`、per-file cap `:583-590`） |
| 3 | 07-19-06 | 非 drafting 剥离 META 块 | `dispatch_helper.py:139` `_strip_meta_for_non_drafting` / `:543` 调用（注释称省 16-31%） |
| 4 | 07-18 §3.1 | reads glob 展开 | `dispatch_helper.py:354` `_resolve_read_path` / `:366` `glob_module.glob` / 专用测试 `tests/pipeline/test_dispatch_helper_glob.py` |
| 5 | 07-18 §3.3 | 输入 `<document>` XML 包裹 | `dispatch_helper.py:669-674`（`:673` `<` 转 `\u003c` + `:674` `<document>` 包裹）/ 专用测试 `test_dispatch_helper_xml.py` |
| 6 | 07-18 §3.6 | 字段级 reads 过滤 | `src/shenbi/contracts/fields.py:83` `filter_to_fields` / `dispatch_helper.py:541` 调用 |
| 7 | 07-18 §3.8 | 审计级联早退 | `chapter_loop.py:327` `_should_skip_audit`（N 章连续 PASS 的启发式，**非原案"core PASS 即跳"——实为部分落地，语义更保守**）/ `:2545` 过滤 |

### 2.2 部分落地（2 项，详述）

#### 2.2.1 SharedAuditContext 仅接 parallel wave，serial `audit_layer` 漏接

`SharedAuditContext`（`audit_context_cache.py:17`）+ `build_shared_audit_context`（`:45`）已实现，一次性预算 `world_rules` / `character_matrix` / `style_profile` / `pending_hooks`。但接线**只到 parallel 审计波**：

- `chapter_loop.py:2558`（Wave 1 core）+ `:2582`（Wave 2 genre）通过 `ReviewTask(..., shared_context=shared_ctx)` 注入 → `dispatch_helper.py:548-560` 消费缓存字段。
- **serial 审计路径 `audit_layer.py:150` `run_audit_layer` 不传 `shared_context`** —— 它对每个 active skill 直接 `dispatch_skill`（`:170`），`dispatch_skill` 形参上接受 `shared_context`（`dispatch_helper.py:1607` def / `:1616` 形参）但调用方从未传。

**后果**：boundary-circle / genre-circle 走 serial 的审计器**各自重新从盘 read_text** 同一批 truth 文件，parallel 波省下的 I/O 在 serial 波全数吐回。

#### 2.2.2 TokenLedger.record() 永无 caller —— cost 报告恒空

`TokenLedger`（`cost/ledger.py:35`）+ `record()`（`:45`，写 `cost/token-ledger.jsonl`）+ `iter_records` / `summarize` 读侧完整。但：

- `record()` 在整个 `src/` 树**零调用点**（grep 仅命中定义行 + 测试 `tests/unit/cost/test_ledger.py`）。
- 运行时 `_record_token_usage`（`dispatch_helper.py:1246-1263`）只更新**内存** `state.token_usage` dict，**从不落盘**。
- 读侧 `report.py:40` 只调 `summarize()` —— 读一个永不被写的文件。

**后果**：整套 cost 基础设施"看起来完整"，但任何 round 后 `cost/token-ledger.jsonl` 恒空，`shenbi-cost-report` 输出全零。这是本轮最欺骗性的发现——单元测试通过（测的是类本身），集成上却是 dead-wire。

### 2.3 未落地 / 死码（4 项）

| # | 提议来源 | 内容 | 状态 |
|---|---|---|---|
| 8 | 07-18 §3.5 | 世界文件确定性摘要器 `world_summarizer.py` | **未实现**——无此文件；`audit_context_cache.py:84` 的 `_summarize_if_large` 只是 `text[:max_chars]` 裸截断 |
| 9 | 07-18 §3.9 | 共享 skill 内容 `skills/_shared/*.md` | **未实现**——无 `_shared` 目录 |
| 10 | 07-18 §3.12 | 上下文新鲜度校验 `_validate_context_freshness` | **未实现**——grep 无命中 |
| 11 | 07-18 §3.10 | 三级指令层次 `_inject_instruction_hierarchy` | **死码**——`dispatch_helper.py:714` 定义，标 `# pyright: ignore[reportUnusedFunction]`，零 caller，`_build_skill_prompt` 在 `:711` return 不调它 |

**小结**：前两轮 13 项 = 7 落地 + 2 部分接线 + 4 未落地（含 1 死码）。落地率 54%，但"部分接线"的 2 项（TokenLedger / shared_context serial）正是高价值项——见 §3.1 / §3.2。

---

## 3. 根因发现（Phase 1 — 新增 10 条）

每条 6 字段：**症状 / 证据 / 根因 / 分类 / 浪费量 / 质量影响**。分类按"砍掉后 G4/gate 是否仍 PASS"标注。

### 3.A 框架层（dispatcher / pipeline）

#### 3.1 TokenLedger dead-wire（dead infrastructure）

- **症状**：`cost/token-ledger.jsonl` 任何 round 后为空；`shenbi-cost-report` 全零。
- **证据**：`ledger.py:45` `record()` 定义；`grep -rn "TokenLedger\|\.record(" src/shenbi/` 仅命中类定义 + `report.py:40` 的 `summarize()`；`dispatch_helper.py:1246` `_record_token_usage` 只写 `state.token_usage` 内存 dict（`chapter_loop.py:2857` 的 `tracker.record()` 是 `EscalationTracker`，非 `TokenLedger`）。**另**：IDE-CLI 路径 `_dispatch_via_ide`（`:1521`）无 `state` 形参、从不调 `_record_token_usage`/`_log_token_usage`——即使 API 路径接了 ledger，IDE dispatch 的用量也从未入账（§3.9 强调 IDE 路径是主要损耗点，却恰是最未观测的路径）。
- **根因**：cost 基础设施按"类 + 读侧"先建，写侧接线（在 `_record_token_usage` 里 `ledger.record(...)`）从未补上。第一轮 spec 把可观测性列为目标，但实施止步于类存在。
- **分类**：dead-wire（修不影响任何 gate）。
- **浪费量**：零 token 节省，但**使所有后续 token 优化无法度量**——没有 baseline 就无法证明 §6 任何 P2 改动的收益。
- **质量影响**：无（纯观测层）。

#### 3.2 SharedAuditContext 漏接 serial 审计路径

- **症状**：boundary / genre serial 审计器各自 `read_text` 同一批 truth 文件。
- **证据**：`chapter_loop.py:2558,2582` 注入 parallel；`audit_layer.py:150` `run_audit_layer` 对每个 skill 调 `dispatch_skill`（`:170`）不传 `shared_context`；`dispatch_helper.py:1607` def / `:1616` `shared_context: Any = None` 形参存在。
- **根因**：parallel 审计波是后加的优化，serial 路径（boundary circle）是更早的旧路径，接线时只覆盖了新路径。典型的"加新优化忘改旧路径"。
- **分类**：冗余待去重（serial 审计器读的 truth 文件 parallel 波也读，内容一致）。
- **浪费量**：serial 审计器数量 × 每器重复 truth（~30KB/器）。boundary circle 通常 4-6 器 → ~120-180KB/章重发。
- **质量影响**：无（读的是同一份文件，内容不缺）。

#### 3.3 跨 dispatch 文件 read_text 无缓存

- **症状**：同一 truth 文件在一章内被 5+ 个 dispatch 重复读取并发送给 LLM。
- **证据**：`dispatch_helper.py:537` `content = full_path.read_text(...)` 每次 `_build_skill_prompt` 调用都执行；无跨调用缓存（对比 `_load_executor_config:127` / `_load_genre_config_cached:164` 是显式缓存的）。`truth/pending_hooks.md` 被 22 个 skill 声明为 read，`truth/chapter_summaries.md` 被 16 个，`truth/character_matrix.md` 被 12 个（grep skills/*/SKILL.md 计数，含 producer 自身契约）；单章链 planning→context→drafting→revision→state-settling 内 `pending_hooks` 至少读 3 次。
- **根因**：dispatcher 把每次 dispatch 视为独立无状态调用，没有"本章已发送文件集"的概念。`SharedAuditContext` 是这个概念的局部实现，但只覆盖审计场景。
- **分类**：冗余待去重（provider 端 prompt caching 能部分兜底，但 IDE-CLI 路径绕过——见 3.9）。
- **浪费量**：单章 ~5-8 个非审计 dispatch × ~30-60KB truth 集合 = ~150-480KB 重发/章。
- **质量影响**：无（重复内容不影响输出）。

#### 3.4 `raw_inputs[basename]` 键冲突

- **症状**：两个同名文件（不同目录）被同 dispatch 读取时，后者覆盖前者。
- **证据**：`dispatch_helper.py:544` `raw_inputs[full_path.name] = content` —— 用 basename（`Path.name`）做键。
- **根因**：用 basename 而非相对路径做键。当前 truth 文件名大多唯一，但 glob 展开（如 `characters/**/*.md`）或 `truth/*.md` + `plans/*.md` 同名时静默丢数据。
- **分类**：correctness bug（潜在）。
- **浪费量**：无直接浪费，但**隐藏数据丢失**——LLM 收到的 inputs 缺一份却无告警。
- **质量影响**：若触发，gate 可能因缺上下文 FAIL，表现为"莫名其妙的输出退化"。

### 3.B 契约层（reads / writes / decisions sidecar）

#### 3.5 5/7 decisions.json sidecar 是 dead output，违反 AGENTS.md §73

- **症状**：7 个 skill 在 `writes:` 声明 `*-decisions.json`，但其中 5 个没有任何下游 skill 在 `reads:` 中消费。
- **证据**：repo-wide grep `reads:` 块引用 decisions 路径，仅 2 条命中：

  | Producer | writes | 下游 reads 命中？ |
  |---|---|---|
  | `shenbi-context-composing` | `context/chapter-N-context-decisions.json` | ✅ `shenbi-chapter-drafting` |
  | `shenbi-chapter-drafting` | `chapters/chapter-N-decisions.json` | ✅ `shenbi-chapter-revision` |
  | `shenbi-chapter-planning` | `plans/chapter-N-plan-decisions.json` | ❌ |
  | `shenbi-chapter-revision` | `chapters/chapter-N-revision-decisions.json` | ❌ |
  | `shenbi-short-drafting` | `short/short-N-decisions.json` | ❌ |
  | `shenbi-market-radar` | `context/market-radar-decisions.json` | ❌ |
  | `shenbi-state-settling` | `truth/state-settling-decisions.json` | ❌ |

- **根因**：AGENTS.md §60-73 规定"ephemeral→artifact 迁移时下游必须声明 decisions 为 reads"，但该规则无机器化校验——契约是文档约定，不是 gate。5 个 producer 产 sidecar 仅 G4 schema 校验通过，随后被忽略（仅 `revision-decisions.json` 在 `state_heal.py:58` 被用来对计数器，内容不消费）。
- **分类**：契约违规 + 纯浪费（LLM 花 token 产 sidecar，无人读）。
- **浪费量**：5 skill × 每次 dispatch 产 ~0.5-2KB decisions JSON ≈ ~5-10KB/章纯产出浪费 + 产出 token（通常 2-3× 输入 token）。
- **质量影响**：无（删 sidecar 不影响任何 gate；保留也不被读）。

#### 3.6 `shenbi-escalation-review` 3 个 dead reads

- **症状**：契约声明读 3 个 score 文件，但 SKILL.md 正文从未引用。
- **证据**：`skills/shenbi-escalation-review/SKILL.md:10-13` 声明 `audits/volume-N-score.md` / `audits/arc-N-score.md` / `audits/stratum-N-score.md`；body `:43` 仅说 `"Read relevant trend/audit files"` 泛指，全文无 "volume-score" / "arc-score" / "stratum-score" / "卷分" / "弧分" 字样（另两个 reads `resonance_trend` / `chapter-N-sensitivity` 在 body 有 "resonance"/"sensitivity" 命中，属 live）。
- **根因**：契约声明是模板化抄来的（所有 review 类 skill 都列了一堆 audits/*），但 escalation-review 的实际逻辑只汇总 escalation 信号，不读细粒度 score。
- **分类**：契约违规 + 纯浪费（读了不用）。
- **浪费量**：3 文件 × ~1-3KB ≈ ~3-9KB/次 escalation dispatch（escalation 本身罕发，绝对量小）。
- **质量影响**：无（删了 gate 仍 PASS，因为 LLM 本来也没"看"这几份——它读了但不引用）。

#### 3.7 字段级 reads 覆盖率 13%，最大三文件零 fields

- **症状**：字段级过滤（Layer B）本是最有效的 token 削减手段，但绝大多数 read 仍是全文件读。
- **证据**：268 条 read 中 dict-form `fields:` 仅 35 条（13.1%），58/73 skill 从不用字段过滤；最该过滤的三个大文件**零 fields 声明**：

  | 文件 | 体积 | 是否任何 skill 声明 fields？ |
  |---|---|---|
  | `chapters/chapter-N.md` | ~31KB | ❌（被 35 个 skill 全文件读） |
  | `world/power_system.md` | ~28.8KB | ❌ |
  | `outline/volume_map.md` | ~26.3KB | ❌（07-18 §3.6 已点名，仍未补） |

- **根因**：字段级过滤是"可选"语法（dict vs string），无 lint 强制；skill 作者默认抄 string 形式。`filter_to_fields` 的逃逸门（field 不匹配返回全文 + WARN）让"声明错了"也无感知。
- **分类**：冗余待去重（大文件里只有 2-10% 与当前 skill 相关——见 07-18 §2.1 volume_map "460 行仅 2 行相关"）。
- **浪费量**：三大文件每次全发 ~86KB；若字段过滤生效可降至 ~3-5KB → 单次省 ~80KB。高频 skill（planning / drafting / context-composing）累计省 ~200-400KB/章。
- **质量影响**：低（字段过滤要验证"砍掉的字段确与该 skill 无关"——但 07-18 §2.1 已逐文件论证过，复用其结论即可，风险可控）。

### 3.C 正文层（SKILL.md body / system prompt）

#### 3.8 auto-generated `## 数据契约` + 空 `AUTO-CHECK` 块跨 72-73 skills 与 frontmatter 重复

- **症状**：每个 SKILL.md 的 body 都有一段 codegen 生成的块，重复 frontmatter 的 `contract:`，且有空占位块。
- **证据**：72/73 skills 含 `<!-- AUTO-GENERATED -->` + `## 数据契约`（重复 frontmatter reads/writes/updates，每 skill ~150-320 字符）；73/73 skills 含 `<!-- AUTO-CHECK-START -->` + `## auto-check (generated -- do not edit)` + `<!-- AUTO-CHECK-END -->` 纯空占位（例：`escalation-review/SKILL.md:19-23`）。
- **根因**：codegen 步骤生成这两块时，body 也被当独立载体发送给 LLM——而 dispatcher 发 system prompt 是**整文件 `read_text`**（`dispatch_helper.py:506`），frontmatter + auto-gen 块 + body 全送。
- **分类**：纯浪费（auto-gen 与 frontmatter 100% 信息冗余；AUTO-CHECK 空块零信息）。
- **浪费量**：~150-320 字符/skill × 72 + ~80 字符空块 × 73 ≈ ~17-27KB 的 system prompt 冗余。因 system prompt 每次 dispatch 全发（见 3.9），单章累计放大 N 倍。
- **质量影响**：无（删了不影响 gate；信息仍在 frontmatter，dispatcher 也只读 frontmatter）。

#### 3.9 SKILL.md 全文每次 dispatch 重发为 system prompt；IDE-CLI 路径绕过 provider caching

- **症状**：同一 skill 在一章内被多次 dispatch 时，其 ~3-13KB 的 SKILL.md 每次都作为 system prompt 全量发送。
- **证据**：`dispatch_helper.py:506` `system_prompt = skill_file.read_text(...)` 每次 `_build_skill_prompt` 重读重发；`dispatch_helper.py:1550` IDE-CLI 路径 `_dispatch_via_ide`（def `:1521`）把 `system_prompt + "\n\n" + user_prompt`（`:1550`）拼成单 stdin 字符串（`subprocess.run(input=full_prompt, ...)` `:1561`），**完全绕过 provider 的 prompt caching**（provider cache 要求 system 与 user 分离、system 前缀稳定）。
- **根因**：dispatcher 把 system prompt 当作"每次都要重新组装的字符串"，而非"跨调用稳定的可缓存前缀"。最大的 5 个 SKILL.md（`review-resonance` 13,987 字节 / `review-arc-payoff` 13,354 / `chapter-pattern` 11,582 / `state-settling` 11,113 / `pacing-design` 11,089）每章被发 N 次。
- **分类**：冗余待去重（API 路径靠 provider cache 部分兜底；IDE-CLI 路径完全不兜底）。
- **浪费量**：review 类一章 ~13 个器 × ~13KB ≈ ~170KB/章（API 路径有 cache 抵消大半；IDE-CLI 路径全损）。
- **质量影响**：无。

#### 3.10 5 个 >10K SKILL.md 内嵌重示例

- **症状**：最大的 5 个 SKILL.md 把参考矩阵、算例、样例报告全嵌在 body 里。
- **证据**：
  - `shenbi-chapter-pattern/SKILL.md`：13×13 模式转移矩阵（`:251-267`）+ Shannon 熵逐步算例（`:305-326`）+ 多输出模板（`:119-228`）—— 是脚本可按需生成的参考材料。
  - `shenbi-review-resonance` / `shenbi-review-arc-payoff`：各 ~6 个 fenced 块的完整填好的样例评分报告。
  - `shenbi-state-settling`：65 行人工审批门禁模板（07-18 §4.4 row 5 已点过可压到 15 行）。
- **根因**：skill 作者把"教学示例"和"每次执行的指令"混在同一文件；没有"按需 read 的 fixture"vs"必发的指令"分离。
- **分类**：冗余待去重（示例对已熟练的执行是参考，不是每次必读）。
- **浪费量**：5 skill × ~3-5KB 可外置示例 ≈ ~15-25KB system prompt 冗余，× N dispatch 放大。
- **质量影响**：低-中（删示例可能影响首次执行的格式遵循度；需 G4 验证"无示例时输出格式仍达标"——建议改为"首次带示例、后续 dispatch 引用 fixture"而非直接删）。

---

## 4. 模式分析（Phase 2）—— 3 个跨 finding 根因簇

| 簇 | 含义 | 成员 | 共同根因 |
|---|---|---|---|
| **A. dead wiring** | 基础设施写了，但派发路径漏接 / 绕过 | 3.1（TokenLedger）/ 3.2（shared_context serial）/ 3.9（IDE-CLI 拼 stdin 绕 cache） | "类 / 函数存在"被当成"功能上线"；缺一条"派发路径端到端调用"的集成校验 |
| **B. 契约↔正文脱节** | 契约声明与 body 实际消费不同步 | 3.5（dead sidecar）/ 3.6（dead reads）/ 3.8（auto-gen 块重复 frontmatter） | codegen 与契约演进无一致性门——AGENTS.md §73 是文档约定，不是 gate；AUTO-CHECK 块本该是"自动校验占位"却永远空 |
| **C. 重复传输** | 无跨调用缓存层 | 3.3（无文件缓存）/ 3.7（字段过滤未用致大文件全发）/ 3.9（system prompt ×N） | dispatcher 把每次 dispatch 当无状态独立调用，没有"本章已发内容集"的概念 |

**簇分析的价值**：修单点不如修模式。Cluster A 的 3 项都靠"补一条派发路径接线"修；Cluster B 都靠"加一个契约一致性 gate（G4 扩展或新 lint）"修；Cluster C 都靠"引入跨 dispatch 上下文记忆层"修。

> **注（3.9 跨簇）**：3.9 同时属 Cluster A（IDE-CLI 路径拼 stdin 绕过 provider cache = dead-wiring）与 Cluster C（system prompt 每次 dispatch 全文重发 = 重复传输）。§1.4 跨 spec 图把 3.9 归 C；本表归 A。二者皆成立（3.9 是 cache-bypass 也是重复传输）——修复时需同时考虑接线（A）与缓存前缀稳定（C）。

---

## 5. 假设与验证（Phase 3）—— 每条 finding 一行

| # | 假设 | 最小验证 |
|---|---|---|
| 3.1 | `record()` 零 caller 是写侧漏接，非有意 | grep `src/` 确认无 caller；跑一章后查 `cost/token-ledger.jsonl` 为空 |
| 3.2 | serial 路径不传 shared_context 是接线遗漏 | `run_audit_layer` 调 `dispatch_skill` 处加 `shared_context=...` 后跑一章，对比 serial 审计器的 prompt_tokens 下降 |
| 3.3 | 同章同文件被多次 read_text | 在 `_build_skill_prompt:537` 加临时日志 `log.info("read_text", path=..., skill=...)`，跑一章统计同文件被多少 skill 读 |
| 3.4 | basename 键会冲突 | 构造两目录同名文件（如 `a/hooks.md` + `b/hooks.md`）的 round，查 LLM 收到的 inputs 是否少一份 |
| 3.5 | 5 个 sidecar 无下游 reads | grep 全 skills 的 `reads:` 块对每个 sidecar 路径（已核：`grep -rn "decisions.json" skills/*/SKILL.md` 的 reads 段，仅 2 命中——见 §3.5 表；5 个 dead 的负证据 = 该 grep 对其路径零 reads 命中） |
| 3.6 | 3 个 score 文件 body 不引用 | 对 escalation-review body 做字面量搜索（已核，见 §3.6） |
| 3.7 | 三大文件零 fields 声明 | grep `contract.reads` 中含这三文件名的 dict-form 命中数（已核 = 0） |
| 3.8 | auto-gen 块与 frontmatter 100% 冗余 | diff 任一 SKILL.md 的 frontmatter `contract:` 与 `## 数据契约` 块内容 |
| 3.9 | IDE-CLI 拼单 stdin 绕过 cache | `dispatch_helper.py:1550` 读源码；对比 API 路径 system/user 分离 vs IDE 路径拼接 |
| 3.10 | 示例可外置 | 把 chapter-pattern 的矩阵外置到 fixture，G4 跑该 skill 看是否仍 PASS |

---

## 6. 修复方案（Phase 4）—— 按质量优先分级

分级原则：**P0 = 纯浪费，删后 gate 必 PASS，零质量风险；P1 = 契约违规修复，需小范围 gate 验证；P2 = 效率优化，需 G4 全量验证；显式不砍 = 质量兜底**。

### 6.1 P0 纯浪费（直接做，无质量风险）

| Finding | 修复 | 落地点 | 验证 |
|---|---|---|---|
| 3.1 | 在 `_record_token_usage` 末尾接 `TokenLedger(project_dir).record(skill, chapter, usage_dict, model)`；**同时把 `state` 穿入 IDE-CLI 路径**（`_dispatch_via_ide` 当前无 `state` 形参、不调 `_record_token_usage`，IDE dispatch 的 token 用量从未入账——见 §3.1 证据补注） | `dispatch_helper.py:1246-1263`（API 路径）+ `:1521` 签名补 `state` + `:1650` 调用点补传 | API 路径：一章 round 后 `cost/token-ledger.jsonl` 非空 ✅；IDE 路径：**延后**——codex exec stdout 是 prose 非结构化 usage 对象，需 codex `--json` / zcode usage-report 支持后方可记录（state 已穿入，`ide_dispatch_uninstrumented_tokens` log 标记观测） |
| 3.4 | `raw_inputs[full_path.name]` → `raw_inputs[str(full_path.relative_to(project_dir))]`，**同步更新 SharedAuditContext 注入块的键**（当前 `dispatch_helper.py:551-557` 用 basename `world_rules.md` / `character_matrix.md` / `style_profile.md` / `pending_hooks.md` 注入；若 read 路径改 relative-path 键而注入块不改，同一逻辑文件会以两个键名各发一次——重复传输，与 Cluster C 目的相悖）。**推荐**：抽取单一 `_input_key(full_path, project_dir)` helper，read 循环与注入块共用。 | `dispatch_helper.py:544` + `:551-557` 注入块同步 | 两同名文件 round 测试：inputs 含两份；**额外**：`raw_inputs` 中同一逻辑文件不出现两个键名（无重复 `<document>`）；shared_context 注入生效后不与磁盘读重复 |
| 3.6 | 删 `escalation-review` 的 3 个 dead reads。**codegen 重跑是硬前置**：`:29` auto-gen `**Reads:**` 行由 frontmatter 生成，只改 frontmatter 不重跑 codegen → LLM 仍在 system prompt 的 `## 数据契约` 块看到 dead reads（见 3.8）。必须 `just generate`（或等价 codegen）使 `:29` 同步删除 | `skills/shenbi-escalation-review/SKILL.md:10-12`（frontmatter）+ `:29`（auto-gen，codegen 重跑后自动同步） | G4 PASS；`## 数据契约` Reads 行不再含 volume/arc/stratum-N-score；escalation 触发时输出不变 |
| 3.8 | codegen 不再生成 `## 数据契约` + `AUTO-CHECK` 块（或 dispatcher 发 system prompt 前剥离它们） | codegen 脚本 or `dispatch_helper.py:506` 后处理 | G4 全过；system prompt 字符数下降 |
| 2.3 #11 | 删死码 `_inject_instruction_hierarchy` 或接进 `_build_skill_prompt`（二选一） | `dispatch_helper.py:714` | 删：无 caller 不影响；接：单测 prompt 结构 |

### 6.2 P1 契约一致（修违规，小范围 gate 验证）

| Finding | 修复 | 验证 |
|---|---|---|
| 3.5 | 5 个 dead sidecar：要么删其 `writes:`（若真无下游需要），要么补一个下游 `reads:`（若设计上该有）—— **逐个判定，非一刀切删**。至少 2 个有设计意图歧义：`plans/chapter-N-plan-decisions.json`（drafting 读 plan.md 但不读其 decisions——是否本应给 drafting？）、`truth/state-settling-decisions.json`（`state_heal.py:58` 读的是 revision-decisions 做计数器，state-settling-decisions 是否预留给尚未建的下游 skill？）。plan 阶段须产出 per-sidecar disposition 表（delete / add-consumer，各附一行理由）。无论 disposition 如何，都加一条 G4/lint：**"writes 中的 `*-decisions.json` 必须在某个 skill 的 reads 中出现"**（防止再生） | 新 lint 跑全 skills 报剩余违规数；per-sidecar disposition 表评审通过 |
| 3.7 | 为三大文件（chapter-N / power_system / volume_map）在高频 skill（planning / drafting / context-composing / review-world-rules）的 reads 声明 fields，复用 07-18 §2.1 的字段结论 | 字段覆盖率 >5KB reads ≥80%；G4 对相关 skill 仍 PASS |

### 6.3 P2 效率（需 G4 全量验证收益与无回归）

| Finding | 修复 | 风险 | 收益验证 |
|---|---|---|---|
| 3.2 | `run_audit_layer` 调 `dispatch_skill` 时传 `shared_context`（需先 `build_shared_audit_context`） | 低（parallel 波已验证） | serial 审计器 prompt_tokens 下降 |
| 3.3 | 引入跨 dispatch 的"本章已发文件"缓存层（在 pipeline state 上挂 dict，`_build_skill_prompt` 命中则引用前次切片）。**失效语义必须基于内容变化（hash/etag of post-write bytes），非"写事件"**——repo 有 6+ skill 同章既读又写 truth 文件（drift-guidance / foreshadowing-recall / memory-distill / state-settling 写 `pending_hooks` 后被下章 planning 读 等）；"写后失效"会过宽失效（mid-chapter 对未变内容重读）或过窄（stale-read）。缓存不变式：cached slice 反映文件在 chapter planning phase 的内容；失效当且仅当 post-write bytes ≠ cached bytes | 中（缓存失效语义：content-hash 比对；read-write-same-file 模式需 §5 加 read→write→read 不 stale 验证） | 同章同文件 read_text 次数下降；read→write→read 序列不返回 stale slice |
| 3.9 | **默认形态**：保证 system 前缀字节稳定以触发 provider cache（system prompt 跨 dispatch 不变即足）。**强形态（stretch）**：IDE-CLI 路径 system/user 分离——**前提是 codex/zcode CLI 支持 system 参数**；当前 `_find_ide_cli`（`:1500`）构造 `codex exec ... -`（stdin 单 prompt），无 `--system` flag，强形态未验证可行。plan 阶段先验证 CLI 能力，不支持则只做默认形态 | 中（依赖 CLI 能力——plan 阶段先验证） | IDE 路径 prompt cache hit rate 上升（默认形态：前缀稳定即可部分受益） |
| 3.10 | 5 大 SKILL.md 示例外置到 `skills/_shared/*.md` 或 `tests/fixtures/`，body 改引用；首次 dispatch 带、后续引用 | 中-高（可能影响格式遵循） | G4 对 5 skill 仍 PASS；system prompt 字符数下降 |
| 2.3 #8/#9 | 落地 `world_summarizer.py` + `skills/_shared/`（07-18 §3.5/§3.9 原案） | 中 | review-world-rules prompt_tokens 下降且 G4 PASS |

### 6.4 显式不砍（质量兜底，登记为"必要上下文"）

- **state-settling 补充上下文**（07-18 §2.3 已论证）：当前仅读 `chapters/chapter-N.md` 一个文件，是 CN1（角色消失）/ CN3（覆盖模式）根因。本 audit 判其为**必要上下文不足**，非浪费——应**补**读 truth 前版 + volume_map 节点 + character_matrix，而非砍。
- 任何 P2 改动若使 G4 FAIL，立即回滚——gate 是唯一裁判。

---

## 7. 验证标准（数值化）

| 标准 | 当前 | 目标 |
|---|---|---|
| 一章 round 后 `cost/token-ledger.jsonl` 行数 | 0 | >0（每 dispatch 一行） |
| dead decisions sidecar 数 | 5 | 0（或全部有下游 reads） |
| escalation-review dead reads 数 | 3 | 0 |
| >5KB reads 的字段级覆盖率 | ~13% | ≥80% |
| basename 同名文件丢失 | 静默 | 有 round 测试覆盖 |
| serial 审计器 prompt_tokens（同章） | baseline | 下降（shared_context 接线后） |
| `just check` | PASS | PASS（无回归） |
| G4 全 skills | PASS | PASS（质量铁律不退让） |

---

## 8. 铁律（5 条，绝对语气）

1. **"类存在"≠"功能上线"。** 任何 cost / cache / filter 基础设施，必须有"派发路径端到端调用"的集成测试，而非仅单元测试类本身。TokenLedger dead-wire（3.1）就是单元测试通过、集成 dead 的例证。
2. **契约即代码。** `writes:` 声明 `*-decisions.json` 就必须有下游 `reads:` 消费，否则删 writes。文档约定（AGENTS.md §73）必须升级为机器化 gate。
3. **读即用。** 声明 read 就要在 body 引用；不引用就是 dead read，删。escalation-review 的 3 个 score reads（3.6）是反例。
4. **每次 dispatch 不是无状态调用。** 同章同文件二次 read 必须走缓存或字段过滤；全文件二次发送是浪费，除非内容已变（写后失效）。
5. **G4/gate 是唯一质量裁判。** 任何 token 优化以 gate 仍 PASS 为前提；FAIL 即回滚。质量 > token > 速度，但不应有浪费。

---

## 9. 依赖关系图

```
archive 07-17/07-18/07-19-06 (设计论证)
        │
        ▼
本 spec（第三轮 audit）
        ├─ §2 实现态复核 ──── 前两轮 13 项落地状态（7/2/4）
        ├─ §3 新增根因 ────── 10 条（框架 4 / 契约 3 / 正文 3）
        ├─ §4 模式 ────────── 3 簇（dead-wiring / 契约脱节 / 重复传输）
        └─ §6 修复 ────────── P0(5) / P1(2) / P2(5) / 不砍(1)

P0/P1 实施前需另写 plan 并批准（本 spec 是 design，不实施）
        │
        ▼
   执行 plan ──► just check + G4 全过 ──► 归档本 spec
```

**修复顺序约束**（plan 阶段必须遵守，源于 §6 各修复间的相互作用）：
- **3.4 → 3.2**：3.4（basename→relative-path 键）必须先于 3.2（shared_context serial 接线）落地——否则 3.2 激活的 SharedAuditContext 注入块（basename 键）与未同步的 read 路径（relative-path 键）冲突，触发 §6.1 C1 所述重复传输回归。
- **3.8 → 3.6**：3.8（移除 auto-gen 块）或 codegen 重跑必须先于/同于 3.6（删 escalation dead reads）——否则 `:29` auto-gen `**Reads:**` 仍向 LLM 广播 dead reads，3.6 对 LLM 视图无效。
- **3.1（含 IDE 路径穿 state）是所有 P2 收益度量的前置**——无 ledger 写入，§6.3 任何"prompt_tokens 下降"不可证。
```

---

## 10. 与前两轮的差异（为何本 spec 非重复）

| 维度 | 前两轮（archive） | 本轮 |
|---|---|---|
| 视角 | 设计 + 提议 | 审计 + 落地复核 + 补漏 |
| 证据 | 推理 + 估算 | 7 个并行 Explore agent 的 `file:line` 实证 |
| 对前两轮 | 不存在 | 逐项标落地状态（7/2/4），接管跟踪职责 |
| dead-wire 发现 | 无 | TokenLedger / shared_context serial / IDE-CLI 绕 cache（Cluster A） |
| 契约违规量化 | 无 | 5/7 dead sidecar、3 dead reads、13% 字段覆盖（Cluster B） |
| 决策原则 | token 优先 | 质量 > token > 速度，但不应有浪费（G4 裁判） |
| 输出 | 设计文档 | 设计 + 实现态审计表 + P0/P1/P2 分级修复路径 |

本 spec 不取代前两轮的**设计论证**（仍作参考），只取代它们的**落地跟踪**职责——前两轮从未做过事后核验，这是本轮的全部新增价值。
