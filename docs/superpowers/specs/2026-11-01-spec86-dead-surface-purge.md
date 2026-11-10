# Spec #86 · 死面清扫批（dead-surface-purge）：纯删除零引用面，为 god 文件拆分减重

**日期**：2026-11-01（r2 修订 2026-11-02：trace 两模块改判删除/调用点与测试影响钉死；**r2.2 2026-11-02 全量对抗式审计修订**——类名/字段数更正、死函数测试占用补列、executor_config 改按键删除、replay 删除理由重写、scr_extractor 文件级验收；**r3 2026-11-10 驳斥复核修订**——r2.2 连带清单系统性缺口补齐：T1 补缓存测试整删+mock 点+step-6 裁定；T2 STATIC/DYNAMIC_FIELDS 活面误判改判死常量；T3 补 3 孤儿 helper+5 测试文件+lint_key_reconciliation 两锚+truth-files 注释；T4 补 4 测试文件+判据补盲；T5 补 tests/support 新建+审计文档失实行；行号全面 re-anchor 至 2026-11-10 树）｜ **系列**：架构复审批次 A（**#87 前置**）｜ **状态**：Design（r3.5，Revised 2026-11-10——r3.5 随 plan 审查轮 1 补 T6 两钉死测试连带，验收 4 计数 18） ｜ **优先级**：🟠 P1
**动机证据**：architecture-review-20261101 #14 卡；本节每项消费者 grep 由协调者复跑（2026-11-02），r2.2 审计逐项对码；r3 驳斥复核（fresh-context 子 agent＋协调者亲核，2026-11-10 main HEAD e585485a）10/10 死面主张存活；**r3.1 2026-11-10 第二轮驳斥修正**——test_triggers:233 改判不删（测活函数）/spec83 canary 13→12 同步/lint_truth_format 白名单承诺锚补列/writer.py:6 docstring 补列；**r3.2 2026-11-10 设计审查轮 1 修订**——T4 补 concurrency:268-274 守卫测试删（验收 1 自相矛盾消除）/T5 补 pyproject per-file-ignores 键迁移+support/__init__+import 改写显式/T3 补 regen_reset+truth-files:104 producer 裁定/T1 语义三钉（窗口排他/Exception 保持/extract_prose 内联）/T9 生成物同步新增/_FINGERPRINT_CACHE 锚修正/registry docstring 计数更正/验收 1 补 T5/T6 判据+验收 2 上修 ~899+/验收 4 计数修正；**r3.3 2026-11-10 设计审查轮 2 修订**——regen_reset 显式三处（补 :228 调用行——悬空 NameError 无测试兜底的半死残径）/producer 裁定改保留 pipeline+注释历史化（否决 external=常驻 R2 WARN/shared=语义失实）/T5 判据改存在性断言/T4 判据加 --exclude-dir=coverage 防假红/T2/T3 补显式 grep 判据/验收 4 计数补 T2=16/spec79 plan:12 注记/锚点微修（registry docstring :9/__all__ :658-682/_clear_snapshots_key :149/steps_restructured:76 间接驱动）

**触及的不变量维度**：无（纯删除零引用面；唯一行为触点=scr_extractor 缩编保留其被消费的 location WARN）

---

## 0. 根因

本仓 v7 rubric 的双向 dead-wire 检查（「实现但零接线=Important」）在自身仓库最密集的违例带：~800 行「看似活着的机制」。每项独立无害，合计是读者与 #87 拆分搬运的持续税。

## 1. 清扫清单（r2.2 逐项亲核；r3 行号 re-anchor 至 2026-11-10 树 + 连带清单补齐）

