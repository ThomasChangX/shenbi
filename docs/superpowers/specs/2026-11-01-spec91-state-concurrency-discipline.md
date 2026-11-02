# Spec #91 · 状态与并发纪律（state-and-concurrency-discipline）：gate_passed 单源、锁窗口闭合、状态写回归封装

**日期**：2026-11-01（r2 修订 2026-11-02：T4 由「删死助手」改判「接线上串行裸写」——助手有锁有测试只缺调用方；T3 并发红测定为可确定性编排；**r2.2 2026-11-02 全量对抗式审计修订**——T2 复用既有 `classify_dispatch_failure`（删除新造签名）、T3 红测注入点重设计、T4 补 `increment_retry_budget`（charge 是幂等 max）、T5 信号量改可选）｜ **系列**：架构复审批次 A ｜ **状态**：Design（r2.2） ｜ **优先级**：🟠 P1
**动机证据**：architecture-review-20261101 #8/#11/#15 卡；亲验——`_gate_passed` 恰 5 定义且 SKIP 语义分歧（triggers.py:505/closure.py:125 接受 PASS or SKIP；chapter_loop.py:1292/genesis.py:283/audit_layer.py:209 仅 PASS）；ledger_archive.py:157 读在 :250 锁外；`state.increment_retry/reset_retry`（state.py:287/295）唯一调用方是 tests/unit/pipeline/test_state_concurrency.py:71,82-83（**生产零调用**），而 chapter_loop 以裸字典写绕过

**触及的不变量维度**：无（运行时状态纪律；SKIP 语义 characterization 钉死，不改判定结果）

---

## 0. 根因

三处同根：**契约靠约定不靠机制**。① truth_io.py:10-14 明文「per-path 锁串行化整个读-合-写事务」，archive_ledger 却 :157 无锁读、:250 才锁盲写（归档半边 :259-260 反而做对）；dispatch_helper outline 合并同型（:2606 读 / :2628 锁 / :2654 写，锁内 `base = base_text` 仍是锁外旧值）。② state.py:255-260 锁纪律只护助手：retry_feedback 裸写 ×10、retry_budget_consumed 裸写 ×3——波路径走加锁的 `charge_retry_budget`（:1320）而串行路径绕过；`increment_retry`/`reset_retry` 有锁、有并发测试，却**没有生产调用方**。③ 同一门结果判定 `_gate_passed` 五拷且 SKIP 分歧——trigger 步骤 SKIP 算过、章步骤算挂，未声明；失败→重试→升级协议两拷（chapter_loop:1767-1844 vs genesis:418-482），C33 确定性零重试修复只落 chapter_loop。**r2.2 已核**：`shenbi/status.py` 只 import enum/typing，是**无依赖叶子**——T1 放它不会产生 pipeline↔status 或 gates↔status 环（原风险条改为已核）。

## 1. 任务分解

### T1 · `gate_passed` 单源 + SKIP 显式化
`shenbi/status.py`（GateStatus 之家）增 `gate_passed(result, *, accept_skip=False) -> bool`；5 站点换装，SKIP 容忍逐调用点显式（triggers/closure 传 `accept_skip=True` 钉死现行为；其余默认 False）。**红测先行**：5 站点 × PASS/SKIP/FAIL 三态现断言表落盘（钉死时若暴露真 bug → 记 deviation 转内容批，不在本 spec 顺手改语义）。

### T2 · 失败协议纯函数共享（**不建 Router 类；复用既有分类器**——r2.2 改判）
**r2.2 事实更正**：C33 分类器**已经存在**——`classify_dispatch_failure(exc=None, returncode=None, *, stderr="") -> FailureClass`（dispatch_helper.py:3355-3378，docstring 列 4 个分类点），parallel_dispatch.py:150-156 已在消费；`_handle_failure` 收的是 `failure_class: FailureClass | None = None`（chapter_loop.py:1775），**11 个调用点只有 4 个传**（:439/:4142/:4454/:4471），其余 **7 个**为 None（gate/output_missing 路径，语义上应保持可重试）。r2 写的 `is_deterministic_failure(gate_result) -> bool` 是**凭空新造**（gate_result 里没有 FailureClass）。
**处置**：把 `classify_dispatch_failure` 提升到 `shenbi/status.py`（无依赖叶）或 contracts 层复用；**genesis 侧须改协议**：`genesis._handle_failure`（:418）增 `failure_class` 形参 + 非 TRANSIENT 短路（现 :443 走 count-only `handle_dispatch_failure`，只补传参不改变零重试语义）；差异表降级为 rc=2 单点行为对比。
**genesis 侧保守化（r2）**：先落「差异表」——genesis 路径对确定性失败的现行为 vs 共享后行为；**表为空/等价才换装**；若确实缺 C33 分类（行为变更）→ 影响卷二创世重跑，**需用户裁定**（记 deviation，不在本批自治改）。

### T3 · 锁窗口闭合（确定性并发红测）
- `ledger_archive`：`live = live_path.read_text()` 与锚检/拼接移入 `with path_lock(live_path):`（~90 行重排缩进；单写者零行为变化；归档半边已对形态为蓝本）；
- `dispatch_helper` outline 合并：base 读移锁内 + 锁内重读重验锚（**r2.2 当前行号：:2606 读 `base_text` / :2628 锁 / :2654 `safe_write`**，锁内 `base = base_text` 用的仍是锁外旧值）；
- **红测设计（禁 sleep，可确定性；r2.2 重设计）**：现码线程 A **读时不持锁**（ledger_archive.py:157 在 :250 `with path_lock` 之前），r2 的「A 持锁并读」与代码相反；`safe_write` 两处都在锁**内**，在其中阻塞只会让 B 卡在非可重入的 `path_lock`，**演示不出丢失**、修复后还会死锁。可行方案：注入窗口内的**纯函数**——`ledger_archive._section_fields`（:118，:197/:220 调用）/ dispatch_helper `_strip_hr_lines`（:2609）；**红绿两测形态不同**：红=线程 B 的更新丢失；绿=结构断言（包装 `Path.read_text`，断言调用时 `_PATH_LOCKS[str(path)].locked()` 为真）+ 双写者终态两行俱在。验收须写明「红绿非同一测试翻转」。

