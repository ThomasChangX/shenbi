# Z3 区独立复核报告 r2 — src/shenbi/pipeline/（2026-08-15 轮）

复核人：Z3 fresh-context 独立复核 agent 轮 2。与初审、复核轮 1 无关的全量重读（34/34 文件，共 ~14,000 行）。
本轮角度：(a) 初审与复核轮 1 中所有 top-N/切片/`[:8]`/`[:5000]` 类截断逻辑的输出完整性（截断后结论是否仍成立、截断标记是否存活）；(b) 里程碑计数三方对账——状态文件内的计数（retry_counts/steps_done/checkpoint_history/skills_done/audit_reports 长度）vs 磁盘产物计数 vs 代码声称，任二不一致即 finding。

编号段：F360-F399（初审 F301-F338 + 正文 F339；复核轮 1 F340-F359）。
验证声明：所有标注"已验证"的条目均于 2026-08-15 实际运行 `uv run python`（临时目录构造真实文件 / 运行时调用真实函数）或 `grep`，关键输出原文粘贴于各条目。只读禁令遵守：未创建/修改/删除任何仓库文件（本报告除外），未执行 pytest，未调用 shenbi-dispatch/pipeline。

**本轮最重要的两个结论：**
1. **新发现 F360（P0）**：`append_dedup` 契约更新模式在生产派发写路径零实现，11 个技能的 truth 累积文件 updates 全部退化为整文件覆写，叠加"技能指示追加 + 契约 reads 不含目标文件"使正确行为在设计上不可能。
2. **误报 MR1**：复核轮 1 的头号新发现 F340（修订步门控漏扫 group-* 审计，P1/P0 边界）核心前提错误——运行时验证证明 4 个 group 审计的契约实际写入的正是 `_any_audit_has_findings` 扫描的 13 个旧维度文件名；r1 把 `ReviewTask.output_path` 的记录名误当作实际写入文件名，其验证用例构造的 `chapter-5-group-factual.md` 是生产中不存在的文件。

---

## 一、漏报（新 findings，F360-F370）

### F360 | append_dedup 契约更新模式全链路零实现：truth 累积文件每章被整文件覆写（或被无法看到现状的 LLM 幻觉重建） | error | P0

- 证据：
  - `src/shenbi/pipeline/dispatch_helper.py:1067-1081` — `_write_parsed_outputs` docstring 自认："For all declared modes — including `append_dedup` — it writes the whole file via `safe_write`. Truth-file append/upsert (`mode: append_dedup`) is NOT routed here"；1178-1181 注释再次确认不分支
  - docstring 声称的兜底——"the upsert itself is the CALLER's responsibility: the state-settling skill calls `write_truth_file` directly"——**不存在**：`write_truth_file` 生产调用点全仓仅 1 处（`chapter_loop.py:3051`，串行 resonance 分支，默认并行流不可达，见初审 F321/F304）
  - `skills/shenbi-state-settling/SKILL.md:110` — 技能铁律："**增量更新** — 追加变更，不重写整个文件"；:158 "chapter_summaries.md (追加)"；契约 reads 仅 `chapters/chapter-N.md`（LLM 看不到被更新文件的当前内容，想重生成完整文件也不可能）
  - `skills/shenbi-state-settling/SKILL.md` 契约 updates：6 个 truth 累积文件（current_state/particle_ledger/emotional_arcs/subplot_board/pending_hooks/chapter_summaries）全部 `mode: append_dedup`
  - `dispatch_helper.py:666-675` — output_paths 从契约 `writes` **和** `updates` 收集（updates 也进整文件写路径）；`_check_content_size_guard`（943-1000）只保护 `chapters/*.md`，truth 文件无任何尺寸护栏；G4 state_settling 检查器只查参数代理词，无行数单调性检查（`src/shenbi/gates/g4/state_settling.py:1-30`）
