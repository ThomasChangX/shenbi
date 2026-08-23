# 输出侧浪费审计：重试放大 / 审计交叉冗余 / revision 原始 glob

> **Date:** 2026-08-01
> **Status:** Design | Revised 2026-08-24（价值门：F8 重试面 superseded→活跃 #47/C33；阶段 3 审查：F7 关闭——3 残留 sidecar 已由归档 plan 2026-08-02 裁决 KEEP（机器消费方存在），本 spec 剩余可执行内容 = F10 聚合去重层 + F9 P2）
> **Severity:** 🟠 High（输出 token 单价 2-3× 输入；输出侧是总纲 spec 的盲点）
> **方法:** [`systematic-debugging`](archive/2026-07-19-06-llm-context-engineering-design.md) skill 四阶段
> **系列:** Token 效率全栈 audit（子 spec 3/3，隶属总纲 [`...read-write-consistency-audit-design.md`](archive/2026-08-01-pipeline-read-write-consistency-audit-design.md) §0 分工）
> **依赖:** 总纲 spec（§3.1 TokenLedger dead-wire 是本 spec 重试计量的前置）；推理控制 spec（§2.9 finish_reason=length 盲点驱动本 spec F8 重试放大）；`src/shenbi/pipeline/{error_handler,revision_router,parallel_dispatch,chapter_loop}.py`
> **范围:** 本 spec 只审 **输出侧浪费**——LLM 产出 token 的浪费（重试放大、审计器交叉冗余、revision 读原始 glob 无去重）。**不审** 输入侧（总纲 §3 的 10 条）、不审调用参数（推理控制 spec）。
> **核心定位:** 总纲 spec §3 的 10 条 findings **全部是输入侧**（reads/system prompt）。但 LLM 调用成本 = 输入 + 输出，输出 token 单价更高。本 spec 补总纲盲点：4 条输出侧 findings，其中 3 条是总纲完全未覆盖的新发现。

---

## 1. 背景：为什么输出侧是独立维度

| 维度 | 总纲覆盖？ | 本 spec |
|---|---|---|
| 输入 token 浪费（reads/system prompt 重复） | ✅ §3 的 10 条 | 不重复 |
| 输出 token 浪费（重试产出、审计冗余产出、dead sidecar 产出） | ❌ 盲点 | §2 的 4 条 |
| 调用参数浪费（温度/模型/截断） | ❌（推理 spec） | 不重复 |

输出 token 通常 2-3× 输入单价（DeepSeek `pricing.py`：prompt $0.14/M vs completion $0.28/M）。重试产出的废弃输出、审计器重复描述同一缺陷的输出、revision 读未去重的原始审计输出——都是被忽视的高单价浪费。

### 1.1 决策原则（继承总纲 §0）

质量 > token > 速度，但不应有浪费。输出侧"砍"的判据：聚合/去重后 G4 仍 PASS = 真浪费。

---

## 2. 根因发现（Phase 1）—— 4 条

### 2.1 [F8] G4 重试放大：坏章最坏 ~6 章等价输出 + 3 审计波

> **[2026-08-24 修订] 本条 superseded，关闭不实施。** 证据（常量、重试链）仍成立，但修复面已全部有主：TokenLedger 计量已接（PR #39，`dispatch_helper.py:1448,1467` 每次 dispatch 含重试均记账 completion_tokens）；截断检测已修（PR #40）；全局重试预算/失败分类由活跃 spec **#47（C33 重试/失败分类统一）** 承接（其 INDEX 登记明确「吸收 #4 的 F8 重试放大」）。本 spec 不再含 F8 的任何实施任务，防止与 #47 重复实施。下文保留原始分析作历史记录。

