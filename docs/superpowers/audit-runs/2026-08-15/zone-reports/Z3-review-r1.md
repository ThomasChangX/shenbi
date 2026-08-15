# Z3 区独立复核报告 r1 — src/shenbi/pipeline/（2026-08-15 轮）

复核人：Z3 fresh-context 独立复核 agent。与初审无关的全量重读（34/34 文件）。
本轮新增角度：(a) 状态/字段/键名字面量 vs 唯一定义源双向核对（PipelineState 字段、CheckpointType 族、audit_results 键族、路径字面量 vs 实际目录布局）；(b) 同一数据结构的全部变体形状逐一枚举 vs 每个消费方解析分支覆盖。

编号说明：任务书指定本 agent 使用 F339-F399，但初审正文在 `_shared.py` 条目中已使用 F339（总表只列到 F338，正文与总表自相矛盾——初审编号管理瑕疵，记录在案）。为避免冲突，本报告从 **F340** 起编号。

验证声明：本报告所有标注"已验证"的条目均在 2026-08-15 实际运行了 `uv run python -c`（临时目录构造真实文件）或 `grep`；关键输出原文粘贴于各条目。只读禁令遵守：未创建/修改/删除任何仓库文件（本报告除外），未执行 pytest，未调用 shenbi-dispatch/pipeline。

---

## 一、漏报（新 findings，F340-F359）

### F340 | 修订步条件门控扫描旧版审计文件名族：group-* 审计报 BLOCKING 时 chapter-revision 被静默跳过 | error | P1（P0 边界，见严重度异议）

- 证据：
  - `src/shenbi/pipeline/chapter_loop.py:1807-1821` — `_any_audit_has_findings` 扫描 13 个旧维度文件名 `chapter-{N}-{atype}.md`（continuity/character/world-rules/pacing/dialogue/motivation/pov/memo-compliance/foreshadowing/anti-ai/texture/reader-pull/sensitivity）
  - `src/shenbi/pipeline/audit_layer.py:125-131` — `audit_suffix("shenbi-review-group-factual") = "group-factual"`：重构后的核心波 6 个审计实际写 `chapter-N-group-factual/group-character/group-craft/group-plan/resonance/sensitivity.md`
  - `src/shenbi/pipeline/chapter_loop.py:1848-1849` — `_should_run_step` 对 `shenbi-chapter-revision` 返回 `_any_audit_has_findings(state)`
  - `src/shenbi/pipeline/chapter_loop.py:2800-2804` — 条件不满足 → `conditional_step_skipped` 直接推进
- 根因：20→16 步重构（MERGE-2 分组审计）后，`_any_audit_has_findings` 的文件名词表未随 `audit_suffix` 迁移。核心波 6 文件中仅 `sensitivity` 能被扫描命中；4 个 group 审计（聚合了 continuity/character/pacing 等旧维度内容的主审计）全部不在扫描范围。
- 控制流后果：并行波 `_route_revision_after_resonance`（chapter_loop.py:2647）用 `collect_audit_issues`（glob 全部 `chapter-N-*.md`，含 group-*）判 route=REVISION/REGENERATE 并递增 `revision_count`（1913-1914）→ step-16 处 `_is_revision_skipped`=False（route≠no-revision）→ 但 `_should_run_step`→`_any_audit_has_findings`=False → **修订步被跳过**。且 2800-2804 跳过路径不调 `_ensure_revision_decisions_exists`（对比 2796）→ 无 decisions 文件。章节带着未解决的 BLOCKING 审计发现被标记 complete。
- 验证命令+输出（已验证，临时目录构造真实审计文件）：
  ```
  audits/chapter-5-group-factual.md 含 "**严重度**: BLOCKING — 主线事实矛盾"
  audits/chapter-5-sensitivity.md 含 "判定: 通过，无敏感问题"
  collect_audit_issues: issues=1, blocking=True
  route_chapter_revision -> regenerate  (需修订)
  _any_audit_has_findings -> False
  _should_run_step(revision) -> False   <<< 修订步被跳过
  ```
