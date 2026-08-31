> **Date:** 2026-08-16 | **Status:** Done (PR #137) | **Severity:** 🟥 Critical | **方法:** systematic-debugging 四阶段
> **系列:** 2026-08-15 全项目深度审计 · 阶段 5（簇 C10，20 条）| **代表 finding:** F301 | **严重度上限:** P0（F301/F504）| **涉及文件面:** src/shenbi/pipeline/dispatch_helper.py、cost/ledger.py、cost/report.py、cost/estimate.py、trace/writer.py + trace/materialize.py、pipeline/chapter_loop.py（_complete_chapter）、pipeline/closure.py
> **修订注（v2 · 2026-08-31）**：SDD 价值门复核剔除已修任务——原 T1/T2/T3（记录点去门控/chapter 现场值/集成护栏）已由 commit 0d36d31a 落地 main（F301/F302/F344/F359/F504/F505/T401/T403/T409/F530 已修）；原 T6 的 T405（_try_avg_g3_score 抓取噪声）已由 commit 2812466c（spec #27 T5）修复；T406「单桶」表述修正（by_chapter 实为多桶，真问题是 per-chapter average 无信息量且无警告行）。
> **修订注（v3 · 2026-08-31，阶段 3 设计审查收敛）**：钉死 v2 遗留的未决选择——T7 二分入账语义（流末失败/中途断流）+ accumulator 穿透 @retry 机制 + dispatch trace 事件发射点；ledger 新字段一律带默认值（防旧存量行被 TypeError-skip 静默销毁）；T4 钉死产出节点与形态；T5 钉死为估记行（弃子进程直写——违反 single-writer）；F523 前移至 T5 之前；T404 改独立标记字段不改写 model 名。任务编号保留原编号。

# token 计量/成本证据链接线（audit-token-metering）v3

## 背景（已修面略，见修订注）

核心 dead-wire（API 路径零落账、chapter 恒 0、resume 归零）已由 0d36d31a 修复：`_dispatch_via_api` 内 `TokenLedger(project_dir).record(...)` 无 state 门控直写（dispatch_helper.py:1618），chapter 用 path_ctx 现场解析值，集成护栏 `tests/unit/pipeline/test_token_ledger_guard.py` 常驻 CI。

仍存活的面（2026-08-31 main HEAD 逐字核实）：

- **T402/F1115**：消费端唯一入口仍是手动 `shenbi-cost report`；章循环/闭卷/genesis 节点零自动产出（chapter_loop.py 全文无 cost 导入）。零计量事故的发现延迟 = 人工。
- **F796/L4（T5）**：`_dispatch_via_ide`（dispatch_helper.py:2020-2128）零 token 捕获——:2114-2122 自述 `"ide_dispatch_uninstrumented_tokens"`；legacy 子进程路由（:2334-2380）:2367-2371 自述 `"legacy subprocess path records no token usage"`。
- **T404**：`cost/ledger.py:23-34` `_safe_estimate_cost` 对未知模型吞 ValueError 返 $0.0（仅 WARN）——成本证据静默失真。
- **T406′**：`cost/report.py:74-78` per-chapter average = sum(各章成本)/len(章桶)，算术上恒等于 total_cost/章数，无独立信息，且无警告行。
- **F523**：`cost/estimate.py:24-32` CJK 判定仅 0x4E00-0x9FFF（不含扩展 A 区 0x3400-0x4DBF、兼容表意 0xF900-0xFAFF、全角形式 0xFF00-0xFFEF）→ 中文 prompt token 系统性低估；`_DEFAULT_CONTEXT_LIMIT = 1_048_576` 对未知模型是乐观回退，且无一次性告警。
- **F1116/T7**：dispatch 全链路（dispatch_helper.py、dispatcher/）今天不产出任何 TraceEvent（trace 事件仅由 materialize_progress 生成，trace/materialize.py:49-53），finish_reason 止步于 `_dispatch_via_api` 局部变量（:1848）；`_call_llm_streaming_with_retry`（:1741-1767）对可重试异常直接抛出。**注意**（v3 钉死）：usage 仅在最终 chunk 携带（stream_options include_usage，:1700-1710）——可重试异常若发生在流中途/建流阶段，usage 从未到达客户端，无真实值可入账；仅「流已走完后的失败」存在已收 usage。

## 修复目标

1. 章循环/闭卷节点自动产出 cost 报告（零计量事故发现延迟从人工降为节点级）。
2. IDE 派发路径与重试失败尝试落估记下界行（`estimated=true` 隔离）。
3. 未知模型显式标记不吞 $0；报告面指标诚实；token 估记保守。
4. dispatch trace 事件（含 finish_reason）接入既有 trace 流。

## Ledger 兼容契约（全任务前置约束，v3 钉死）

`TokenUsageRecord` 新增字段一律带默认值：`estimated: bool = False`、`attempt: int = 1`、`pricing_status: str = "ok"`。`iter_records` 现行 `TokenUsageRecord(**data)` TypeError-skip（ledger.py:96-99）意味着任何无默认值新字段都会使**全部存量行**被静默跳过——历史成本证据读取侧清空。验收含「旧格式行 + 新格式行混合文件全量可读」。

## 任务分解（顺序即执行顺序，v3 调整：F523 前移至 T5 之前）

- **T6′a · 估记基础（F523）**：`estimate_prompt_tokens` CJK 判定扩区（0x3400-0x9FFF 基本区+扩展A、0xF900-0xFAFF 兼容表意、0xFF00-0xFFEF 全角）；未知模型上下文上限回退改保守值（128K）+ 进程内一次性告警（模块级 flag 须带测试 reset 钩子）。
- **T5 · 子进程/IDE 路径（F796/L4）**：**钉死为估记行**（v3 裁定：弃「子进程直写」——ledger 锁为进程内 threading.Lock（ledger.py:57），跨进程 append 无锁协同且 ledger 可能分裂两目录，违反 single-writer；弃「--json 回传」——改动面大收益同）。IDE 路径对 prompt 文本用（T6′a 修复后的）`estimate_prompt_tokens` 落估记下界行，`estimated=true`；legacy 子进程路由同样落估记行（prompt 可得，输出量未知→下界）。report 侧 estimated 行分列不计入精确成本。
- **T4 · 消费面自动化（T402/F1115）**：**钉死节点与形态**（v3）：`chapter_loop._complete_chapter`（:1014）+ `pipeline/closure.py` 闭卷收尾各调用 `render_report` 渲染 `cost/report.md`（复用手动 CLI 同一渲染函数，不另造格式）；产出失败仅 WARN 不阻断循环（与 ledger 写侧同 fail-safe 语义）。`cost/report.md` 为运行时产物（与 `cost/token-ledger.jsonl` 同目录同性质），非 truth 文件、不入契约面。
- **T6′b · 报告面正确性（T404/T406′）**：
  - T404：`_safe_estimate_cost` 的 ValueError 路径不再静默 $0——ledger 行加独立字段 `pricing_status: "unknown-model"`（**不改写 model 字段**，保留真实模型名供排障；标记须从 `_safe_estimate_cost` 穿出到 `record()`——resolve_model 在 record 内部，ledger.py:67，需重构为 record 侧可感知）。
  - T406′：per-chapter average 保留但**输出警告行**（v3 钉死，弃移除——不改 CLI 消费面），说明该值=总成本/章数无独立信息。
- **T7 · trace 计量盲点（F1116/T410）**：
  - **入账二分**（v3 钉死）：(a) 流已完整走完后的失败路径——真实已收 usage 入账；(b) 建流/中途断流——以 T5 估记行机制落 prompt 估记下界（`estimated=true`、`attempt=N`）。**机制**：`_call_llm_streaming` 增加传入 mutable accumulator dict（`usage_acc: dict`），函数内收到 usage 即写入——@retry 装饰器下失败 attempt 的局部状态经 accumulator 逃逸，`_call_llm_streaming_with_retry` 捕获可重试异常时按二分语义入账后 re-raise。
  - **trace 接线**（v3 钉死，防 dead-wire）：dispatch trace 事件的发射点 = `_dispatch_via_api` 成功/失败收尾处（该函数已有 project_dir/round_dir 上下文），新建事件类型（如 `DISPATCH`），payload 含 skill/chapter/model/finish_reason/estimated/attempt；经既有 TraceWriter（round_dir 可得时）落 trace 流。若 round_dir 不可得则跳过 trace（仅 ledger）+ DEBUG 日志。`finish_reason` 字段经 payload 传递，不改 TraceEvent schema 强制字段（避免 schema_version bump 与 G7 链校验连锁）——payload 为自由 dict，compaction/replay 不受影响。

## 批量清理

- F359 已随 0d36d31a 消解；T410（重试失败尝试 usage 丢弃）随 T7 修复。

## 验收标准

1. 章循环完成节点与闭卷收尾产出 `cost/report.md`（fixtures/护栏驱动测试表达，禁真实 dispatch），内容含累计 token；产出失败不阻断循环（fail-safe 测试断言）。
2. IDE 路径派发后 ledger 出现 `estimated=true` 估记行（测试驱动）。
3. 未知模型名的派发在 ledger 中产出 `pricing_status="unknown-model"` 行且 model 字段保留真实模型名（T404 断言）。
4. per-chapter average 后跟警告行（测试断言）。
5. 含扩展 A 区（U+3400 区段）与全角字符的中文 fixture：`estimate_prompt_tokens` 估记**严格大于** BMP-only 旧实现的返回值（钉死比较断言，非弱断言）；未知模型回退 128K 且进程内仅告警一次（reset 钩子下二次调用无告警断言）。
6. 模拟流末失败：真实 usage 入账 `attempt=N`；模拟中途断流：估记行 `estimated=true`（测试断言）。dispatch trace 事件含 finish_reason payload 字段（round_dir 可得路径测试断言）。
7. 旧格式 ledger 行 + 新字段行混合文件 `iter_records` 全量可读零 skip（兼容契约断言）。
8. `just check` 全绿。

## 风险与回滚

- 风险：T4 自动产出在章循环节点加 I/O——fail-safe（WARN+跳过）；T5 估记行混入真实计量——`estimated` 标记隔离 + report 分列；T7 accumulator 改变 `_call_llm_streaming` 签名——调用方仅 `_call_llm_streaming_with_retry` 一处（grep 验证后写进 plan）；trace 新事件类型对 replay/compaction 的影响——payload 自由 dict 不触 schema。
- 回滚：各任务独立可 revert；T3 护栏（已落地）常驻防 API 路径回归。

## 簇成员清单（C10 · 20 条，2026-08-31 处置状态）

已修（0d36d31a）：F301 F302 F344 F359 F504 F505 T401 T403 T409 F530
已修（2812466c，spec #27 T5）：T405（F511 面归 C1）
本 spec 存活：T402 F796 T404 T406 F523 F1116 T410 F1115
随 T4 记录：T1611（生产无 cost/ 的互证项，消费面自动化后节点级可见）
