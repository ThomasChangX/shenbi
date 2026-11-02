# Spec #94 · 接口诚实批（interface-honesty）：modes 清障、cli 引擎出鞘、scoring 子命令化、dispatch 上下文收拢

**日期**：2026-11-01（r2 修订 2026-11-02：接收 #87 移出的 DispatchContext；T5 范围校准——`_record_gate_manifest` 三拷与 `now_iso` 双拷只收敛后者为共享 helper，前者仅登记；**r2.2 2026-11-02 全量对抗式审计修订**——T2 收益核算须含 cmd_review（原范围不可达 <900）、T1 错误移 dispatch() 非 detect_mode、T3 补调用方迁移、T4 参数是 legacy 载荷非无用、T5 计数 6 非 12、T6 依赖 #85）｜ **系列**：架构复审批次 A ｜ **状态**：Design（r2.2） ｜ **优先级**：🟡 P2
**依赖**：T4（dispatch 累积器/上下文）须 #87 后施工；其余独立可先行
**动机证据**：architecture-review-20261101 #13/#19/#23/#25/#26 卡；亲验：`codex_api.py:1-8` 自declared "Safe to delete entirely"；`detect_mode()` 只返回 codex/internal；cli.py 测试进口 5 个私有名；`dispatch_skill` 11 参数（`test_type`/`round_dir` 零 src 传参）

**触及的不变量维度**：无（接口/文档诚实层）

---

## 0. 根因

四处「名与实分居」：① dispatcher/modes/ 假缝——真三路由（API/IDE CLI/legacy 子进程）是 `dispatch_skill`（**定义在 :4301**）内的**三段 early-return（:4356-4460）**，无文档；modes/ 包里是 1 真 adapter + 死桩 + 穿戏服错误；docs/framework/dispatcher.md 9 行只记 legacy CLI。② cli.py 穿 CLI 服的编排器（~700 行引擎）。③ scoring.py 手术式 argv + 归一化双拷。④ `_dispatch_via_api` **475 行**（3529-4003）混运输/计量/观测/业务：4 段 trace 转发 + 两处逐行同体的 usage 算术（成本报发散风险）；`dispatch_skill` 11 参数里 2 个 legacy 专属。

## 1. 任务分解

### T1 · modes 清障 + 真路由文档（独立）
- 删 `modes/codex_api.py`（自declared 死桩）；`modes/internal.py` 的 NoReturn 错误消息**移入 `dispatch()` 的 else 分支（:241-243）后删文件**——**r2.2 更正**：`detect_mode()` 是被日志（:213-214）与 3 个测试当作**纯探测函数**断言返回 `"internal"` 的（test_dispatcher_executor.py:189/197/205；test_executor_gate_order.py:24/50/72 patch 成 `lambda: "internal"`），在 detect_mode 里抛异常会改 API 语义并破测；
- **测试连带（r2.2）**：`tests/unit/test_dispatcher_modes.py:9,29`、`tests/unit/dispatcher/test_executor_no_codex_api.py:20` import/monkeypatch `codex_api` 与 `internal`——同批删除/改写；验收 grep 扩到 `src/ tests/`；
- `docs/framework/dispatcher.md` 重写：真三路由链（env 探测优先级 / 各路由返回形态 / 两 write-audit 包装分工——`executor.dispatch_with_write_audit` vs `dispatch_helper._with_write_audit:4197`【r2.2 +3 行漂移】，**合并留待 #87 后续触碰**，本批只记录分工）；**r2.2 更正**：路由体在 **:4356-4460**（签名+docstring 在 :4313-4333），形态是 `if: return` ×2 + 隐式 fallthrough，不是 if/elif。
- **不建 DispatchRoute Protocol**（两真一路由；第三 adapter 才是真缝条件——YAGNI）。