- 测试掩盖：`tests/pipeline/test_chapter_steps_restructured.py:97-100`、`tests/unit/pipeline/test_chapter_loop.py:683-685`、`tests/unit/pipeline/test_chapter_loop_full.py:448-451` 全部 **mock** `_any_audit_has_findings`，无任何测试喂入真实 group-* 审计文件。
- 建议方向：`_any_audit_has_findings` 改为 glob `chapter-{N}-*.md` 全量扫描（与 `collect_audit_issues` 同源），或直接消费路由器结果（`audit_results["revision_route"]`）；补"仅 group 审计有 BLOCKING"回归测试。
- 置信度：high

### F341 | 审计级联缺数据生产者：audit_results 键族无 `passed`/`hard_failures` 形状，`_get_audit_history` 恒空；group-* 短名也不在 CORE/CASCADABLE 词表（F303 的第三层死因 + 修复方向修正） | error | P1（并入 F303，加重其根因描述）

- 证据：
  - audit_results 全部写入点（grep 已验证）：仅 `chapter_loop.py:1908`（revision_route:str）、`2641/2970`（blocking_found:bool）、`2642/2972`（audit_reports:list）、`2971`（issues:list）——**没有任何写入者产出 `_get_audit_history`（chapter_loop.py:379-389）所要求的 `{passed, hard_failures}` dict 形状**；`isinstance(audit_result, dict)` 过滤后恒为空
  - `src/shenbi/pipeline/state.py:200-208` — 线程安全 API `add_audit_result` 零调用者（grep 已验证，仅定义）
  - 词表缺口：`_audit_short_name("shenbi-review-group-factual")="group-factual"` 不在 `CORE_AUDITS`(309) 也不在 `CASCADABLE_AUDITS`(313-322)（已验证输出：`group-factual: in CORE=False, in CASCADABLE=False`，同理 group-character/group-craft/group-plan/resonance）
- 根因：三层死因叠加——(1) 无生产者写 per-skill 通过记录；(2) 初审 F303 已述的扁平/分组格式不匹配；(3) 新分组审计短名未入两张词表（即使前两层修复，"unknown skill → run normally" 分支仍永不跳过）。
- 对初审修复方向的修正：F303 建议"在 _get_audit_history 内按章分组"**不足以修复**——分组后每章的 `chapter_results.get(skill)` 仍取不到值，因为 state 里根本没有 per-skill 记录。必须在并行波 consolidate 后写入 per-skill `{passed, hard_failures}`（或改用 blocking_found/audit_reports 现有键推导）。
- 验证命令+输出（已验证）：
  ```
  3 章 audit_results(真实键族 blocking_found/audit_reports/revision_route) -> history = []
  _should_skip_audit("group-factual", h) = False
  _should_skip_audit("dialogue", h) = False
  ```
- 建议方向：见上；词表同步补 group-* 短名或改为按 audit_suffix 全词表驱动。
- 置信度：high

### F342 | 共享审计上下文 style_profile 注入键路径错误：`truth/style_profile.md` vs 实际 `style/style_profile.md` | error | P2

- 证据：`src/shenbi/pipeline/dispatch_helper.py:624-627`（注入键 `_input_key(project_dir/"truth"/"style_profile.md")`）；`src/shenbi/pipeline/audit_context_cache.py:63-65`（缓存从 `style/style_profile.md` 读）；`skills/shenbi-review-resonance/SKILL.md:15`（契约 reads 键为 `style/style_profile.md`，已验证）
- 根因：路径字面量与实际布局漂移（本轮角度典型案例）。注入键永不匹配契约读取键 `style/style_profile.md` → (a) 缓存对 style_profile 是 no-op，审计技能照旧从盘上读；(b) 幽灵键 `truth/style_profile.md` 把同一内容以"额外输入文件"形式重复注入每个审计调用（~2000 字符 × 每章 6-8 个审计调用 ≈ 12-16K 字符/章纯浪费），且无任何契约消费方。
- 与初审判定对照：初审 dispatch_helper 覆盖缺口处置把 615-634（共享上下文注入）标为 must-test 但未发现此键错。
- 验证：静态读码 + SKILL.md 契约键核对（grep 输出如上）。未运行注入级集成测试（无现成入口）。
- 建议方向：注入键改为 `style/style_profile.md`；补"注入键必须出现在某审计技能契约 reads 中"的接线断言。
- 置信度：high

