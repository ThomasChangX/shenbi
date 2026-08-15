# Z3 区独立复核报告 r3 — src/shenbi/pipeline/（2026-08-15 轮）

复核人：Z3 fresh-context 独立复核 agent 轮 3。34/34 文件全量重读（~14,000 行），与初审、r1、r2 无共享上下文。

本轮强制新角度（与前两轮均不复用）：
- (a) **状态机转换合法性与乱序/重复事件**——phase 转换守卫、checkpoint_history 作为事件流的重复消费、崩溃后半写状态、幂等重入、"代码假设顺序到达但磁盘状态可乱序"的缺口。
- (b) **默认值/常量假设 vs 实际数据形态**——DEFAULT/cap/阈值/`.get` 默认与 **真实生产数据**（novel-output/xinghuo-ranqiong，56 章真实项目）及技能自产格式的对照；默认值静默吞掉异常数据流的点。

编号段：F371-F381（承接初审 F301-F339、r1 F340-F359、r2 F360-F370）。

只读声明：除本报告外未创建/修改/删除任何仓库文件；未运行 pytest；未调用 shenbi-dispatch / pipeline 子命令；无 git 写操作。所有验证命令输出原文粘贴。

**事故披露（已恢复）**：本轮一次 `_build_skill_prompt` 抽验误将真实项目目录作为 project_dir，导致 `novel-output/xinghuo-ranqiong/context/review-checklist-5.json` 被重新生成覆盖（该文件受 git 跟踪）。已立即用 `git show HEAD:<path>` 读出原字节回写，`git status novel-output/` 确认 clean（恢复 6876 字节，误写为 6877 字节）。后续全部实验改用 /tmp/z3r3/ 临时目录。该事故本身顺带证实了 review-checklist 的 mtime 失效重生成路径可正常工作。

---

## 一、总体结论

1. **新发现 11 条（F371-F381）：P1×2、P2×6、M×3**。两条 P1 均由本轮新角度直接命中：
   - **F371**：`cmd_resume` 把 `checkpoint_history[-1]` 当"刚消费的事件"用且从不消费——auto 模式下卷一内任何崩溃后 `resume`（文档指定的崩溃恢复入口）会把 `current_chapter` 重置回 1，全书静默从头重生成（实跑复现 5→1）。
   - **F372**：`_parse_resonance_score` 的三种模式与技能自己规定的输出格式（`**结果**: 通过 (84/100)`）**零匹配**——真实项目 55/55 份共鸣报告全部解析为 None，state 中 56/56 章 resonance_score=null。这是 F304（floor 失效）之外的第二条独立根因。
2. **真实数据形态对照是本轮最高产的审计方法**：F372-F376 五条全部由"代码假设形状 vs xinghuo-ranqiong 实文/技能自产格式"对照命中，前三轮（纯代码+测试推演）全部漏网。真实项目同时为 F360（append_dedup 整覆）提供了生产实证：`truth/resonance_trend.md` 56 章后只剩 1 行。
3. **F318 需要severity 重审**：实验证明 `_emergency_cleanup` 经 atexit 在**正常退出**即触发（不需要崩溃/信号），交互模式下每个 checkpoint 的 staging 在人工评审前就被销毁——"紧急清理"实际上是"每次退出清理"。
4. 既有 70 条（F301-F370）逐条复读：**无误报推翻**；对有实跑声称的条目做了独立重跑（F302/F303/F306/F308/F311/F312/F361/F364/F367 等，输出见第三节），全部复现；对 r2 的 MR1（F340 降级）独立验证后**支持降级**。

---

## 二、漏报（新 findings，F371-F381）

### F371 | cmd_resume 的 phase 转换基于 checkpoint_history[-1] 且事件永不消费：auto 模式崩溃恢复把全书游标重置回第 1 章 | error | P1（P0 边界）

