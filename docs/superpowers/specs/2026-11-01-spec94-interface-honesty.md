# Spec #94 · 接口诚实批（interface-honesty）：modes 清障、cli 引擎出鞘、scoring 子命令化、dispatch 上下文收拢

**日期**：2026-11-01（r2 修订 2026-11-02：接收 #87 移出的 DispatchContext；T5 范围校准——`_record_gate_manifest` 三拷与 `now_iso` 双拷只收敛后者为共享 helper，前者仅登记）｜ **系列**：架构复审批次 A ｜ **状态**：Design（r2） ｜ **优先级**：🟡 P2
**依赖**：T4（dispatch 累积器/上下文）须 #87 后施工；其余独立可先行
**动机证据**：architecture-review-20261101 #13/#19/#23/#25/#26 卡；亲验：`codex_api.py:1-8` 自declared "Safe to delete entirely"；`detect_mode()` 只返回 codex/internal；cli.py 测试进口 5 个私有名；`dispatch_skill` 11 参数（`test_type`/`round_dir` 零 src 传参）

**触及的不变量维度**：无（接口/文档诚实层）

---

## 0. 根因

四处「名与实分居」：① dispatcher/modes/ 假缝——真三路由（API/IDE CLI/legacy 子进程）的 if/elif 在 dispatch_helper.py:4313-4333 无文档，modes/ 包里是 1 真 adapter + 死桩 + 穿戏服错误；docs/framework/dispatcher.md 9 行只记 legacy CLI。② cli.py 穿 CLI 服的编排器（~700 行引擎）。③ scoring.py 手术式 argv + 归一化双拷。④ `_dispatch_via_api` 474 行混运输/计量/观测/业务：4 段 trace 转发 + 两处逐行同体的 usage 算术（成本报发散风险）；`dispatch_skill` 11 参数里 2 个 legacy 专属。

## 1. 任务分解

### T1 · modes 清障 + 真路由文档（独立）
- 删 `modes/codex_api.py`（自declared 死桩）；`modes/internal.py` 的 NoReturn 错误消息移入 `detect_mode()` else 分支后删文件；
- `docs/framework/dispatcher.md` 重写：真三路由链（env 探测优先级 / 各路由返回形态 / 两 write-audit 包装分工——`executor.dispatch_with_write_audit` vs `dispatch_helper._with_write_audit:4194`，**合并留待 #87 后续触碰**，本批只记录分工）。
- **不建 DispatchRoute Protocol**（两真一路由；第三 adapter 才是真缝条件——YAGNI）。

### T2 · cli 引擎出鞘（纯搬家零新抽象）
`_execute_pending_re_dispatches`（:260-460）/ `_orchestrate_to_checkpoint`（:477-659）/ staging 提交域（:676-789）/ redo-rollback（:990-1148）/ `_verify_truth_integrity`（:1414-1470）迁 `pipeline/orchestrator.py` 并公共化；`cmd_*` 留 argparse → 一调用 → emit_json；测试改 import 正名符号。cli.py 目标 <900 行。

### T3 · scoring 子命令化 + 归一化单源
`scoring.main` 转 argparse 子命令（`score` / `gate-only` / `--kill-switch` 为 score 的显式旗标）；`parse_scores_dict` 吸收 codex 版差异（bool 豁免进单实现；**红测钉两版现行为差异表**——分叉处取更正确者并注释）；codex.py import 单源。

### T4 · dispatch 上下文收拢 + `_DispatchOutcome` 累积器（依赖 #87）
- `DispatchContext` dataclass 收 per-dispatch 上下文（uses_staging/shared_context/state/path_context/outputs_override）；`dispatch_skill` **删除 `test_type`/`round_dir` 两个零 src 传参**（先删纯无用参数——最小动作；legacy 路由自 context/独立入口读）；docstring 记述不存在的 `timeout` 参数一并修（:4327）；
- `_DispatchOutcome` 对象收 usage 累积/archive 帧/trace 发射（`record(success, finish_reason, failure_class)` 单方法）：4 段 trace 块 → 1、账目算术双拷（`_account_failed_attempt` :3176-3217 vs 成功面 :3755-3767）→ 1；
- **characterization 红测**：成功/失败/超时/再升帽四出口的 trace 事件字段与重构前逐字节一致。

### T5 · 文档诚实小批
- AGENTS.md「phase_runner.py — T2/T3 phase state machine」→「T2 phase state machine（T3 走 pipeline/state.py——模块自述 :1-2）」；
- ADR 0004 附注实际插件集（pytest-randomly；asyncio/ordering 未装）；
- ≥12 处跨文件行号注释改**函数名引用**（≥1 已烂：decisions_validator.py:184 引 shared.py:113——fail 的 must_fix 逻辑实在 :583-585）；
- `now_iso` 双拷（phase_runner:83 vs machine.py:26）→ 收敛一个共享 helper（落 pipeline/_shared 或 safe_write 旁）；
- `_record_gate_manifest` best-effort 三拷（phase_runner:87-112 / dispatch_helper:4579 / codex:221-239）：**本批只登记**（三者门检语义细节差异需逐个核对，收敛放后续触碰——不做盲目合并）。

### T6 · 杂项微型接口修复
- `write_truth_file` 的 `mode` 4 魔法串 → Literal（零成本，调用方类型自检）；
- ReviewChecklist 序列化双 dict（:130-145,:167-183 手拷）→ `dataclasses.asdict`；
- 角色显示名：`review_checklist.py:409` 全文正则（`name:` 任意行可被散文劫持）→ 走 truth_index frontmatter 解析（#85 后的 `split_frontmatter`）；
- `closure.py:148-165` 魔法步号（`step_num in (4,5)`/`==2`/`in (6,7,10)`）→ `ClosureStep.context_kind` 字段（知识上表，插步不再静默错位）。

## 2. 验收

1. `grep -rn codex_api src/` 零；dispatcher.md 含三路由决策树；
2. cli.py <900 行且测试零 import cli 私有（orchestrator 正名符号替代）；
3. `shenbi-score --help` 显两子命令；codex.py 无 `_normalize_scores` 定义（import 单源）；
4. T4 四出口 trace 逐字节一致（characterization）＋ `dispatch_skill` 签名无 test_type/round_dir；
5. T5 三文档/常量判据绿；行号注释剩余 ≤2（稳定锚注记豁免）；
6. `just check` exit 0。

## 3. 顺序

T1/T2/T3/T5/T6 相互独立可并行小 PR；T4 必须 #87 落地后（同函数域）。