### F343 | `_load_genre_config_cached` 死函数且路径错误：读 `config/genre-config.json`（实际在项目根） | deps | P2

- 证据：`src/shenbi/pipeline/dispatch_helper.py:201-208`（`# pyright: ignore[reportUnusedFunction]` 自认无调用者；无 exists 检查，接错路径一旦接线即 FileNotFoundError）；实际写入点 `cli.py:454-456` 与读取点 `chapter_loop.py:2599`、`review_checklist.py:204,235` 均为项目根 `genre-config.json`（grep 已验证）
- 根因：路径字面量 vs 唯一定义源（cmd_init 写入位置）漂移。
- 验证：grep 已验证（定义处唯一命中，无调用方）。
- 建议方向：删除，或改路径为根目录并去 pyright-ignore。
- 置信度：high

### F344 | `state.token_usage` 为未声明动态属性：不参与 to_dict/from_dict，跨进程全部丢失；`print_token_summary` 只统计本进程 | error | P2

- 证据：`src/shenbi/pipeline/dispatch_helper.py:1327-1328`（`if not hasattr(state,"token_usage"): state.token_usage={}` 动态挂载）；`src/shenbi/pipeline/state.py:162-183`（PipelineState 无该字段）+ to_dict 显式字段清单不含它（已验证输出：`"token_usage" in to_dict = False`）
- 根因：状态形状未入唯一定义源（本轮角度：动态属性绕过 dataclass 契约）。ledger jsonl 是持久记录（F301 修复后），但 state 级聚合/`print_token_summary`（chapter_loop.py:948 每章完成时调用）只反映本进程，多进程 resume 场景（每章一次 `pipeline next` 是设计用法）下摘要恒偏小、误导观测。
- 验证：已验证（to_dict 键清单输出粘贴如上）。
- 建议方向：token_usage 声明为 ChapterLoopStateData 或 PipelineState 的 ephemeral 字段（同 step_timings 处置），或在 summary 中注明"per-process"。
- 置信度：high

### F345 | `dispatch_skill(timeout=...)` 死参数：签名/文档/测试均以为生效，实际恒用 `_compute_dispatch_timeout` | deps | P2

- 证据：`src/shenbi/pipeline/dispatch_helper.py:1826`（形参 `timeout: int = 900`）、`1900`（`cli_timeout = _compute_dispatch_timeout(...)`，形参从未被读）；`tests/unit/pipeline/test_dispatch_helper.py:55` 传 `timeout=1`（被忽略，测试可能意外长挂或依赖 mock）
- 验证：grep 已验证（唯一 timeout= 传参在测试）。
- 建议方向：删除形参或在 legacy 路径取 `min(timeout, cli_timeout)`。
- 置信度：high

### F346 | `_get_snapshot_retention` 硬编码 50：`PipelineConfig.snapshot_retention_chapters` 配置死项 | error | P2

- 证据：`src/shenbi/pipeline/chapter_loop.py:1399-1404`（函数不接收 state/config，直接 `return 50`，docstring 自称 "matching PipelineConfig"）；`src/shenbi/pipeline/state.py:73`（配置字段存在且完整参与 to_dict/from_dict 往返）
- 根因：配置字面量 vs 唯一定义源脱钩——用户改配置无任何效果（静默违反配置契约）。
- 验证：静态读码（函数体 4 行）+ state.py 字段核对。
- 建议方向：调用方传入 `state.config.snapshot_retention_chapters`。
- 置信度：high

### F347 | `_append_integrity_findings` 并行波读-改-写竞态：无 per-path 锁，同章并行审计互相覆盖 findings；G4 generic 是真实消费方 | error | P2

- 证据：`src/shenbi/pipeline/dispatch_helper.py:1039-1054`（read_text 全文 + 追加 + safe_write 整体重写，无锁；truth_io.py:54-70 的 `_path_lock` 模式未复用）；并行波同章 6+ 审计并发调用（parallel_dispatch.py:171-188）；消费方 `src/shenbi/gates/g4/generic.py:193-197`（读 `audits/.integrity-findings-{chapter}.jsonl`）
- 根因：lost-update 窗口在 read→write 之间（safe_write 只保证单次写原子）。两个审计线程同时发现 issue 时后写者覆盖前写者的行 → G4 generic 漏检。当前因 F305（波内无 G4）消费时点错后，但修复 F305 后此竞态立即显形。
- 验证：未运行并发复现（需线程调度运气）；静态控制流 + 消费方 grep 已验证。
- 建议方向：复用 truth_io._path_lock 或改 append 模式 + 文件锁。
- 置信度：medium-high（竞态窗口确证；触发频率未测）

