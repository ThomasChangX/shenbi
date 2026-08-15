> **Date:** 2026-08-16 | **Status:** Design | **Severity:** 🟥 Critical | **方法:** systematic-debugging 四阶段
> **系列:** 2026-08-15 全项目深度审计 · 阶段 5（簇 C10，20 条）| **代表 finding:** F301 | **严重度上限:** P0（F301/F504）| **涉及文件面:** src/shenbi/pipeline/dispatch_helper.py（落账点）、cost/ledger.py、cost/report.py、state checkpoint 字段、parallel_dispatch/genesis/closure/triggers 8+ 调用点
> **注:** 归档 spec #12（2026-08-14 cost-ledger）与 PR #39 已接 API 路径一段；本 spec 为 2026-08-15 审计簇级合并版，含修复形状修正（T401）

# token 计量/成本证据链接线（audit-token-metering）

## 背景

候选元根因 E：TokenLedger 存在但生产运行零 token 证据——40 小时/56 章真实运行无 cost/ 目录（F1115 生产实证）。系统性 dead-wire：

- **F301/F504（P0）**：8 个调用点（并行审计波/并行 post-draft/genesis/closure/triggers 等）派发均不传 state，TokenLedger 系统性少计。
- **F302/F505**：chapter 键恒 0（`getattr(state,"chapter",0)`，PipelineState 无该属性）→ by_chapter 坍缩。
- **T403/F344/F530**：state.token_usage 为未声明动态属性，不参与 to_dict/from_dict/checkpoint——跨进程全丢、resume 归零，print_token_summary 只统计本进程。
- **T404（P1）**：未知模型 `_safe_estimate_cost` 吞 ValueError，2M tokens 记 $0.0000。
- **F796（阶段 4 提案升 P1）**：IDE dispatch 路径零 token 捕获 + chapter 列恒 0。
- **消费面**：T402（durable 消费端仅手动 CLI）、F523（未知模型上下文上限乐观回退告警失火）、T405（cost-per-quality-point 吞噬非 G3 分数）、T406（per-chapter average 恒等于总成本）、F511（avg G3 分数抓取噪声，归 C1 同报）、F1116（trace 无 finish_reason、重试无反馈变化）、T1611（生产项目无 cost/ledger、无 trace——与 F301/F504 互证）。
- **护栏缺失**：T409——spec R1 验收无集成护栏，是 dead-wire 两次复发（07-20、08-02）的根因。

**修复形状修正（本 spec 核心，T401 verified）**：F301 的直觉修法"逐调用点补传 state"是错误形状——落账单点被 state 双重门控（dispatch_helper.py:1310 `if state:` + :1345 `if project_dir`），而落账所需四要素（project_dir/skill/usage/chapter）在 `_dispatch_via_api` 记录现场全部可得（chapter 已在 :1520-1524 从 path_ctx 解析）；E1 实验证明传 state 后 chapter 仍=0；并行路径传 state 更违反代码库 single-writer 契约（chapter_loop.py:2400、state.py:513 自述不变式）。**正确形状 = 记录点去 state 门控**：在 `_dispatch_via_api` 内直接 `TokenLedger(project_dir).record(skill, chapter or 0, {...})`，一处改动接通 13/13 API 调用点，改动面比"全调用点传 state"小一个数量级。

## 修复目标

1. 生产 API 路径每次派发产生一行持久 ledger 记录（13/13 调用点）。
2. chapter 维度真实（非恒 0）；resume 后累计连续（不归零）。
3. 未知模型不静默 $0；报告面指标正确。
4. 集成护栏防 dead-wire 第三次复发。

## 任务分解（顺序即 T4 报告裁定的修复顺序）

- **T1 · 记录点去门控（T401/F301/F504）**：`_dispatch_via_api` 内直接落账（chapter 用 :1520-1524 现场值），删除 :1310/:1345 的 state 双重门控（durable 写不依赖 state）；legacy 分支收 state 静默丢弃处同步清理。state 仅保留内存摘要或整体废弃（单一事实源=ledger，print_token_summary 改读 ledger）。
- **T2 · chapter 键与持久化（F505/F302/T403/F344/F530）**：chapter 用记录现场值；token_usage 若保留则提升为 state 序列化字段（to_dict/from_dict/checkpoint 补齐）。
- **T3 · 集成护栏（T409）**：fake OpenAI client 跑 genesis + chapter step，断言 token-ledger.jsonl 行数 == dispatch 数（T401 方案下断言不依赖 state 传参）；护栏入 CI。
- **T4 · 消费面自动化（T402/F1115）**：章循环/闭包节点自动产出 cost 报告（不再依赖手动 `shenbi-cost report`）；F1115 类零计量事故的发现延迟从人工降为节点级。
- **T5 · 子进程/IDE 路径（F796/L4）**：子进程路由三选一（--json 回传/估记行/子进程直写）；IDE 路径最少落估记下界行（真实 56 章零计量的面）。
- **T6 · 报告面正确性（T404/T405/T406/F523）**：未知模型显式 "unknown-model" 标记行（不吞 ValueError、不 $0）；cost-per-quality-point 只读登记的 G3 分数（字段名白名单）；单桶 by_chapter 输出警告行；上下文上限回退改保守值+一次性告警。
- **T7 · trace 计量盲点（F1116）**：trace 事件补 finish_reason；重试尝试 usage 入账（T410 归批量）。

## 批量清理（纯 M 成员）

- F359（resume VOLUME_BOUNDARY 分支不传 state）随 T1 自动消解（落账不再依赖 state 传参）；T410（重试失败尝试 usage 丢弃）随 T7 记录。

## 验收标准

1. 集成护栏（T3）在 CI 绿：ledger 行数 == dispatch 数（fake client 两 step 各 ≥1 行）。
2. dry-run 两章后 `cost/token-ledger.jsonl` 存在且 chapter 字段为 1、2（非 0）（F505/T401 断言）。
3. kill + resume 后 report 累计 token 单调不减（F530/T403 断言）。
4. 未知模型名的派发在 ledger 中产出 "unknown-model" 标记行而非 $0 行（T404 断言）。
5. `just check` 全绿。

## 风险与回滚

- 风险：去门控使落账路径无条件执行，若 project_dir 解析失败需 fail-safe（跳过落账 + WARN，不得阻断派发）；废弃内存累计（T1 选项 B）改变 print_token_summary 行为，CLI 消费方需同步。T5 子进程直写与 C11 并发簇的写协议联动（ledger 追加需锁）。
- 回滚：T1 单点改动可独立 revert（回退后恢复现状=零计量，无数据损坏面）；T3 护栏常驻防回归。

## 簇成员清单（与 phase4-clustering.md §2 机械对照）

C10（20 条，代表 F301）：

F301 F302 F344 F359 F504 F505 F523 F530 F796 F1115 F1116 T401 T402 T403
T404 T405 T406 T409 T410 T1611