- 证据：
  - `src/shenbi/pipeline/cli.py:798-812` — resume 时无条件检查 `checkpoint_history[-1]`：`decision == "approve"` 且 `type == genesis-complete` → `transition_genesis_to_chapter_loop(state)`；`:808-833` volume-boundary 分支同理（重派 snapshot-manage + 可能的 `transition_chapter_to_closure`）。**该历史条目在任何路径上都不会被标记为"已消费"**——只要没有新的 checkpoint 被解决，`history[-1]` 永远保持不变。
  - `src/shenbi/pipeline/transitions.py:26-41` — `transition_genesis_to_chapter_loop` 无相位守卫、非幂等：无条件 `current_chapter = 1; step_index = 0`。
  - `src/shenbi/pipeline/cli.py:471-477` — `--auto` 只关闭 per-chapter/chapter-memo/state-settle 评审；`genesis_review_required` 与 `volume_boundary_review_required` 保持 True → auto 模式在卷一边界前**不产生任何会被解决的 checkpoint**，history[-1] 长期停留在 `{genesis-complete, approve}`。真实项目（auto 模式）佐证：56 章仅 2 条 history（genesis-complete + ch35 escalation）。
  - `cli.py:841` 的 `is_at_checkpoint` BLOCKED 守卫在 history 分支**之后**：无 pending checkpoint 时（崩溃现场正是如此），转换结果经 `cli.py:852 save_state` **持久化**。
- 控制流后果（"代码假设 resume 紧跟 review、但磁盘状态可以滞后任意章"的典型缺口）：
  - **auto 模式**：卷一（ch1-15，真实节奏约 10+ 小时生成量）内任何崩溃 → `pipeline resume` → current_chapter=N 重置为 1、step_index=0 → 从 step-1 重新派发 planning/drafting/审计波 → **ch1..N 全部静默重生成并覆盖章节文件**（正常流程无差分快照保护，F351；pre-rev 备份仅存在于修订路径）→ 原稿不可恢复。
  - **交互模式**：窗口收窄到第 1 章 step-1/2（首个 chapter-memo checkpoint raise 之前）；checkpoint 已 pending 时 BLOCKED 返回不落盘（`cli.py:849` 先于 852 的 save），内存变异被丢弃。
  - **volume-boundary 分支重放**：history[-1]={volume-boundary,approve} 存续期间（auto 模式=直到下一边界；交互模式=直到下一 checkpoint 解决），每次冗余 resume 都会**在 BLOCKED 守卫之前**重派 `shenbi-snapshot-manage` LLM 调用（`cli.py:819-823`）+ 重跑 `_update_total_chapters`，产出不经任何 checkpoint。
- 验证命令+输出（已验证，实跑）：
  ```
  构造 phase=chapter-loop / current_chapter=5 / step_index=7 / history[-1]={genesis-complete,approve}，
  按 cmd_resume:798-807 原样执行分支：
  AFTER re-fired transition (no phase/current_chapter guard in the branch):
    phase            = chapter-loop
    current_chapter  = 1  (was 5)
    step_index       = 0  (was 7)
  ```
- 根因：转换触发条件用"最后一条已解决决策"这一**持久累积**状态充当**一次性事件**，且转换函数本身非幂等、无相位合法性检查（transitions.py 五个转换函数全部无 from-phase 断言）。
- 影响面：所有 auto 模式项目的崩溃恢复路径；交互模式第 1 章；所有冗余 resume 的 snapshot-manage 重派。
- 建议方向：history 条目加 `consumed_at`/`transitioned` 标记（resume 消费后置位），或转换函数加幂等守卫（`phase is GENESIS` 才执行 genesis→chapter_loop；`current_chapter` 只在 0/None 时置 1）；volume-boundary 分支移到 `is_at_checkpoint` 守卫之后。
- 置信度：high

### F372 | `_parse_resonance_score` 三模式与技能自产报告格式零匹配：串行路径即使接线也解析不出分数，共鸣体系在生产从未产出过一个分数 | error | P1

- 证据：
  - `src/shenbi/pipeline/chapter_loop.py:1313-1349` — 三个解析模式：YAML frontmatter `resonance_score:`、`**Resonance Score**: N`、`(?:Score|resonance_score)\s*:\s*(\d+)`。
  - `skills/shenbi-review-resonance/SKILL.md:133` — 技能自己规定的报告头格式：`**章节**: 第N章 | **计划角色**: 高潮 | **结果**: 通过 (82/100) / 阻断 (XX/100) / 待人机复核`。真实报告（audits/chapter-30-resonance.md）即此格式，无 frontmatter、无 "Score:" 字面量。
  - 真实数据实跑（已验证）：
    ```
    n resonance reports: 55 ; parsed None count: 55 / 55 ; value distribution: Counter({None: 55})
    真实 pipeline-state.json：56/56 章 resonance_score = None
    ```