### F348 | snapshot `TRUTH_FILES` 集合缺 `book_strata.md`/`volume_summaries.md`/`arcs/`：触发器阶段写入的累积 truth 文件完全不入差分快照 | error | P2

- 证据：`src/shenbi/pipeline/snapshot_diff.py:18-28`（TRUTH_FILES 仅 9 个文件；`truth_dir.iterdir()` + `f.name in TRUTH_FILES` 过滤 → `truth/arcs/arc-N.md` 子目录与上述两文件全漏）；写入方 `src/shenbi/pipeline/triggers.py` TRIGGER_STEPS（memory-distill L4→`truth/book_strata.md`，volume-consolidation→`truth/volume_summaries.md`，memory-distill L2→`truth/arcs/arc-N.md`）
- 根因：字面量集合 vs 实际 truth 写入方集合双向核对失败（本轮角度）。restore 无法恢复卷摘要/地层/弧段累积状态。
- 验证：静态读码双侧核对（快照侧与触发器侧行号如上）。
- 建议方向：TRUTH_FILES 补齐或改为"truth/ 下全部 *.md + arcs/ 递归"。
- 置信度：high

### F349 | `_drift_guidance_triggered` 读不存在的 `state.drift_alerts` 属性（getattr 幽灵字段，恒 False） | error | P2（F315 的附加陷阱层）

- 证据：`src/shenbi/pipeline/chapter_loop.py:1792-1795`（`getattr(state, "drift_alerts", [])`）；`src/shenbi/pipeline/state.py` 无 drift_alerts 字段（to_dict 键清单已验证不含）；全仓无任何写入者（grep `drift_alerts` 仅此一处，已验证）
- 根因：字段名臆断（与 F302 同族：`state.chapter`）。CONDITIONAL_STEPS 目前死（F315），但任何人重新接线 drift-guidance 时该条件永不触发且无报错。
- 建议方向：接真实数据源（如 soft_fail_trackers 或 drift 检测结果）或删除。
- 置信度：high

### F350 | 紧急快照不入 snapshots/manifest.json（不受保留策略管理、永久累积）+ 快照文件命名三套并存 | error | P2

- 证据：`src/shenbi/pipeline/crash_recovery.py:154-177`（写 `snapshots/chapter-{N}-{label}.md`，非填充、无时间戳，**不更新 manifest**）；对照 `chapter_loop.py:1723-1729`（legacy 路径会更新 manifest）；`chapter_loop.py:1747`（差分目录 `chapter-{N:03d}/`）；`_prune_old_snapshots`（1538-1573）只清理 manifest 中登记的文件 → 紧急快照永不清
- 附加：crash_recovery.py:138 调 `_snapshot_chapter_files(project_dir, chapter, label="emergency")` **不传 state** → 即使紧急路径也不更新 `state.last_snapshot`（`_snapshot_chapter_files` 的 state 参数仅 chapter_loop 内部传，而该调用点不存在，见 F358）。
- 建议方向：紧急快照登记 manifest；命名统一走单一 helper。
- 置信度：high

### F351 | step-15 `pipeline-pre-revision-snapshot` 为空操作；差分快照系统在正常流程中无任何调用点（唯一生产调用方是紧急清理） | deps | P2（同时构成 F306 的严重度异议依据）

- 证据：`src/shenbi/pipeline/chapter_loop.py:246-251`（step 15 定义）；`2755-2769`（`pipeline-` 分支仅 mark done + advance，无快照调用）；grep 已验证：`create_differential_snapshot` 生产调用仅 `chapter_loop.py:1748`（`_snapshot_chapter_files` 差分分支）与 `crash_recovery.py:138`（紧急路径），而 `_snapshot_chapter_files` 本身在 chapter_loop 中无调用者；正常流程的修订前保护实际由 `_create_pre_revision_backup`（1896-1910，shutil 复制 `chapter-N-pre-rev.md`）承担
- 根因：步骤表重构（新增 5 个 pipeline-* 确定性步骤）时快照步只加了壳没接线。
- 建议方向：step-15 接 `_snapshot_chapter_files(..., state=state)` 或删除该步；与 F306 一并修复（先接线再修 ring-buffer 匹配）。
- 置信度：high