### T1 · scr_extractor 缩编（:69-437）
**亲核事实（r2.2 更名）**：类名是 `StructuredChapterRepresentation`（:22），**`ScrReport` 在本仓不存在**；数据字段 17 个（除 `chapter`/`extracted_at`），除 `world_refs` 外 **16 个死字段**。两个生产调用点（r3 re-anchor）：`_run_post_draft_extract`（chapter_loop.py:2177，函数体=纯预热——extract_scr 返回值丢弃+吞异常）在 **:4492** 被调用（step-5 scene-split 尾部 bundle 循环，R4-I2 rehang）与 world freshness 块 **:2270-2282**（仅读 `world_refs` 且只取 `category=="location"`，**per-chapter try/continue 容错**）。`_scan_fatigue_words`（**:365**）与 gates/shared 疲劳词概念三套词表重复——**随本 task 删除**（#85 不承接词表；疲劳词表归并另议，不属 #85 域）。
**处置**：替换为单函数 `recent_location_terms(project_dir, chapter, lookback=10) -> set[str]`（~20 行，无缓存——每章一次；**语义钉死（r3.2）**：①窗口排他——`range(max(1, chapter-lookback), chapter)` **不含当前章**，与现消费面逐字同形；②per-chapter `except Exception: continue` 逐字保持——不得窄化为 FileNotFoundError；③`extract_prose`（:56，公共、test_scr_extractor.py:31-36/:132-135 独立测）**内联进替换函数**（单函数模块预算 ≤60 行下不留第二公共面，其 META/标题头剥离逻辑吸收、独立测随删））；删 16 死字段、缓存写、`_scan_fatigue_words`、`_run_post_draft_extract` 整函数及其 :4492 调用行（缓存存在的唯一理由消失）。
**连带（r3 补齐）**：
- `tests/pipeline/test_scr_extractor.py` 进口 6 个非 extract_scr 符号（5 个下划线私有抽取器+待内联的 `extract_prose`，r3.4 措辞正）——随删除重写为单函数测试（保留 location 抽取断言、删除 16 字段断言）；
- **`tests/pipeline/test_scr_cache_invalidation.py` 整文件删**（r3 发现：4 个测试专测 SCR 缓存 `_cache_key`/context/chapter-N-scr.json——缓存删除后失去对象）；
- **`tests/pipeline/test_bundle_stepping.py:322`**（r3 发现：`mp.setattr(cl, "_run_post_draft_extract", ...)` mock 点——函数删除后 AttributeError，同批改写）；
- **step-6 条目（`pipeline-post-draft-extract`，CHAPTER_STEPS:209-210）裁定：保留为 pass-through**——该 step 今日即无专属 handler（四项 post-draft 检查已 rehang 于 step-5 尾部 R4-I2），删条目=reorder 级变更，牵 `PIPELINE_STEPS_VERSION`（:308=3）bump+迁移映射+`tests/pipeline/test_resume_anchor.py:96-97` 快照 pin——超「纯删除零引用」边界；登记为已知 no-op step，归 **#87** CHAPTER_STEPS 重构域处置（此处为纯提及非依赖）。
**判据（r3.3 补显式）**：`grep -rn "StructuredChapterRepresentation\|extract_scr" src/ tools/ tests/ | grep -v scr_extractor.py` 零输出；**文件级验收：scr_extractor.py ≤60 行**（只靠总行数会让「缩编」变成「保留大半」）。
**备选（本批不选）**：world freshness WARN 保留——它是本文件唯一活行为触点（header 已声明）；整删模块属产品判断，另议。

