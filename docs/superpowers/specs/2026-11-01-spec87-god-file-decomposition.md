# Spec #87 · god 文件拆分与正名（god-file-decomposition）：五体制出鞘、prompt 装配降维、事实公共 API 正名

**日期**：2026-11-01（r2 修订 2026-11-02：T6 DispatchContext 移出至 #94/后钩机制简化/验收校准；**r2.2 2026-11-02 全量对抗式审计修订**——验收算术重定标（<7,900→≤9,100）、T2 签名事实更正、后钩拆三时机、压制目标 ≤11、增 test_spec83 白名单连带）｜ **系列**：架构复审批次 A ｜ **状态**：Design（r2.2） ｜ **优先级**：🟥 P0
**依赖**：#86 先行（死分支先删再拆）；建议排在 #84 卷二开卷冻结窗后执行（改动面 = 两热文件全量）；**#95 先行本 spec（r2.1 注记，2026-11-02）**——#95 是束4 解冻最短路径且与本章 prompt 装配/失败路径同文件域，冻结窗内 #95 优先插队，本 spec 排 #95＋束4 验收之后；characterization 基线=含 #95 落地后的装配面（分窗/范例章/反馈模板）
**动机证据**：architecture-review-20261101 #2 卡（3×代理独立收敛）；协调者亲验：`_run_chapter_step_impl` 恰在 :3777-4693 = 917 行；`_build_skill_prompt` :736-1541 = 806 行；`extractor_failed_fulltext` 恰 18 处；pipeline 内 `reportPrivateUsage` 压制 20 处

**触及的不变量维度**：无（行为保持重构——characterization 先行；T4 语义收紧面红测钉死）

---

## 0. 根因

`_run_chapter_step_impl`（917 行）以 if/elif 分派五体制，体制 5 内再嵌 4 个按技能名子协议——每个 spec 落地都凿进同一函数。`_build_skill_prompt`（806 行）9 参数 + 5 元组返回（spec #30/#81 逐次加槽）。私有边界虚构：`_build_skill_prompt` 被 27 个测试文件 import、`_write_parsed_outputs` 17 个。

## 1. 任务分解

### T0 · characterization 骨架（先钉行为）
对五体制各补一条走 `run_chapter_step` 公共入口的路径测试（并行审计波/串行后起草对/pipeline 内部/条件跳过/通用串行各一），断言 checkpoint 契约（返回 bool + 状态副作用）。现有测试多凿私有面——公共入口覆盖是拆分安全网。

### T1 · `BuiltPrompt` dataclass（替换 5 元组）
`@dataclass BuiltPrompt {system, user, output_paths, reads_manifest, raw_disk_reads}`；`_build_skill_prompt` 及全部解包点机械替换。此后加字段=加具名属性。

### T2 · extractor 注册表
`read_extractors.REGISTRY: dict[str, ExtractSpec]`，`ExtractSpec = {impl, requires_chapter, warn_when, keep}`（**r2.2 更正签名事实**：read_extractors.py 只有 **8** 个 extractor——`hooks_audit_scoped(project_dir, chapter, content)` 唯一符合三参、`hooks_overview`/`hooks_inventory_scoped`/`book_strata_current` 仅 `content`、`recent_increments`/`relationships_overview`/`locations_overview` 带 keyword-only `keep`、`threads_overview(content, chapter=None)` 两参；`volume_chapter` 实为 `_shared.load_volume_context(project_dir, chapter)` 且**不在本文件**）；`contracts/loader.READ_EXTRACTORS` 现为手写 9 名字面量（loader.py:94-106），改为 `frozenset(REGISTRY)` 派生（`tests/unit/pipeline/test_read_extractors_slicing.py:261-277` 硬编码同一名字集，派生后改断言「contract 出现的 extractor 名 ⊆ REGISTRY」）；dispatch_helper.py:869-1105 九臂（+1107-1112 guard）坍缩为一臂——**但不能只加一个 WARN 谓词**：`volume_chapter`/`hooks_audit_scoped` 在 `chapter is None` 时静默回退全文、`recent_increments` 只在 `has_chapter_units` 时 WARN、其余空即 WARN——per-extractor 策略由 ExtractSpec 承载。~237 行 → ~30 行（**−207，非 r2 的 −300**）；第 10 个 extractor = 2 处编辑（**#95 T3 分窗 extractor 的形态由 #95 plan 定**：以 read extractor 落地则入表；以 dispatch_helper 读过滤器落地则不入表）。

