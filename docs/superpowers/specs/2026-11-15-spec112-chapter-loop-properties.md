# Spec #112 · chapter_loop 状态机性质测试（chapter-loop-properties）：resume/重试/升级不变量清单文档化、hypothesis 状态机、已知反例回归收编

**日期**：2026-11-15｜ **系列**：多专家审计批（expert-audit）｜ **状态**：Design（r2，2026-11-24 Revised）｜ **优先级**：🟠 P1
**动机证据**（2026-11-15 状态机审计，标注〔亲验〕/〔代理枚举待性质测试钉死〕）：`chapter_loop.py:3996-4004`〔亲验〕（core wave savepoint `_wave_savepoint(state, project_dir, chapter)(core_wave)` **漏传 wave_chapters**——genre 波 `:4040-4042` 传了；core 波 savepoint 只落 leader 章 ChapterState，与 `:539-540` docstring 的 cluster 契约相悖）；`error_handler.py:126`〔亲验，grep 全仓〕（`cs.status = SETTLING_FAILED` 唯一写者、**全仓无复位者**——「已修复待重跑」与「仍坏」不可区分，操作面盲）；`chapter_loop.py:4728-4749`〔亲验〕（`--auto` 模式 G4 硬失败 `count<=1` 重试、`>1` `reset_retry` 后**直落成功路径放行**；per_chapter_review 模式同点走 `_handle_failure`——同因异果，语义未文档化未裁定）；`cli.py:563/:584`〔亲验〕（trigger 后 `cl.step_index = 1` 防再触发——若 step 0 为 pipeline-volume-align，新章跳过对齐面）；`chapter_loop.py:3107`〔代理〕（revision_count wave/serial 双路径调用面——resume 重放 wave 可再 +1，cap 检查 `:3119` 可被虚假触发）；`chapter_loop.py:587-615`〔代理〕（`_clamp_resume_cursor` 只回卷「零 steps_done」游标章——wave 已批量标 done 的 runaway 章拒绝回卷）；`machine.py:131-139`〔代理〕（escalation resolve `cp.chapter is None` → **全清所有章 retry budget**——跨章 durable 史一键抹平）；`chapter_loop.py:1951-1970`〔代理〕（scene-split 熔断预算记 drafting 键 vs checkpoint 挂当前章——前缀清理错键风险）；`state_heal.py:36-64`〔代理〕（revision_count heal 0/1 floor 与重放双计交互）；`cli.py:507+`〔代理〕（`_cleanup_residual_staging` 与 `_mark_staged_for_checkpoint` 的时序窗——CHAPTER_MEMO auto-commit 失败分支后崩溃可清掉待审 staged 计划）；历史反例在册（spec #91 归档：re-settle 死锁 P0/两锁窗口；probe20 恢复路径死亡；fixcheck ch2 整维消失——`:4083-4085` 注释自认）。

**触及的不变量维度**：无（状态机基建——约束的是管线自身状态一致性）

**r2 修订（2026-11-24 · 实现审计回写；证据＝八席实现审计之状态机席，协调者逐条亲验）**：
- **主张复核**（原动机 10 条代理枚举，逐条在 HEAD 重开文件核对）：
  - **仍成立**：E-3（核心波存档点漏传 `wave_chapters`——现 `chapter_loop.py:4317`；genre 波 `:4356` 传了）；E-9（`SETTLING_FAILED` 唯一写者 `error_handler.py:126`、无复位者；`_complete_chapter` 仍会把状态改写为 COMPLETE〔`:2462/:2474`〕，影响面待性质测试钉死）；E-11（`--auto` 第二次硬失败放行——现 `:5040-5051`）；E-26（trigger 后 `step_index = 1`——`cli.py:563/:584` 行号未漂；影响很小，`CHAPTER_STEPS[0]`〔pipeline-volume-align〕在 `chapter_loop.py` 只有定义〔`:165`〕没有处理分支）；E-24（`chapter=None` 全清预算——`machine.py:131-139` 行号未漂）。
  - **不成立，从 T3 清单删除**：E-10「scene-split 熔断预算键与检查点章号不一致」——三处用的是同一个 `chapter`（`chapter_loop.py:4696/:4717/:4728`）。
  - **改定性**：E-16「备忘自动提交失败后崩溃会清掉待审计划」在人审模式下字面不成立——先 `set_checkpoint` 再打标记（`:2735-2742`），resume 清理保留已标记产物（`:3879`）；真缺陷在 `--auto` 的提交失败分支（`:2677-2682` 与 `:2726-2727`：缺文件只告警 → `clear_staging` → 步骤照常前进）。T3 改为收编此形态。
  - **未证实，悬置**：E-18（`revision_count` 的非幂等 `+= 1` 存在〔`:3368`〕，但没找到重放路径）。
