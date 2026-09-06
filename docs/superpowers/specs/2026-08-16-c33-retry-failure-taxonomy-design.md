> **Date:** 2026-08-16 | **Status:** Design (Revised 2026-09-07 · 阶段 3 设计审查 C1-C2/I1-I5/M1-M5 吸收；T507 已由 PR #103 修复、F365 半面已由 PR #158 修复，scope 相应缩减) | **Severity:** 🟠 P1 | **方法:** systematic-debugging 四阶段
> **系列:** 2026-08-15 全项目审计 · 阶段 5 修复 spec（批次 C，簇 C33）| **依赖:** ~~C32~~（**已满足**：rc=2 写审计语义已由 PR #43 落地，#46 Rejected 收口——R1 直接按落地语义分类，无占位分支）；C10（已满足：PR #137）| **范围:** tenacity 死层、openai SDK 重试、parallel/serial/scoring 外层重试、audit_retry_count 生命周期、失败分类枚举——**显式限定 chapter_loop 域**（genesis/closure 计数器无持久预算面为已知残留，不归本簇扩容，记 I1 裁决） | **核心洞察:** 三套互不知情的重试（SDK 隐式 max_retries=2 / tenacity 永不触发 / 外层无退避）相乘——修任何一层而不加全局预算，最坏放大到 27 请求/任务；确定性失败最多烧 6 次全价 LLM 调用验证必然失败结局

# C33 · 重试/失败分类统一（retry-failure-taxonomy）

## 元信息
- 簇：C33（重试/失败分类分裂：三套退避互不协调），11 条，最高严重度 P1（F977/T508 verified），证据等级=实验佐证
- 成员：T507（代表）、F363、F365、F533、F977、T506、T508、T510、T511、T512、T514——**2026-09-07 复核**：9 条存活；T507 已由 PR #103 独立修复；F365 半面（缺失产物不标 steps_done）已由 PR #158 修复，残留 lifecycle 派发失败/G4 失败路由归 R4
- 来源：thread-reports/T5.md + Z3-review-r2 + Z5-review-r4 + Z9-review-r2
- 关系：吸收 `archive/2026-08-14-tooling-gate-chain-design.md`（#24）的重试面（F301/F354/T501/T502）与 `archive/2026-08-01-output-side-waste-audit-design.md`（#4）的 F8 重试放大

## 背景与根因
传输层与业务层各有 retry 机制但无共享分类/预算：
1. **tenacity 死层**（F977 P1 verified）：`_is_retryable` 仅 httpx 两分支，openai SDK 异常 issubclass 双 False——tenacity 层对 SDK 异常永不触发；T506（verified）修正事实：SDK 默认 max_retries=2 隐式兜底存在，但"修通 tenacity 而不加约束"会叠加放大至 27 请求/任务。
2. **计数器无生命周期**（T508 P1 verified）：audit_retry_count 无任何重置路径——ESCALATION 解决后首个 BLOCKING 立即再升级，永不再尝试 revision，与 machine.py "all per-phase retry counters are reset" 契约矛盾。
3. **外层无退避/无界**（T510：串行三层零退避；T511：scoring 路径无界重试）。
4. **无失败分类**（T512：确定性失败无跨层分类——单步最多 6 次全价 LLM 调用；F533：rc=2 写审计 GATE_FAIL 与瞬时失败在所有重试决策不可区分，test-validation 生产数据即重试放大实证）。
5. **预算记账缺失**（F363：并行审计波重试完全绕过持久 retry_budget_consumed；F365：lifecycle 派发失败/两步 G4 失败仍标记 steps_done）；T514：RETRY_JITTER=2.0 为全仓唯一显式 jitter。

## 目标
1. 单一失败分类枚举（`transient` / `deterministic_gate` / `deterministic_content`——budget-exhausted 是路由结果非失败签名、unknown 由 transient-or-escalate 一次性成文规则裁决，均不进枚举，M1），每层重试决策消费同一分类
2. 全局重试预算：章级持久记账（SDK 重试经 max_retries=0 根除后，全部重试可见于 tenacity/外层计数），超预算直接升级不重试
3. 确定性失败（rc=2、schema REJECT、scoring exit-2/exit-3 校验 FAIL）零重试、直接路由 revision/escalation

## 任务分解
### R1 · 失败分类枚举与分类点（T512 + F533 + F977）
- `FailureClass` 枚举入 enums.py（C8 单源；同步登记契约 schema 文档）；分类器统一放 dispatch 边界。**分类点清单（M3，全部接线，缺一即 dead-wire）**：① tenacity 谓词（dispatch_helper.py `_is_retryable`）按 FailureClass 判定，openai SDK 异常（含 `__cause__` 链上的 httpx 异常）→ transient；② `_with_write_audit` rc=2 GATE_FAIL 降级点 → deterministic_gate；③ `run_chapter_step` gate/scoring 出口（chapter_loop.py）→ deterministic_content；④ audit_layer 派发失败出口。T507 已由 PR #103 修复（typed timeout 路由），分类器建立在已有 typed exception 分支之上
- **验收**：F977 复现用例——SDK 异常进 tenacity 重试；rc=2 样本零重试直达升级；分类结果写 trace（**字段名 `failure_class`**，M5——C10 成本报告可 join；`_emit_dispatch_trace` 现有点位扩展）

### R2 · 全局预算与层间协调（T506 + T507 + T510 + T511）
- 每 dispatch 携带 retry_budget（章级持久字段，复用既有 `retry_budget_consumed` 机制而非另建）；**SDK max_retries 强制设 0**（单点：dispatch_helper OpenAI() 构造；"或 1"方案删除——SDK 不暴露内部重试计数，无法计入预算，C2），全部瞬时重试收敛到 tenacity 层（其 attempts 已有 `usage_acc["attempts"]` 计数）；scoring/串行路径加同一分类门（deterministic 不重试）+ 指数退避含 jitter（复用 parallel_dispatch 的 RETRY_JITTER 模式，T514 收敛为"串行/scoring 路径复用"）
- **exit-2/exit-3 重分类为显式交付物（I2）**：error_handler.py `handle_scoring_failure` 的 exit-2 validation-failure 无限重试路径（T511）改 deterministic 零重试直达 `_handle_failure`；模块 docstring 与 S11 语义同步修订
- **APPROVE 路径预算语义成文（I4）**：ESCALATION approve 后 `retry_budget_consumed` 保持在顶（人工担保语义，machine.py 现状）——本簇不改该行为，但在 R3 验收中显式断言（approve 后新失败应走升级而非再次烧预算重试），防止语义未定义
- **验收**：模拟持续 5xx 的任务总请求数 ≤ 预算上限（T506 的 27 请求放大场景测试断言 ≤ 上限）；退避曲线单测（注入 fake clock/tenacity wait 工厂，禁真实 sleep，M4b）

### R3 · audit_retry_count 生命周期（T508）
- ESCALATION checkpoint 解决时重置对应 per-phase 计数器——**覆盖全部三种决策 APPROVE/REJECT/MODIFY（C1）**：`clear_checkpoint`（machine.py）ESCALATION 分支增清 `chapter_states[ch].audit_retry_count` 与 `revision_count`；`_reset_retry_budget`（cli.py）同步扩展纳入两字段（与既有 `retry_budget_consumed` 处理对齐）；machine.py "all per-phase retry counters are reset" 契约兑现
- **验收**：ESCALATION→每种决策解决→再 BLOCKING 场景走 revision 重试而非立即再升级（状态机集成测试，T2 层级，M4c）；approve 后新失败走升级（I4 断言）

### R4 · 预算记账接线（F363 + F365 残留半面）
- **并行审计波预算接线设计（I3）**：`_dispatch_with_retry`（parallel_dispatch.py）工作线程无 state 句柄——采用**波次聚合**方案：worker 返回 attempts 计数（ReviewTask 增字段），波完成时主线程一次性计入 `retry_budget_consumed`（持锁写，避开 ThreadPool 内跨线程写 state）；崩溃一致性 = 波次聚合幂等重放（savepoint 已有语义），trace 为对账源
- F365 残留半面（PR #158 已修"缺失产物不标 steps_done"）：lifecycle 派发失败（chapter_loop.py 仅 log.error）与两步 G4 失败（仅 log.warning）改路由 `_handle_failure`（failed 步 + 可重试状态 + 预算记账）
- 与 C10 协同：每次重试的 token 消耗落 TokenLedger（含失败 attempt，修正上轮 F520 面）
- **验收**：注入失败 fixture 跑并行波（**具体路径：`tests/unit/pipeline/test_retry_budget.py` / `test_retry_accounting.py` 扩展**，M4a），state 中预算字段非零且与 trace `failure_class`/attempts 一致

## 验收（簇级）
- `just check` 全绿；`tests/unit/pipeline/test_retry_taxonomy.py` 覆盖 R1-R4 全部分类×层级矩阵
- C33 全部 11 条 merged-into T507 回写关闭

## 风险
- 预算上限选值过紧会误伤慢网络真瞬时失败——上限入 PipelineConfig（去 C37 死旋钮后），先宽后紧并在 CI 环境校准
- genesis/closure 域计数器无持久预算（I1 裁决残留面）——本簇不扩容，遗留记入 deviations 供后续 spec

## 验证命令
- 分类矩阵：`pytest tests/unit/pipeline/test_retry_taxonomy.py -q`（FailureClass × 三层重试 × 预算边界）
- 放大护栏：`pytest tests/unit/pipeline/ -k "amplification or budget_cap" -q`（T506 的 27 请求场景断言 ≤ 上限）
- 计数器生命周期：`pytest tests/unit/pipeline/ -k "audit_retry_reset" -q`（T508 场景：ESCALATION 解决后再 BLOCKING 走 revision）
- 成本落账：C10 合入后 `shenbi-cost report` 含失败 attempt token（对照 R4）
- 回归：`just check` 全绿

## 回写
- merged 关系（phase4 §3）：`T507 <- F363, F365, F533, F977, T506, T508, T510-T512, T514`
- 上轮承接：#24 的重试面（F301/F354/T501/T502）与 #4 的 F8 重试放大随本簇关闭；T513（上轮 T503-T505 断链重立）归 C35 承接机制处置