### T3 · 五体制拆分
```
run_chapter_step ── 游标/推进/checkpoint 不变量（唯一持有者）
 ├→ _run_audit_wave_step        (L3839-4089 域)
 ├→ _run_post_draft_pair_step   (L4098-4260 域)
 ├→ _run_pipeline_internal_step (L4269-4345 域)
 ├→ (条件/跳过判定留主函数——3 行)
 └→ _run_serial_dispatch_step   (L4364-4693 域)
```
体制 5 的 4 个技能后协议**分属三种时机，不能收成一个 post_success 函数**（r2.2 更正）：`:4391`（revision 聚合刷新）/`:4398`（settle 前卫）在 `dispatch_skill`（:4405-4416）**之前**；`:4425`/`:4437` 在**失败分支**；`:4597-4692`（含 :4611 resonance）才是成功尾。收为三个显式具名函数 `_pre_dispatch_hooks(step, state, project_dir, chapter)` / `_on_dispatch_failure(...)` / `_on_dispatch_success(...)`，内部各用局部 dict「skillsuffix → 函数」+ 有序调用——**不做全局注册表/装饰器**（4 项不值得机制化；表 + 显式顺序 = 数据，可读可测）。

### T4 · 子串判定消灭
`:4425 "state-settling" in step.skill`、`:4437/:4611 "review-resonance" in step.skill`、**`:1636 "state-settling"` / `:4637 "chapter-revision"`（r2.2 补——仍在用）**、`dispatch_helper.py:1520` 调用点（实现 `"review" in skill.lower()` 在 **:1546**，r2.2 更正）等 → ChapterStep 显式属性（`settles_state`/`emits_resonance`/`is_review`）或精确集合常量。
**红测**：构造技能名含 `review-resonance` 子串但非该技能的 step，断言不触发 resonance 后处理（当前误触——红转绿）。

### T5 · 事实公共 API 正名 + 增量 lint
~12-15 个最高频被测符号正名（`_build_skill_prompt→build_skill_prompt`、`_write_parsed_outputs→write_parsed_outputs`、`_should_skip_audit`、`_parse_resonance_score` 等）；新增 lint 面：`tests/**` 对 `shenbi.pipeline` 的 `_` 前缀 import **增量**为零——**r2.2 修正：基线不能是「当前对数」**（删旧增新净零即过），须落 `tests/private_imports_baseline.txt`（(file, symbol) 对，受版本控制，判定=当前集合 ⊆ 基线），`--update` 仅人工评审后可用；存量随触碰逐步清（反过度工程：止血增量，非本周清零）。pyright 压制随正名逐个摘除。

## 2. 验收

1. **r2.2 重定标**：`chapter_loop.py` + `dispatch_helper.py` 合计 **≤9,100 行**（现 **9,300**=4,693+4,607，r2 的 9,297 是 #275 前旧值；核算 9,300−37(#86)−207(T2)+15(T1)=**9,071**）。**<7,900 不再作为本 spec 验收**：需把 T3 的四个大域（821 行）＋第 5 个 context_assembly 分支（4 行）与 `_build_skill_prompt`（806）搬入新模块（`pipeline/chapter_steps/`＋`pipeline/prompt_builder.py`，合计 1,631 行）才可达，列为 **Phase 2 独立任务**；度量同时给 per-file 上限（防「搬迁刷合计分」）：`chapter_loop.py` **≤4,660**（4,693−37=4,656）、`dispatch_helper.py` **≤4,415**（4,607−207+15=4,415——r2.2 复核：r2 写的 4,410 差 5 行不可满足）；
2. `_run_chapter_step_impl` 消失；**五个**体制函数各有独立红测——**r2.2 补**：第 5 个=`_run_context_assembly_step`（现 :4264-4267 分支，仅 4 行；r2 图漏了它）；条件/跳过实际是 **:4347-4362=16 行**（r2.2 复核：原文「3 行/19 行」均不准）；serial 段现 330 行，须再抽 3 块（dispatch 调用/post 三钩/revision 聚合）才 <260；
3. extractor WARN 位点 `grep -c extractor_failed_fulltext src/shenbi/pipeline/dispatch_helper.py` = 1（现 18）；
4. T4 红测绿；pipeline 内 pyright 私有压制 **≤11**（现 20；#94 T2 搬走 cli.py 8 处 →12，T5 真需摘的只有 `_ending_archetype_of` 1 处 →11；r2 的 ≤8 不可达——若 T3 同时公共化 chapter_loop 4 处与 read_extractors:392 则 ≤7，作为加项）；
5. `tests/private_imports_baseline.txt` 子集断言绿（增量=0）；
6. `just check` exit 0 + 全量测试绿（T0 characterization 为证）。

## 3. 施工序

- 一次一个体制（五 task 串行），任何一步红即回滚该步；
- #85 先落（格式正则归位一次）；本 spec 不动格式正则；**#95 先行**（T2 的第 10 项形态由 #95 plan 定，见依赖行）；
- **连带必改（r2.2）**：`tests/unit/pipeline/test_spec83_stale_declarations.py:62-95` 以「enclosing function」机械枚举 `dispatch_skill(` 调用点，白名单含 `("pipeline/chapter_loop.py","_run_chapter_step_impl")`——T3 拆函数会直接打红；T3 验收须含该白名单同步更新；
- **行号纪律（r2.2）**：本 spec 全部行号为 2026-11-02 快照（#275 后）；#85/#95 落地会再漂——plan 首步按符号 re-anchor，行号只作定位；
- DispatchContext（原 T6）移至 #94 T4 域（public 接口批，避免在拆分中同时改签名面）。
