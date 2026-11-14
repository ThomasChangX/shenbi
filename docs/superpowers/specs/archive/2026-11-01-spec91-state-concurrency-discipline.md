# Spec #91 · 状态与并发纪律（state-and-concurrency-discipline）：gate_passed 单源、锁窗口闭合、状态写回归封装

**日期**：2026-11-01（r2 修订 2026-11-02：T4 由「删死助手」改判「接线上串行裸写」——助手有锁有测试只缺调用方；T3 并发红测定为可确定性编排；**r2.2 2026-11-02 全量对抗式审计修订**——T2 复用既有 `classify_dispatch_failure`（删除新造签名）、T3 红测注入点重设计、T4 补 `increment_retry_budget`（charge 是幂等 max）、T5 信号量改可选；**r2.3 2026-11-15 价值门驳斥修订（REWRITE 轮）**——#87 已偿还 T5 两正名子项（dispatch_with_retry/dispatch_serial_reviews 已公共名，本 spec 划除）；T1 判定点 5→8（+phase_runner/cli 三漏网点）+新增比较侧 lint 守卫（④a/c 博弈路径仍通的缺口封堵）；T2 安放改判 contracts 层主选（status.py 须保纯叶给 T1）；全量行号重锚（#95/#86/#87/#88/#89 连续大改后）+T4 pop 侧缩减（_clear_retry_feedback 已收编 4/5）；genesis 差异表预判非空；**r2.3b 2026-11-15 阶段 2 微修**——判定面续扩（phase_runner:378 负比较+chapter_loop:1597 复合判定归域裁定）+Semaphore(4) 真限流知悉+域外姊妹写点挂账；**r2.3c 2026-11-15 设计审查轮 1 吸收**——判定面终值 11 点（+chapter_loop:4063）/genesis 改造三件整体挂裁定不落码/T4 红测重分类（tdd+characterization）/reset 侧接线清单/lint 已知残余登记）｜ **系列**：架构复审批次 A ｜ **状态**：Done (PR #343) ｜ **优先级**：🟠 P1
**动机证据**：architecture-review-20261101 #8/#11/#15 卡；亲验（**r2.3 重锚 2026-11-15，main=805c3c6f**）——`_gate_passed` 恰 5 定义且 SKIP 语义分歧（triggers.py:505/closure.py:125 接受 PASS or SKIP；chapter_loop.py:1446/genesis.py:284/audit_layer.py:209 仅 PASS）；**另有 3 个 spec 清单外漏网判定点（r2.3 时点快照；r2.3c 终值判定面=11 点，见 T1）**（phase_runner.py:146 裸 `"PASS"` 字符串比较、pipeline/cli.py:223/:255 `== GateStatus.PASS` 直比）；ledger_archive.py:158 读在 :251 锁外；`state.increment_retry/reset_retry`（state.py:292/300）唯一调用方是 tests/unit/pipeline/test_state_concurrency.py:71,82-83（**生产零调用**，r2.3 复跑确认——machine.py:142/cli.py 的 `_reset_retry_budget` 为子串撞名的不同函数），而 chapter_loop 以裸字典写绕过

**触及的不变量维度**：无（运行时状态纪律；SKIP 语义 characterization 钉死，不改判定结果）

---

## 0. 根因