### F352 | genesis ESCALATION checkpoint 传 `chapter=0`（F336 同族第二实例）；0/None 字面量语义分裂 | docs | M

- 证据：`src/shenbi/pipeline/genesis.py:260`（`set_checkpoint(..., chapter=0, artifact="audits/escalation-genesis-report.md")`）vs 同文件 `:247`（`dispatch_escalation(project_dir, None)` 用 None 表达 genesis）vs `cli.py:318-322`（RetryExhausted 在 genesis 相位用 None）vs `cli.py:300`（closure 用 0）。dispatch_escalation 的 None 分支（revision_router.py:154-165）才生成 genesis 语义路径上下文。
- 建议方向：统一 None=无章上下文。
- 置信度：high

### F353 | triggers G3 失败路径不写 `state.last_trigger_failure`（stage 值族缺 "g3"） | docs | M

- 证据：`src/shenbi/pipeline/triggers.py:556-562`（stage:"dispatch"）、`574-580`（stage:"g4"）、`583-593`（g3 失败仅 log + return False，无状态记录）——同一 dict 形状族（{chapter,skill,mode,stage,timestamp}）三个分支只覆盖两个。
- 建议方向：补 `stage:"g3"` 记录。
- 置信度：high

### F354 | `_verify_truth_integrity` genesis_outputs 漏 `world/factions.md`（genesis step-5 输出）与 `foundation/review_report.md` | docs | M

- 证据：`src/shenbi/pipeline/cli.py:708-723`（14 项清单）vs `genesis.py:58-82` GENESIS_STEPS 输出路径双侧核对（已验证）。影响低（F325：返回值本就被丢弃）。
- 置信度：high

### F355 | OPTIONAL_READS 含已移除技能死条目（context-composing / foreshadowing-plant / foreshadowing-track） | docs | M

- 证据：`src/shenbi/pipeline/dispatch_helper.py:373-379` vs `chapter_loop.py:124-125`（"Deprecated skills removed: foreshadowing-plant, foreshadowing-track, ..., context-composing"，grep 已验证）。
- 置信度：high

### F356 | audit_context_cache `chapter_summary` 字段从未填充（死字段），叠加 F312 使 estimated_tokens 显著低估 | docs | M

- 证据：`src/shenbi/pipeline/audit_context_cache.py:22`（字段）、`45-81`（build 函数只设 6 个字段，chapter_summary 恒 ""）。
- 置信度：high

### F357 | `_FORESHADOWING_LIFECYCLE_IDX = 6` 魔法索引（对照 `_FIRST_AUDIT_IDX`/`_LAST_AUDIT_IDX` 为推导式）：CHAPTER_STEPS 再次重排即静默错位 | docs | M

- 证据：`src/shenbi/pipeline/chapter_loop.py:2392` vs `:293-296`。当前值正确（idx6=lifecycle、idx7=settling、idx8=_FIRST_AUDIT_IDX），但 2664 分支只检查 `step_idx == 6` 不校验 skill。
- 置信度：high

### F358 | step-2（chapter-planning）过早触发 context assembly：plan 尚不存在 → assemble 抛错 → 每章写一次废弃的 minimal fallback，step-3 再重装配 | optimization | M

- 证据：`chapter_loop.py:150-151`（step2 calls_context_assembly=True）、`2749-2752`（dispatch 前装配）、`context_assemble.py:287`（plan 不存在直接 read_text 抛 FileNotFoundError）、`chapter_loop.py:1181-1187`（捕获后写 fallback）。浪费为确定性小成本 + 每章一条 error 噪音。
- 置信度：medium（行为推演自控制流，未逐步运行）

### F359 | cli resume VOLUME_BOUNDARY 分支的 snapshot-manage 派发不传 state（F301 证据链补遗） | error | 并入 F301