- 根因：三方矛盾——契约声明 append_dedup（G0.16 校验契约用）、技能正文指示"追加"、派发写路径整文件覆写且技能无法读取目标文件现状。三路派发（API/IDE/legacy dispatcher CLI）均无 upsert 实现。
- 影响面（热路径，每章执行）：shenbi-state-settling（step 8，6 文件/章）、shenbi-foreshadowing-lifecycle（step 7，pending_hooks）、shenbi-review-resonance（审计波，resonance_trend + audit_drift）；周期路径：volume-consolidation、drift-guidance、score-arc/score-volume、review-arc-payoff、foreshadowing-resolve。LLM 遵从"追加"指示 → 单行/增量输出整覆累积文件（**丢失全书累积状态**）；LLM 遵从派发提示"Each file's content must be the COMPLETE file content"（dispatch_helper.py:704）→ 在看不到当前内容的情况下幻觉重建历史。任一分支都违反 truth 语义。
- 验证命令+输出（已验证）：
  ```
  grep -rn "append_dedup" src/shenbi/ → 仅 dispatch_helper.py:1072/1074/1178 三处注释（"NOT routed here"），零实现
  grep -rn "write_truth_file" src/shenbi/pipeline/ → 生产调用仅 chapter_loop.py:3051（串行死分支）
  grep -rln "append_dedup" skills/ → 11 个技能声明该模式
  grep -rn "updates\|append\|write_truth" src/shenbi/dispatcher/ → dispatcher CLI 同样无实现
  ```
- 建议方向：`_write_parsed_outputs` 对 `updates` 契约条目路由到 `truth_io.write_truth_file`（mode/key_field 都在契约里现成可用）；在此之前，为 state-settling 的 6 个文件加"输出必须含全量行"或"行数不得少于现文件"的护栏。修复时一并消解 F360 与 MR2 中 resonance_trend 的整覆问题。
- 置信度：high（代码层三方矛盾是确定性的；实际数据丢失幅度取决于 LLM 输出行为，故 P0 定级依据是"设计上不可能正确"而非"每次必丢"）

### F361 | 输入 per-file 32K 截断静默无标记、无日志；且预算截断标记本身可被 32K cap 切掉 | error | P2

- 证据：`src/shenbi/pipeline/dispatch_helper.py:313-315`（`_budgeted_truncate` 末尾 `result[name][:_INPUT_MAX_CHARS_PER_FILE]` 无标记二次截断）；:657-664（总预算内路径 `text[:_INPUT_MAX_CHARS_PER_FILE]` 完全静默）；对照 :645-651 超预算路径至少有 `input_over_budget_applying_priority_truncation` 警告 + :313 的 `[... truncated from N chars]` 标记
- 根因：per-file cap 在两条路径上都后置于标记逻辑，且预算内路径没有日志。累积型 truth 文件（chapter_summaries.md、pending_hooks.md、character_matrix.md 随章数单调增长）超 32K 字符后，LLM 看到一份貌似完整的截断前缀。
- 验证命令+输出（已验证）：
  ```
  45K 文件 + 100B 文件（总 45.1K < 128K 预算）→ 预算内路径截断: len=32000, 含截断标记=False
  _budgeted_truncate({"chapters/chapter-1.md": 45K}, 128000) → 分配额 128000>45000 不加标记, cap 后 len=32000, 含标记=False
  _budgeted_truncate 两条目例 → 两个文件 len=32000, 标记在末尾且存活=False（分配额>内容时无标记；分配额在 32K-内容之间时标记被 [:32000] 切掉）
  ```
- 建议方向：per-file cap 统一走 `_summarize_if_large` 式带标记截断；预算内路径超 cap 时补 WARN。
- 置信度：high

### F362 | 共享审计上下文注入的 pending_hooks 静默截断至 3000 字符：6 个核心审计中 5 个对该文件无契约读取，截断副本是其唯一视角 | error | P2

