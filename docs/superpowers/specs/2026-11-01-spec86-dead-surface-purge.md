# Spec #86 · 死面清扫批（dead-surface-purge）：纯删除零引用面，为 god 文件拆分减重

**日期**：2026-11-01（r2 修订 2026-11-02：trace 两模块改判删除/调用点与测试影响钉死）｜ **系列**：架构复审批次 A（**#87 前置**）｜ **状态**：Design（r2） ｜ **优先级**：🟠 P1
**动机证据**：architecture-review-20261101 #14 卡；本节每项消费者 grep 由协调者复跑（2026-11-02）

**触及的不变量维度**：无（纯删除零引用面；唯一行为触点=scr_extractor 缩编保留其被消费的 WARN）

---

## 0. 根因

本仓 v7 rubric 的双向 dead-wire 检查（「实现但零接线=Important」）在自身仓库最密集的违例带：~800 行「看似活着的机制」。每项独立无害，合计是读者与 #87 拆分搬运的持续税。

## 1. 清扫清单（r2：逐项已亲核）

### T1 · scr_extractor 缩编（:69-437）
**亲核事实**：两个生产调用点——`chapter_loop.py:1991`（`_post_draft_extract_scr`：仅为预热缓存，返回值丢弃）与 `:2075`（world freshness：仅读 `scr.world_refs` 且只取 `category=="location"`）。其余 15 字段零消费；`_scan_fatigue_words`（:362）与 gates/shared 疲劳词概念三套词表重复（同批并入 #85 词表单源或删）。
**处置**：替换为单函数 `recent_location_terms(project_dir, chapter, lookback=10) -> set[str]`（~20 行，无缓存——每章一次）；删 `ScrReport` 15 死字段、缓存写、`_scan_fatigue_words`；`:1991` 预热点整删（缓存存在的唯一理由消失）。
**连带**：`tests/pipeline/test_scr_extractor.py` 进口 6 个私有抽取器——**随删除重写为单函数测试**（保留 location 抽取断言、删除 15 字段断言）；`tests/unit/test_*` 中引用 ScrReport 的断言同批清理（plan 期 grep 列全）。
**判据**：`grep -rn "extract_scr\|ScrReport" src/ tools/ tests/ | grep -v scr_extractor.py` 零输出。
**备选**：若裁定 world freshness WARN 无价值 → 整删模块与两侧调用（world freshness 块 :2066-2100 一并删）。

### T2 · review_checklist 死半边（:546-654 + __all__:657-681）
**亲核**：`generate_static_template`/`generate_chapter_delta`/`get_checklist`/`_load_blacklist`/`_load_voice_constraints`/`_load_pov_mode`/`_load_world_rules_brief`/`_extract_hooks_from_plan` 逐名 grep 外部引用 0；`__all__` 含 10 个 `_` 私有名（含活函数 6 个 + 死函数 4 个）。
**处置**：删 8 个死函数；`__all__` 只留真公共面（`ReviewChecklist`/`STATIC_FIELDS`/`DYNAMIC_FIELDS`/`ENDING_PATTERNS`/`generate_review_checklist`/`inject_checklist_into_prompt`），私有名移出 `__all__`（测试若需私有则 import 模块属性，不进 `__all__`）。
**死桩自相矛盾的证据留档**（plan 期写入 commit message）：`third_person_limited`/`multi_pov` 捏造、`truth/world_rules.md` 不存在（活半边读 `world/rules.md`）、`chapter-{ch:03d}` 零填充与全管线不一致、`sensitivity_flags: 0` int 冒充 list。

### T3 · chapter_loop 死分支 ×4（:2847-2851,:4690,:4593-4594）+ 死 manifest
**亲核**：`shenbi-intent-management`/`shenbi-drift-guidance` 不在 CHAPTER_STEPS（注释 :141-142 自认）；:4593 被 :4098 同指标拦截不可达；`_load_manifest`/`_save_manifest` 仅服务 `_update_last_drift_manifest`（自身零调用）。
**处置**：纯删。

### T4 · trace/materialize.py + trace/replay.py —— **删除**（r2 改判）
**r2 判据升级**：原稿「文档化为恢复工具」经复审否决——**留死码换个标签仍是死码**（本仓 anti-rationalization：实现但零接线 = Important）。硬事实：
- 零生产消费者（src/tools 仅 `trace/__init__.py` 重导出自身）；
- `replay.py:18 _verify` 与 `trace/compaction.py:13 verify_chain` 重复实现签名链校验——G7 走 compaction，replay 是**第二套判定**；
- 「trace 权威、progress 派生」哲学未被采纳：`codex.py:40-62` 以直接变更写 progress；`crash_recovery.py` 已承担真实恢复职责（信号/急救快照）。
- **处置**：删 `materialize.py`（163 行）+ `replay.py`（63 行）+ `trace/__init__` 导出 + 对应测试（`tests/unit/trace/`、`tests/property/trace/` 中 related 用例）。**显式替代条款**：若用户视事件溯源为既定方向 → 保留两模块原状（不文档化），单独立项接线；两者不并存。

### T5 · capability_fs.py 移 tests 支撑（58 行）
**亲核**：唯一消费者 = 两个测试文件；无门注入。
**处置**：迁 `tests/support/capability_fs.py`（tests/conftest 旁）。**备选**（需用户裁定）：真接线（G4 纯判器入口注入只读句柄）另立 spec；本批不接线。

### T6 · executor_config.toml 6 DEPRECATED 覆盖块（:120-191）+ 死 kind
**亲核**：`review-continuity`/`review-anti-ai`/`review-pov` 等盘上 SKILL.md 含 DEPRECATED 横幅（抽查 3/6 均中）；`lint_routing_faces` 禁路由 DEPRECATED → 覆盖块不可达。`registry.py:14-31` `"short"` kind 全 yaml 零使用。
**处置**：删 6 块 + 删 `"short"` 成员（schema `extra:forbid` 会拦截漏网）。
**连带**：`executor_config.toml` 覆盖键无 lint 面（#90 不收此面——**v2 裁剪**：新增 `overrides ⊆ live skills` 面的成本高于收益，且删除 6 块后死键面已消；只登记为已知缺口）。

### T7 · 非死面（复核结论：不动）
`_FINGERPRINT_CACHE`（chapter_drafting.py:366）为文档化 stat-keyed memo，幂等保持——保留。`state.increment_retry/reset_retry` **不删**（#91 T4 改为接线）。

## 2. 验收

1. 每 T 的 grep 判据零输出（T4 额外：`grep -rn "materialize_progress\|trace.replay" src/ tools/ tests/` 零）；
2. src/ 净减 ≥650 行；测试净减/改写记录入 plan；
3. `just check` exit 0；
4. 无测试因删除被 skip（skip 计数不增）。