- **症状**：一个质量差的章节触发重试链，产出多份废弃全量输出。
- **证据**：
  - `error_handler.py:36-37`：`MAX_DISPATCH_DETRIES = 2`（=3 总尝试）、`MAX_AUDIT_RETRIES = 3`。
  - `handle_dispatch_failure`（`error_handler.py:40-57`）：drafting 失败重试最多 3 次全量输出。
  - `handle_audit_blocking`（`error_handler.py:60-81`）：revision↔audit 循环最多 3 次修订 + 3 次重审。
  - drafting 输出 ~31KB 章节 prose。坏章最坏路径：3 次 draft 输出（~93KB，仅末份保留）+ 3 次 revision 输出（~93KB）+ 3 审计波 = **~6 章等价输出 + 3 审计波**。
- **根因**：重试无预算计量（每次重试烧多少 completion token 无记录）；且若根因是 `finish_reason=length` 截断（推理 spec §2.9），重试同参必再截断——纯空烧。
- **分类**：纯浪费（废弃输出）+ 质量风险（截断章节）。
- **浪费量**：坏章最坏 ~6× 章节输出 token（completion 单价 2× 输入）+ 3 审计波。56 章中若 10% 触发重试 = ~5.6 章 × 6 ≈ 34 章等价废弃输出。
- **质量影响**：截断章节是残缺的（与推理 spec §2.9 同根因）。
- **假设**：重试预算计量 + 截断检测（推理 spec §2.9）联合后，废弃输出降至仅"真有修复希望"的重试。
- **验证**：mock 一个 G4 FAIL 章节，统计 completion token 总量 vs 最终保留输出比。

### 2.2 [F9] 审计器交叉冗余：同一缺陷 5 份报告各描述

- **症状**：审计器管辖域设计上重叠，同一缺陷被多器独立报告，各烧输出 token 描述。
- **证据**：
  - `chapter_loop.py:203-244`：4 个 review-group（factual/character/craft/plan）+ resonance + sensitivity。
  - `audit_layer.py:44-53`：genre circle 加 review-character/-motivation/-dialogue/-world-rules 等。
  - **`review-group-character` 与 `review-character`/`-motivation`/`-dialogue` 都评角色**——段落 Y 的一次 OOC 会独立出现在 3-5 份报告，各用不同 prose 描述。
  - `tests/fixtures/audit-report-example.md`（119 行）：单份报告内一个缺陷（`:95`"了"密度警告）就在 findings 表 + fix 建议（`:107`）+ 评分理由（`:99-101`）出现 3 次。跨 5 报告 = 5× 输出。
- **根因**：审计器是独立 dispatch，无缺陷共享/去重层；各器各自完整产报告。
- **分类**：冗余待去重（缺陷事实一致，描述冗余）。
- **浪费量**：5 器 × 同缺陷 ~0.5-1KB 描述 = ~2.5-5KB/缺陷 输出 token；一章若 5 缺陷 × 5 器冗余 = ~12-25KB 冗余输出。
- **质量影响**：低（去重后 revision 仍收全部缺陷事实）。
- **假设**：审计器间共享已发现缺陷（按段落位置键），后续器引用而非重述，输出降。
- **验证**：跑一章审计，按段落+缺陷类型聚簇，统计冗余描述 token。

### 2.3 [F10] revision 读原始 glob 无去重：~60-120KB/次输入 + 冗余延续到输出

- **症状**：`shenbi-chapter-revision` 的 `reads: audits/chapter-N-*.md` glob 吃进全部原始审计报告，无聚合去重层。
- **证据**：
  - `skills/shenbi-chapter-revision/SKILL.md:9-10`：`reads: - audits/chapter-N-*.md`。
  - `revision_router.py:205`：`for audit_file in sorted(audit_dir.glob(f"{prefix}*.md")):` 扫全部匹配。
  - **无聚合去重层**：`parallel_dispatch.consolidate_review_results`（`parallel_dispatch.py:189-249`）只提 `BLOCKING`/`CRITICAL` **行**生成摘要文件，**不去重缺陷**；revision 契约仍单独读 raw glob。
  - 6 wave-1 + 至多 9 wave-2 审计器 × ~6-8KB/报告 = **~60-120KB 原始审计输入/次 revision**，大量描述重叠缺陷。