三处同根：**契约靠约定不靠机制**。① truth_io.py:10-14 明文「per-path 锁串行化整个读-合-写事务」，archive_ledger 却 :158 无锁读、:251 才锁盲写 :252（归档半边 :260-261 锁内读+写反而做对）；dispatch_helper outline 合并同型（**r2.3 行号**：:2596 读 / :2618 锁 / :2644 写，锁内 :2619 `base = base_text` 仍是锁外旧值）。② state.py 锁纪律只护助手（:292 increment_retry/:300 reset_retry/:306 charge_retry_budget 全带锁）：retry_feedback 裸赋值 ×12（chapter_loop 10 + cli 域外 2）、retry_budget_consumed 裸写 ×3——波路径走加锁的 `charge_retry_budget`（唯一生产调用 chapter_loop:1474 wave 聚合）而串行路径绕过；`increment_retry`/`reset_retry` 有锁、有并发测试，却**没有生产调用方**。③ 同一门结果判定 `_gate_passed` 五拷且 SKIP 分歧——trigger 步骤 SKIP 算过、章步骤算挂，未声明；**且清单外仍有 3 个漏网直比点**（phase_runner.py:146 裸 `"PASS"`、pipeline/cli.py:223/:255 `== GateStatus.PASS`）——判定面实为 8 点（r2.3 快照；r2.3c 终值 11，见 T1）；失败→重试→升级协议两拷（chapter_loop `_handle_failure` :1931 vs genesis `_handle_failure` :419），C33 确定性零重试修复只落 chapter_loop。**r2.2 已核**：`shenbi/status.py` 只 import enum/typing，是**无依赖叶子**——T1 放它不会产生 pipeline↔status 或 gates↔status 环。**r2.3 已核**：`classify_dispatch_failure` 为纯函数（无 log/IO，仅依赖 FailureClass）；`_PATH_LOCKS` 为 per-path `threading.Lock` **非 RLock 不可重入**（truth_io.py:74）。

## 1. 任务分解

### T1 · `gate_passed` 单源 + SKIP 显式化 + 比较侧守卫（r2.3 扩容；r2.3c 计数拉齐 11 点）
`shenbi/status.py`（GateStatus 之家）增 `gate_passed(result, *, accept_skip=False) -> bool`；**11 个判定点换装**（r2.3c：5 定义——triggers.py:505/chapter_loop.py:1446/closure.py:125/audit_layer.py:209/genesis.py:284 + phase_runner.py:146/:378 裸 `"PASS"` 两点 + pipeline/cli.py:223/:255 直比 + chapter_loop.py:1597 复合判定 + **chapter_loop.py:4063 裸 `"PASS"` 负比较（r2.3c 轮 1 审查新发现——`_g3_parallel_wave` 结果判定，纯 log.warning 可观测点）**），SKIP 容忍逐调用点显式（triggers/closure 传 `accept_skip=True` 钉死现行为；其余默认 False）。**红测先行**：11 点 × PASS/SKIP/FAIL 三态现断言表落盘（钉死时若暴露真 bug → 记 deviation 转内容批，不在本 spec 顺手改语义）。
**比较侧 lint 守卫（r2.3 新增，封 ④a 博弈路径）**：现状 `lint_status_strings` 只拦 emit 侧（dict 裸值），比较侧零覆盖——phase_runner:146 裸字符串比较存续至今即为活证据。新增 AST 守卫：a) `src/shenbi/pipeline/`+`phase_runner.py` 域内新增 `def *_gate_passed` 模式定义零容忍；b) 同域内 status 与 PASS/SKIP 的比较（`GateStatus.PASS`/`GateStatus.SKIP`/裸 `"PASS"`/`"SKIP"` 字面量）仅允许出现在 `gate_passed` 单源本体内。载体 plan 期裁定（扩 lint_status_strings 或对标 #88 finding() lint 新建）；**误报处置**：换装完成后首跑须零红（全绿基线），豁免面若有须逐一登记。
**r2.3b 归域裁定（阶段 2 同类锚点裁定）**：①phase_runner.py:378 裸 `"PASS"` **负比较**（`!= "PASS"`）与 :146 同型——并入 T1 换装+lint 面（phase_runner 域判定点实为 2 处，判定面 8→11[r2.3c 终值]）；②dispatcher/executor.py:205/:250 裸 `"PASS"` 属 dispatcher 域——**不在本 spec lint 域**（登记知悉）；③chapter_loop.py:1597 `not in ("PASS", None)` 复合判定——换装为 `gate_passed(...) or status is None` 语义等价形态或 lint 豁免登记，plan 期定；④gates 域内直比（scoring/g3/g5/g6/g7/gate_manifest 各点）系门内自产自销（passed()/fail() 构造后判定）——**不在本 spec lint 域**。
**lint 已知残余（r2.3c 登记免扩面）**：反演式（`== "FAIL"`/`!= GateStatus.FAIL` 间接放行 SKIP/WARN）**不纳入**本 lint 罩面——当前 lint 域内零命中（轮 1 已 grep 验证），纳入则误报面不可控；变量间接比较（`expected="PASS"` 再比）单文件 AST 天然罩不住——均登记为已知残余，防 plan 期随意扩面。