- 根因：解析器假设的数据形状与技能规范/实际输出三方漂移（角度 b 教科书案例）。附注三方不一致全貌：技能规范 §154 还规定了 resonance_trend 的**bullet 格式**（`- 第 N 章 情感落地 22 | ...`），而 escalation_bridge 解析器与 `_upsert_markdown_table_row` 消费的是 `|` 表格行——真实文件里 LLM 实际产出的是表格行（唯一侥幸对上解析器的一方）。
- 影响面：
  - F304（floor 失效）的**第二独立根因**：仅修 F304 的接线（并行波后解析）不解决问题，解析恒 None → `check_resonance(None)=True` 恒过。
  - `cmd_chapters` 全书 resonance_score: null；`_get_recent_resonance_scores`（soft-fail 升级链输入，chapter_loop.py:1481-1494）恒空 → `detect_score_decline`（需 5 样本）永不触发 → **soft-fail 升级链的共振维度整体饿死**。
  - 串行分支的 resonance_trend 写入（3046-3058）因 `overall is None` 被跳过——趋势文件唯一幸存数据来自技能自身 append_dedup 更新，受 F360 整覆污染（实测只剩 ch55 一行）。
- 建议方向：解析模式补 `**结果**:\s*(?:通过|阻断|待人机复核)?\s*\((\d+)/100\)` 中文形态；或让技能契约同时产出机器可读 frontmatter；补"真实报告样本 → 解析非 None"的回归测试（fixture 可用 xinghuo-ranqiong 真实报告，符合 G0.9）。
- 置信度：high

### F373 | pending_hooks/book_spine 消费者假设 YAML hooks:/hook_master_list 形状，生产实文为"元数据 frontmatter + markdown 表格"：钩子消费链在真实项目全数返回空，且 state 过滤词表含非规范值 | error | P2

- 证据（真实数据实跑，已验证）：
  ```
  真实 truth/pending_hooks.md（6106 字符，filled_by: shenbi-foreshadowing-track）：
  frontmatter 无 hooks: 键；钩子在 body 表格（| P0-4 (quiet阈结构) | RELEVANT→TRIGGERED… |）
  _read_pending_hooks(real)          -> 0 hooks
  _read_spine_master_hooks(real)     -> 0 MH hooks   （book_spine.md 无 hook_master_list frontmatter、无 | MH 行）
  _extract_hook_deliverables(real,56)-> 0 deliverables
  _count_triggered_hooks(real text)  -> 0            （frontmatter 失败后 fallback 找字面量 "state: TRIGGERED"，实际 0 处）
  ```
  - 消费方代码：`context_curation.py:361-384`（_read_pending_hooks 只认 frontmatter hooks:）、`:387-435`（_read_spine_master_hooks 只认 hook_master_list/`| MH` 行）；`review_checklist.py:315-375`（_extract_hook_deliverables 同源解析）；`chapter_loop.py:1284-1310`（_count_triggered_hooks）。
  - 附加词表缺陷：`review_checklist.py:357` 过滤 `state in ("PLANTED","ACTIVE","PENDING")`——HookState 规范值（contracts/schemas/hooks.py:19-27）为 PLANTED/RELEVANT/TRIGGERED/RESOLVED/ARCHIVED/EXPIRED：**ACTIVE/PENDING 非规范值，主力状态 RELEVANT 被排除**。即使形状修好，过滤仍漏掉大部分活跃钩。
  - 对照设计：`truth_index.py:167-218` 对同一文件做了 frontmatter+body 双源索引（注释自认 "the production state"）——同一格式漂移，truth_index 预设了兜底，其余四个消费者没有。
