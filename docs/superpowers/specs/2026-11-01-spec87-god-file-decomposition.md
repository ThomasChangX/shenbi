# Spec #87 · god 文件拆分与正名（god-file-decomposition）：五体制出鞘、prompt 装配降维、事实公共 API 正名

**日期**：2026-11-01（r2 修订 2026-11-02：T6 DispatchContext 移出至 #94/后钩机制简化/验收校准；r2.2 2026-11-02 全量对抗式审计修订；r3 2026-11-12 快照漂移重定标——七批落地后行数与计数全面 re-anchor、验收 1/3/4 三处失真修正、T1 选型记录 NamedTuple、T2 表扩 11 项+roster-叶纪律、T4 双路径钉死；**r3.1 2026-11-12 二轮驳斥 GO 附修正**——T4 路径 B 名单裁定含 escalation/foundation-review（26 名，防活行为收紧）+计数/锚点事实修正六项）｜ **系列**：架构复审批次 A ｜ **状态**：Design（r3.1） ｜ **优先级**：🟥 P0
**依赖**：#86 先行（已归档 ✓）；#95 先行（已归档 ✓——**T2 悬置项已判定**：#95 r1.3 改道「升格既有 extractor 体系」，matrix_scoped/volume_opening_protocol 以 read extractor 形态落在 read_extractors.py → **入表分支成立**）；建议排在 #84 卷二开卷冻结窗后执行（#84 已归档，卷二 ch51+ 待实弹令=无活跃运行，当前窗口可施工）
**动机证据**：architecture-review-20261101 #2 卡（3×代理独立收敛；session 级产物不在盘，方向主张由源码锚独立支撑）；r3 协调者+驳斥子 agent 双核验（2026-11-12 现树）：`_run_chapter_step_impl` 恰在 **:3856-4780 = 925 行**（延伸至 EOF）；`_build_skill_prompt` **:746-1607 = 862 行**（r3.1 锚修正：return 止于 :1607，:1613 落在下一块 _BUDGET_DROP_TIERS 注释内；9 参数、5 元组返回）；`extractor_failed_fulltext` 恰 **21 处**（:322 注释 + 20 处代码位）；pipeline 内 `reportPrivateUsage` 压制 **17 处**（cli 8/chapter_loop 4/dispatch_helper 2/audit_context_cache 1/context_assemble 1/plan_skeleton 1；r2.2 的「20」含 #85 后已摘的 truth_io._THREAD_ID_* 3 处）。**根因快照后持续复发**：#95 +2 臂 +232 行 dispatch_helper、#84 +71 行——「每个 spec 落地都凿进同一函数」在 r2.2 落库后又发生 5 次

**触及的不变量维度**：无（行为保持重构——characterization 先行；T4 语义收紧面红测钉死）

---

## 0. 根因

`_run_chapter_step_impl`（925 行）以 if/elif 分派五体制，体制 5 内再嵌按技能名后协议——每个 spec 落地都凿进同一函数。`_build_skill_prompt`（868 行）9 参数 + 5 元组返回（spec #30/#81/#95 逐次加槽）。私有边界虚构：`_build_skill_prompt` 被 **19 个测试文件** AST-import（任意提及口径 30 文件）、`_write_parsed_outputs` **13 个**（提及 18）——正名后增量归零由基线 lint 承接；5 元组现有 **54 处解构位点**（r3.1 修正：src 2 处 :3887/:4360 + tests 52 处，含星号解包 1 处 test_dispatch_snapshot.py:55——NamedTuple 对星号/索引/len 全兼容，零反例）。

## 1. 任务分解

### T0 · characterization 骨架（先钉行为）
对五体制各补一条走 `run_chapter_step` 公共入口的路径测试（并行审计波/串行后起草对/pipeline 内部/条件跳过/通用串行各一），断言 checkpoint 契约（返回 bool + 状态副作用）。现有测试多凿私有面——公共入口覆盖是拆分安全网。

### T1 · `BuiltPrompt` NamedTuple（替换 5 元组）
**r3 选型记录**：`class BuiltPrompt(NamedTuple)` 而非 `@dataclass`——54 处 5 元解构位点（`a, b, c, d, e = _build_skill_prompt(...)`，含星号解包 1 处）在 NamedTuple 下**零破坏**（tuple 协议兼容星号/索引/len；全仓无拼接 `+`/`.count()`/`.index()` 反例），dataclass 则全部打碎为 54 处手术；两者同样达成「加字段=加具名属性」（新字段带默认值）。字段：`{system, user, output_paths, reads_manifest, raw_disk_reads}`；`_build_skill_prompt` 返回类型注解改 `BuiltPrompt`，解包点零改动，具名访问逐步迁移。