### T2 · 失败协议纯函数共享（**不建 Router 类；复用既有分类器**——r2.2 改判；**安放改判 contracts 层——r2.3**）
**r2.2 事实更正**：C33 分类器**已经存在**——`classify_dispatch_failure(exc=None, returncode=None, *, stderr="") -> FailureClass`（**r2.3 行号** dispatch_helper.py:3411，纯函数无 log/IO），parallel_dispatch.py:151-154 已在消费；`_handle_failure` 收的是 `failure_class: FailureClass | None = None`（chapter_loop.py:1931），**11 个调用点只有 4 个传**（r2.3 行号 :455/:4227/:4477/:4632），其余 **7 个**为 None（:4281/:4299/:4527/:4592/:4722/:4750/:4782——gate/output_missing 路径，语义上应保持可重试）。r2 写的 `is_deterministic_failure(gate_result) -> bool` 是**凭空新造**（gate_result 里没有 FailureClass）。
**处置（r2.3 安放改判）**：把 `classify_dispatch_failure` 提升到 **contracts 层**（FailureClass 之家 enums.py 旁的纯函数模块，plan 期定名；同包 import 零环风险）——**主选**；`status.py` 安放弃选（会引入 contracts.enums import 破坏纯叶性质，而纯叶留给 T1 的 gate_passed）；原地不动（dispatch_helper genesis:28 已 import，零移动成本）为**备选**（若 contracts 安放与 loader/registry 面冲突）。dispatch_helper 换 re-export 保住既有消费面（消费点 ：3773/:3794/:4345 等）。
**genesis 侧改造范围钉死（r2.3c 裁定——解轮 1 I1 矛盾）**：**本批 T2 交付 = classify 迁移 + re-export + genesis 差异表落盘，三件**；genesis 侧协议改造三件（`_handle_failure` 增 `failure_class` 形参 + 非 TRANSIENT 短路分支 + 生产调用方接线传 classify 结果）**整体挂用户裁定**——裁定通过后作 follow-up 小批，本批不落码（差异表预判非空：rc=2 现 genesis 烧满 3 次重试 vs chapter_loop 零重试，形参先落而无人传 = 零接线死参数，正是价值门自设封堵对象）。差异表内容：genesis 路径对确定性失败的现行为 vs 接线后行为（rc=2 单点对比）。