- 影响面：(1) 注入每个 review 技能 prompt 的 checklist `hook_deliverables` 恒空（唯一活消费），审计对"本章应推进哪些钩"失明（部分被 F362 的 3000 字符截断注入缓解——5/6 审计仍能看到截断副本）；(2) curated 文档第 9 节 Hook 债务简报双层表恒"(无)"（叠加 F311 curated 死输出）；(3) 真实钩 ID 族是 `P0-*`，既不匹配 MH* 也不匹配 H* 前缀分层。
- 建议方向：钩数据源统一走 truth_index 的双源解析（或抽共享 parser）；state 过滤改用 HookState 规范值；分层前缀改配置。
- 置信度：high

### F374 | `_style_profile_is_stale` 自愈触发器在真实项目永久误触发：`confidence: low` 是诚实自评而非 bootstrap 标记，sample count 字段不存在 → 每章强制追加一次 style_learning 派发 | error | P2

- 证据（真实数据实跑，已验证）：
  ```
  _style_profile_is_stale(xinghuo-ranqiong) -> True   （56 章完成后的今日现状）
  真实 style/style_profile.md（6621B）第 5 行：**confidence**: low；全文无 sample…count 模式
  check_triggers → not r.style_learning and stale → 每章 log.warning + r.style_learning = True
  ```
  - 代码：`triggers.py:92-121` — 判定 `is_bootstrap and sample_count == 0`；bootstrap 标记包含 `"confidence: low" in text`（对任何诚实标注低置信的成品画像误报），sample_count 来自 `[Ss]ample.{0,20}count` 正则（真实格式无此字段 → 恒 0）。
- 影响面：每章一次冗余 style-learning LLM 派发（token 浪费约 +1/10 派发调用每章，处于 P1 阈值边缘；56 章项目 ≈ 50+ 次多余调用），同时使 get_trigger_steps 的去重设计（volume 边界抑制 periodic 条目）形同虚设。
- 建议方向：bootstrap 判定改为显式标记（frontmatter `generation_mode: seed_fingerprint` 且独立 sample_count 字段），或在 style-learning 成功后写 `bootstrap_complete: true` 终止条件。
- 置信度：high

### F375 | `check_genre_config_drift` 的 `warning|drift|fatigue`+冒号正则与技能自产 audit_drift 格式（`- [维度] 描述`）零匹配：genre-config 运行时更新触发器（spec §6.6）生产死 | error | P2

- 证据（真实数据实跑，已验证）：
  ```
  _WARNING_RE.findall(真实 truth/audit_drift.md) -> 0 matches（文件 386B，真实条目形如 “- [场景临场感] 0 感官词 = …”）
  check_genre_config_drift(real) -> False
  ```
  - `triggers.py:323-326` — `_WARNING_RE = (?:warning|drift|fatigue)\s*[:：]\s*(.+)`（英文关键词+冒号形态）。
  - `skills/shenbi-review-resonance/SKILL.md:150-152` — 技能规定的 audit_drift 条目格式：`- [维度] [短板描述] → 下章 PRE_WRITE_CHECK 防范建议`——**与正则结构上不可能匹配**（角度 b：与 F372 同族，解析器形状 vs 技能自产格式）。
- 影响面：`genre_config_update` 触发器（TriggerResult）永不置位 → TRIGGER_STEPS 尾部的 shenbi-genre-config 运行时更新分支死；`config.genre_config_update_on_drift` 配置死项。
- 建议方向：正则改为匹配 `- [维度]` bullet 形态并以"维度标签"为重复键计数；与技能格式规范同步。
- 置信度：high

### F376 | 语言学漂移链全链死线：baseline 生产者 `establish_baseline` 零调用者，step-6 读一个永远不存在的文件——真实项目 56 章 drift check 全部静默 no-op（连带 F307 不可达） | error | P2

- 证据：
  - `chapter_loop.py:2042-2047` — `_check_linguistic_drift` 读 `style/linguistic_baseline.json`，缺失即 `log.warning("no_linguistic_baseline")` + return None。
  - 该文件的唯一写者 `src/shenbi/skill_utils/drift_detection/baseline.py:24,77-78`（`establish_baseline`）**生产零调用**（grep 全仓仅定义 + `__init__.py` 再导出；测试直调）。
  - 另一同名不同路径的实现：`linguistic_drift.py:278` 读/自建 `context/linguistic_baseline.json`（目录都不同）。
  - 真实项目：`ls style/` → 仅 style_profile.md，**无 linguistic_baseline.json** → 56 章的 step-6 全部走 warning + no-op。