### T2 · review_checklist 死半边（**:572-655** + `__all__`:658-682）
**亲核（r2.2 修正；r3 再改判）**：8 个死函数（现树 **:572/:584/:594/:611/:634/:643/:647/:651**——`generate_static_template`/`generate_chapter_delta`/`get_checklist`/`_extract_hooks_from_plan`/`_load_blacklist`/`_load_voice_constraints`/`_load_pov_mode`/`_load_world_rules_brief`），其中 **`generate_chapter_delta`/`get_checklist` 被 `tests/pipeline/test_review_checklist.py:6-7,38,44,55` 使用**——删除必须同批改写/删除这些测试（r2 称「逐名 grep 外部引用 0」系只查 src）。
**r3 改判（推翻 r2.2「活导出」认定）**：`STATIC_FIELDS`(:551)/`DYNAMIC_FIELDS`(:559) 实为**零消费死常量**——文件内零自用（仅定义+`__all__`:659/:661 导出），文件外 src/tools/tests 也零消费者（r3 驳斥复核逐面 grep 实锤）→ **加入删除面**。保留面=`ReviewChecklist`/`ENDING_PATTERNS`/`generate_review_checklist`/`inject_checklist_into_prompt`（生产消费者 dispatch_helper.py:1580-1594）+ 其真私有依赖（`__all__` 14 个 `_` 名中 9 活：`_build_checklist`/`_extract_ai_blacklist`/`_extract_fatigue_warnings`/`_extract_hook_deliverables`/`_extract_voice_constraints`/`_get_max_source_mtime`/`_get_recent_ending_types`/`_load_genre_config`/`_summarize_world_rules`；5 死随死函数删）。
**处置**：删 8 死函数+`STATIC_FIELDS`/`DYNAMIC_FIELDS` 两死常量；`__all__` 收缩至真活面（公共 4 名+活私有 9 名的去留按 `__all__` 只留真公共面原则重审——活私有名是否留 `__all__` 由 plan 裁定，但死名必删）；**r3.1 补：`tools/lint_truth_format_single_source.py:57` NAMED_WHITELIST 条目 `review_checklist.py: hook_pattern` 随删（r3.4 连带补：:18-19 模块 docstring 两行「named whitelist: review_checklist.py's dead hook_pattern (removed with #86 T2…)」与条目同体，同批删）**——#85 r8 成文承诺锚（「#86 落地时本白名单条目随之删除，防白名单永久化」）。
**死桩自相矛盾的证据留档**（plan 期写入 commit message）：`third_person_limited`/`multi_pov` 捏造、`truth/world_rules.md` 不存在（活半边读 `world/rules.md`）、`chapter-{ch:03d}` 零填充与全管线不一致、`sensitivity_flags: 0` int 冒充 list。
**判据（r3.3 补显式）**：`grep -rn "generate_static_template\|generate_chapter_delta\|get_checklist\|_extract_hooks_from_plan\|_load_blacklist\|_load_voice_constraints\|_load_pov_mode\|_load_world_rules_brief\|STATIC_FIELDS\|DYNAMIC_FIELDS" src/ tools/ tests/` 零输出（test_review_checklist.py 改写后）。