### T2 · cli 引擎出鞘（纯搬家零新抽象）
`_execute_pending_re_dispatches`（:260-461）/ `_orchestrate_to_checkpoint`（:477-661）/ staging 提交域（:676-792）/ redo-rollback（:990-1148）/ `_verify_truth_integrity`（:1414-1470）迁 **`orchestration/checkpoint_flow.py`**（r2.2：避免 `orchestrator` 与既有 `orchestration/` 双名）并公共化；**r2.2 收益核算**：五段实测 720 行，cli.py 1809−720=**1089**，连 `_re_dispatch_g4_must_fix`(200-259) 一并搬 →1029，**仍不到 <900**——须把 `cmd_review`(1151-1379，229 行) 的决策体也下沉 →**~860**；该决策体正是 redo 逻辑的第三份拷贝（`_chapter_mismatch`/`_defer_redo…`/`_queue_re_dispatches` 在 cmd_review 与 `_apply_reject_redo` 双写），下沉顺带消重；`cmd_*` 留 argparse → 一调用 → emit_json；测试改 import 正名符号（**实为 8 个私有符号**：`_apply_reject_redo`/`_commit_staging_for_checkpoint`/`_execute_pending_re_dispatches`/`_queue_re_dispatches`/`_read_total_chapters`/`_rollback_genesis_to_steps`/`_update_total_chapters`/`_verify_truth_integrity` + 2 常量 + 4 处 `cli_mod._x` patch）。

### T3 · scoring 子命令化 + 归一化单源
`scoring.main` 转 argparse 子命令（`score` / `gate-only` / `--kill-switch` 为 score 的显式旗标）；**r2.2 补调用方迁移**：`dispatcher/modes/codex.py:285-300` 以**位置参数**调 `shenbi-score <rubric> <scores> --test-type --round-dir --subagent`——改子命令后断；同批迁移或加一版兼容 shim（无子命令→等价 `score`）；测试 `test_scoring.py`(4 处)/`test_process_guard.py:63`/`test_phase_cli.py:115`/`test_file_list.py:37` 与 AGENTS.md 用法同步。`parse_scores_dict` 吸收 codex 版差异——**r2.2 更正：差异不止 bool 豁免，共 4 项**（值强转 float 并丢弃非数值 / scoring 版值留 Any / 键判定 `int(k)` try vs `_INT_KEY_RE` / 异常面）；**红测钉四表**——分叉处取更正确者并注释；codex.py import 单源。

### T4 · dispatch 上下文收拢 + `_DispatchOutcome` 累积器（依赖 #87）
- `DispatchContext` dataclass 收 per-dispatch 上下文（uses_staging/shared_context/state/path_context/outputs_override）；**r2.2 改判**：`test_type`/`round_dir` 不是「纯无用参数」，而是 **legacy/IDE 路由的实际载荷**（`round_dir` 进 `_with_write_audit` 与 `shenbi-dispatch` 位置参数 :4389/:4436；`test_type` 进 CLI 参数与日志）——src 恒用默认值≠无用；删除须给 legacy 路由新来源，否则 rd 恒=project_dir 是行为变更；**改为「记为 legacy 专用参数并文档化」，并补第三个零 src 参数 `skip_reads`**（仅测试用）；docstring 记述不存在的 `timeout` 参数一并修（:4327）；
- `_DispatchOutcome` 对象收 usage 累积/archive 帧/trace 发射（`record(success, finish_reason, failure_class)` 单方法）：4 段 trace 块 → 1、账目算术双拷（`_account_failed_attempt` **:3179-3220** vs 成功面 :3758-3773）→ 1；
- **characterization 红测**：成功/失败/超时/再升帽四出口的 trace 事件**经归一化后**逐字节一致——**r2.2：必须定义归一化白名单**（`ts`(now)、`seq`(文件续号)、`signature`(ts+seq+payload 的 sha256)；archive 记录另带 `ts`）——照字面「逐字节」必假红；签名改为「重算校验」而非比较原值。