- 影响面：CHAPTER_STEPS step-6（pipeline-linguistic-drift-check）为恒空操作；其下游 ESCALATE/HARD/WARN 三级干预（含 `_inject_drift_correction`）与 `DriftEscalationError`（F307 讨论的那个异常）**在生产根本不可能被抛出**——F307 的实际严重度因此低于表面；drift-guidance 条件族（F315/F349）的输入也从未存在。
- 建议方向：`_check_linguistic_drift` 内嵌 baseline 自建（复用 `_load_baseline` 的 early-chapters 逻辑），或把 establish_baseline 接到 step-6 首次执行。
- 置信度：high

### F377 | 触发器扇出/审计波/并行 post-draft 均无中途状态保存点：崩溃后整段重放（含 revision_count 重复累加窗口） | error | P2

- 证据（静态控制流，三方核对）：
  - 触发器扇出：`cli.py:212-276` — trigger block 在 `step_index==0` 时一次性执行 `run_triggered_skills`（内部顺序派发最多 17 个技能，triggers.py:532-601，无逐技能进度记账；`_update_total_chapters` 在序列**尾部** 602-604）；state 仅在 checkpoint raise（cli:248/269）或随后首个 chapter step 完成后（cli:276）保存。崩溃于序列中段 → resume 时 `step_index` 仍为 0 → **整个扇出从头重放**，已派发技能的 truth 产物被重写（append_dedup 语义下即 F360 整覆）。
  - 审计波：`chapter_loop.py:2541-2656` — 波为单"步"，期间无保存；崩溃于波内 → 重入后 6+12 个审计重新派发（token 浪费），且 `_route_revision_after_resonance`（2647）重跑 → `cs.revision_count += 1`（1913-1914）**对同一章重复累加**（state_heal 只取 max，不会纠正回 1）。
  - 并行 post-draft（2664-2746）同构：崩溃于两派发之间 → 双技能重放。
- 根因：检查点粒度全部落在"步"边界，而"步"的内部成本是数个 LLM 调用；恢复语义为 at-least-once 但写路径不具备幂等性（F360）。
- 建议方向：run_triggered_skills 每技能后 save_state（或至少记录 trigger 进度游标）；波重入前检测 `audits/chapter-N-review-summary.md` 已存在则跳过。
- 置信度：high（控制流确定；重放成本估算为静态推演）

### F378 | `_validate_state_consistency` / `_audit_context_coverage` 死线且注释谎称已接线：step_index 越界钳制从未在生产运行 | deps | P2

- 证据：
  - `state.py:469` — pyright-ignore 注释 `-- called from cli.py on resume`；grep 全仓：**src/ 零调用**（仅 tests/pipeline/test_state_machine_heal.py 直调）。
  - `chapter_loop.py:2136` — docstring "Called at pipeline resume initialization to surface the 77% coverage gap"；grep：src/ 零调用（仅 tests/unit/pipeline/test_context_audit.py）。
  - `cmd_resume`（cli.py:747-858）实际只做 heal_state_counters + EMERGENCY current_step 修复，无 step_index 钳制。
- 影响面：(1) `step_index > len(CHAPTER_STEPS)` 永不钳制——步骤表从 20 步缩到 16 步后（真实项目即 20 步时代产物），旧项目带着 step_index 17-19 resume 时 `run_chapter_step` 在 2484 直接 return True（"all consumed"）→ `_complete_chapter` 不会被调 → **current_chapter 停滞、每次 next 空转 OK 的死锁**（该 heal 正是为此设计却从未接线）；(2) 上下文覆盖率缺口（spec §3.1 的 77% gap 观测）无生产可见性。
- 建议方向：cmd_resume 在 heal_state_counters 旁实际调用两者；或删除并修正注释。
- 置信度：high

### F379 | genesis 批准后误用 `next`（而非 `resume`）= 静默 OK 空转死胡同：phase 永留 genesis | error | M