- 证据：`src/shenbi/pipeline/audit_context_cache.py:67-69`（`ctx.pending_hooks = read_text()[:3000]` 无截断标记，对照 :53-56/:58-61 的 `_summarize_if_large` 有标记）；`src/shenbi/pipeline/dispatch_helper.py:628-634`（注入语义 `if cached and fname not in raw_inputs` —— 契约未声明者拿到的正是截断副本）；契约核对：核心波 6 技能中仅 shenbi-review-group-craft 声明读 `truth/pending_hooks.md`（grep 已验证），group-factual/plan/resonance/sensitivity 均未声明
- 根因：pending_hooks.md 随章节单调增长（hook_planting 每章追加、不清理），超 3000 字符后 5/6 审计技能看到的钩子清单是被静默截断的前缀——伏笔状态类审计（factual/plan 的 foreshadowing 一致性核查）对截断点之后的钩子"视而不见"且不知情。与 F342（style_profile 幽灵键注入）同源不同害：F342 是重复注入，F362 是唯一视角被截断。
- 验证：静态读码 + 契约 grep（输出见上）；未运行注入级集成测试（无现成入口）。
- 建议方向：`[:3000]` 改 `_summarize_if_large`（带标记）或改按 hook 条目数截断（保结构完整）；审计技能契约显式声明 pending_hooks 读取的应全量。
- 置信度：high

### F363 | 并行审计波重试完全绕过持久重试预算：retry_counts/retry_budget_consumed 对默认审计路径恒零记录 | error | P2

- 证据：`src/shenbi/pipeline/parallel_dispatch.py:77-128`（`_dispatch_with_retry` 每任务 MAX_RETRIES=2 → 3 次尝试，无任何 state 记账）；`src/shenbi/pipeline/chapter_loop.py:2541-2656`（波分支无 `_handle_failure` 调用；2649 的 `_reset_retries` 只 pop 一个从未写入的 key）；对照 `chapter_loop.py:607-629`（串行 `_handle_failure` 的持久预算契约注释 "Durable budget (spec §3.1): NOT cleared by _reset_retries, so crash-resume can enforce max_audit_retries"）与 `dispatch_helper.py` 的 RetryExhaustedError 机制
- 根因（计数三方对账）：默认流 = 并行波。state.retry_counts/retry_budget_consumed 对审计技能**零条目**，而日志/账本（若 F301 修复）显示每任务最多 3 次真实调用——state 计数 vs 实际尝试数 vs 代码声称（spec §3.1 持久预算）三方不一致。RetryExhaustedError 对审计路径不可触发；一个持续 5xx 的后端下，波内放大 = 6 任务 × 3 尝试 = 18 次调用/章，全部不被预算系统看见。与初审 F309（失败静默放行）同枝不同叶：F309 是结果丢失，F363 是重试消耗不可见。
- 验证：静态读码（两文件控制流对照）。
- 建议方向：波结果含失败时按任务回报 `_handle_failure` 语义记账（或至少把失败任务数并入 retry_budget_consumed）。
- 置信度：high

### F364 | 审计波把 6 个审计步全部记为 steps_done（含被级联跳过/失败者）；audit_results["audit_reports"] 记录 4 个永不存在的幽灵 group-\* 路径 | error | P2

- 证据：`src/shenbi/pipeline/chapter_loop.py:2629-2631`（无条件 `for i in range(_FIRST_AUDIT_IDX, _LAST_AUDIT_IDX+1): add_step_done(...)`，先行的 `_keep_task` 过滤与 2631 无关）；:2642（`cs.audit_results["audit_reports"] = [t.output_path for t in core_tasks + genre_tasks]`，其中 4 个 group 任务的 output_path 由 2583 按 audit_suffix 生成 = `chapter-N-group-*.md`）；:2583 的记录名 vs 技能契约实际写入路径不符（运行时验证见下）
- 根因（计数三方对账）：state.steps_done 恒 6 条；state.audit_reports 记录 6 个路径中 4 个（group-factual/character/craft/plan）磁盘**永不存在**；磁盘实际是 13 个 per-dimension 文件。audit_reports 目前无任何消费者（grep：仅写入点），但它是 F305 修复（波后批量 G4）的天然校验清单——按现值接线会对 4 个幽灵路径报 G4 not_found。
- 验证命令+输出（已验证）：
  ```
  _build_skill_prompt("shenbi-review-group-factual", tmp, "…", 5, json_mode=True) → output_paths =
    ['audits/chapter-5-continuity.md', 'audits/chapter-5-world-rules.md', 'audits/chapter-5-pacing.md']
  波记录路径（audit_suffix 生成）= audits/chapter-5-group-factual.md / group-character / group-craft / group-plan / resonance / sensitivity
  （resonance/sensitivity 两者的记录名恰与契约一致，幽灵的是 4 个 group-*）
  ```