### T2 · extractor 注册表（**11 项**）
`read_extractors.REGISTRY: dict[str, ExtractSpec]`，`ExtractSpec = {impl, requires_chapter, warn_when, keep}`。**r3.1 设计注记（arg-shape）**：10 个 `extract_*` 签名有 4 种形态（三参 ×2：hooks_audit_scoped/matrix_scoped；仅 content ×4；content+keyword-only keep ×3；threads_overview(content, chapter=None)）——REGISTRY 统一调用须落 read_extractors 内的**统一包装层**（归一签名为 `(project_dir, chapter, content) -> str | None`，包装不吃 dispatch_helper 行数预算），ExtractSpec.impl 指包装。**r3 表扩**：现 **11 臂**（:879-1160，#95 后 matrix_scoped :1091/volume_opening_protocol :1113 加入）——表 = 本文件 10 个 `extract_*` + `volume_chapter`（impl=本文件薄包装 `_shared.load_volume_context(project_dir, chapter)`，:887 现调用点）。
**单源分层纪律（r3，采纳 #90 roster-叶同族方案）**：名字单源落 **contracts 侧零依赖叶**（如 `contracts/read_extractor_names.py`，纯 frozenset 无内部 import）——`contracts/loader.READ_EXTRACTORS`（现 :94-107 手写 **11 名**字面量）改 `frozenset(READ_EXTRACTOR_NAMES)` 派生；`read_extractors.REGISTRY` keys 断言 == 叶集合（模块级 assert 或测试）。**禁直接 `frozenset(REGISTRY)` 派生 loader**——会造成 contracts→pipeline import 反边（现仓 0 先例）。加第 N 个 extractor = 叶 +1 名 + REGISTRY +1 项（**2 处编辑**）。
dispatch_helper 11 臂 + guard（:1160）坍缩为一臂——**但不能只加一个 WARN 谓词**（r3.1 None 语义三态精确化）：①`volume_chapter` 在 `chapter is None` 时落 :1160 guard WARN（extractor_unrouted_fulltext）**非静默**；②真静默回退仅 `hooks_audit_scoped`（chapter None 时 fallthrough 全文、§4.3 注释自述）；③`matrix_scoped` chapter None 走 loud WARN；④`recent_increments` 只在 `has_chapter_units` 时 WARN（under-keep no-op by design）；⑤其余臂空结果即 WARN——per-extractor 策略由 ExtractSpec.warn_when 承载（warn_when 须能表达 guard-warn/silent/loud/no-op 四态）。坍缩量 **−252**（现链 :879-1160 = 282 行 → ~30 行；验收 1 dispatch_helper 线 ≤4,680 对估计值 4,673 余量仅 7 行——实现超 ~40 行即越线，须按坍缩下限施工）。**防复发禁令（r3）**：同批落测试断言——dispatch_helper 内 `grep "extractor =="` 字面量比较为零（现 11 处全在臂链内，链外零误伤；新 extractor 不得重写裸 if 臂，#95 加臂先例即博弈路径实锚）；`tests/unit/pipeline/test_read_extractors_slicing.py:271-284` 硬编码名字集（r3.1 锚修正，断言 `== READ_EXTRACTORS` 在 :286）改断言「contract 出现的 extractor 名 ⊆ REGISTRY keys」。

