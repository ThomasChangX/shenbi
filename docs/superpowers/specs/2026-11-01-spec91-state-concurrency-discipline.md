# Spec #91 · 状态与并发纪律（state-and-concurrency-discipline）：gate_passed 单源、锁窗口闭合、状态写回归封装

**日期**：2026-11-01（r2 修订 2026-11-02：T4 由「删死助手」改判「接线上串行裸写」——助手有锁有测试只缺调用方；T3 并发红测定为可确定性编排）｜ **系列**：架构复审批次 A ｜ **状态**：Design（r2） ｜ **优先级**：🟠 P1
**动机证据**：architecture-review-20261101 #8/#11/#15 卡；亲验——`_gate_passed` 恰 5 定义且 SKIP 语义分歧（triggers.py:505/closure.py:125 接受 PASS or SKIP；chapter_loop.py:1292/genesis.py:283/audit_layer.py:209 仅 PASS）；ledger_archive.py:157 读在 :250 锁外；`state.increment_retry/reset_retry`（state.py:287/295）唯一调用方是 tests/unit/pipeline/test_state_concurrency.py:71,82-83（**生产零调用**），而 chapter_loop 以裸字典写绕过

**触及的不变量维度**：无（运行时状态纪律；SKIP 语义 characterization 钉死，不改判定结果）

---

## 0. 根因

三处同根：**契约靠约定不靠机制**。① truth_io.py:10-14 明文「per-path 锁串行化整个读-合-写事务」，archive_ledger 却 :157 无锁读、:250 才锁盲写（归档半边 :259-260 反而做对）；dispatch_helper outline 合并同型（~:2624 读 / ~:2645 锁写）。② state.py:255-260 锁纪律只护助手：retry_feedback 裸写 ×10、retry_budget_consumed 裸写 ×3——波路径走加锁的 `charge_retry_budget`（:1320）而串行路径绕过；`increment_retry`/`reset_retry` 有锁、有并发测试，却**没有生产调用方**（r2 亲验）。③ 同一门结果判定 `_gate_passed` 五拷且 SKIP 分歧——trigger 步骤 SKIP 算过、章步骤算挂，未声明；失败→重试→升级协议两拷（chapter_loop:1767-1889 vs genesis:418-482），C33 确定性零重试修复只落 chapter_loop。

## 1. 任务分解

### T1 · `gate_passed` 单源 + SKIP 显式化
`shenbi/status.py`（GateStatus 之家）增 `gate_passed(result, *, accept_skip=False) -> bool`；5 站点换装，SKIP 容忍逐调用点显式（triggers/closure 传 `accept_skip=True` 钉死现行为；其余默认 False）。**红测先行**：5 站点 × PASS/SKIP/FAIL 三态现断言表落盘（钉死时若暴露真 bug → 记 deviation 转内容批，不在本 spec 顺手改语义）。

### T2 · 失败协议纯函数共享（**不建 Router 类**）
提取 `is_deterministic_failure(gate_result) -> bool`（C33 语义）与重试预算/升级次序判定为纯函数；chapter_loop._handle_failure 换装（行为不变）。
**genesis 侧保守化（r2）**：先落「差异表」——genesis 路径对确定性失败的现行为 vs 共享后行为；**表为空/等价才换装**；若确实缺 C33 分类（行为变更）→ 该变更影响卷二创世重跑，**需用户裁定后另行实施**（记 deviation，不在本批自治改）。

### T3 · 锁窗口闭合（确定性并发红测）
- `ledger_archive`：`live = live_path.read_text()` 与锚检/拼接移入 `with path_lock(live_path):`（~90 行重排缩进；单写者零行为变化；归档半边已对形态为蓝本）；
- `dispatch_helper` outline 合并：base 读移锁内 + 锁内重读重验锚；
- **红测设计（禁 sleep，可确定性）**：用 `threading.Barrier` + monkeypatch 在「读之后、写之前」插入同步点——线程 A 持锁并读，线程 B 在锁外窗口写入并 release barrier，A 继续写 → 断言 B 的行丢失（现状红）；修复后 A 的读发生在锁内，B 被锁阻塞，终态两行俱在（绿）。若不便注入，则 monkeypatch `safe_write` 为可观测点达成同一交错。

### T4 · 状态写回归封装（**接线，不删除**——r2 改判）
**判据**：`increment_retry`/`reset_retry` 已实现且被并发测试覆盖，缺的只是生产调用方——deletion test 的答案是「接线」不是「删除」（删掉等于扔掉既有正确机制再从裸写重建）。
- chapter_loop 的 `retry_counts` 直接变异（:1789-1790,:4560-4561 等）→ `state.chapter_loop.increment_retry/reset_retry`；
- `retry_budget_consumed` 三处裸写（:1796,:4320,:4548）→ 加锁的 `charge_retry_budget`（必要时补 setter 语义，保持预算语义不变）；
- PipelineState 增 `set_retry_feedback`/`pop_retry_feedback`（替换 10 处裸写）；
- **红测**：并发两线程交替 increment/charge，终值等于串行和（复用 test_state_concurrency 既有模式）。

### T5 · 命名诚实
`_dispatch_with_retry` 正名公共 `dispatch_with_retry`（已有 1 外部消费者 + pyright 压制）；`run_parallel_post_draft_steps` → `run_post_draft_pair`（名说 parallel 实 SEQUENTIALLY，docstring 自认）；`_dispatch_serial_reviews` 的 1 许可信号量戏法删除（正名后直接循环）。

## 2. 验收

1. `grep -rn "def _gate_passed" src/` 唯一；
2. T3 确定性并发红测绿（交错编排，无 sleep）；
3. `grep -n "retry_budget_consumed\[" src/shenbi/pipeline/chapter_loop.py` 零；retry_feedback 裸写零；`increment_retry/reset_retry` 生产调用方 ≥1（T4 接线后）；
4. genesis 差异表落盘（等价则换装；不等价挂用户裁定）；
5. `grep -rn "Semaphore" src/shenbi/pipeline/chapter_loop.py` 零；
6. `just check` exit 0。

## 3. 顺序

T3 独立可先行；T4/T5 的 chapter_loop 调用点若与 #87 T3 撞面 → #87 先行、本 spec 适配新结构（不并行施工同函数）。