- 建议方向：2642 改为收集契约解析后的真实写入路径；2629-2631 只标记实际派发的任务对应步。
- 置信度：high

### F365 | lifecycle 派发失败 / 两步 G4 失败仍标记 steps_done：并行 post-draft 分支无重试、无升级、无预算记账 | error | P2

- 证据：`src/shenbi/pipeline/chapter_loop.py:2682-2688`（`if not lifecycle_result.success:` 仅 log.error，无 `_handle_failure`、无 return）；:2690-2701（两步 G4 失败仅 log.warning，对照串行路径 2876-2941 的 hard-fail 重试/预算/升级全链）；:2704-2707（无条件 `add_step_done` 两个技能 + `_reset_retries`）
- 根因：并行分支只处理了 settling 失败（2671-2679 有 checkpoint），lifecycle 失败与 G4 失败被静默吸收。三方对账：state.steps_done 含 shenbi-foreshadowing-lifecycle，磁盘 pending_hooks.md 可能未更新/结构非法，无任何 retry_counts 条目。
- 验证：静态读码（分支控制流完整核对）。
- 建议方向：lifecycle 失败走 `_handle_failure`；G4 失败对齐串行路径的 `_classify_g4_failures` 处置。
- 置信度：high

### F366 | `_maybe_materialize_progress` 的 %5 节拍在标准 16 步流程中永不触发——三个 5 倍数计数点全部落在不调用物化的代码路径 | error | P2

- 证据：调用点仅 2 处——`chapter_loop.py:2717`（lifecycle+settling 并行分支后）与 :3065（dispatched 步成功后）；而计数 5（pipeline-post-draft-extract）落在 2755-2769 的 `pipeline-` 分支（2769 提前 return）、计数 10 被审计波 8→14 的一次性 +6 跳过（2629-2631，波分支无物化调用）、计数 15（pipeline-pre-revision-snapshot）同样落在 `pipeline-` 分支；条件跳过路径（2800-2804）也不调用
- 根因：步骤表重构成 6 个 pipeline- 内部步 + 6 合 1 审计波后，"每 5 步物化"的计数语义与完成事件的落点脱钩。docstring 声称 "Materialize progress.json from trace events every 5 steps"（684-692）在默认流中为假——progress.json 实际只靠 cmd_resume 的 `_auto_rebuild_progress_if_stale`（794-796）在恢复时重建。
- 验证命令+输出（已验证，全步骤模拟）：
  ```
  完成事件 (steps_done, 物化调用点): 1(N) 2(Y) 3(N) 4(Y) 5(N)<--%5==0 6(N) 8(Y) 14(N,审计波+6) 15(N)<--%5==0 16(Y)
  物化实际触发次数: 0   落在非调用点路径的 5 倍数: [5, 10(波内跳过), 15]
  ```
- 建议方向：物化改为按事件（每 dispatched 步 + 波结束）或固定每章一次；或删掉 %5 逻辑明示依赖 resume 重建。
- 置信度：high（REJECT 重跑等扰动不改变结论：add_step_done 幂等使计数不回退，调用点计数集合 {2,4,8,16} 与 5 互素）

### F367 | genesis.skills_done 非幂等 append：REJECT 重做后 17 步流程出现 18 条记录 | error | M

- 证据：`src/shenbi/pipeline/genesis.py:375`（`state.genesis.skills_done.append(step.skill)` 无成员检查）；对照 `closure.py:131-135`（`_record_done` 有 `if skill not in` 检查）与 `state.py:185-198`（`add_step_done` 幂等）；REJECT 路径 `cli.py:555-557`（GENESIS_COMPLETE → `current_step -= 1` → step 17 重跑 → 再次 append）
- 验证命令+输出（已验证）：
  ```
  17 步完成后 skills_done 长度: 17 → REJECT 后 current_step: 16 → 重跑 append 后长度: 18
  对照: closure _record_done 两次调用 = ['shenbi-style-learning']（幂等）; add_step_done 两次 = ['shenbi-chapter-drafting']（幂等）
  ```