- 证据：`src/shenbi/pipeline/cli.py:819-823`（`dispatch_skill("shenbi-snapshot-manage", project_dir, ...)` 无 state）。初审 F301 列举了 cli.py:140（re-dispatch）但漏了此点。已验证（读码）。

---

## 二、误报（初审条目反驳）

**结论：无完全推翻的初审条目。** 34 文件全量重读后，初审 F301-F338 的字面证据（file:line）全部复核属实。但有两条需要**修正影响面/机制描述**：

### 2.1 F306（ring-buffer 全文备份永不命中）——字面 bug 成立，但影响面前提不成立

- 初审声称"修订回滚（restore 的核心卖点）无法恢复章节正文"，P1 定级隐含前提是**正常流程每章产出差分快照**。
- 反驳证据（已验证，grep）：`create_differential_snapshot` 的生产调用链仅 `crash_recovery.py:138`（SIGTERM/SIGINT 紧急清理）；step-15 `pipeline-pre-revision-snapshot` 是空操作（chapter_loop.py:2755-2769 的 `pipeline-` 分支只 mark done，见 F351）。正常流程中修订回滚的实际保护是 `_create_pre_revision_backup`（1896-1910，chapter-N-pre-rev.md），与 ring-buffer 无关。
- 即：F306 的 bug 在代码中真实存在（若快照被触发，章节全文确实永不入快照——已用临时目录复现 `ring_buffer_full=True 但全文文件=[]`），但"每章修订回滚失效"的叙事不成立——正常流根本没有每章差分快照这回事。真实影响 = 紧急崩溃场景下的恢复能力缺口（truth 全文仍可恢复；chapters/plans 不可）。
- 处置：F306 保留为真 bug，但建议严重度 P1→P2（见下节），并与 F351（快照步空操作）合并修复。

### 2.2 F303（audit 级联 dead-wire）——结论正确，机制描述不完整导致修复方向错误

- 初审把死因归结为"`_get_audit_history` 扁平格式与 `_should_skip_audit` 分组格式不兼容"。复核发现这是三层死因中的第二层：第一层是 **audit_results 键族根本没有 `{passed, hard_failures}` 形状的生产者**（F341，已验证 history 恒 []），第三层是 group-* 短名不在两张词表。
- 后果：初审建议的修复（"在 _get_audit_history 内按章分组"）单独实施**不会生效**。完整修复需同时：(a) 波后写入 per-skill 结果；(b) 统一形状；(c) 同步词表。
- 处置：F303 维持 P1，按 F341 修正根因与修复方案。

### 2.3 次要修正（不改定级）

- F311：初审验证命令引用 `resolve_chapter_path` 输出正确；补充核对 `skills/shenbi-chapter-drafting/SKILL.md` 只读 `chapter-N-context.md` 属实（curated 无消费者成立）。
- F336：genesis.py:260 是同族第二实例（F352），初审仅列 cli closure 一处。
- 初审 _shared.py 条目编号 F339 与其总表（止于 F338）冲突——编号管理瑕疵，非技术误报。

---

## 三、覆盖空洞（初审未覆盖/覆盖不足）

1. **`_any_audit_has_findings` 的真实文件路径**：全部测试 mock 之（3 处，见 F340 证据）；"审计文件名词表 vs audit_suffix 产物"的一致性无任何测试。这是 F340 漏报的直接原因。
2. **路由器与 step-16 门控的联动**：`_route_revision_after_resonance` 写入 `revision_route` 后，`_is_revision_skipped`/`_should_run_step` 两道门的一致使无集成测试（F340 的第二层原因）。
3. **注入键 ↔ 契约 reads 键一致性**：dispatch_helper `_INJECT_FROM_CACHE` 的 4 个键与审计技能 SKILL.md reads 的交集断言缺失（F342 因此漏网）；初审虽把 615-634 标为 must-test 但未给出具体断言方向。
4. **audit_results 形状家族无契约测试**：4 个字面量写入者 + 1 个零调用 mutator（`add_audit_result`）+ 3 个读取方（`_get_audit_history`/`_is_revision_skipped`/cmd_chapters 显示）之间无 schema 约定（F341）。
5. **快照系统全链路**：`_snapshot_chapter_files` 在 chapter_loop 内无调用者这一事实（F351）说明初审对 snapshot_diff 的审查停留在"函数内部正确性"（F306/restore 测试缺口），未做"生产调用图"核对——`restore_from_snapshot` 同样无任何生产调用方（grep：仅 tests）。整个差分快照+restore 子系统当前是**紧急路径专属 + 回滚入口未接线**。
6. **crash/emergency 路径的 state 一致性**：紧急快照不传 state（F350 附注）、不更新 manifest、`_emergency_cleanup` 在 atexit 多次注册下重复执行——初审 F318 只覆盖 atexit 累积与 staging 清理两半。
7. **gate manifest 记录空洞**：genesis（genesis.py:333 G4 无 chapter/phase）与 triggers（triggers.py:566 G4 无 chapter/phase）的 gate 结果不入 manifest——对照 chapter_loop 每步都记录。G7 审计视角下这两个相位的 gate 证据链缺失。
8. **并行波 + auto-mode 组合**：`_auto_settle_parallel`（896-921）与 G4-continue auto 路径（F332）的组合行为无测试。

