> **Date:** 2026-08-16 | **Status:** Design | **Severity:** 🟠 P1 | **方法:** systematic-debugging 四阶段
> **系列:** 2026-08-15 全项目审计 · 阶段 5 修复 spec（批次 C，簇 C33）| **依赖:** C32（rc=2 写审计语义先行——失败分类的输入）；C10（重试成本落账）| **范围:** tenacity 死层、openai SDK 重试、parallel/serial/scoring 外层重试、audit_retry_count 生命周期、失败分类枚举 | **核心洞察:** 三套互不知情的重试（SDK 隐式 max_retries=2 / tenacity 永不触发 / 外层无退避）相乘——修任何一层而不加全局预算，最坏放大到 27 请求/任务；确定性失败最多烧 6 次全价 LLM 调用验证必然失败结局

# C33 · 重试/失败分类统一（retry-failure-taxonomy）

## 元信息
- 簇：C33（重试/失败分类分裂：三套退避互不协调），11 条，最高严重度 P1（F977/T508 verified），证据等级=实验佐证
- 成员：T507（代表）、F363、F365、F533、F977、T506、T508、T510、T511、T512、T514
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
1. 单一失败分类枚举（transient / deterministic-gate / deterministic-content / budget-exhausted / unknown），每层重试决策消费同一分类
2. 全局重试预算：每章/每步持久记账（含 SDK 隐式重试次数），超预算直接升级不重试
3. 确定性失败（rc=2、schema REJECT、校验 FAIL）零重试、直接路由 revision/escalation

## 任务分解
### R1 · 失败分类枚举与分类点（T512 + F533 + F977）
- `FailureClass` 枚举入 enums.py（C8 单源）；分类器统一放 dispatch 边界：openai/httpx 异常→transient（tenacity `_is_retryable` 改按 FailureClass 判定）；rc=2（C32 修复后的确定性违规）/ 退出码与 JSON REJECT→deterministic
- **验收**：F977 复现用例——SDK 异常进 tenacity 重试；rc=2 样本零重试直达升级；分类结果写 trace

### R2 · 全局预算与层间协调（T506 + T507 + T510 + T511）
- 每 dispatch 携带 retry_budget（章级持久字段）；SDK max_retries 显式设 0 或 1 并计入预算；tenacity 与外层共享同一预算计数；scoring/串行路径加同一分类门（deterministic 不重试）+ 指数退避含 jitter（推广 T514 的 RETRY_JITTER）
- **验收**：模拟持续 5xx 的任务总请求数 ≤ 预算上限（T506 的 27 请求放大场景测试断言 ≤ 上限）；三层退避曲线单测

### R3 · audit_retry_count 生命周期（T508）
- ESCALATION checkpoint 解决（review approve）时重置对应 per-phase 计数器；machine.py 契约兑现
- **验收**：ESCALATION→解决→再 BLOCKING 场景走 revision 重试而非立即再升级（状态机集成测试）

### R4 · 预算记账接线（F363 + F365）
- 并行审计波/lifecycle 派发的重试计入 retry_budget_consumed；lifecycle 两步 G4 失败不再标 steps_done（改 failed 步 + 可重试状态）
- 与 C10 协同：每次重试的 token 消耗落 TokenLedger（含失败 attempt，修正上轮 F520 面）
- **验收**：注入失败 fixture 跑并行波，state 中预算字段非零且与 trace 一致

## 验收（簇级）
- `just check` 全绿；`tests/unit/pipeline/test_retry_taxonomy.py` 覆盖 R1-R4 全部分类×层级矩阵
- C33 全部 11 条 merged-into T507 回写关闭

## 风险
- 预算上限选值过紧会误伤慢网络真瞬时失败——上限入 PipelineConfig（去 C37 死旋钮后），先宽后紧并在 CI 环境校准
- 与 C32 的接口依赖：rc=2 语义在 C32 R1/R4 合入前，F533 分类先按"写审计失败=deterministic"占位实现，C32 合入后回归

## 验证命令
- 分类矩阵：`pytest tests/unit/pipeline/test_retry_taxonomy.py -q`（FailureClass × 三层重试 × 预算边界）
- 放大护栏：`pytest tests/unit/pipeline/ -k "amplification or budget_cap" -q`（T506 的 27 请求场景断言 ≤ 上限）
- 计数器生命周期：`pytest tests/unit/pipeline/ -k "audit_retry_reset" -q`（T508 场景：ESCALATION 解决后再 BLOCKING 走 revision）
- 成本落账：C10 合入后 `shenbi-cost report` 含失败 attempt token（对照 R4）
- 回归：`just check` 全绿

## 回写
- merged 关系（phase4 §3）：`T507 <- F363, F365, F533, F977, T506, T508, T510-T512, T514`
- 上轮承接：#24 的重试面（F301/F354/T501/T502）与 #4 的 F8 重试放大随本簇关闭；T513（上轮 T503-T505 断链重立）归 C35 承接机制处置