- 影响：纯状态失真（skills_done 无其他消费者，仅 to_dict 序列化）；计数对账角度记录在案。
- 建议方向：对齐 closure 写法加成员检查。
- 置信度：high

### F368 | retry_feedback 永不清理：成功路径只清 retry_counts；30 条修剪逻辑在死代码 compact_pipeline_state 内 | error | M

- 证据：写入点 `chapter_loop.py:2914`、`genesis.py:343`；成功清理点 `chapter_loop.py:3062`/`_reset_retries:674-676`（只 pop retry_counts）、`genesis.py:374`（同）——grep `retry_feedback.pop|retry_feedback.clear` 全仓 **0 处**；唯一修剪 `state.py:425-428`（dict(items[-30:])）在死函数 compact_pipeline_state 内（F316）
- 影响：(1) 每条含完整 G4 结果 JSON（`json.dumps(g4)`），随章数单调增长入 pipeline-state.json；(2) 同章步进重跑（REJECT 回退 step_index）时向 prompt 注入过期的 "prior attempt failed G4" 纠正反馈（2821-2828），即使上一轮已成功或已被人工修复。
- 验证：grep 已验证（0 处清理）。
- 建议方向：`_reset_retries` 同时 pop retry_feedback；或接线 compact。
- 置信度：high

### F369 | genre 波 era/fanfic/highpoint 审计不在 `_any_audit_has_findings` 词表：这三维度为唯一 BLOCKING 来源时修订步被跳过（F340 的残存窄核） | error | P2

- 证据：`src/shenbi/pipeline/chapter_loop.py:1807-1821`（13 维度词表）vs 运行时验证的 genre 技能契约写入路径 `audits/chapter-5-era.md` / `chapter-5-fanfic.md` / `chapter-5-highpoint.md`（`_build_skill_prompt` 输出）；词表核对（已验证）：全部审计产物维度中不在扫描词表的 = era、fanfic、highpoint（audit_drift/resonance_trend 为 truth 文件、resonance 为 always-run 评分维度，排除合理）
- 机制：genre-config 激活上述维度且其报告为唯一 BLOCKING 来源时——`collect_audit_issues`（glob 全量）判 route=REVISION → `_is_revision_skipped`=False → 但 `_should_run_step`→`_any_audit_has_findings`=False → 2800-2804 条件跳过 + 无 decisions 文件 → 章节带未解决 BLOCKING 标记 complete。与 r1 F340 描述的机制相同，但范围从"全部 group 审计"收窄到这 3 个 genre 维度。
- 验证：运行时输出见 F364 验证块（era/fanfic/highpoint 契约路径）+ 词表差集计算输出。
- 建议方向：词表改为按 audits/ glob 推导（与 collect_audit_issues 同源）或补 3 个名字。
- 置信度：high

### F370 | `_any_audit_has_findings` 的 "FAIL" 裸子串匹配过宽："FAILURE"/"FAILED"/"No FAIL" 均误触发修订 | docs | M

- 证据：`src/shenbi/pipeline/chapter_loop.py:1825`（`if "BLOCKING" in text or "FAIL" in text`）vs 同仓 `revision_router.py:73-84` 的 `_SEVERITY_BLOCKING_RE`（专门防 "No BLOCKING issues" 误报的 severity 正则）
- 影响：方向与 F369 相反——误开修订门（多耗一次修订派发）；"BLOCKING" 裸子串同样会把 "No BLOCKING issues detected" 计为发现。
- 验证：静态读码（两处匹配逻辑对照）。
- 建议方向：复用 revision_router 的 severity 正则。
- 置信度：high

---

## 二、误报（对初审与复核轮 1 条目的反驳）