- **根因**：consolidate 只做"提严重行"，未做"缺陷去重"；revision 直读 raw。
- **分类**：冗余待去重（输入侧浪费，但驱动原因是输出侧审计器冗余产出，故归此 spec）。
- **浪费量**：~60-120KB/次 revision 输入（输入 token）+ revision 因读冗余而产冗余修订（输出 token）。
- **质量影响**：低-中（去重后 revision 聚焦真缺陷，可能升质量）。
- **假设**：revision 前加审计聚合去重层（按段落+缺陷类型合并），输入降至 ~10-20KB，revision 输出更聚焦。
- **验证**：fixtures 驱动测试（G0.9：输入只用 `tests/fixtures/` 真实审计产物，禁手写 mock）——多审计器重叠场景用真实产物，对比去重前后 revision 输入字符数 + 修订质量。

### 2.4 [F7] dead decisions sidecar 的产出 token（总纲 §3.5 的输出视角补全）

> **[2026-08-24 二次修订（阶段 3 审查纠正）：本条关闭，无实施动作。]** 首次修订曾误将 3 个残留 sidecar 改为本 spec 承接「删 writes」——经设计审查复核，该处置与已合并归档 plan `plans/archive/2026-08-02-token-efficiency-master-p0-p1.md` 的既有裁决矛盾：该 plan 已按消费方逐项裁定 **chapter-revision / short-drafting / market-radar 三个 sidecar 均 KEEP writes**，因为它们有非 LLM 的机器消费方——`state_heal.py:58` 用 `chapter-N-revision-decisions.json` 的存在性对账 `revision_count`；`chapter_loop._ensure_revision_decisions_exists`（:1967）在 revision 跳过时补写该文件；G4 `g4_decisions`（`g4/generic.py:332-334`）对三者做 schema 校验（derive_expected_outputs 从 writes 派生，删 writes 会连带拆掉 G4 期望面）。AGENTS.md「Decisions-Sidecar Artifacts」本身将 decisions.json 定为 Layer A 框架特性——「dead」仅指无 LLM 下游 reads，非纯浪费。首次修订注记作废，以本注记为准。

- **症状**：（历史记录）decisions.json sidecar 无 LLM 下游 reads，产出 token 似为纯浪费。
- **结论**：不成立为浪费——机器消费方（state_heal / G4 schema 校验）构成合法消费；既有 plan 裁决 KEEP。
- **修复**：无。本 spec 不含 F7 的任何实施任务。

---

## 3. 模式分析（Phase 2）—— 2 个根因簇

| 簇 | 成员 | 共同根因 |
|---|---|---|
| **无输出聚合层** | 2.2 / 2.3 / 2.4 | 审计/sidecar 各自独立产出，无"产出去重/合并"中间层；revision 直读 raw |
| **无重试预算计量** | 2.1 | 重试烧的 completion token 无记录（依赖总纲 §3.1 TokenLedger dead-wire）；截断致空烧（推理 spec §2.9） |

跨 spec 簇（归总纲 §1b）：2.1 属 Cluster A（dead-wiring——重试计量未接）+ Cluster E（输出放大）；2.2/2.3 属 Cluster C（重复传输的输出面）。

---

## 4. 假设与验证（Phase 3）

每条见 §2"假设/验证"。关键：

- 2.1：重试预算计量 + 截断检测联合后废弃输出降
- 2.2/2.3：审计聚合去重层（按段落+缺陷类型键）使 revision 输入降 ~80% 且质量不退

---

## 5. 修复方案（Phase 4）

### 5.1 P0（纯浪费，直接做）

| finding | 修复 | 落地点 | 验证 |
|---|---|---|---|
| 2.3 | revision 前加审计聚合去重层（设计见 §5.1a） | `chapter_loop.py` 审计波完成后确定性产出聚合文件；`shenbi-chapter-revision` reads 改聚合文件 | revision 输入字符数降 + G4 PASS + 无损不变量测试 |
| 2.3b | 顺带修复：`shenbi-chapter-revision` reads 同时声明 `audits/chapter-N-*.md` glob 与 `audits/chapter-N-resonance.md` 单条——glob 已匹配共振文件，同一文件每章被读两次 | 同一行契约修改 | 契约 lint + `just generate` diff 空 |