### T3 · 锁窗口闭合（确定性并发红测）
- `ledger_archive`：`live = live_path.read_text()`（**r2.3 行号 :158**）与锚检/拼接移入 `with path_lock(live_path):`（:251；~90 行重排缩进；单写者零行为变化；归档半边 :260-261 锁内读+写形态为蓝本）；
- `dispatch_helper` outline 合并：base 读（**r2.3 行号 :2596**）移锁内（:2618）+ 锁内重读重验锚（:2610 check_new_volume_anchor 锚检随之入锁；锁内 :2619 `base = base_text` 现用锁外旧值）；safe_write 在 :2644；
- **红测设计（禁 sleep，可确定性；r2.2 重设计）**：现码线程 A **读时不持锁**（:158 在 :251 `with path_lock` 之前）；`safe_write` 两处都在锁**内**，在其中阻塞只会让 B 卡在非可重入的 `path_lock`，**演示不出丢失**、修复后还会死锁。可行方案：注入窗口内的**纯函数**——`ledger_archive._section_fields`（**r2.3 行号 :119**，:198/:221 调用）/ dispatch_helper `_strip_hr_lines`（:2219，:2599 消费）；**红绿两测形态不同**：红=线程 B 的更新丢失；绿=结构断言（包装 `Path.read_text`，断言调用时 `_PATH_LOCKS[str(path)][0].locked()` 为真——**r2.3c 修正**：`_PATH_LOCKS` 值为 `(threading.Lock, refcount)` 元组，断言须取 `[0]`）+ 双写者终态两行俱在。验收须写明「红绿非同一测试翻转」；
- **path_lock 不可重入约束落 docstring（r2.3 新增）**：`_PATH_LOCKS` 为 per-path `threading.Lock` 非 RLock（truth_io.py:74）——T3 顺手在 path_lock docstring 补「锁内禁调 write_truth_file 同路径（不可重入会自锁）」警告，防后续新代码在锁内嵌套。

### T4 · 状态写回归封装（**接线，不删除**——r2 改判）
**判据**：`increment_retry`/`reset_retry` 已实现且被并发测试覆盖，缺的只是生产调用方——deletion test 的答案是「接线」不是「删除」（删掉等于扔掉既有正确机制再从裸写重建）。
- chapter_loop 的 `retry_counts` 直接变异（**r2.3 行号 :1954 `_handle_failure` 内 / :4726**）→ `state.chapter_loop.increment_retry/reset_retry`；**r2.3c 补 reset 侧接线清单（轮 1 I3）**：`_reset_retries`（:2056-2058 `retry_counts.pop`，调用方 7 处 :3890/:3899/:3907/:4162/:4291/:4430/:4786）与 :4737 裸 pop 是 `reset_retry` 的天然接线点——一并换装；
- `retry_budget_consumed` 三处裸写（**r2.3 行号 :1959-1960 `_handle_failure` 内 / :4412-4413 / :4709-4713 区域**）→ **r2.2 改判：新增 `increment_retry_budget(chapter, skill)`（锁内 `+=1`）**，不要用 `charge_retry_budget`——后者是**幂等 max(current, retries)**（docstring 明写 crash-resume replay 不能双计），传「绝对 consumed」在 stale read 时会**向下丢计**；`charge_retry_budget` 保留给 wave 聚合（`_charge_wave_retries` chapter_loop:1458 注释已声明该分工：主线程 wave 完成时一次 charge，唯一生产调用 :1474）；
- PipelineState 增 `set_retry_feedback`/`pop_retry_feedback`（替换裸写；**r2.2 定义**：裸写=对 `state.chapter_loop.retry_feedback` 的任何不经存取器的读写；**r2.3 清单刷新**：赋值 12 点=chapter_loop :1879,:4191,:4220,:4252,:4272,:4387,:4524,:4589,:4629,:4697 + 域外 cli.py:1324/:1345；**裸 pop 已收编 4/5**（`_clear_retry_feedback` :1242 存在，消费点 :2317/:4262/:4528/:4654）——残余裸 pop 仅 :2416（章闭清扫）+ 封装内部 :1244 + 域外 triggers.py:746；读点 :594/:1316/:2030-2031 一并换装；`state.genesis.retry_feedback` 为 genesis 域**不在本任务范围**（spec T4 定义域=chapter_loop）；
- **既有内容封装不动（r2.3 判定）**：`accumulate_retry_feedback`（:1201）只封装内容计算（`return merged` 由调用方裸赋值）且内部 `_failure_history_map` 无锁——**不构成锁存取器，不可升格替代** set/pop_retry_feedback（正交组合：新薄锁内存取器 + accumulate 保留内容计算）；`_clear_retry_feedback` 内部 pop 换走 `pop_retry_feedback` 即锁纪律收编；
- **红测重分类（r2.3c——解轮 1 I2：CPython dict STORE_SUBSCR 原子，纯赋值无可见性丢失；生产侧无双写者——`_charge_wave_retries` docstring 明证 workers-never-touch-state，11 个 `_handle_failure` 调用点全在主线程）**：①increment_retry 接线红测 = 新 API 接线点先删后接的 trivially-red（tdd_red_green）+ 「经 `_handle_failure` 裸路径双线程并发编排」的预防性演示（演示锁纪律单点化，非现存 bug 复现——标注预防性）；②budget 并发 charge→max(charges)（幂等非和）= **characterization**（charge 今日已带锁，钉死幂等语义）；③feedback 并发 set/pop 终态 last-writer-wins = **characterization**（裸赋值本就原子——存取器的价值在 RMW 单点化与读改写序，非可见性）；三组测试形态 plan 期按此分类落，不声称「修复前必红」。
- **与 #95 交汇（r2.1 注记；r2.2 校正；#95 已完结——约束自动满足）**：#95 T4（反馈模板内容）与 T5 均流经本任务封装的 retry_feedback/预算写点——本任务封装**机制**（锁/单点写），不改 #95 的**内容**（模板/重试策略）。束模式预算双计数（束内双章各计一次失败、retry_budget_consumed 双倍消耗——vol1-ledger 裁决 #05 实证）是否并入本任务 charge 语义修正：plan 期裁定，不在本 spec 自治改。