### T3 · 五体制拆分
```
run_chapter_step ── checkpoint 创建/恢复唯一持有；各体制显式持有各自推进语义
 ├→ _run_audit_wave_step        (:3913-4162 域；一次推进整波)
 ├→ _run_post_draft_pair_step   (:4170-4351 域；推进 2 步并直写 step_index/retry_feedback)
 ├→ _run_pipeline_internal_step (:4360-4432 域)
 ├→ (条件/跳过判定留主函数——:4435-4448 约 14 行)
 ├→ _run_context_assembly_step  (:4355-4357，3 行小体制)
 └→ _run_serial_dispatch_step   (:4450-4780 域 = 331 行，须再抽 3 块 [dispatch 调用/post 三钩/revision 聚合] 才 <260)
```
**r3 措辞降格**：r2 图的「游标/推进/checkpoint 不变量（唯一持有者）」不可达——三体制推进语义互异（整波/2 步直写/1 步），拆出函数必须各自调用 `_advance`/失败处理。正确口径：**checkpoint 创建与恢复唯一持有于 run_chapter_step；推进语义各体制函数显式持有**。
体制 5 的技能后协议**分属三种时机，不能收成一个 post_success 函数**：`:4485-4486`（write_audit_aggregate）`:4492-4501`（_pre_settle_guard）在 `dispatch_skill`（:4503）**之前**；`:4521`/`:4533` 在**失败分支**；`:4702`（resonance）`:4728`（revision）才是成功尾。收为三个显式具名函数 `_pre_dispatch_hooks(step, state, project_dir, chapter)` / `_on_dispatch_failure(...)` / `_on_dispatch_success(...)`，内部各用局部 dict「skillsuffix → 函数」+ 有序调用——**不做全局注册表/装饰器**（4 项不值得机制化；表 + 显式顺序 = 数据，可读可测）。

### T4 · 子串判定消灭（**双路径**）
chapter_loop 五位点（r3.1 计数修正；step 对象在手）：`:1819 "state-settling" in step.skill`（uses_staging 行）、`:4521`（失败分支 state-settling）、`:4533 "review-resonance"`（失败分支）、`:4702`（成功尾 resonance）、`:4728 "chapter-revision"` → **路径 A**：ChapterStep 加布尔属性 `settles_state`/`emits_resonance`/`is_revision`（升格既有 uses_staging/calls_context_assembly/is_audit 属性面，现十个字段），CHAPTER_STEPS 表填值。
dispatch_helper 两位点（**无 step 对象**——`_build_skill_prompt` 体内 :1577 只有裸 skill 字符串）：调用点 :1577、实现 :1709-1711 `return "review" in skill.lower()` → **路径 B（r3.1 名单裁定）**：精确 frozenset 常量 **26 名** = 24 个 `shenbi-review-*` 前缀 + **`shenbi-escalation-review` + `shenbi-foundation-review`**（后两名今日即被 `"review" in skill.lower()` 匹配并吃到 :1577 注入——`dispatch_escalation`（revision_router:217）chapter 可非 None 真实触发；**只收 24 前缀名=活行为收紧非卫生加固，禁**）+ 测试目录扫描对账（`skills/` 下凡名字含 `review` 的目录名 ⊆ 常量，新 review 技能漏登即红）+ **escalation-review 保留注入特征测试**（防名单裁定回退）。
**红测**：构造技能名含 `review-resonance` 子串但非该技能的 step，断言不触发 resonance 后处理（当前误触——红转绿）；构造 `shenbi-preview-x` 假想名断言不触发路径 B review 注入。
**r3 如实标注（r3.1 修正口径）**：今日 26 个含 review 名全部语义为 review（escalation-review 经 dispatch_escalation 真实消费注入）；三个子串各只有一个真实技能命中——本 task 是**卫生加固而非活 bug 修复**（根因防御：杜绝未来技能名撞子串面），价值在防复发不在纠错；路径 B 名单等权保留现行为零语义变化。

### T5 · 事实公共 API 正名 + 增量 lint
~12-15 个最高频被测符号正名（`_build_skill_prompt→build_skill_prompt`、`_write_parsed_outputs→write_parsed_outputs`、`_should_skip_audit`、`_parse_resonance_score` 等；**须覆盖 chapter_loop 4 处 reportPrivateUsage 压制的私有符号与 audit_context_cache.py:124 `_ending_archetype_of`**——r3.1 手段精确化：:64 `_check_emergency_flag`/:3685 `_merge_step_result`/:3802 `_dispatch_with_retry` 三处为名字级私有、正名即摘；:1066 `AuditResult` 为模块级私有（audit._shared）但 `shenbi/audit/__init__.py:6` 已公共再导出——**改 import 路径即摘压制**（非改名））；新增 lint 面：`tests/**` 对 `shenbi.pipeline` 的 `_` 前缀 import **增量**为零——基线落 `tests/private_imports_baseline.txt`（(file, symbol) 对，受版本控制，判定=当前集合 ⊆ 基线；概念模板=tools/lint_dead_code_allowlist.py 冻结白名单先例，justfile:40 已挂同族先例），`--update` 仅人工评审后可用；存量随触碰逐步清（反过度工程：止血增量，非本周清零）。**r3 注记**：pyproject executionEnvironments tests 域 `reportPrivateUsage = "none"`（r3.1 锚修正：pyproject.toml:560）是 pyright 侧既有开关，本 lint 为独立新增面（ruff/29 个既有 lint_* 无等价物，负列举成立；PLC2701 为 preview 门控不可低成本启用），该开关**不动**（打开会淹死在 19 文件存量里）；pyright 压制随正名逐个摘除。