### T3 · chapter_loop 死分支 ×4（r3 re-anchor）+ 死 manifest + 孤儿 helper
**亲核（r3 re-anchor 至现树）**：死分支=①②`:3044-3048`（`shenbi-intent-management`/`shenbi-drift-guidance`——不在 CHAPTER_STEPS（:155-310 全 16 条目无此二 skill），注释 :142-143 自认）；③`:4810-4813`（foreshadowing-lifecycle serial 分支——源码 NOTE 自认 "unconditionally intercepted by the parallel post-draft block... stays unreachable in production"，:4295 拦截块 `if step_idx == _FORESHADOWING_LIFECYCLE_IDX:` 全出口 return）；④`:4909-4910`（drift-guidance manifest 更新——不可达，见 manifest 链）。
**manifest 三函数（r3 re-anchor）**：`_load_manifest` :2924/`_save_manifest` :2937 仅服务 `_update_last_drift_manifest` :2960（唯一调用 :4910 死分支④内）；中间 `:2944 _get_recent_resonance_scores` 是**活函数**（:2561 调用）——按段删，禁止整段区间。
**r3 补：3 孤儿 helper 随分支同删**（唯一生产调用点在死分支内）：`_check_conditional_resolve` :2814（唯一生产调用 :4813 死分支③内）、`_is_volume_boundary` :2967（唯一生产调用 :3045 死分支①②内）、`_drift_guidance_triggered` :2977（唯一生产调用 :3048 死分支①②内）。
**连带（r3 补齐；r3.1 修正——4 测试文件+2 lint+2 文档）**：
- `tests/unit/pipeline/test_chapter_loop.py:343-375,546-561`（`_check_conditional_resolve` 直测——删）；
- `tests/pipeline/test_chapter_steps_restructured.py:48,51,76`（`_is_volume_boundary` patch 两处+`:76` 经 `_should_run_step(state, step)` 间接驱动 `_drift_guidance_triggered`（r3.3 措辞正）——改写或删）；
- `tests/unit/pipeline/test_adaptive_triggers.py:47,52`（`_is_volume_boundary` patch 点——改写）；
- **r3.1 改判**：`tests/unit/pipeline/test_triggers.py:233`（`test_is_volume_boundary_direct`）**不删**——第二轮驳斥核实其测的是**活函数** `shenbi.pipeline.triggers.is_volume_boundary`（triggers.py:318，签名 `(chapter, project_dir)`，生产调用 chapter_loop.py:2257），非 chapter_loop 孤儿 wrapper（:2967，签名相反、委托 triggers 版）——删之=无红灯的静默覆盖损失；
- `tests/unit/pipeline/test_spec83_stale_declarations.py:87`（声明守卫 pin `("pipeline/chapter_loop.py", "_check_conditional_resolve")`——删该行）**+:105 canary `dispatch_skill` 调用点计数 `==13` 同步改 `==12`**（r3.1 补：`_check_conditional_resolve` 体内 :2832 占 13 处之一，删函数后计数变——canary「增减都红」）；
- **`tools/lint_key_reconciliation.py` 两 ReadKey 锚（现树 :135/:142：`chapterloop/drift-guidance`→`_drift_guidance_triggered`、`chapterloop/pending-hooks`→`_check_conditional_resolve`）同批删**——该 lint 是 just check 成员（justfile:33 --strict），不改则验收 3 必红（纯 registry 驱动无跨条目依赖，删条目自洽——第二轮亲核）；
- `docs/framework/truth-files.yaml:102` 注释指认 manifest.json drift marker 由 `_update_last_drift_manifest` 写——删后同批改写（防静默过期）；**r3.3 裁定：:104 条目 `{name: snapshots/manifest.json, kind: config, producer: pipeline}` 保留 producer 原值+注释历史化**（「写方已于 #86 删除；存量项目盘上文件遗留容忍，无新写入」——否决 external：lint_registry_reconcile:466 豁免仅 pipeline/shared，改 external 产生**常驻 R2 orphan WARN**（该名不在 truth-files.index.json，fnmatch 不可匹配 snapshots/chapter-NNN/）与反白名单永久化立场相悖；否决 shared：语义失实——注释承载真相、producer 值维持豁免零噪音）；
- **r3.2 补 / r3.3 显式三处**：`tools/regen_reset.py` ——**:149-156 `_clear_snapshots_key` 整函数**（docstring「Drop last_drift_chapter from snapshots/manifest.json」）+ **:228 调用行 `_clear_snapshots_key(project_dir)`**（r3.2 漏列——悬空调用 NameError 仅工具实跑时暴露、test_regen_reset 不触及该函数=无红灯兜底的半死残径）+ **:186 动作标签行 `clear snapshots/manifest.json last_drift_chapter`**——清理动作失去对象，三处同批删（该函数缺文件容忍语义已内建 early-return，删除后 regen-reset 对存量 manifest.json 仅少清一个不再产生的键，无破坏面）；
- **r3.3 补（轻微）**：`docs/superpowers/plans/2026-10-26-spec79-regen-acceptance.md:12` 活跃 plan 文档描述「`snapshots/manifest.json` 清 `last_drift_chapter` 键」——行为随本批消失，顺手加一行注记（plan 为历史执行文档，不重写仅注记）；
- **r3.1 补（轻微）**：`src/shenbi/records/writer.py:6` docstring「via chapter_loop._check_conditional_resolve」——删函数后同批改写。
**处置**：纯删（分支+manifest 三函数+3 孤儿 helper），连带面同批。
**判据（r3.3 补显式；r3.4 预期修正）**：`grep -n "shenbi-intent-management\|shenbi-drift-guidance\|_load_manifest\|_save_manifest\|_update_last_drift_manifest\|_check_conditional_resolve\|_drift_guidance_triggered" src/shenbi/pipeline/chapter_loop.py` **零输出**（:142-143 条件步注释写的是无前缀形 `(intent-management, drift-guidance, snapshot-manage)` 本就不命中，注释可保留）；`grep -n "_is_volume_boundary\|_clear_snapshots_key" src/shenbi/pipeline/chapter_loop.py tools/regen_reset.py` 零（孤儿 wrapper 与 regen_reset 面）。