---

## 四、严重度异议（无权改定级，仅提异议）

| 初审条目 | 初审定级 | 异议 | 依据 |
|---|---|---|---|
| F306 | P1 | **建议降 P2** | 影响面前提不成立（2.1）：正常流程无每章差分快照（F351），修订回滚由 pre-rev 备份承担；ring-buffer bug 只在紧急崩溃恢复场景显形，且 truth 全文仍可恢复 |
| F340（本报告新发现） | —（按决策表取 P1） | **建议 P1，但处在 P0 边界** | "章节带未解决 BLOCKING 被静默标记 complete"符合决策表 P0 的"pipeline 静默产出错误结果"；因需 group 审计单独报 BLOCKING 的具体条件且质量门（非数据损坏）性质，取 P1 并明确标注 P0 边界，供裁决 |
| F309 | P1 | 维持，且 F340 与其构成同族放大：F309 让失败的审计静默通过，F340 让通过的审计发现静默丢弃——两者共同瓦解审计门 | — |
| F338 | M | 维持 M（复核确认：CLI 路径有 `is_at_checkpoint` 前置守卫（cli.py:581），"none" 历史仅在其他直接调用 clear_checkpoint 时可能，防御性修复即可） | — |
| F316/F314/F315 | P2 | 维持（grep 复核全部确认零调用者/死表） | — |
| F323 | P2 | 维持 P2；补充：MODIFY 回退 step_index=1 后 `_run_context_assembly` 将用**已提交的人工编辑版 plan** 重装配（顺序：592 先 commit → 612 回退 → resume 时 step2 前装配），语义冲突描述准确 | — |
| F301 | P0 | 维持 P0；证据链补 cli.py:819-823（F359）与 IDE 路径结构性无计量（dispatch_helper.py:1803-1811 自认）两点 | — |

---

## 五、本轮角度专项结论

### 5.1 字面量 vs 唯一定义源双向核对（新命中 9 处）

| 字面量 | 唯一定义源 | 状态 |
|---|---|---|
| `getattr(state,"chapter",0)`（dispatch_helper:1348） | PipelineState 字段表 | ✗ 不存在（F302，复核确认） |
| `getattr(state,"drift_alerts",[])`（chapter_loop:1794） | 同上 | ✗ 不存在（F349 新发现） |
| `state.token_usage` 动态挂载（dispatch_helper:1328） | to_dict/from_dict 序列化契约 | ✗ 不入序列化（F344 新发现） |
| `config/genre-config.json`（dispatch_helper:205） | cmd_init 写入位置=项目根 | ✗ 错路径（F343 新发现） |
| `truth/style_profile.md` 注入键（dispatch_helper:626） | 实际文件=style/style_profile.md（audit_context_cache:63 + SKILL.md 契约） | ✗ 错路径（F342 新发现） |
| `_any_audit_has_findings` 13 类型词表（chapter_loop:1807-1821） | audit_suffix 产物=group-* 族 | ✗ 词表漂移（F340 新发现，本报告最重） |
| `chapter-{chapter:03d}` 零填充族（audit_context_cache:49、snapshot_diff:113-114、review_checklist:511,526） | 实际章节文件=非填充（resolve_chapter_path） | ✗ F312/F306/F319 复核确认，同族第 5 处（review_checklist 两处）初审已含 |
| TRUTH_FILES 9 文件集合（snapshot_diff:18-28） | triggers/状态结算实际写入的 truth 文件集 | ✗ 缺 3 项（F348 新发现） |
| `snapshot_retention_chapters` 配置（state.py:73） | `_get_snapshot_retention` 硬编码 50 | ✗ 配置死项（F346 新发现） |

