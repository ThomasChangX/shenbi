# Spec #86 · 死面清扫批（dead-surface-purge）：纯删除零引用面，为 god 文件拆分减重

**日期**：2026-11-01（r2 修订 2026-11-02：trace 两模块改判删除/调用点与测试影响钉死；**r2.2 2026-11-02 全量对抗式审计修订**——类名/字段数更正、死函数测试占用补列、executor_config 改按键删除、replay 删除理由重写、scr_extractor 文件级验收）｜ **系列**：架构复审批次 A（**#87 前置**）｜ **状态**：Design（r2.2） ｜ **优先级**：🟠 P1
**动机证据**：architecture-review-20261101 #14 卡；本节每项消费者 grep 由协调者复跑（2026-11-02），r2.2 审计逐项对码

**触及的不变量维度**：无（纯删除零引用面；唯一行为触点=scr_extractor 缩编保留其被消费的 location WARN）

---

## 0. 根因

本仓 v7 rubric 的双向 dead-wire 检查（「实现但零接线=Important」）在自身仓库最密集的违例带：~800 行「看似活着的机制」。每项独立无害，合计是读者与 #87 拆分搬运的持续税。

## 1. 清扫清单（r2.2：逐项已亲核，行号为 2026-11-02 当前树）

### T1 · scr_extractor 缩编（:69-437）
**亲核事实（r2.2 更名）**：类名是 `StructuredChapterRepresentation`（:22），**`ScrReport` 在本仓不存在**；数据字段 17 个（除 `chapter`/`extracted_at`），除 `world_refs` 外 **16 个死字段**。两个生产调用点：`chapter_loop.py:1984` 定义 `_run_post_draft_extract`、调用在 `:1993`（预热缓存，返回值丢弃）与 `:2083`（world freshness：仅读 `world_refs` 且只取 `category=="location"`）。`_scan_fatigue_words`（**:365**）与 gates/shared 疲劳词概念三套词表重复——**随本 task 删除**（#85 不承接词表；疲劳词表归并另议，不属 #85 域）。
**处置**：替换为单函数 `recent_location_terms(project_dir, chapter, lookback=10) -> set[str]`（~20 行，无缓存——每章一次）；删 16 死字段、缓存写、`_scan_fatigue_words`；`:1993` 预热点整删（缓存存在的唯一理由消失）。
**连带**：`tests/pipeline/test_scr_extractor.py` 进口 6 个私有抽取器——随删除重写为单函数测试（保留 location 抽取断言、删除 16 字段断言）；**r2.2 实测：无 tests 引用 `StructuredChapterRepresentation`**（原「tests/unit/test_* 同批清理」条无对象，删除；唯一字段读点是 chapter_loop.py:2084 的 `.world_refs`）。
**判据**：`grep -rn "StructuredChapterRepresentation\|extract_scr" src/ tools/ tests/ | grep -v scr_extractor.py` 零输出；**文件级验收：scr_extractor.py ≤60 行**（只靠总行数会让「缩编」变成「保留大半」）。
**备选（本批不选）**：world freshness WARN 保留——它是本文件唯一活行为触点（header 已声明）；整删模块属产品判断，另议。

### T2 · review_checklist 死半边（**:571-654** + `__all__`:657-681）
**亲核（r2.2 修正）**：`:546-568` 是**活**导出 `STATIC_FIELDS`(:550)/`DYNAMIC_FIELDS`(:558)，不在删除面；8 个死函数实际从 **:571** 起（571/583/593/610/633/642/646/650）。`generate_static_template`/`generate_chapter_delta`/`get_checklist`/`_load_blacklist`/`_load_voice_constraints`/`_load_pov_mode`/`_load_world_rules_brief`/`_extract_hooks_from_plan` 中，**`generate_chapter_delta`/`get_checklist` 被 `tests/pipeline/test_review_checklist.py:6-7,38,44,55` 使用**——删除必须同批改写/删除这些测试（r2 称「逐名 grep 外部引用 0」系只查 src）。
**处置**：删 8 个死函数（`:571-654`；逐个删，勿整段含 550/558）；`__all__` 只留真公共面（`ReviewChecklist`/`STATIC_FIELDS`/`DYNAMIC_FIELDS`/`ENDING_PATTERNS`/`generate_review_checklist`/`inject_checklist_into_prompt`）；私有名移出 `__all__`（**r2.2 计数：`__all__` 含 14 个 `_` 名=9 活+5 死**，非 r2 的 10=6+4）。
**死桩自相矛盾的证据留档**（plan 期写入 commit message）：`third_person_limited`/`multi_pov` 捏造、`truth/world_rules.md` 不存在（活半边读 `world/rules.md`）、`chapter-{ch:03d}` 零填充与全管线不一致、`sensitivity_flags: 0` int 冒充 list。

### T3 · chapter_loop 死分支 ×4（:2847-2851,:4690,:4593-4594）+ 死 manifest
**亲核**：`shenbi-intent-management`/`shenbi-drift-guidance` 不在 CHAPTER_STEPS（注释 :141-142 自认）；:4593 被 :4098 同指标拦截不可达；`_load_manifest`/`_save_manifest` 仅服务 `_update_last_drift_manifest`（自身仅 :4690 一处**不可达**调用）。
**处置**：纯删。**注意 manifest 三函数不连续**：`_load_manifest`/`_save_manifest` 在 :2727-2745、`_update_last_drift_manifest` 在 :2763-2769，中间 `:2747 _get_recent_resonance_scores` 是**活函数**（:2364 调用）——按两段删，禁止整段区间。