- **I6 须先对账再立**：原拟不变量 I6「escalation resolve 只清其章」与 `src/shenbi/pipeline/machine.py:93-95` 文档化的既有设计（C33／spec #47 R3：升级裁决后**故意**清全部重试计数——有事故背景，「只清一部分会让预算在第一次新失败时就误报耗尽」）方向相反；且 `:124-126` 对三个 `retry_counts` 表的清理本就不看章号。I6 不是修 bug，是改一条有事故背景的规则——**执行前须用户裁定**以哪个为准；若保留 C33，I6 改写为「显式登记的设计内行为」，并以性质测试钉住「清全部之后不会立即误报耗尽」。
- **E-11 的现实范围**：vol1 运行配置为 `per_chapter_review_enabled: true`——auto 放行分支在真实项目上不走，T4 裁定件优先级最低；它与 #114 T1（同门三振分诊）改的是同一段代码的两个分支，两件须一起裁（#114 原文未知会本件）。
- **性质测试必须绑真代码**：T2 原文「复用 `state.py` 真实类」——但反例所在全是 `chapter_loop.py`／`cli.py` 的函数（`_wave_savepoint` `:547`、`_clamp_resume_cursor` `:605`、`_handle_failure` `:1985`、`_escalate_step_failure` `:2063`）。增补判据：I1–I12 每条在测试里点名它所约束的真实函数；mutation 演示从「至少 3 条」提到「每条现状成立的不变量各一次」；绑不到真实函数的不变量标「仅模型层」，不计入覆盖。
- **新增不变量 I13 · FAILED 相位可达性**：`src/shenbi/pipeline/transitions.py:76`（`transition_to_failed`，FAILED 相位的唯一写者）全仓零调用，`cli.py:518/:873` 的 FAILED 分支恒不可达（架构席发现，协调者复核）——归 T3：接线或删相位，与 #122 T3 的零引用清偿同批。
- **I14 候选（仅核代码、未实跑）· 收尾异常后的游标卡死**：步骤全部跑完后若 `_complete_chapter` 抛异常（`chapter_loop.py:2456` 的 `ProductContractError`），此时 `step_index` 已被 `_advance` 推到末尾（`:2649`、`:2745`）；退出钩子把内存态原样存盘（`src/shenbi/pipeline/crash_recovery.py:174-185`，注释自述「内存态权威于磁盘」），此后每次恢复在 `chapter_loop.py:4077` 直接返回，不再补跑收尾——游标永不前进、无检查点。plan 期先写一条能红的复现（确认 `cmd_next`／`cmd_resume` 的异常处理不会先行存盘），再决定归入 I 清单与 T3。
- **行号重锚**：`:3996-4004`→`:4317`；`:4040-4042`→`:4356`；`:4728-4749`→`:5034-5051`；`:587-615`→`:605-633`；其余 plan 首步 re-anchor。
- **依赖**：#109 已归档——原「#109 后链尾」解除；现排 #121／#101／#122 之后（三者先改 `chapter_loop.py`／`cli.py` 的重派、bundle、修订路由面）。

---

## 0. 根因

**单测盖路径、性质层缺席**：chapter_loop 的失败/恢复/升级交叠面靠历史事故逐点修补（每处注释都是一座墓碑），但「任意 kill 点后 resume 的状态一致性」「游标跳跃 ≡ bundle 快照」「done 集 ⊆ 实产物存在」这类**不变量从未被声明**，更没有被自动化断言。E 审计 27 条缺口中 8 条集中在「崩溃/恢复/升级的三方交叠」，每条都是下一次长跑的停机面候选。

**用户裁定（2026-11-15）**：`--auto` 模式 G4 二次失败放行（E-11）语义**挂账待裁定**——本件 T4 出示证据后由用户定「设计内（文档化+披露行）」或「缺陷（改 escalate）」，本件不预裁。

**备选案已评估并否决**：「全量 TLA+/模型检查形式化」——状态空间含 LLM 派发结果不可枚举，hypothesis 性质测试是可达边界内的最大覆盖；「只补单测不建性质层」——历史反例证明单测只盖已见路径，性质层才是反例发生器。

## 1. 任务分解