### T4 · 状态写回归封装（**接线，不删除**——r2 改判）
**判据**：`increment_retry`/`reset_retry` 已实现且被并发测试覆盖，缺的只是生产调用方——deletion test 的答案是「接线」不是「删除」（删掉等于扔掉既有正确机制再从裸写重建）。
- chapter_loop 的 `retry_counts` 直接变异（:1789-1790,:4560-4561 等）→ `state.chapter_loop.increment_retry/reset_retry`；
- `retry_budget_consumed` 三处裸写（:1796,:4320,:4548）→ **r2.2 改判：新增 `increment_retry_budget(chapter, skill)`（锁内 `+=1`）**，不要用 `charge_retry_budget`——后者是**幂等 max(current, retries)**（docstring 明写 crash-resume replay 不能双计），传「绝对 consumed」在 stale read 时会**向下丢计**；`charge_retry_budget` 保留给 wave 聚合（chapter_loop.py:1318 注释已声明该分工：主线程 wave 完成时一次 charge）；
- PipelineState 增 `set_retry_feedback`/`pop_retry_feedback`（替换裸写；**r2.2 定义**：裸写=对 `state.chapter_loop.retry_feedback` 的任何不经存取器的读写——含 10 个赋值点 :1721,4114,4139,4169,4187,4298,4401,4468,4534,4660、5 个 `.pop` :2181,2280,4177,4493,4664，以及 chapter_loop 外的 triggers.py:746、cli.py:1308/:1313）；
- **红测（r2.2 拆分）**：①`increment_retry` 并发两线程→终值等于串行和；②budget 并发 charge→终值等于 **max(charges)**（幂等，不是和）+ 锁内可见性断言；③feedback 并发 set/pop 后终态为 last-writer-wins。
- **与 #95 交汇（r2.1 注记，2026-11-02；r2.2 校正）**：#95 T4（反馈模板内容）与 T5（字数早检——**#95 r1.2 主线路=束级早检，单章重试属 Phase 2**）均流经本任务封装的 retry_feedback/预算写点——本任务封装**机制**（锁/单点写），不改 #95 的**内容**（模板/重试策略），先落/后落皆可、后落者适配（机械兼容性口径；批次排程仍见 §3 总序——#95 先行）。束模式预算双计数（束内双章各计一次失败、retry_budget_consumed 双倍消耗——vol1-ledger 裁决 #05 实证）是否并入本任务 charge 语义修正：plan 期裁定，不在本 spec 自治改。

### T5 · 命名诚实
`_dispatch_with_retry` 正名公共 `dispatch_with_retry`（已有 1 外部消费者 + pyright 压制）；`run_parallel_post_draft_steps` → `run_post_draft_pair`（名说 parallel 实 SEQUENTIALLY，docstring 自认）；`_dispatch_serial_reviews` 的 1 许可信号量戏法删除——**r2.2 注意**：semaphore 是 `_dispatch_with_retry(task, semaphore, state=None)` 的**必填位置参数**（parallel_dispatch.py:92-96，体内 `with semaphore:` :118），删 `Semaphore(1)`（chapter_loop.py:3726）会直接断调用——改为 `semaphore: Semaphore | None = None` + `nullcontext()` 分支（或 parallel_dispatch 提供 `_no_limit`）。
**改名接线清单（r2.2）**：`tests/unit/pipeline/test_spec83_stale_declarations.py:75/:81` 以函数名字面量机械穷举（pinned tuple）；5 个测试文件以字符串 monkeypatch（test_retry_taxonomy.py:351/:388、test_chapter_loop.py:536/:1351/:1367、test_parallel_steps.py、test_spec83_stale_chain.py:21/:74）；`_dispatch_with_retry` 另有 test_c15_wave_and_context_branches.py:45/:56、test_parallel_dispatch_safety.py。**已验证无影响**：pipeline 无 ProcessPool/pickle、log event 不含函数名。

## 2. 验收

1. `grep -rn "def _gate_passed" src/` 唯一；
2. T3 确定性并发红测绿（交错编排，无 sleep；**红绿两测形态不同**——红=丢失更新，绿=锁内读结构断言+双写者共存）；
3. `grep -n "retry_budget_consumed\[" src/shenbi/pipeline/chapter_loop.py` 零；**retry_feedback 裸写零（定义见 T4：含 pop 与 chapter_loop 外 triggers/cli 点）**；`increment_retry/reset_retry/increment_retry_budget` 生产调用方 ≥1（T4 接线后）；
4. genesis 差异表落盘（等价则换装；不等价挂用户裁定）；
5. `grep -rn "Semaphore" src/shenbi/pipeline/chapter_loop.py` 零（semaphore 改可选/nullcontext 后）；
6. `just check` exit 0。

## 3. 顺序

T3 独立可先行；T4/T5 的 chapter_loop 调用点若与 #87 T3 撞面 → #87 先行、本 spec 适配新结构（不并行施工同函数）；T4/T5 写点与 #95 T4/T5 同域 → #95 先行（束4 解冻路径），本 spec 在其落地面上适配（总序 #85→#95→束4 验收→#86→#87→本 spec）；**#95 落地后须重新枚举**写点/行号清单（不得沿用本 spec 的 2026-11-02 快照）。