### MR1 | r1 F340（修订步门控漏扫 group-\* 审计，P1/P0 边界）——核心前提错误，建议降为 P2 并改写为 F369

- r1 的核心论断："audit_layer.py:125-131 — audit_suffix("shenbi-review-group-factual") = "group-factual"：重构后的核心波 6 个审计实际写 chapter-N-group-factual/group-character/group-craft/group-plan/resonance/sensitivity.md"，进而"4 个 group 审计全部不在 `_any_audit_has_findings` 扫描范围，仅 group 审计报 BLOCKING 时修订步被跳过"。
- 反驳证据（已验证，运行时）：
  ```
  _build_skill_prompt("shenbi-review-group-factual", tmp, "…", 5, json_mode=True).output_paths =
    ['audits/chapter-5-continuity.md', 'audits/chapter-5-world-rules.md', 'audits/chapter-5-pacing.md']
  （group-character → character/dialogue/motivation/pov；group-craft → texture/reader-pull/anti-ai；group-plan → memo-compliance/foreshadowing）
  ```
  派发写路径的 output_paths 来自**技能契约** writes/updates（dispatch_helper.py:666-675），`audit_suffix` 只用于 `ReviewTask.output_path` 这个 state 记录字段（chapter_loop.py:2583）。4 个 group 审计实际写入的 13 个 per-dimension 文件**正是** `_any_audit_has_findings` 扫描的 13 个名字（chapter_loop.py:1807-1821）——门控在主流场景下工作正常。
- r1 验证方法缺陷：其"已验证"用例在临时目录手工构造了 `audits/chapter-5-group-factual.md`——一个生产中不会出现的文件名，把错误前提固化进了测试数据。
- 残存真实问题（收窄后保留为 F369/F370/F364）：era/fanfic/highpoint 三维度不在词表；"FAIL" 子串过宽；audit_reports 幽灵路径。r1 据此提出的"审计词表四份互不一致、应建单一注册表"方向仍然成立（F364 的幽灵路径正是 output_path 记录名与契约路径两套来源不一致的实证）。
- 处置：F340 从 P1（P0 边界）降为 P2；其"与 F309 构成审计门双侧失效"的定性随之弱化。

### MR2 | 初审 F304 后半（"resonance_trend.md 永不更新 → escalation_bridge 数据源枯竭"）——论据不成立

- 初审声称默认并行流中 resonance_trend.md 永不更新，escalation_bridge.parse_resonance_scores 数据源枯竭。
- 反驳证据：`skills/shenbi-review-resonance/SKILL.md` 契约 `updates: truth/resonance_trend.md (mode: append_dedup, key: chapter)` + 正文 :51（"本技能把每章的分数序列写入 truth/resonance_trend.md"）、:81（"写报告 + 追加 resonance_trend 行"）、:154-158（行格式规范）。并行波中的 resonance 派发照常走契约驱动写路径，该文件**会被写入**（escalation_bridge.py:10-37 确认其读取源就是 resonance_trend.md）。
- 但注意：该写入落在 F360 的整文件覆写缺陷上——文件"有更新"但语义可能是"被单行整覆/幻觉重建"，数据质量不可信。即 F304 后半的真相从"数据源枯竭"变为"数据源被 F360 污染"。
- F304 前半维持：`cs.resonance_score` 仅在串行分支 3034 赋值，默认流恒 None → `_route_revision_after_resonance` 的 floor 检查（1925-1932）经 `check_resonance(None)=True` 恒过（revision_router.py:109-117）+ cmd_chapters 全书显示 resonance_score: null。
- 处置：F304 维持 P1（floor 失效仍在），但"escalation_bridge 枯竭"论据撤回，修复方案需与 F360 合并（先修 upsert 路由再谈趋势文件质量）。

### MR3 | 次要修正（不改定级）