### T1 · 不变量清单文档化
- `docs/framework/chapter-loop-invariants.md`：10-15 条声明式不变量（首版草案）：
  I1 游标跳跃 ≡ `bundle_chapters` 快照（完成时刻与 done 集成员一致）；I2 steps_done ⊆ 盘上产物存在（或 invalid 感知——引 #109 T4/T5）；I3 SETTLING_FAILED 可复位（存在转移至可重跑态）；I4 resume 重放幂等（revision_count/audit_retry_count/budget 不双计）；I5 retry budget 键章号 ≡ checkpoint 章（前缀清理可达）；I6 escalation resolve 只清其章（chapter=None 全清须显式授权语义）；I7 staging 清理不吞 checkpointed 标记物；I8 cascade streak 只数 valid 产物（引 #109）；I9 wave savepoint 覆盖 bundle 全员；I10 emergency 注记在 read 模式锁下不丢（或文档化丢失面）；I11 trigger step_index 推进不跳过对新章的 mandatory 步；I12 clamp 与 done 集一致（runaway 章可回收）。
- 每条注「现状：成立/悬置（挂 #109/挂账）」——本件只测现状成立者，悬置者标依赖。

**判据**：文档落盘且 12 条各含现状标注；`lint_invariant_coverage` 不涉及（非 13 维面）——独立文档无 lint 义务，plan 期定是否入 lint。

### T2 · hypothesis RuleBasedStateMachine
- `tests/property/test_chapter_loop_machine.py`：状态 = {游标, step_index, per-章 ChapterState 摘要, checkpoint, budget/feedback 键集}；规则族 = {step 成功推进, dispatch 失败(classify 分类), G4 硬失败(auto/per-chapter 两模式), escalation resolve(带/无章号), crash-resume(任意点快照→重载), volume_map 外改}；对 I1-I12 现状成立者逐条断言；
- 模型层用纯状态转移动词（不真派发——LLM 派发以 mock 结果枚举 {success, g4_hard, no_files, empty}），复用 `state.py` 真实类（非影子模型——测真代码）。

**判据**：性质测试入 `just test`（fast 面）；hypothesis profile 对齐 pre-push（#97 先例）；至少 3 条不变量被规则破坏时红（mutation 抽查演示）。

### T3 · 已知反例回归收编
- 每反例一红测（转绿或xfail 哨兵——按修复态）：E-3 savepoint 漏参（修：core 波补传 wave_chapters）；E-9 SETTLING_FAILED 复位通道（修：approve/修复路径复位为可重跑态）；E-10 budget 键章号一致性；E-16 staging 清理时序；E-18 revision_count 重放双计；E-26 trigger 后 mandatory 步不跳（修或文档化）；E-24 chapter=None 全清改显式；
- 修复与收编分离：本 task 只收编**测试**，修复按反例危险度排序（E-3/E-9 P1 级先修；其余 xfai 哨兵挂账）。

**判据**：`pytest tests/property/ -k regression` 12 反例条目在册；E-3/E-9 修复版红转绿。

### T4 · auto 模式 G4 语义裁定件
- 出示 `chapter_loop.py:4728-4749` 行为差分证据（auto: 二次硬失败放行 vs per-chapter: escalation）+ 放行率估算（vol1 trace 中 auto 模式 g4 连败事件计数）→ 用户裁定 → 文档化（`--auto` 语义节）或改 escalate（改动入 T3 回归）。

**判据**：裁定记录入 spec-deviations 或 docs；两分支各有测试钉死。

## 2. 验收
1. T1-T4 判据全绿；
2. mutation 演示：故意破坏 I4（重放双计）→ 性质测试红；
3. E-3/E-9 修复后全量 `just check` 绿（无行为回归——差分：对 vol1 状态文件重放 resume 路径，前后状态一致面不含 savepoint/status 面）。

## 3. 风险
- hypothesis 状态机维护成本——规则面收敛在游标/重试/checkpoint 三族，每规则 ≤5 分支；
- xdist 假 flake 先例（束7 随机序 6 失败）——profile 钉死 + no:xdist 证据路径备忘；
- **共享文件面**：`chapter_loop.py` 与 #105/#106/#109 最热文件链——施工序 **#109 → #112**（#112 收编 #109 修复面反例；plan 首步 re-anchor）；`error_handler.py`/`cli.py` 无在飞 spec 冲突；
- 性质测试发现新反例的熔断纪律（发现即停批升级用户——#112 自身不扩面修）。
