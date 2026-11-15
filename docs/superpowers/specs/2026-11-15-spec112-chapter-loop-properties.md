# Spec #112 · chapter_loop 状态机性质测试（chapter-loop-properties）：resume/重试/升级不变量清单文档化、hypothesis 状态机、已知反例回归收编

**日期**：2026-11-15｜ **系列**：多专家审计批（expert-audit）｜ **状态**：Design（r1，2026-11-15）｜ **优先级**：🟠 P1
**动机证据**（2026-11-15 状态机审计，标注〔亲验〕/〔代理枚举待性质测试钉死〕）：`chapter_loop.py:3996-4004`〔亲验〕（core wave savepoint `_wave_savepoint(state, project_dir, chapter)(core_wave)` **漏传 wave_chapters**——genre 波 `:4040-4042` 传了；core 波 savepoint 只落 leader 章 ChapterState，与 `:539-540` docstring 的 cluster 契约相悖）；`error_handler.py:126`〔亲验，grep 全仓〕（`cs.status = SETTLING_FAILED` 唯一写者、**全仓无复位者**——「已修复待重跑」与「仍坏」不可区分，操作面盲）；`chapter_loop.py:4728-4749`〔亲验〕（`--auto` 模式 G4 硬失败 `count<=1` 重试、`>1` `reset_retry` 后**直落成功路径放行**；per_chapter_review 模式同点走 `_handle_failure`——同因异果，语义未文档化未裁定）；`cli.py:563/:584`〔亲验〕（trigger 后 `cl.step_index = 1` 防再触发——若 step 0 为 pipeline-volume-align，新章跳过对齐面）；`chapter_loop.py:3107`〔代理〕（revision_count wave/serial 双路径调用面——resume 重放 wave 可再 +1，cap 检查 `:3119` 可被虚假触发）；`chapter_loop.py:587-615`〔代理〕（`_clamp_resume_cursor` 只回卷「零 steps_done」游标章——wave 已批量标 done 的 runaway 章拒绝回卷）；`machine.py:131-139`〔代理〕（escalation resolve `cp.chapter is None` → **全清所有章 retry budget**——跨章 durable 史一键抹平）；`chapter_loop.py:1951-1970`〔代理〕（scene-split 熔断预算记 drafting 键 vs checkpoint 挂当前章——前缀清理错键风险）；`state_heal.py:36-64`〔代理〕（revision_count heal 0/1 floor 与重放双计交互）；`cli.py:507+`〔代理〕（`_cleanup_residual_staging` 与 `_mark_staged_for_checkpoint` 的时序窗——CHAPTER_MEMO auto-commit 失败分支后崩溃可清掉待审 staged 计划）；历史反例在册（spec #91 归档：re-settle 死锁 P0/两锁窗口；probe20 恢复路径死亡；fixcheck ch2 整维消失——`:4083-4085` 注释自认）。

**触及的不变量维度**：无（状态机基建——约束的是管线自身状态一致性）

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
