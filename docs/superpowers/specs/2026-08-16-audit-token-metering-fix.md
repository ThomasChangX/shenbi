> **Date:** 2026-08-16 | **Status:** Design · Revised 2026-08-31 | **Severity:** 🟥 Critical | **方法:** systematic-debugging 四阶段
> **系列:** 2026-08-15 全项目深度审计 · 阶段 5（簇 C10，20 条）| **代表 finding:** F301 | **严重度上限:** P0（F301/F504）| **涉及文件面:** src/shenbi/pipeline/dispatch_helper.py、cost/ledger.py、cost/report.py、cost/estimate.py、trace/writer.py、pipeline/chapter_loop.py（闭卷/章循环节点）
> **修订注（v2 · 2026-08-31）**：SDD 价值门复核剔除已修任务——原 T1/T2/T3（记录点去门控/chapter 现场值/集成护栏）已由 commit 0d36d31a 落地 main（F301/F302/F344/F359/F504/F505/T401/T403/T409/F530 已修）；原 T6 的 T405（_try_avg_g3_score 抓取噪声）已由 commit 2812466c（spec #27 T5）修复；T406「单桶」表述修正（by_chapter 实为多桶，真问题是 per-chapter average 无信息量且无警告行）。本版只含存活任务 T4/T5/T6′/T7，任务编号保留原编号以维持可追溯。

# token 计量/成本证据链接线（audit-token-metering）v2

## 背景（已修面略，见修订注）

候选元根因 E 的核心 dead-wire（API 路径零落账、chapter 恒 0、resume 归零）已由 0d36d31a 修复：`_dispatch_via_api` 内 `TokenLedger(project_dir).record(...)` 无 state 门控直写（dispatch_helper.py:1618），chapter 用 path_ctx 现场解析值，集成护栏 `tests/unit/pipeline/test_token_ledger_guard.py` 常驻 CI。

仍存活的面（2026-08-31 main HEAD 逐字核实）：

- **T402/F1115**：消费端唯一入口仍是手动 `shenbi-cost report`；章循环/闭卷/genesis 节点零自动产出（chapter_loop.py 全文无 cost 导入）。零计量事故的发现延迟 = 人工。
- **F796/L4（T5）**：`_dispatch_via_ide`（dispatch_helper.py:2020-2128）零 token 捕获——:2114-2122 自述 `"ide_dispatch_uninstrumented_tokens", hint="IDE path cannot record usage; ledger row skipped"`；legacy 子进程路由（:2334-2380）:2367-2371 自述 `"legacy subprocess path records no token usage"`。真实 56 章零计量的面。
- **T404**：`cost/ledger.py:23-34` `_safe_estimate_cost` 对未知模型吞 ValueError 返 $0.0（仅 WARN）——2M tokens 记 $0.0000，成本证据静默失真。
- **T406′**：`cost/report.py:79-82` per-chapter average = sum(各章成本)/len(章桶)，算术上恒等于 total_cost/章数，无独立信息，且无警告行提示读者。
- **F523**：`cost/estimate.py:24-32` CJK 判定仅 0x4E00-0x9FFF（不含扩展 A 区 0x3400-0x4DBF、兼容表意、全角字符/中文标点）→ 中文 prompt token 系统性低估；`_DEFAULT_CONTEXT_LIMIT = 1_048_576` 对未知模型是乐观回退，且无一次性告警（每次仅标准 WARN）。
- **F1116/T7**：trace 事件零 finish_reason 字段（trace/writer.py、event.py grep 零命中）；`_call_llm_streaming_with_retry`（dispatch_helper.py:1741-1767）对可重试异常直接抛出，中途已收到的 usage 随异常丢弃——重试失败尝试的 tokens 不入 ledger（T410 随本项记录）。

## 修复目标

1. 章循环/闭卷节点自动产出 cost 报告（零计量事故发现延迟从人工降为节点级）。
2. IDE 派发路径至少落估记下界行；子进程路由 usage 可观测。
3. 未知模型显式标记不吞 $0；报告面指标诚实；token 估记保守。
4. trace 含 finish_reason；重试尝试 usage 入账。

## 任务分解

- **T4 · 消费面自动化（T402/F1115）**：章循环/闭卷节点自动产出 cost 报告（渲染 `cost/report.md` 或等价摘要行），不再依赖手动 CLI。产出失败只 WARN 不阻断章循环（与 ledger 写侧同 fail-safe 语义）。
- **T5 · 子进程/IDE 路径（F796/L4）**：IDE 路径最少落估记下界行（estimate_prompt_tokens 对 prompt+输出文本估记，ledger 行带 `estimated=true` 标记）；legacy 子进程路由三选一（--json 回传/估记行/子进程直写），选实现成本最低且不违反 single-writer 契约者。
- **T6′ · 报告面正确性（T404/T406′/F523）**：
  - T404：未知模型产出 `unknown-model` 标记行（estimated_cost_usd 保留 0.0 但 model 字段显式标记），不静默吞 ValueError。
  - T406′：per-chapter average 若无独立信息则输出警告行（或移除该指标），不误导读者。
  - F523：CJK 判定扩区（≥0x3400-0x9FFF + 全角 0xFF00-0xFFEF）；未知模型上下文上限回退改保守值（如 128K）+ 进程内一次性告警。
- **T7 · trace 计量盲点（F1116/T410）**：dispatch 相关 trace 事件补 finish_reason；重试尝试（含失败 attempt）的 usage 入 ledger（attempt 序号入行）。

## 批量清理

- F359 已随 0d36d31a 消解；T410（重试失败尝试 usage 丢弃）随 T7 记录并修复。

## 验收标准

1. dry-run/护栏路径下章循环完成节点产出 cost 报告文件（或日志摘要），内容含累计 token（fixtures/护栏驱动测试表达，禁真实 dispatch）。
2. IDE 路径派发后 ledger 出现 `estimated=true` 估记行（测试驱动）。
3. 未知模型名的派发在 ledger 中产出 `unknown-model` 标记行而非静默 $0 行（T404 断言）。
4. per-chapter average 指标不再无信息量误导（警告行或移除，测试断言）。
5. 含扩展 A 区/全角字符的中文文本 estimate_prompt_tokens 估记高于现行 BMP-only 实现（测试断言）；未知模型回退为保守上限且仅告警一次。
6. dispatch trace 事件含 finish_reason 字段；模拟重试场景下失败 attempt 的 usage 入账（测试断言）。
7. `just check` 全绿。

## 风险与回滚

- 风险：T4 自动产出在章循环节点加 I/O——须 fail-safe（WARN+跳过，不阻断循环）；T5 估记行进入 ledger 会混入真实计量——必须 `estimated` 标记隔离，report 侧分列；T7 重试 usage 入账改变 ledger 行语义（新增 attempt 字段须向后兼容旧行解析）。
- 回滚：各任务独立可 revert；T3 护栏（已落地）常驻防 API 路径回归。

## 簇成员清单（C10 · 20 条，2026-08-31 处置状态）

已修（0d36d31a）：F301 F302 F344 F359 F504 F505 T401 T403 T409 F530
已修（2812466c，spec #27 T5）：T405（F511 面归 C1）
本 spec 存活：T402 F796 T404 T406 F523 F1116 T410 F1115
随 T4 记录：T1611（生产无 cost/ 的互证项，消费面自动化后节点级可见）
