# Spec #87 · god 文件拆分与正名（god-file-decomposition）：五体制出鞘、prompt 装配降维、事实公共 API 正名

**日期**：2026-11-01（r2 修订 2026-11-02：T6 DispatchContext 移出至 #94/后钩机制简化/验收校准）｜ **系列**：架构复审批次 A ｜ **状态**：Design（r2） ｜ **优先级**：🟥 P0
**依赖**：#86 先行（死分支先删再拆）；建议排在 #84 卷二开卷冻结窗后执行（改动面 = 两热文件全量）
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
`read_extractors.REGISTRY: dict[str, Callable]`（统一签名 `(project_dir, chapter, content) -> str`；现有 9 实现签名已近乎一致，唯 volume_chapter 用 project_dir）；`contracts/loader.READ_EXTRACTORS = frozenset(REGISTRY)` 派生；dispatch_helper.py:869-1112 九臂坍缩为一臂（单份 try/except/WARN + `recent_increments` 的 WARN 条件改谓词标志）。~230 行 → ~30 行；第 10 个 extractor = 2 处编辑。

### T3 · 五体制拆分
```
run_chapter_step ── 游标/推进/checkpoint 不变量（唯一持有者）
 ├→ _run_audit_wave_step        (L3839-4089 域)
 ├→ _run_post_draft_pair_step   (L4098-4260 域)
 ├→ _run_pipeline_internal_step (L4269-4345 域)
 ├→ (条件/跳过判定留主函数——3 行)
 └→ _run_serial_dispatch_step   (L4364-4693 域)
```
体制 5 的 4 个技能后协议（:4391 revision 聚合刷新 / :4398,:4425 settle 前卫 / :4437,:4611 resonance / :4597-4692 审计收尾+revision 复验）**收敛为一个显式具名函数 `_run_post_success_hooks(step, state, project_dir)`**，内部用一张局部 dict「skillsuffix → 函数」+ 有序调用——**不做全局注册表/装饰器**（4 项不值得机制化；表 + 显式顺序 = 数据，可读可测）。

### T4 · 子串判定消灭
`:4425 "state-settling" in step.skill`、`:4437/:4611 "review-resonance" in step.skill`、`dispatch_helper.py:1520 "review" in skill.lower()` 等 → ChapterStep 显式属性（`settles_state`/`emits_resonance`/`is_review`）或精确集合常量。
**红测**：构造技能名含 `review-resonance` 子串但非该技能的 step，断言不触发 resonance 后处理（当前误触——红转绿）。

### T5 · 事实公共 API 正名 + 增量 lint
~12-15 个最高频被测符号正名（`_build_skill_prompt→build_skill_prompt`、`_write_parsed_outputs→write_parsed_outputs`、`_should_skip_audit`、`_parse_resonance_score` 等）；新增 lint 面：`tests/**` 对 `shenbi.pipeline` 的新增 `_` 前缀 import **增量**为零（基线=当前对数；存量随触碰逐步清——反过度工程：止血增量，非本周清零）。pyright 压制随正名逐个摘除。

## 2. 验收

1. `chapter_loop.py` + `dispatch_helper.py` 合计 <7,900 行（现 9,297；#86 减 ~40、本 spec 减 ~300——**r2 校准**：DispatchContext 移出后不重复计入）；
2. `_run_chapter_step_impl` 消失；五体制函数各 <260 行且各有独立红测；
3. extractor WARN 位点 `grep -c extractor_failed_fulltext src/shenbi/pipeline/dispatch_helper.py` = 1（现 18）；
4. T4 红测绿；pipeline 内 pyright 私有压制 ≤8（现 20；#94 T2 承接已搬走的 cli 侧）；
5. tests 私有 import 基线 lint 绿（增量=0）；
6. `just check` exit 0 + 全量测试绿（T0 characterization 为证）。

## 3. 施工序

- 一次一个体制（五 task 串行），任何一步红即回滚该步；
- #85 先落（格式正则归位一次）；本 spec 不动格式正则；
- DispatchContext（原 T6）移至 #94 T4 域（public 接口批，避免在拆分中同时改签名面）。