- 证据（实跑，已验证）：
  ```
  构造 review-approve 后状态（genesis.current_step=17、state=CHECKPOINT_PENDING、phase=GENESIS）：
  run_genesis_step returns: True ; phase still: genesis | genesis.state: checkpoint-pending
  => cmd_next emits OK with phase=genesis；无转换发生；每次 next 均为 no-op，直到调用 resume
  ```
  - `genesis.py:295-297`（游标耗尽即 return True）+ `cli.py:202-210`（phase GENESIS 分支对 True 直接 return）+ `_emit_orchestration_result` 输出 OK。转换只存在于 cmd_resume（F371 的分支）。
- 影响面：用户把 next 当"继续"使用（review 后的自然直觉）时得到 status OK 的成功假象，流水线实际卡死；无任何 BLOCKED/ERROR 提示。
- 建议方向：genesis 分支检测 `genesis.state == CHECKPOINT_PENDING and checkpoint 已清` 时 emit BLOCKED + "run resume" 提示。
- 置信度：high

### F380 | volume-boundary 触发后的 C1 守卫 `cl.step_index = 1` 跳过新章 step-1：pipeline-volume-align 永不执行也不记 steps_done | error | M

- 证据：`cli.py:246-249` 与 `:267-270` — trigger checkpoint raise 后 `cl.step_index = 1  # C1: prevent re-fire`。CHAPTER_STEPS[0] 是 step-1（pipeline-volume-align，chapter_loop.py:135-141）；step_index=1 使下一 `run_chapter_step` 直接执行 CHAPTER_STEPS[1]（chapter-planning）→ 新卷首章的 steps_done 恒少 1 条（15/16）。设计意图是防 trigger block 重入（要求 step_index==0），实现顺带跳过了 step-1。与 F314（volume-align 本身是死模块）叠加后实际影响仅为 steps_done 记账失真（影响 `_maybe_materialize_progress` 的计数语义与 G7 审计视角），故 M。
- 置信度：high

### F381 | `_check_volume_completion` 对未知卷界返回 True（默认吞掉未知状态）：volume_objective_missed 升级信号在 volume_map 缺失/不可解析时永不触发 | error | M

- 证据：`chapter_loop.py:983-992` — `current_volume is None → return True`（"volume objective met"）；`skill_utils/escalation/check.py:86-91` — `not volume_objective_met` 才产生信号。数据不可得被静默解释为"已达成"（fail-open 方向）。仅作用于 `_check_soft_fail_escalation` 输入（该链本已被 F372 的空分数饿死）。建议 None 时跳过该信号并 WARN。
- 置信度：high

---

## 三、误报/事实修正（对初审 + r1 + r2 全部 70 条的复读结论）

**总判定：无整条误报。** 逐条复读 F301-F370 的代码事实（全部 34 文件重读），字面证据均成立。以下为抽验记录（有实跑声称的优先）与事实修正。

### 3.1 实跑复现记录（独立重跑，全部通过）

| 条目 | 复现命令要点 | 结果 |
|---|---|---|
| F303/F341 | `_get_audit_history(真实 state, 56)` | **0 entries**；`_should_skip_audit('dialogue', h)=False` —— 真实数据确认 audit_results 键族（blocking_found:bool/audit_reports:list/revision_route:str）无 dict 形状 |
| F302 | `hasattr(state,'chapter')` | **False** |
| F308 | `'a<b'.replace('<','\u003c')=='a<b'` | **True**（恒等替换） |
| F306 | 临时目录 chapter-3.md → create_differential_snapshot | `ring_buffer_full=True` 但 full-content files=**[]** |
| F311 | 临时目录（assembled context 存在路径） | P1 contains plan=**False**、P1 shows 未产出=**True**、plan lands in P7=**True**（注：minimal fallback 路径的 P1 是正确的——初审未区分，影响面描述略宽但结论成立） |
| F312 | `build_shared_audit_context(真实项目, 30)` | chapter_text len=**0**（ch30 磁盘存在）、volume_context len=**0** |
| F361 | 45K 文件两路径 | len=32000、截断标记=**False**（两路径均无标记） |
| F364 | `_build_skill_prompt(group-factual,…)`（临时目录补做） | output_paths=continuity/world-rules/pacing（记录名 group-* 为幽灵，r2 结论复现） |
| F367 | 17 步 + 重做 append | len=**18** vs 17 |
| F366 | 静态重推导 | 物化调用点 {2,4,8,16}（计数）均非 5 倍数；5/15 落在 pipeline- 分支（2769 提前 return）、10 被波 +6 跳过 —— r2 结论成立 |