### T4 · trace/materialize.py + trace/replay.py —— **删除**（r2 改判；r2.2 理由重写；r3 连带补齐）
**硬事实**：
- 零生产消费者（`src/` 仅 `trace/__init__.py:5-6` 重导出自身+`__all__`:21）；
- **r2.2 更正：`replay._verify` 与 `compaction.verify_chain` 不是重复实现**——前者逐事件签名比对（`sign(prev_sig,payload)`），后者只看 COMPACTION 事件的 `prev_compaction_seq` 单调/缺口；删除理由改为「**第二套 trace 读取器**，G7 走 compaction，replay 无职责」；
- 「trace 权威、progress 派生」哲学未被采纳：`dispatcher/modes/codex.py:40-62` 以直接变更写 progress；`crash_recovery.py` 已承担真实恢复职责（信号/急救快照）。
- **连带（r3 补齐：测试实为 6 文件，非 r2.2 的 2 个）**：①`tests/unit/trace/test_compaction.py:6` `from shenbi.trace.replay import replay`（:22/:44 当读取器用）改本地 helper；②`tests/property/trace/test_chain_invariants.py:10`（:22/:37 调用）同改；③**`tests/unit/trace/test_materialize.py` 整文件删**（专测 materialize_progress）；④**`tests/unit/trace/test_replay.py` 整文件删**（专测 replay）；⑤**`tests/unit/test_t4_scatter_guards.py:127`** `from shenbi.trace.materialize import _round_field`（F614 断言用——**改本地 helper 且必须换名（如 `round_field`，r3.4 补：沿用 `_round_field` 名会使验收 1 第二条 grep 非零自相矛盾），且该行不含 `materialize_progress`/`trace.replay` 字样，原 grep 判据对它漏网**）；⑥**`tests/unit/pipeline/test_concurrency_regression.py:134,:192`**（F630 materialize 行为测试+replay 消费——改写）**+:268-274 `test_periodic_materialize_removed` 守卫测试同批删（r3.2 补——其职责（断言 materialize 调用点不存在）被模块整删吸收；且 :274 字符串字面量 `"materialize_progress(Path(state.project_dir)"` 会使验收 1 的 grep 判据非零输出——不改则验收自相矛盾）**。文档引用 `docs/framework/status-vocab.md:20`、`docs/superpowers/full-project-audit-prompt.md:335` 同批改写。
- **处置**：删 `materialize.py`（163 行）+ `replay.py`（63 行）+ `trace/__init__` 导出 + 上述 6 测试文件改写/删除。**显式替代条款**：若用户视事件溯源为既定方向 → 保留两模块原状（不文档化），单独立项接线；两者不并存。

### T5 · capability_fs.py 移 tests 支撑（58 行）
**亲核**：文件在 `src/shenbi/capability_fs.py`（非 pipeline/）；唯一消费者 = `tests/unit/test_capability_fs.py` 与 `tests/property/gates/test_capability_fs_properties.py`；无门注入。
**处置**：迁 `tests/support/capability_fs.py`。**r3 补**：`tests/support/` 目录**现不存在须新建**（tests/ 含 `__init__.py` 是包，import 路径可行）；**r3.2 补三件**：①`tests/support/__init__.py` 显式新建（先例 tests/pipeline/helpers/__init__.py；绝对导入 `from tests.support.capability_fs import ...` 常规包语义需要它）②**两测试文件 import 行改写显式列入连带**（tests/unit/test_capability_fs.py 与 tests/property/gates/test_capability_fs_properties.py 的 `from shenbi.capability_fs import` → `from tests.support.capability_fs import`）③**`pyproject.toml:432` per-file-ignores 键 `"src/shenbi/capability_fs.py" = ["RUF001","RUF002","RUF003","RUF005","RUF059"]` 随迁改写为 `"tests/support/capability_fs.py"`**（`"tests/**"` 只豁免 BLE001/T201 不覆盖 RUF 族——中文 docstring 触发 RUF001-003 致 ruff 面红；旧键悬空指向不存在文件）。`docs/superpowers/full-project-audit-prompt.md:336` 把 capability_fs 列为 T12 安全审计对象——迁出 src 后该行同批改写（防失实）。**备选**（需用户裁定）：真接线（G4 纯判器入口注入只读句柄）另立 spec；本批不接线。

### T6 · executor_config.toml 死覆盖块（**按键删，6 块**）+ 死 kind
**亲核（r2.2 重钉）**：`DEPRECATED` 字样在 executor_config.toml **零命中**（r2 的判据线索「SKILL.md 含横幅」在 6 个技能里确实各 1 条，但配置侧无标记，不能作判据）；权威判据=`shenbi.skill_utils.deprecated.deprecated_skill_names(skills)`——当前 15 个 deprecated，与 35 个 override 键交集**恰 6 个**：`shenbi-review-continuity`、`shenbi-review-anti-ai`、`shenbi-review-memo-compliance`、`shenbi-review-world-rules`、`shenbi-review-pov`、`shenbi-review-dialogue`。
**处置（r2.2 关键修正）**：**按键删除这 6 块，禁止按行区间删**——r2 写的 `:120-191` 区间内还夹着 10 个**活**覆盖块（review-resonance:**128**、foreshadowing-lifecycle:132-138、score-arc/stratum/volume:145-156、review-arc-payoff:165-167、review-era/fanfic/sensitivity/spinoff:173-187），整段删会误杀生产配置。`lint_routing_faces` 禁路由 DEPRECATED → 覆盖块不可达。`registry.py` 的 `"short"` kind 实际在 **`contracts/schemas/registry.py:38`**（pydantic `RegistryKind` Literal，全 yaml 零使用；**r3.2 补 / r3.3 锚正**：`:9` 模块 docstring「16 kind values (the real yaml uses all 16)」计数失实——yaml 实用 15 种、删 short 后 Literal 恰 15，docstring 同批更正）。
**连带**：executor_config.toml 覆盖键仍无 lint 面（#90 不收此面——**v2 裁剪**：新增 `overrides ⊆ live skills` 面的成本高于收益；只登记为已知缺口）。