### T5 · 命名诚实（**r2.3 范围缩减——两正名子项已由 #87 偿还**）
**已偿还划除（r2.3）**：`_dispatch_with_retry`→`dispatch_with_retry`、`_dispatch_serial_reviews`→`dispatch_serial_reviews` 两正名已随 #87（f5aac4f6）落地，src+tests 旧名零残留——本 spec 不再做。
- `run_parallel_post_draft_steps` → `run_post_draft_pair`（名说 parallel 实 SEQUENTIALLY，docstring 自认；消费面 r2.3 刷新：chapter_loop:4179 内部 1 处 + tests/pipeline/test_parallel_steps.py）；
- semaphore 可选化：`dispatch_with_retry(task, semaphore, state=None)` 的 semaphore 仍是**必填位置参数**（parallel_dispatch.py:94，体内 :118 `with semaphore:` 无 None 分支），`dispatch_serial_reviews` 的 `Semaphore(1)` 戏法（chapter_loop.py:3780）仍在——改为 `semaphore: Semaphore | None = None` + `nullcontext()` 分支后删除戏法（stdlib 一行，优于自造 no-op 信号量对象）；**r2.3b 知悉**：parallel_dispatch.py:269 `Semaphore(MAX_CONCURRENT_REVIEWS)`（=4 并行评审限流器本体）系真限流非戏法，**保留不动**——验收 5 域限 chapter_loop.py 正确；
- **接线清单（r2.3 刷新）**：r2.2 清单大半失效（test_retry_taxonomy 等已用新名）；实施时以 `grep -rn "run_parallel_post_draft_steps\|Semaphore" src/ tests/` 现场枚举为准。**已验证无影响**：pipeline 无 ProcessPool/pickle（r2.3 复跑 N7 零命中）、log event 不含函数名。

## 2. 验收