## 2. 验收（r3 全面重定标，基线 2026-11-12 现树：chapter_loop **4,780** + dispatch_helper **4,910** = **9,690**）

1. `chapter_loop.py` + `dispatch_helper.py` 合计 **≤9,500 行**；per-file：`chapter_loop.py` **≤4,820**（T3 同文件拆函数近中性，+40 增长余量；五体制函数留本文件——搬 `pipeline/chapter_steps/` 新模块仍列 **Phase 2 独立任务**，其 1,631+ 行搬迁不做）、`dispatch_helper.py` **≤4,680**（4,910−252(T2)+15(T1)≈4,673）。**r2.2 的 ≤9,100/≤4,660/≤4,415 作废**：其算术基线 9,300 已漂移至 9,690，+390 全落在本 spec 无法削减的域（r3.1 归因复算：#95 +232 dispatch_helper 分窗执法块/#84 +134/#99 +9/束4束5 chapter_loop +142/#86 −132——非 T0-T5 触及面）；
2. `_run_chapter_step_impl` 消失；**五个**体制函数各有独立红测——第 5 个=`_run_context_assembly_step`（现 :4355-4357 仅 3 行）；条件/跳过实际是 **:4435-4448 ≈14 行**；serial 段现 331 行，须再抽 3 块（dispatch 调用/post 三钩/revision 聚合）才 <260；**checkpoint 创建/恢复唯一持有于 run_chapter_step**（推进语义各体制显式持有，见 T3 措辞）；
3. `grep -c extractor_failed_fulltext src/shenbi/pipeline/dispatch_helper.py` = 1——**r3 补**：:322 注释行含该字面量（`# 降级路径（extractor_failed_fulltext 回全文）同受此预算约束`），T2 同批改写注释措辞（如「extractor 降级回全文」不含机器判据字面量），否则 grep -c 恒 ≥2（r2.2 时已如此=当时即过不了字面验收的隐藏口径 bug）；
4. T4 红测绿；pipeline 内 pyright 私有压制 **≤12**（**#87 时点算术，r3 修正/r3.1 手段精确化**：现 17 − 1（T5 摘 `_ending_archetype_of` audit_context_cache:124）− 3（T5 正名 chapter_loop :64/:3685/:3802 三处名字级私有）− 1（:1066 `AuditResult` 经 `shenbi.audit` 公共再导出改 import）= 12；**撤 r2.2 的 #94 T2 时序引用**——#87 排 #94 前，cli.py 8 处不在本批口径；撤 `read_extractors:392` 引用——#85 已摘，该文件现 0 压制。加项：dispatch_helper 2 处 truth_io 压制（:2537 `truth_io._OUTLINE_SECTION_KEY_RE`/:2692 `truth_io._TABLE_HEADER_BOOTSTRAP`）若随正名公共化 → ≤10）；
5. `tests/private_imports_baseline.txt` 子集断言绿（增量=0）+ T2 防复发禁令断言绿（dispatch_helper 零 `extractor ==` 字面量）；
6. `just check` exit 0 + 全量测试绿（T0 characterization 为证）。

## 3. 施工序

- 一次一个体制（五 task 串行），任何一步红即回滚该步；
- 本 spec 不动格式正则（#85 已落）；
- **连带必改**：`tests/unit/pipeline/test_spec83_stale_declarations.py:73-89` settle_capable 三元组含 `("pipeline/chapter_loop.py","_run_chapter_step_impl")`、:91-101 以 `_enclosing` 机械枚举 `dispatch_skill(` 调用点未分类即红——T3 拆函数会直接打红；T3 验收须含该白名单同步更新（拆出函数内的 dispatch_skill 调用点须逐一归类）；
- **行号纪律（r3）**：本 spec 全部行号为 2026-11-12 快照（#86 合并后现树）；plan 首步仍须按符号 re-anchor；
- DispatchContext（原 T6）移至 #94 T4 域（public 接口批，避免在拆分中同时改签名面）。