- 初审 F303/r1 F341（audit 级联死链）：两轮结论均维持——我独立复核确认 `_get_audit_history` 的 `isinstance(audit_result, dict)` 过滤在现有 audit_results 键族（blocking_found:bool / audit_reports:list / issues:list / revision_route:str）下恒空。r1 对初审修复方向的修正（三层死因）正确。
- r1 F351（差分快照无生产调用）：独立复核确认——`create_differential_snapshot` 生产调用仅 chapter_loop.py:1748（死函数 `_snapshot_chapter_files` 内）；crash_recovery.py:154-176 的同名函数是另一个独立实现（平面复制）。r1 对 F306 的降级建议（P1→P2）我方支持。
- r1 F342（style_profile 幽灵键注入）：独立复核确认——`grep truth/style_profile.md skills/` 零命中，唯一声明 `style/style_profile.md` 的是 shenbi-review-resonance。

---

## 三、覆盖空洞（两轮审查均未覆盖，本轮角度下暴露）

1. **契约 updates 模式 → 派发写路径的语义映射**：`append_dedup` 声明（G0.16 校验对象）与实际写行为（整文件覆写）之间无任何测试；初审与 r1 都读到了 dispatch_helper:1072-1081 的"NOT routed here"注释却止步于字面，未追到"技能指示追加 + reads 不含目标文件 → 正确行为设计上不可能"的运行时后果（F360 由此漏网）。`write_semantics` 只用于打日志（1142-1143），契约 mode 与写行为的一致性无断言。
2. **审计文件名三角一致性**：ReviewTask.output_path（记录名，audit_suffix 产物）vs 技能契约 writes（真实写入）vs `_any_audit_has_findings` 词表（消费）——三方无一致性测试。这是 r1 F340 误报的直接根源，也是 F364 幽灵路径的根源。
3. **计数型状态 vs 磁盘产物对账**：steps_done / audit_reports / skills_done / checkpoint_history 与磁盘文件的核对无任何测试（F364/F365/F367 全部由此漏网）。唯一存在的对账是 state_heal 的 `_heal_revision_counts`（revision_count vs decisions 文件，且自知 disk 值是下界）。
4. **物化/进度节拍**：`%5` 计数与步骤完成事件（含 pipeline- 步与审计波的批量标记）的组合行为无测试（F366）。
5. **截断标记存活与注入键一致性**：F361/F362（标记被 cap 切掉、注入值无标记）在初审的 F330 与 r1 的 F342 中均只覆盖了相邻侧面。
6. **并行波与串行路径的失败处理等价性**：F363（预算绕过）与 F365（lifecycle 失败吸收）都是"并行重构未迁移串行失败语义"族——初审只记录了 F309 一个实例，未做两路径失败处理差集的全枚举。

---

## 四、严重度异议（无权改定级，仅提异议）

| 条目 | 原定级 | 异议 | 依据 |
|---|---|---|---|
| r1 F340 | P1（P0 边界） | **降 P2** | MR1：核心前提错误，主流 group 审计文件名恰在扫描词表内；残存问题仅 F369（3 个 genre 维度窄条件）+ F370（M 级误触发） |
| 初审 F304 | P1 | 维持 P1，修正论据 | MR2：floor 失效（前半）成立；"escalation_bridge 枯竭"（后半）撤回，真相是 F360 污染 |
| 初审 F306 | P1 | **同意 r1 降 P2** | 本轮独立验证 F351 成立：差分快照在正常流程零调用，ring-buffer bug 仅在紧急恢复场景显形 |
| 新 F360 | —（本轮新报） | **P0** | 决策表 P0 典型例"truth 覆盖 bug"的直接实例；11 技能、每章热路径、设计上无正确行为分支 |
| r1 F346（快照保留配置死项） | P2 | 维持 | 复核确认 `_get_snapshot_retention` 硬编码 50（chapter_loop.py:1399-1404） |
| 初审 F309 | P1 | 维持，并建议与 F363/F364/F365 打包 | 四者共同构成"并行波下游消费与记账链"修复批次 |

---

## 五、本轮角度专项结论

### 5.1 角度 (a) 截断完整性——全部截断点枚举与结论存活判定