双向核对通过项（无发现）：CheckpointType 8 值族全部 set_checkpoint 调用合法且 cmd_resume 消费分支匹配；`pending_re_dispatches` 元素形状 {skill,checkpoint_type,chapter,feedback} 生产/消费一致；`checkpoint_history` 元素形状 {type,chapter,decision,resolved_at(+feedback)} 生产/消费一致；DERIVED_TRUTH_MAP 键用 `.value` 与枚举一致；`world/rules.md` 确由 shenbi-worldbuilding 写入（SKILL.md:35），review_checklist/truth_index 读它正确（初审未涉，复核排除疑点）；`_verify_truth_integrity` 的 outline/volume_map.md 与实际布局一致（反证 F312 的 truth/volume_map.md 是错方）。

### 5.2 形状家族枚举 vs 消费分支覆盖

- **audit_results 值形状族**（枚举完毕）：`blocking_found:bool`、`audit_reports:list[str]`、`issues:list[dict]`、`revision_route:str`。消费方：`_get_audit_history`（要求 dict 形状 → 全不匹配，恒空，F341）；`_is_revision_skipped`（读 revision_route ✓）；cli cmd_chapters（不读此字段）。**结论：4 形状中 3 个无消费方、1 个消费方解析分支零覆盖。**
- **ChapterState.status 值族**：`pending`/`complete`/`settling_failed`（error_handler.py:115）。消费方 cmd_chapters 直显 ✓。
- **checkpoint chapter 字面量族**：None（genesis 语义）/0（genesis.py:260、cli.py:300）/正整数。消费方 `_reset_retry_budget` 用 `f"ch{ch}-"` 前缀——ch=0 时前缀 "ch0-" 无害但语义漂移（F352）。
- **快照文件命名族**：`chapter-{N}-{label}.md`（紧急）/`chapter-{N:03d}-{ts}.md`（legacy）/`chapter-{N:03d}/` 目录（差分）三套并存（F350）；`_heal_last_snapshot` 只认第一二套的扁平 .md（F317 维持）。
- **last_trigger_failure stage 值族**：dispatch/g4（缺 g3，F353）。

### 5.3 审计词表一致性总表（本轮角度核心产出）

核心波 6 技能短名在四张词表/扫描器中的覆盖：

| 短名 | CORE_AUDITS | CASCADABLE_AUDITS | _any_audit_has_findings 词表 | collect_audit_issues |
|---|---|---|---|---|
| group-factual/-character/-craft/-plan | ✗ | ✗ | ✗ | ✓（glob 全量） |
| resonance | ✗（ALWAYS_RUN ✓） | ✗ | ✗ | ✓ |
| sensitivity | ✗ | ✓ | ✓（唯一命中） | ✓ |

三列 ✗ 即 F340/F341 的联合根因：**同一"审计维度"概念存在四份互不一致的词表，且没有一份是从 audit_suffix/技能清单派生的**。建议建立单一 audit 维度注册表供四処派生。

---

## 六、复核结论摘要

- 初审 34 文件全部重读；F301-F338 字面证据全部复核属实，无误报条目；2 条影响面/机制修正（F306 前提、F303 根因）。
- 新增漏报 19 项（F340-F359）：P1×2（F340 修订步门控、F341 级联无生产者）、P2×9、M×7、并入 F301×1。
- 最重新发现 F340：与 F309 构成审计门的"双侧失效"（失败的审计静默通过 + 通过的审计发现静默丢弃），建议与 F303/F304/F305/F309/F341 作为同一修复批次（并行审计波的下游消费链）统筹处理。
- 覆盖空洞 8 项，其中"词表/键名一致性无派生源、无测试"是本轮角度下最高频的系统性根因（9 处字面量漂移中 7 处可由"单一注册表+派生"消除）。