### 3.2 事实修正/补强（不改编号，供裁决参考）

1. **F318（atexit 清 staging）——触发面事实修正 + 升级建议见第四节**。初审/r1 将其表述为"紧急清理可丢弃 staged 输出"；实跑证明（实验 3，输出原文）：
   ```
   模拟 cmd_next 正常退出（无信号、无崩溃，atexit._run_exitfuncs()）：
   current_step after normal exit : EMERGENCY_SHUTDOWN_AT_shenbi-chapter-drafting
   pending checkpoint type        : state-settle
   staging/truth still exists?    : False
   ```
   atexit 钩子在**每次正常进程退出**都执行 `_emergency_cleanup` → 重新保存带 EMERGENCY 标记的 state + 清 staging。交互模式下（staging→checkpoint→人工 review→approve→commit 的设计主路径），**每个 chapter-memo/state-settle checkpoint 的 staged 产物在评审前即被销毁**，`_commit_staging_for_checkpoint`（cli.py:369-374）吞掉 FileNotFoundError → approve"成功"但什么都没提交。auto 模式（真实项目用法）因进程内 auto-commit 不受影响——这解释了为何真实项目 plans/ 完好。
2. **F360（append_dedup 整覆）——生产实证补强**：真实 `truth/resonance_trend.md` 56 章后**只剩 1 行**（ch55，9 列富格式行，即技能自产格式而非 `_build_resonance_trend_row` 的 7 列占位格式）——每章的 updates 整文件覆写只留最后一章的行，P0 定级获得直接生产证据。
3. **F304——根因补全**：F372 是第二条独立根因（解析器与技能格式零匹配）。修复方案必须同时 (a) 接线并行波解析（F304）(b) 修解析模式（F372），缺一仍恒 None。
4. **F307——影响面收缩**：F376 证明 `style/linguistic_baseline.json` 的生产者为零调用，`DriftEscalationError` 在生产不可能抛出 → F307 的 except-Exception 吞异常是"不可达路径上的缺陷"，修复优先级应低于 F376（先接线 baseline 生产者）。
5. **F340（r1 头号新发现，r2 MR1 降级）——独立验证支持降级**：本轮 `_build_skill_prompt("shenbi-review-group-factual")` 输出 paths=['chapter-5-continuity.md','chapter-5-world-rules.md','chapter-5-pacing.md'] ⊂ 13 名词表；r2 的 MR1 反驳成立，F340 应按 r2 处置降 P2 并并入 F369 窄核。
6. **F339（_shared 双读）维持**：`_resolve_volume_at_runtime` 先 `read_volume_boundaries`（内部已读全文）再 `read_text` 一次（_shared.py:176-180），复审属实。
7. 其余条目（F301/F305/F309/F310/F313-F337/F342-F359/F362-F365/F368-F370）逐行复读代码事实全部成立；静态条目（F313/F314/F315/F316/F319/F321/F322/F325/F345/F346/F349/F350/F351 等）的调用图结论本轮 grep 复核一致。

---

## 四、严重度异议（无权改定级，仅提异议）