### T4 · trace/materialize.py + trace/replay.py —— **删除**（r2 改判；r2.2 理由重写）
**硬事实**：
- 零生产消费者（`src/` 仅 `trace/__init__.py:5-6` 重导出自身）；
- **r2.2 更正：`replay._verify` 与 `compaction.verify_chain` 不是重复实现**——前者逐事件签名比对（`sign(prev_sig,payload)`），后者只看 COMPACTION 事件的 `prev_compaction_seq` 单调/缺口；删除理由改为「**第二套 trace 读取器**，G7 走 compaction，replay 无职责」；
- 「trace 权威、progress 派生」哲学未被采纳：`dispatcher/modes/codex.py:40-62` 以直接变更写 progress；`crash_recovery.py` 已承担真实恢复职责（信号/急救快照）。
- **连带（r2.2 补）**：`tests/unit/trace/test_compaction.py:6` `from shenbi.trace.replay import replay`（:22/:44 当读取器用）**与** `tests/property/trace/test_chain_invariants.py:10`（:22/:37 调用）——删 replay.py 会破两处测试，必须同批改本地 helper；文档引用 `docs/framework/status-vocab.md:20`、`docs/superpowers/full-project-audit-prompt.md:335` 同批改写。
- **处置**：删 `materialize.py`（163 行）+ `replay.py`（63 行）+ `trace/__init__` 导出 + 上述测试改写。**显式替代条款**：若用户视事件溯源为既定方向 → 保留两模块原状（不文档化），单独立项接线；两者不并存。

### T5 · capability_fs.py 移 tests 支撑（58 行）
**亲核**：文件在 `src/shenbi/capability_fs.py`（非 pipeline/）；唯一消费者 = `tests/unit/test_capability_fs.py` 与 `tests/property/gates/test_capability_fs_properties.py`；无门注入。
**处置**：迁 `tests/support/capability_fs.py`（tests/conftest 旁）。**备选**（需用户裁定）：真接线（G4 纯判器入口注入只读句柄）另立 spec；本批不接线。

### T6 · executor_config.toml 死覆盖块（**按键删，6 块**）+ 死 kind
**亲核（r2.2 重钉）**：`DEPRECATED` 字样在 executor_config.toml **零命中**（r2 的判据线索「SKILL.md 含横幅」在 6 个技能里确实各 1 条，但配置侧无标记，不能作判据）；权威判据=`shenbi.skill_utils.deprecated.deprecated_skill_names(skills)`——当前 15 个 deprecated，与 35 个 override 键交集**恰 6 个**：`shenbi-review-continuity`、`shenbi-review-anti-ai`、`shenbi-review-memo-compliance`、`shenbi-review-world-rules`、`shenbi-review-pov`、`shenbi-review-dialogue`。
**处置（r2.2 关键修正）**：**按键删除这 6 块，禁止按行区间删**——r2 写的 `:120-191` 区间内还夹着 10 个**活**覆盖块（review-resonance:**128**、foreshadowing-lifecycle:132-138、score-arc/stratum/volume:145-156、review-arc-payoff:165-167、review-era/fanfic/sensitivity/spinoff:173-187），整段删会误杀生产配置。`lint_routing_faces` 禁路由 DEPRECATED → 覆盖块不可达。`registry.py` 的 `"short"` kind 实际在 **`contracts/schemas/registry.py:38`**（全 yaml 零使用）。
**连带**：executor_config.toml 覆盖键仍无 lint 面（#90 不收此面——**v2 裁剪**：新增 `overrides ⊆ live skills` 面的成本高于收益；只登记为已知缺口）。

### T7 · 非死面（复核结论：不动）
`_FINGERPRINT_CACHE`（chapter_drafting.py:366）为文档化 stat-keyed memo，幂等保持——保留。`state.increment_retry/reset_retry` **不删**（#91 T4 改为接线）。

### T8 · 交叉引用更正（r2.2）
r2 曾写「`_scan_fatigue_words` 同批并入 #85 词表单源或删」——**#85 无 fatigue/词表任务**（全文零命中），该引用凭空；本 spec 已改为「随 T1 删除，词表归并另议」。

## 2. 验收

1. 每 T 的 grep 判据零输出（T1 判据含 `StructuredChapterRepresentation`；T4 额外：`grep -rn "materialize_progress\|trace.replay" src/ tools/ tests/` 零，文档引用同批改）；
2. src/ 净减 ≥650 行（r2.2 核算：scr_extractor 407+、review_checklist ~101、trace 226、capability 58、chapter_loop ~33 = 825+；**前提是 scr_extractor ≤60 行**——单列文件级断言）且测试净减/改写记录入 plan；
3. `just check` exit 0；
4. 无测试因删除被 skip（skip 计数不增）；**test_compaction.py / test_review_checklist.py 改写后仍通过**。