（原 2.4 行删除：F7 已于 2026-08-24 二次修订关闭，无实施动作。）

### 5.1a 聚合层接线契约（阶段 3 审查补充——防 dead-wire）

- **产出者**：纯 Python 确定性函数（零 LLM 调用；structlog 记录、pathlib、幂等），落在 `src/shenbi/pipeline/audit_aggregate.py`（新模块）
- **触发点**（两条 revision 入口都要接，缺一即 dead-wire）：
  1. `chapter_loop.py` Step 16（shenbi-chapter-revision）派发前——审计波完成后
  2. `chapter_loop.py` BLOCKING 重派路径（~:3074）重审后再次派发 revision 前——**每次审计集变化后必须再生成**，否则聚合过期（正确性风险，非仅效率）
- **聚合文件路径**：`audits/chapter-N.aggregate.md`——**必须不匹配 `chapter-N-*.md` glob**（用 `.` 不用 `-` 分隔）：否则聚合文件会被 `revision_router.py:207` 的 severity 扫描（BLOCKING 原文保留 → 恒命中 → 双计数）、聚合产出者自身的输入 glob、以及 `shenbi-drift-guidance` 的 `audits/chapter-N-*.md` reads 反复吃回自己。改名一次性关闭全部三个回路面，零逐消费者补丁
- **消费契约**：`shenbi-chapter-revision` SKILL.md reads 删 `audits/chapter-N-*.md` glob 与 resonance 单条，改 `audits/chapter-N.aggregate.md`（共振结论并入聚合）；`just generate` 同步 deps.json/docs。**契约图 ORPHAN_READ 机制**：`tools/lint_contract_graph.py:8,85` 将「无 producer 的 read」判 exit-1 阻塞，而聚合文件的 producer 是框架代码（对 SKILL.md 契约不可见）——plan 必须给机制：将 `audits/chapter-N.aggregate.md` 登记进 truth-files 注册表为框架产出 pattern，或在 `find_closure_violations` 引入 FRAMEWORK_PRODUCERS 白名单。 dangling-write 侧无忧（audit writes 仍被 drift-guidance glob read 消费，且 dangling writes 本就只 WARN）
- **回退（须在 G1 之前生效）**：聚合文件缺失（旧项目目录/异常路径）时若只在 dispatcher 读取阶段 fail-open，G1.1 输入就绪检查（`g1.py:198-199` 对缺失 declared read 硬 FAIL）会先拦——**回退必须落在 dispatch_helper 的 reads 解析阶段、G1 之前**：declared read `audits/chapter-N.aggregate.md` 缺失 → 该次 dispatch 的 reads 集改写为 raw glob `audits/chapter-N-*.md` 注入 + log WARN（对齐字段过滤 escape-hatch 语义，但作用于路径集而非内容），不阻塞 revision
- **G4/C32 交互**：聚合文件是派发之间的框架写——与 Step 15 pre-revision 快照同构的先例（非 skill writes，不在 declared 谓词面内）；`write_audit` 快照围绕单次 dispatch，框架写不触发
- **阶段 3 终轮 Minor 折入（plan 须落实）**：① 聚合格式不得以 `---` 开头（G1.3 frontmatter 解析，`g1.py:213-217`）；② `_is_audit_file`（`dispatch_helper.py:1013-1026`）会把 `.aggregate.md` 误分类为 LLM 审计报告——扩展排除或文档化；③ 无损不变量测试加独立覆盖断言（每份 raw 报告在聚合中被引用 + 各报告解析键数与聚合条目对账 + 逐字保留块），防解析器自证；④ ORPHAN_READ 机制**首选** truth-files 注册表登记（`lint_contract_graph.py:63-73` 已支持 pipeline producer，零 lint 改动），FRAMEWORK_PRODUCERS 白名单仅作后备（YAGNI）
- **去重键（保守去重，防误删缺陷）**：按「段落位置 + 缺陷类型」精确匹配才合并；不匹配则逐字保留。**无损不变量**：聚合文件必须包含 raw 报告的全部缺陷事实——以 fixtures 驱动测试表达（raw findings 条目 ⊆ 聚合条目，**且显式覆盖 resonance 报告**——其单条 read 被删除，共振结论只能经聚合存活），测试输入只用 `tests/fixtures/` 真实审计产物（G0.9 禁手写；现无多审计器重叠 fixture——`tests/fixtures/audits/` 为空、仅有单份 `audit-report-example.md`——**fixture 生成是 plan 的第 0 号任务**：由上游 dispatch 产出后提交为 fixture，不得手写）
- **验收对齐**：revision 输入审计字节 ~60-120KB → ~10-20KB