### T7 · 非死面（复核结论：不动）
`_FINGERPRINT_CACHE`（gates/g4/chapter_drafting.py:420，r3.2 锚修正）为文档化 stat-keyed memo，幂等保持——保留。`state.increment_retry/reset_retry` **不删**（#91 T4 改为接线）。

### T9 · 生成物同步（r3.2 补）
`tests/tiers/deps.json` 的 `_tool_hashes` 对全部 src 文件 sha256——本批 5 个 src 触面（scr_extractor/review_checklist/chapter_loop/capability_fs 迁出/trace 删除）hash 全变：plan 收尾必须 `just generate` 重生成+生成物入库（just check 的 `git diff --exit-code` 面要求已提交树态——锁→生成→commit→check 流序）。

### T8 · 交叉引用更正（r2.2）
r2 曾写「`_scan_fatigue_words` 同批并入 #85 词表单源或删」——**#85 无 fatigue/词表任务**（全文零命中），该引用凭空；本 spec 已改为「随 T1 删除，词表归并另议」。

## 2. 验收

1. 每 T 的 grep 判据零输出（T1 判据含 `StructuredChapterRepresentation`；T4 额外两条——r3 补盲：`grep -rn --exclude-dir=coverage "materialize_progress\|trace.replay" src/ tools/ tests/` 零（r3.3 补 --exclude-dir=coverage——tests/coverage/coverage.xml 未跟踪产物含旧 replay 条目且 `.` 通配 trace/replay，批后重跑测试前会假红）**且** `grep -rn --exclude-dir=coverage "from shenbi.trace.materialize\|from shenbi.trace.replay\|_round_field" src/ tools/ tests/` 零（私有导入行判据）；**r3.2 补 T5/T6 判据（r3.3 修 T5 鉴别力）**：`test ! -e src/shenbi/capability_fs.py`（原 grep 内容匹配形同虚设——src 内容本就不含该串，改存在性断言）+ `grep -n "shenbi-review-anti-ai\|shenbi-review-continuity\|shenbi-review-dialogue\|shenbi-review-memo-compliance\|shenbi-review-pov\|shenbi-review-world-rules" executor_config.toml` 零，文档引用同批改）；
2. src/ 净减 ≥650 行（r3 重核算：scr_extractor 493→≤60 减 ~433+、review_checklist 死函数+死常量 ~110、trace 226、capability 58、chapter_loop 分支+manifest+孤儿 helper ~79 = **~906**（阶段 3 复核；tools/regen_reset 三处为 tools/ 侧另计）；**前提是 scr_extractor ≤60 行**——单列文件级断言）且测试净减/改写记录入 plan；
3. `just check` exit 0（**前置（r3.2 汇总）**：lint_key_reconciliation 两锚+spec83 canary 13→12+lint_truth_format 白名单条目+pyproject per-file-ignores 键迁移——四处任一漏改必红或留悬空键，见各 T 连带）；
4. 无测试因删除被 skip（skip 计数不增）；**全部 18 个受影响测试文件改写后仍通过**（具名关键件：test_scr_extractor / test_compaction / test_chain_invariants / test_review_checklist / test_bundle_stepping / test_t4_scatter_guards / test_concurrency_regression / test_executor_config / test_registry；r3.5 修正计数：T1 三+T2 一+T3 四+T4 六+T5 两+**T6 两（plan 审查轮 1 补：test_executor_config discriminative 列表钉死 4 死键+test_registry kinds 钉死 short）**=18）。