| 截断点 | 标记 | 结论 |
|---|---|---|
| `_budgeted_truncate` 分配截断（dispatch_helper:313） | 有 | 但标记可被 :315 的 32K cap 切掉 → F361 |
| 32K per-file cap 两条路径（:315 / :657-664） | **无** | 静默截断 + 预算内路径无日志 → F361 |
| `audit_context_cache` world_rules/character_list（:56/:61） | 有（_summarize_if_large） | 通过 |
| `audit_context_cache` style_profile `[:2000]`（:65） | 无 | 死键注入的副本（F342），本身影响小 |
| `audit_context_cache` pending_hooks `[:3000]`（:69） | **无** | 5/6 审计的唯一视角被截断 → F362 |
| `_extract_volume_chapter` `result[:50]`（:103） | 无 | 死代码（F312 错路径），不触发 |
| `review_checklist._summarize_world_rules` `[:2000]`（:434） | 无 | 字段名即 "brief"，设计使然，M 级备注 |
| `_load_blacklist` `[:10]`（:552） | 无 | 死代码段（F319） |
| scr_extractor `sent[:80]`/`text[:100]`/`results[:3]` | 无（节选型） | 证据摘录语义，文档声明，通过 |
| context_assemble `_ROUTE_C_MAX_CHARS=2000`（:192）、`_PLAN_QUERY_CHARS=500`（:159） | 无 | 有 docstring 声明（防 runaway/限延迟），可接受 |
| `_write_minimal_context_fallback` `[:2000]`（chapter_loop:1215） | 无 | 兜底路径，可接受 |
| 各种 stderr 预览 `[:200]`/`[:500]`/`[:2000]` | 无 | 纯日志展示，通过 |
| `_validate_json_output` raw_decode 截断恢复（:836-869） | 有（log）+ schema 校验 | 通过 |

### 5.2 角度 (b) 计数三方对账——对账矩阵

| 计数 | state 值 | 磁盘产物 | 代码声称 | 判定 |
|---|---|---|---|---|
| 审计 steps_done（波） | 恒 6 条 | 实际派发任务数（≤6）×成功文件数（per-dimension 13 个） | "Record all review steps as done" | ✗ F364 |
| audit_reports 路径列表 | 含 4 个幽灵 group-* 路径 | 13 个 per-dimension 文件 | output_path"for tracking" | ✗ F364 |
| retry_counts/retry_budget_consumed（审计） | 恒零 | 日志最多 18 次调用/章 | spec §3.1 持久预算 | ✗ F363 |
| retry_feedback | 单调增长、成功不清 | 无对应盘面 | "prior attempt failed"（一次性语义暗示） | ✗ F368 |
| genesis.skills_done | REJECT 重做后 18 条 | 17 个产物 | 17 步表 | ✗ F367 |
| steps_done %5 物化 | 触发 0 次 | progress.json 仅 resume 时重建 | "every 5 steps" | ✗ F366 |
| truth 累积文件行数（append_dedup） | — | 每章整覆 vs 契约"追加" | "the upsert itself is the CALLER's responsibility" | ✗ F360（调用方不存在） |
| revision_count vs decisions 文件 | heal 时取 max，自知下界 | decisions 每轮覆写 | state_heal 文档声明 | ✓（唯一有意识对账的点） |
| checkpoint_history | NONE 也入账（F338） | — | — | 已由初审记录，维持 |
| lifecycle/settling steps_done | 失败也记 done | pending_hooks 可能未更新 | "Record both steps as done" | ✗ F365 |

### 5.3 两轮结论的净状态

- 初审 F301-F339：本轮全部重读核对，字面证据无一误报（F304 后半论据修正见 MR2）。
- 复核轮 1 F340-F359：F340 核心前提被运行时证据推翻（MR1）；其余抽查条目（F341/F342/F346/F351/F352）复核属实。
- 本轮新增 11 项（F360-F370）：P0×1、P2×6、M×3、（F369 计 P2）。
- 建议的修复批次划分：**批次一（truth 写路径）**= F360 + F304 前半 + F306/F351（快照接线）；**批次二（审计波下游）**= F309+F363+F364+F365+F369+F370+F305；**批次三（记账/观测）**= F366+F367+F368+F301/F302。