### 5.2 P1（机制，需验证）

| finding | 修复 | 风险 |
|---|---|---|
| ~~2.1~~ | ~~重试预算计量：接 TokenLedger~~ **[2026-08-24 移交]** 归活跃 #47（C33）——TokenLedger 接线已由 PR #39 落地，全局重试预算/失败分类由 #47 承接，本 spec 不实施防重复 | — |
| ~~2.1~~ | ~~截断致空烧的修复归推理 spec §2.9 P0~~ **[已修]** PR #40 已落地 | — |

### 5.3 P2（效率，需全量 G4）

| finding | 修复 | 风险 |
|---|---|---|
| 2.2 | 审计器缺陷共享：wave-1 器产出后，wave-2 器 reads 共享缺陷池，引用而非重述 | 中（需保证 wave-2 独立判断不被 wave-1 带偏——与 `requires_independent_agent` 可能冲突，需评估） |

### 5.4 显式不动

- 2.2 的审计器独立判断是质量保证（`requires_independent_agent`）；共享缺陷池若带偏 wave-2 则不取。G4 裁判。

---

## 6. 验证标准（数值化）

| 标准 | 当前 | 目标 |
|---|---|---|
| revision 输入审计字节/次 | ~60-120KB raw glob | ~10-20KB 聚合去重 |
| 聚合无损性 | —（无聚合层） | raw 缺陷条目 ⊆ 聚合条目（fixtures 驱动测试） |
| `just check` | PASS | PASS |

转出注记：重试 completion token 计量已接（PR #39），全局重试预算归活跃 #47——非本 spec 验收面。dead sidecar：3 个残留经阶段 3 审查复核为已裁决 KEEP（见 §2.4 二次修订注记），非本 spec 验收面。

---

## 7. 铁律（3 条）

1. **重试产出是被计量资源。** 每次 G4 重试烧的 completion token 必须记入 TokenLedger；无计量的重试 = 隐形成本。
2. **审计去重在 revision 前，不在 revision 内。** revision 直读 raw glob 审计 = 输入冗余 + 输出冗余；聚合层应在 revision_router 前置。
3. **输出 token 单价高于输入。** 输出侧浪费的优先级 ≥ 输入侧。（原「dead sidecar 产出是纯成本」表述已于 2026-08-24 修正：decisions sidecar 有 G4/state_heal 机器消费方，非纯成本——见 §2.4。）

---

## 8. 依赖关系图

```
总纲 spec
  ├─ §3.1 TokenLedger dead-wire ──► 本 spec 2.1 重试计量的前置
  └─ §3.5 dead sidecar ──► 本 spec 2.4 输出视角补全

推理控制 spec
  └─ §2.9 finish_reason=length 盲点 ──► 本 spec 2.1 截断致空烧的根因

本 spec（2026-08-24 修订后）
  ├─ 2.1 重试放大 ──► ✗ superseded：计量已接（PR #39）+ 截断已修（PR #40）+ 预算面归 #47/C33
  ├─ 2.2 审计交叉冗余 ──► P2 共享缺陷池（评估独立性冲突）
  ├─ 2.3 revision raw glob ──► P0 聚合去重层（接线契约见 §5.1a）
  └─ 2.4 dead sidecar 产出 ──► ✗ 关闭：3 残留经复核为已裁决 KEEP（归档 plan 2026-08-02，机器消费方存在）

P0/P1 实施前需另写 plan 并批准
```