### T5 · 文档诚实小批
- AGENTS.md「phase_runner.py — T2/T3 phase state machine」→「T2 phase state machine（T3 走 pipeline/state.py——模块自述 :1-2）」；
- ADR 0004 附注实际插件集（pytest-randomly；asyncio/ordering 未装）；
- **r2.2 计数更正**：`src/` 内行号注释**实为 6 个 `.py:N` 引用 / 5 行**——3 行非 pyright（g6.py:76 一行**两引**、decisions_validator.py:184、chapter_loop.py:2704）+ 2 行 pyright（chapter_loop.py:3528/:3559）；r2 的「≥12」把 `docs/superpowers/specs/` 的 11,375 处历史记录算进来了；且现有引用**全部已烂**（`shared.py:113` 实为 `out.append`、fail 在 **:580**；`chapter_loop.py:2704` 引 `chapter_loop.py:1389` 实为 decisions 晋升；`g6.py:76` 引 `triggers.py:110`/`dispatch_helper.py:1701` 均不对应；`cli.py:195` 是 frozenset 字面量）；判据改「`src/` 内 =0（含 pyright 行，改函数名），另设显式豁免清单文件（文件+行+理由）」——「剩余 ≤2」可被故意留两条最烂的凑数；
- `now_iso` 双拷（phase_runner:83 vs machine.py:26）→ 收敛一个共享 helper（落 pipeline/_shared 或 safe_write 旁）；
- `_record_gate_manifest` best-effort 三拷（phase_runner:87-112 / dispatch_helper:**4582** / codex:221-239——**codex 处是内联调用非函数拷贝**，三处均「ShenbiError 重抛、其余吞」）：**本批只登记**（不做盲目合并）。

### T6 · 杂项微型接口修复（**依赖 #85**——r2.2 更正：原标「独立」不成立）
- `write_truth_file` 的 `mode` 4 魔法串 → Literal（零成本，调用方类型自检）；
- ReviewChecklist 序列化双 dict（:130-145,:167-183 手拷）→ `dataclasses.asdict`；
- 角色显示名：`review_checklist.py:409` 全文正则（`name:` 任意行可被散文劫持）**与 `:416 voice_fingerprint` 同款**→ 走 truth_index frontmatter 解析（**#85 后的 `split_frontmatter`**；`_index_characters` 已有 `fm.get("name", card.stem)` 语义，只复用不新解析）——**#85 先落，本项排后**；
- `closure.py:148-165`（用**函数名** `_closure_step_context` 定位，r2.2：#91 T1 会改同文件 :125 的 `_gate_passed`，行号会漂）魔法步号（`step_num in (4,5)`/`==2`/`in (6,7,10)`）→ `ClosureStep.context_kind` 字段（知识上表，插步不再静默错位）。

## 2. 验收

1. `grep -rn codex_api src/ tests/` 零（**r2.2：只查 src/ 会以「零」通过而 CI 红**）；dispatcher.md 含三路由决策树；
2. cli.py <900 行（**前提：T2 含 cmd_review 决策体下沉**；否则改 ~1,050）且测试零 import cli 私有（checkpoint_flow 正名符号替代）；
3. `shenbi-score --help` 显两子命令；**codex.py 调用方已迁移或 shim 覆盖（红测：位置参数调用仍可用）**；codex.py 无 `_normalize_scores` 定义（import 单源）；
4. T4 四出口 trace **归一化后**逐字节一致（白名单 ts/seq/signature）＋ `dispatch_skill` 签名文档化 legacy 专用参数（test_type/round_dir/skip_reads）；
5. T5 三文档/常量判据绿；**`src/` 行号注释 =0（豁免清单另计）**；
6. `just check` exit 0。

## 3. 顺序

T1/T2/T3/T5 相互独立可并行小 PR；**T6 依赖 #85 先落**（split_frontmatter 单源）；T4 必须 #87 落地后（同函数域），且应在 #95 之后（反馈/预算写点）。