| 编号 | 现级 | 意见 | 依据 |
|---|---|---|---|
| F318 | P2 | **升 P1** | 实验证明触发条件是"每次正常退出"而非"紧急"（3.2-1）：交互模式（默认模式）下每个 checkpoint 的 staged 产物确定性地丢失且 approve 静默无效——"正常路径功能错误 + 静默数据丢失"，符合 P1；auto 模式不受影响是唯一减罪 |
| F307 | P1 | **降 P2**（或挂起至 F376 修复后） | F376：baseline 生产者零调用 → 异常生产不可达；缺陷真实但当前无触发面 |
| F304 | P1 | 维持 P1，修复范围扩大 | F372 第二根因；真实 56 章 0 个分数 |
| F360 | P0 | 维持 P0 | 生产实证：resonance_trend 56 章→1 行 |
| F369 | P2 | 维持 P2（附事实注记） | 真实 genre-config 的 auditDimensions 未激活 era/fanfic/highpoint（实测 keys：antiAi/character/motivation/pacing/continuity/foreshadowing/sensitivity/worldRules/dialogue/texture）→ 当前生产触发面为零，但条件成立时机制缺陷仍在 |
| F371（本轮新） | — | **P1，P0 边界** | auto 模式卷一内崩溃+resume → 全书静默重生成覆盖、原稿无备份（不可恢复）；因需要"崩溃 + auto 模式 + 卷一窗口"三条件叠加取 P1，供裁决 |
| F338/F316/F314/F315 | P2/M | 维持 | 复读确认 |

---

## 五、覆盖空洞（三轮 + 初审共同的方法缺口）

1. **checkpoint/决策事件的"消费语义"从未被审计**：三轮都把 checkpoint_history 当静态数据核对形状（r1 §5.2），从未问"这个事件被消费了吗/会重放吗"。F371（本轮最重）正是事件重放缺陷。建议后续对 `pending_re_dispatches`、`last_trigger_failure`、gate manifest 等一切"队列/历史"状态做同样的消费语义审查。
2. **真实生产数据从未用作审计基线**：初审与 r1/r2 全部基于代码 + 单元测试推演。本轮用 xinghuo-ranqiong（56 章、23.7MB、1226 文件）对照后一次命中 F372/F373/F374/F375/F376 五条 + F360/F304 的实证补强。建议：(a) 把真实项目的脱敏快照固化为 contract 测试 fixture（G0.9 允许真实产出）；(b) 建立"技能自产格式规范（SKILL.md 输出样例）vs 框架解析器"的对照测试——本轮五条中有三条（F372/F375 + F373 的规范值词表）是"解析器 vs 技能规范"漂移，一条命令可比对。
3. **进程级生命周期从未端到端验证**：atexit/信号路径（F318 补强、F374 相关）只有单测直调 `_emergency_cleanup`，从未有"注册→正常退出→观察磁盘"的进程级测试。建议补 subprocess 级 smoke。
4. **"注释/docstring 声称已接线"的反向核对缺失**：r1 做了零调用者 grep（F316/F343 等），但没有对注释中"called from X"的声明做反向验证（F378 的 `_validate_state_consistency` 注释谎称 cli 调用）。建议 grep 所有 `pyright: ignore[reportUnusedFunction]` + "called from"注释逐条核对。
5. **转换函数的相位合法性**：transitions.py 五个转换全部无 from-phase 断言（本轮确证），三轮均未提出"转换表应有守卫"的系统性建议（spec §3.1 有状态转换表但代码不 enforcement）。
6. **状态文件的旧格式兼容**：真实 state 缺 `retry_budget_consumed` 键（from_dict 默认 {}）、novel.json `total_chapters: null`（read_total_chapters→0 触发 mid-book heal 重写为 100）、20 步时代 steps_done——旧格式 resume 兼容只靠偶然兜底（F378 的钳制本应为此存在）。

---

## 六、收敛判定意见（对照标准）

- 本轮：**新增 11 条**（P1×2、P2×6、M×3），**无误报推翻**，1 条严重度升级异议（F318 P2→P1）、1 条降级异议（F307 P1→P2）。
- **硬收敛（连续 2 轮 0 新）：未达成** —— 本轮 11 条新发现。
- **软收敛（连续 3 轮无新 P0/P1 且每轮 ≤3 条）：未达成** —— r2 有新 P0（F360），本轮有新 P1×2（F371/F372）且条数 11 > 3。
- 判定：**未收敛**。但需说明结构：本轮新 P1 全部来自两个前三轮未使用的方法（事件消费语义、真实数据形态对照），其中数据形态对照的产出密度最高且可一次固化（fixture 化后该维度将快速枯竭）。建议第 4 轮以 (i) pending_re_dispatches/gate-manifest/trigger 队列的消费语义 + (ii) 真实数据 fixture 化后的回归核对为主轴；若连续两轮仅余 M/P2 且 ≤3 条，可判软收敛。