1. `grep -rn "def _gate_passed" src/` **零残留（r2.3c 措辞修正：单源是 `def gate_passed` 无下划线，旧名应全数删除而非保留一个 wrapper）**；**11 判定点全部换装或显式豁免（r2.3c：5 定义 + phase_runner.py:146/:378 + pipeline/cli.py:223/:255 + chapter_loop.py:1597/:4063）**；**比较侧 lint 守卫落盘且首跑零红（r2.3 新增）**；
2. T3 确定性并发红测绿（交错编排，无 sleep；**红绿两测形态不同**——红=丢失更新，绿=锁内读结构断言+双写者共存）；
3. `grep -n "retry_budget_consumed\[" src/shenbi/pipeline/chapter_loop.py` 零；**retry_feedback 裸写零（定义见 T4：赋值含域外 triggers/cli 点；pop 含 :2416/:1244 与 triggers:746；读点一并经存取器）**；**`grep -n "retry_counts\[\|retry_counts\.pop" src/shenbi/pipeline/chapter_loop.py` 零（r2.3c 补 reset 侧——含 `_reset_retries` 与 :4737 换装）**；`increment_retry/reset_retry/increment_retry_budget` 生产调用方 ≥1（T4 接线后）；
4. genesis 差异表落盘（**r2.3 预判不等价——rc=2 现 genesis 烧满 3 次重试 vs chapter_loop 零重试**；**r2.3c 钉死：差异表本身即本批 T2 的 genesis 侧交付，换装三件整体挂用户裁定，本批不落码**）；
5. `grep -rn "Semaphore" src/shenbi/pipeline/chapter_loop.py` 零（semaphore 改可选/nullcontext 后）；
6. `just check` exit 0。

## 3. 顺序

T3 独立可先行；T4/T5 的 chapter_loop 调用点若与 #87 T3 撞面 → #87 先行、本 spec 适配新结构（不并行施工同函数）——**#87 已完结（2026-11-13，PR #331/#332），约束满足，r2.3 行号已按拆分后新树重锚**；T4/T5 写点与 #95 T4/T5 同域 → #95 先行——**#95 已完结（PR #287-#295），约束满足，写点清单已按 #95 落地面重枚举（r2.3）**。**r2.3c 同文件并发声明（轮 1 M4）**：T4（:1954/:4726/:2056-2058 等 retry 写点）与 T5（:3636/:3762-3790 改名/信号量）同动 chapter_loop 但区域不相交，无实冲突；T2（:3411 迁移）与 T3（:2596-2644 锁窗）同动 dispatch_helper 亦然——plan 排序按 T1→T2→T3→T4→T5 或按依赖重排皆可，仅须避免同函数同批并行编辑。实施时 plan 首步仍须按符号 re-anchor（INDEX 行号锚纪律）。

**r2.3 附注**：dispatcher/executor.py:208/:253 存在 log event 名 `gate_passed`（字符串），与 T1 新公共函数无实冲突——知悉即可，不改。

**r2.3b 域外姊妹写点登记（阶段 2 发现，明确不并入本 spec）**：genesis 域 retry_feedback 裸写 6 点（genesis.py:632/:658、cli.py:1085/:1093/:1097/:1294）+pop 1 点（genesis.py:648）；genesis.retry_counts 裸写 2 点（genesis.py:444/:677）；closure_retry_counts 裸写 1 点（closure.py:217）——与 T4 同根因但属 genesis/closure 域，本 spec T4 定义域=chapter_loop 域（单 spec 原子性）；**记挂账**：若 T4 接线后需同域治理，另立小 spec 或并入后续批次。

## 4. genesis 差异表（r2.3c 落盘——用户裁定输入；验收 4）

| 场景 | genesis 现行为（count-only） | 接线后（failure_class 短路） | 差异 |
|---|---|---|---|
| dispatch rc=2（DETERMINISTIC_CONTENT/GATE） | `genesis._handle_failure` :445 count-only——烧满 `max_revision_retries`（默认 3 次尝试）才 escalation | 首败即 escalation（非 TRANSIENT 短路） | **有**：重试次数 3→0 |
| dispatch rc=1/-1/异常（TRANSIENT） | 同上 count-only 重试 | 不短路，count-only 重试（行为同） | 无 |
| G4/结构失败路径 | 不经 `_handle_failure` dispatch 分支 | 同左 | 无 |

**裁定请求**：rc=2 类确定性失败在 genesis（创世重跑场景）是否切换为零重试直通 escalation。裁定通过 → follow-up 小批落「形参+短路+接线」三件；裁定驳回 → 保持 count-only（差异表归档备查）。
