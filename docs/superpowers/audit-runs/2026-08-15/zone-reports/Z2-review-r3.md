# Z2 分区独立复核报告 r3（2026-08-15 轮）

- 复核 agent: Z2 fresh-context 独立复核轮 3（与初审、r1、r2 均无关）
- 复核方式: 38 文件重点深读（schemas/skills/ownership/paths/fields/legacy/graph + dispatcher 全部）+ 本轮强制新角度 **(a) producer/consumer 键空间三方对账**、**(b) 真实数据形态对照（novel-output/xinghuo-ranqiong/ 全量产物）** + `uv run python -B -c` 实跑验证 + git 考古
- 编号段: F237–F243（初审 F201–F223、r1 F224–F230、r2 F231–F236 已用）
- 只读约束遵守: 除本报告外未创建/修改/删除任何仓库文件；脚本只写 /tmp/z2r3/；novel-output 只读；未运行 pytest / shenbi-dispatch / pipeline 任何子命令；无 git 写操作

## 总结论

三轮 36 条旧 finding 逐条复读（含 12 组本人独立实跑/grep）**无整条误报**，r1 对 F210 汇总的"fields 已接线"勘误维持。但本轮两个强制角度均高产出：**(1) 契约 schema 的键空间与真实生产者的键空间从未对账**——DecisionsDoc 的 Literal 词表 vs 89 个真实 decisions.json（仅 3 个通过 schema，44 个连 JSON 都不是）、NovelConfig 的字段类型 vs seed_parser 生产代码（genre 声明 str、生产者写 list）、pending_hooks 的记录格式假设 vs 生产者的表格格式（消费端解析对真实文件恒空 → 条件 resolve 步骤静默失效）；**(2) Layer B 的 35 个字段声明对真实 truth 文件零命中率达 54%**（F227 的 povMode 只是冰山一角，声明追随 fixture 模板而非活的生产模板）。r1 的"声明→归一化之后断线"家族在本轮扩展为更根本的"**契约↔生产者从未见面**"家族。

---

## 一、漏报（新 finding）

### F237 | DecisionsDoc 键空间与真实生产者全面断裂：89 个真实 decisions.json 仅 3 个通过 schema（44 个非法 JSON + 42 个违反 Literal/extra=forbid） | error | P1
- 证据（实际运行，脚本见 /tmp/z2r3/）:
  ```
  $ uv run python -B -c "…DecisionsDoc.model_validate(全量 89 文件)…"
  total=89 pass=3 fail=42 (+44 json.loads 直接失败)
  ```
  - **44 个非法 JSON**: "Extra data"（合法 JSON + 尾随散文，28 个）、"Expecting value: line 1 col 1"（以英文散文开头，如 chapter-40-decisions.json 首行 "The file on disk can't be updated (read-only sandbox)…"、chapter-12-revision-decisions.json 首行 "The revision is complete. Here's a summary…"）、坏控制字符、缺分隔符；
  - **42 个可解析但违反 schema**: `basis` 自由文本（可解析文件 198 个 selections 中 81 个 = 41% 不在 4 值 Literal 内，实测自由文本 basis 约 60 种：route_c_diagnosis、audit_drift、anti-detect为专项表面变换skill…）；`handling` 约 30 种自由文本（compensate_via_breath_parameter、spot-fix: 三十七枚半→四十六枚半…）；`severity` 出现 blocking/critical/info/minor/none（**两个 Severity 域——decisions 的 low/medium/high 与 enums 的 BLOCKING/CRITICAL/MINOR——都不覆盖**，F211 的真实数据版）；顶层多余键（revision_mode×6、preservation_verification×4、revision_stats×3…撞 extra=forbid）；
  - **通过的 3 个**: chapter-24/38-decisions.json（basis=volume_scope）与 chapter-39-revision-decisions.json——并非巧合地全部使用枚举值。
- 根因（三方对账结论）:
  1. **schema 源头是测试内联字面量**: schemas/decisions.py:3 docstring 自述 "Field shapes from phase-0 investigation of tests/unit/gates/test_g4_decisions.py"——tests/fixtures/ 下没有任何 decisions fixture（本轮 find 证实），词表从手写字面量反推，从未对照生产者；
  2. **生产者从未被告知词表**: 派发 prompt 仅一行 "Decisions JSON must conform to shenbi-decisions-v1 schema (see docs/framework/decisions-schema.md)"（dispatch_helper.py:738），且**仅当 len(output_paths)>1 时注入**（:735-739），API 模式子代理读不到 docs/，basis/handling 枚举不在任何 SKILL.md 的输出说明里（grep 证实 chapter-drafting/SKILL.md 无 basis 词表）；
  3. **时间线**: git 考古——写时强制（dispatch_helper._validate_json_output 的 DecisionsDoc 检查）与 corpus 快照同在 dd1fc62（2026-07-20）落地：corpus 由无强制的旧代码产出（genre-config updated=2026-07-16），enforcement 加入后从未有新章节产出验证过生产者能否收敛到词表。
- 影响: ① 在案生产 corpus 对"单一信源"schema 的违反率 95%+ 且无任何门扫描过（G2 decisions 分支只在 T1 路由运行、pipeline 模式整体跳 G2）；② 前向看，下次真实 pipeline 运行中任何非枚举 basis/多余键的 decisions 写入都会触发 `output_validation_failed` ValueError → 派发中断（正常路径功能错误）；③ G4 revision checker（chapter_revision.py docstring "must not invent fields" 依赖 extra=forbid）与真实 revision 产物形状互斥。
- 建议方向: 枚举词表进 SKILL.md 输出模板 + 派发 prompt（无条件注入）；或 schema 的 basis/handling 放宽为 str + 独立 lint 层收紧；对 corpus 做一次性盘点归档标注。
- 定级依据: P1（正常路径功能错误 + 生产契约违反不可见）。可争 P0（决策表"生产契约静默违反"字面命中在案 corpus），因违反主体是历史快照且 enforcement 未放过任何新违规，主判 P1。

### F238 | pending_hooks.md 真实格式与消费端解析假设断裂：`_read_pending_hooks`/`_count_triggered_hooks` 对真实文件恒返回空/0，条件 resolve 与召回升级静默失效 | error | P1
- 证据（实际运行）:
  ```
  $ uv run python -B -c "from shenbi.pipeline.chapter_loop import _count_triggered_hooks; …"
  triggered count on REAL file: 0        # 而该文件正文出现 'TRIGGERED' 15 次
  ```
  - 真实 truth/pending_hooks.md（143 行，filled_by=foreshadowing-track, last_chapter=56）: frontmatter **无 `hooks:` 键**（仅 title/project/version/…/track_chapter），正文是按章 H2 + markdown 表格（"当前生命周期"列记 `RELEVANT→TRIGGERED(待track确认)`），`state: TRIGGERED` 字面量 0 次；
  - 消费端假设: chapter_loop.py:1305/1440 与 context_curation.py:361-386 均要求 frontmatter `hooks:` 列表 + `state:` 字段；`_count_triggered_hooks` 的回退分支是 `text.count("state: TRIGGERED")`（对表格格式恒 0）；
  - Z2 契约侧: ownership.py:52-71 `_HOOK_KEYS_NEW_RECORD`（16 键记录式，"fixture ## hooks 16 键 亲手核对"）与 fixture tests/fixtures/pending-hooks-example.md（`## hooks` + `state: PLANTED` 记录）描述的是真实生产者已不再写的格式。
- 影响（正常路径静默失效）: ① `_check_conditional_resolve`（chapter_loop.py:1258-1282，spec 6.1 step 7b）**从不派发** shenbi-foreshadowing-resolve——文件自己的表格记录了 P0-4 在 ch56 RELEVANT→TRIGGERED，但 triggered_count=0；② `_should_recall` 条件 1（max_distance 逼近）与条件 2（>5 TRIGGERED）恒不触发，仅剩条件 3（距上次召回>8 章）存活；③ context_curation 的 hook-debt 上下文恒空。
- 根因: fixture 格式（记录式）与活的生产格式（表格式）分裂后，契约层（OWNERSHIP 键集、HookState 词表）与消费端（frontmatter 解析）都锚定在 fixture 上，无任何一致性检查。
- 建议方向: 二选一——生产侧（track/state-settling SKILL.md）恢复结构化记录区，或消费端改写表格解析器；OWNERSHIP 与 hooks schema 注明权威格式。跨区提示：消费端代码在 chapter_loop/context_curation（Z3 范围），建议联动工单。
- 定级依据: P1（正常路径功能错误：设计内的条件步骤在真实数据上静默永不触发；无数据损坏故非 P0）。

### F239 | Layer B 字段声明与真实 truth 文件键空间过半零命中：19/35 声明声明的字段在真实文件中一个都不存在 + 4 个声明文件本身不存在 | error | P2（潜伏，被 F224 掩盖）
- 证据（实际运行 /tmp/z2r3/field_scan.py，全量 35 个 dict+fields 声明 × novel-output/xinghuo-ranqiong 真实文件）:
  - **19 个声明零命中**（含宽松子串匹配仍不中），典型三类:
    1. **动态标题类**: truth/pending_hooks.md 真实 H2 是"第56章伏笔呈现"式按章标题，声明却是稳定字段名 活跃伏笔/伏笔统计/伏笔时间线（5 个技能声明）；truth/chapter_summaries.md 真实 H2 是"第55章：…/第56章：…"，声明 已完成章节（5 个技能）；
    2. **模板版本类**: style/style_profile.md 声明 `11. 综合画像`/`6. 修辞模式`/`9. 对白占比`（3 个技能），真实文件是 8 节"（推测）"模板：`5. 修辞模式`、`8. 综合画像`、**无对白占比节**——声明锚定在 tests/fixtures/style-profile-example.md（11 节）上；
    3. **近义漂移类**: truth/current_state.md 声明 主角状态/当前世界局势/活跃线索（2 个技能）——**这正是 AGENTS.md "Field-Level Reads" 一节自己的示例字段**——真实 H2 是 系统演化阶段/参数当前位置/进行中的情节线/世界状态变化（第56章）；
  - **4 个声明文件在真实项目不存在**: truth/book_strata.md、truth/volume_summaries.md、truth/arcs/arc-N.md、chapters/chapter-N.md 的 `POST_WRITE_SELF_CHECK` 字段（review-resonance）。
- 根因: 字段声明追随 fixture/理想模板而非活的生产输出；truth 文件生产者写动态标题，静态字段名匹配（fields.match_field 精确匹配）结构上不可能命中。
- 影响: 当前触发面=0（F224 过滤死线掩盖）；**若按 r1/r2 建议单独修复 F224**，54% 声明将立即零匹配 → escape-hatch 全文件回退 + WARN 刷屏，Layer B 对这些技能退化为无效——修复顺序必须 F239 先于/同步于 F224。
- 建议方向: 全仓字段声明按真实生产文件重校准（本扫描脚本可直接复用为 CI 检查）；动态标题类文件（pending_hooks/chapter_summaries）要么改生产模板加稳定字段节，要么放弃对它们的字段级声明。
- 定级依据: P2（潜伏 dead-wire 家族系统性扩大版；F227 的 povMode 是同族单点，本条为其系统化全貌）。

### F240 | NovelConfig 模型与生产者代码 + 真实数据三方矛盾：genre 声明 str 而 seed_parser 写 list、golden_opening_chapters 声明 str 而生产者写 int、world_version 未声明 | error | P2
- 证据（实际运行）:
  ```
  $ uv run python -B -c "NovelConfig.model_validate(json.load('novel-output/xinghuo-ranqiong/novel.json'))"
  3 validation errors: genre(Input should be a valid string, input_type=list),
  golden_opening_chapters(input_value=3, input_type=int), world_version(Extra inputs are not permitted)
  ```
  - 生产者代码本身就写矛盾形状: pipeline/seed_parser.py:117 `novel_json["genre"] = [g.strip() …]`（list）、:131 `novel_json["golden_opening_chapters"] = 3`（int）；
  - schemas/novel.py docstring 声称 "the model uses the producer-authoritative name target_word_count; g6.py now reads it"——D26 只对了键名（target_word_count ✓），**类型与键集从未对照生产者**；g6 消费者本身仍是裸 dict（F210），故当前零触发。
- 影响: 该模型若按 docstring 接线到 g6 会在每个真实项目上抛 ValidationError——"单一信源"模型连形状都是错的，F210 的修复成本被低估。
- 建议方向: `genre: str | list[str]`、`golden_opening_chapters: int`、补 `world_version`（或 producer 停写）；接线前必须以真实 novel.json 为 fixture 加回归。
- 定级依据: P2（未接线故潜伏；但属 schema 单源区的形状级错误）。

### F241 | ProgressDoc 键空间与真实 progress.json 不符：completed_skill_names 在真实运行中从未产出 | error | M
- 证据: 真实 novel-output/xinghuo-ranqiong/progress.json 顶层键 = {current_scorer_agent, scoring_history}——无 completed_skill_names、无 skills；而 schemas/state.py ProgressDoc 声明 {skills, completed_skill_names, scoring_history}，dispatcher/modes/codex.py:34-46 `_record_completion` 写的恰是 completed_skill_names/skills。两个 writer（codex CLI 路由 vs pipeline API 路由）各写一半键空间，真实运行只走了 API 路由。
- 影响: ProgressDoc 目前零消费者（F210）故无直接破坏；g_dispatch 读 completed_skill_names 对该真实项目将得空列表。registry 亦未收录 progress.json（见 F242 注）。
- 建议方向: 统一 progress.json writer 与键空间，schema 注明双路由。
- 定级依据: M（死模型键空间漂移，无现行消费者）。

### F242 | truth-files.yaml 注册表：context/review-checklist-N.json 是唯一"参数化形态概念"却无 patterns 映射也无 glob 覆盖——56 个真实实例 resolves() 全 False | error | P2（潜伏）
- 证据（实际运行）:
  ```
  $ uv run python -B -c "…遍历 13 个 patterns + 31 个 globs 对全部含 N 概念做参数化覆盖检查…"
  parametric-shaped concepts lacking pattern entry AND glob coverage:
     context/review-checklist-N.json
  $ resolves('context/review-checklist-1.json', reg) -> False   # 真实 corpus 有 56 个实例
  $ normalize_to_glob / dag_key('context/review-checklist-N.json') -> 原样返回（含 N 字面量）
  ```
  - 对照: 其余全部参数化概念（chapters/chapter-N.md 等 13 个）都有 patterns 条目；audits/chapter-N-review-summary.md 虽无 pattern 但被 audits/chapter-*.md glob 兜住；唯独 review-checklist-N.json 两头落空——契约若声明它只能写字面量 "…-N.json"，DAG 里与真实编号文件永不相交（dag_key 不同键）；
  - schemas/registry.py TruthFilesRegistry 只验形状（16 kind/extra=forbid/non-empty），**无"参数化形态概念必须有 patterns 条目"的引用完整性校验**；
  - 附带（M 级，并入本条）: 真实 corpus 顶层 progress.json、config-change-log.jsonl、pipeline-state.json.lockfile 均 resolves()=False——注册表自称 "Canonical file vocabulary"，pipeline-state.json 已收录而同为 pipeline 产物的 progress.json 未收录，收录标准不一致。
- 影响: 今日无技能契约声明该文件（grep skills 零命中）→ 潜伏；一旦声明或 DAG 工具扫描真实文件，56 个实例全部不可解析/孤键。
- 建议方向: 补 patterns 条目（`context/review-checklist-*.json`）或 glob；registry schema 加引用完整性 model_validator；progress.json 等补录或注明排除原则。
- 定级依据: P2（注册表一致性缺口，潜伏）。

### F243 | OutputKind.EPHEMERAL 是数据死值：72 个契约技能 0 个使用 kind: ephemeral，executor 唯一消费分支数据不可达 | dead-wire | M
- 证据: `grep -rl "kind: ephemeral" skills/*/SKILL.md | wc -l` → 0（本轮全量 frontmatter 扫描 kind 分布: artifact×41 + report×31 = 72）；legacy.py:42 定义 EPHEMERAL，唯一消费分支 executor.py:84（EPHEMERAL→chapter 默认）在真实契约数据上永不可达（AGENTS.md "kind: ephemeral skills migrate to kind: artifact" 的迁移已完成，枚举值成为遗留）。
- 建议方向: 删除枚举值 + 分支，或注明保留理由。
- 定级依据: M（dead-wire 无现实影响）。

---

## 二、误报/事实修正（初审 23 + r1 7 + r2 6 = 36 条逐条复读）

**结论: 0 条整条误报。** 全部 36 条经本轮独立复读（代码重读 ×26、实跑复现 ×7、grep 复核 ×12、coverage/文档对照 ×3）成立。r1 对 F210 汇总"fields 已接线"的勘误与 r2 的全部维持。逐条明细:

| 编号 | 本轮独立验证方式 | 结论 |
|---|---|---|
| F201 | fields.py:55-64 复读（`if not matched` 仅零匹配回退） | 成立；维持 r1 降级异议 |
| F202 | genre_config.py:93-94 复读 | 成立 |
| F203 | codex.py:75 复读 `\{[^{}]*\}` | 成立 |
| F204 | executor.py:127,147 复读（无 returncode/stderr 守卫） | 成立 |
| F205 | executor.py:86-91 复读 + `grep -c G4 tests/round-exec.sh` → 0 | 成立 |
| F206 | codex.py:27-48 复读（无锁 RMW） | 成立 |
| F207/F208/F209 | paths.py:104-121/:112/:143 本人复读 | 成立 ×3 |
| F210 | gates 目录 grep NovelConfig/ScoreReport/ChapterPlanning/ContextComposing/VolumeOutlining → 零命中；**本轮补强**: context_composing "9 节"规则值与真实 corpus（chapter-55-context.md 15+ 节）矛盾；F240 再证 novel 模型形状也错 | 成立（范围继续扩大） |
| F211 | decisions.py:16 vs enums.py 双 Severity 复读；**本轮真实数据加证**: 真实 decisions 用 blocking/critical/info/minor——两域都不含 | 成立 |
| F212 | decisions.py:36 + AGENTS.md:70 复读 | 成立 |
| F213 | pacing_design.py:7（[20,30]）vs :55（[15,35]）本行复核 | 成立 |
| F214 | 真实 genre-config.json 8 键（本人 json.load）+ ownership.py:38-50 9 键复读 | 成立 |
| F215 | legacy.py:93-113 复读无缓存；量测 r1/r2 两轮一致（8.4/8.7ms） | 成立 |
| F216 | tests/coverage/z_e388ac45cc02448c_cli_py.html → 0%；tests/ 无 cli 引用（conftest 仅注释提及） | 成立 |
| F217/F218 | executor.py:77-80,107-116 / codex.py:53-54,74,114-116 复读 | 成立 ×2 |
| F219 | internal.py 报错原文复读（"Set SHENBI_LLM_API_KEY to use API mode"） | 成立 |
| F220 | grep 仅 docs/superpowers/plans/archive/ 命中 | 成立 |
| F221 | _scoring_base.py:37 `class ScoreReport` 复读 | 成立 |
| F222 | grep 证实 concepts[].glob 零消费；**补充**: 真实 yaml 中也无任何 concept 携带 glob: 键（零数据零消费双死） | 成立（+补充） |
| F223 | pacing_design.py:97-123 复读；**本轮实跑真实生产文件升级证据**: from_markdown(真实 rhythm_principles.md) 解析出 scene_types=[dialogue, transition, 战斗, 对话, 日常, 修炼, 揭示, 情感]——dialogue/transition 系从 86/103/104/109 行"单调性检测规则/章尾收束方式"散文污染而来（真实场景类型列表应只有 6 个中文词），**污染已实际发生于生产数据并通过 G4 校验** | 成立（假设性→实发） |
| F224 | dispatch_helper.py:581-605 本人复读: `contract.get("reads")` 已被 legacy._validate 归一化为 list[str] → `isinstance(dict)` 恒假 → `if fields:` 不可达；check_fields_exist 生产调用方 grep 零命中 | 成立 |
| F225/F226 | `get("key")/["key"]` grep 零命中；no_op_behavior 仅 docstring；skip_paths 无调用方传值 | 成立 ×2 |
| F227 | 复核成立；**范围补充**: skills/shenbi-review-pov/SKILL.md:49,74 正文亦指示读 genre-config.json 的 povMode（prose 层同漂移，其契约 reads 只声明裸文件无 fields） | 成立（+扩） |
| F228/F230 | paths.py:112-117 提前 return / pacing_design.py:82 初始化后无赋值 :129 传 [] | 成立 ×2 |
| F229 | read_keys grep 零命中（仅 lint_contract_graph.py 的局部变量同名 all_read_keys，非字段消费） | 成立 |
| F231 | 本人复跑 phase_of: 5 个漏账技能与不存在技能同返 None；deps.json 位于 tests/tiers/ | 成立 |
| F232 | genre_config.py 仅 7 validator 复读；**补充**: 真实 genre-config.json 恰好带 approval+8 键（本轮 model_validate PASS），真实数据未触雷 | 成立 |
| F233/F234/F235/F236 | fields.py:44-51 字典覆盖 / paths.py:155-157 首匹配 / g4 genre_config.py:40 errors[:5] / contracts/registry.py:62 | 成立 ×4 |

**事实修正（不推翻条目）**: 无新增。r1 已修正的 F210"fields 已接线"子句维持勘误状态。

---

## 三、覆盖空洞

1. **无任何"契约健康"机制扫真实 corpus**（F237/F238/F239 共同成因）: G2 decisions 分支只在 T1 路由运行、pipeline 跳 G2、_validate_json_output 只拦新写——89 个在案 decisions 文件、13 个 truth 文件、全部 truth/*.md 从未被任何 schema/门对账过。本轮三个人工扫描脚本（/tmp/z2r3/field_scan.py 等）可直接产品化为 CI 检查。
2. **生产者侧 schema 传播缺失**（F237 根因）: 派发 prompt 仅一行注记且仅多输出文件时注入；enum 词表不在任何 SKILL.md。schema 是"验消费者"而不是"教生产者"。
3. **fixture 与活生产模板无一致性防线**: style-profile fixture 11 节 vs 生产 8 节"（推测）"模板；pending-hooks fixture 记录式 vs 生产表格式——fixture 是 G0.9 意义上的"真实产物"，但其真实性无保鲜机制，成为假基准（F238/F239 根因）。
4. **注册表引用完整性无校验**（F242）: TruthFilesRegistry 验形状不验"参数化概念必有 pattern"；progress.json 等顶层文件收录标准不一致。
5. **progress.json 双 writer 键空间分裂**（F241）: codex 路由与 API 路由各写一半。
6. r1/r2 的 must-test 清单全部维持（dispatcher/cli.py 整模块、SHENBI_G1_SKIP_READS/dispatch_exception 路径、legacy 归一化守卫、decisions rationale 长度、registry version!=1、genre_config 规则 7 与 ①②）。

---

## 四、严重度异议表（无权改定级，仅提异议）

| 编号 | 现级 | 异议 | 依据 |
|---|---|---|---|
| F201 | P1 | **维持 r1 的 P1→P2 强异议** | 本人复读确认生产调用点死代码（F224），当前触发面=0 |
| F237 | P1（本轮主判） | 弱异议可升 P0 | 决策表 P0"生产契约静默违反"字面命中在案 corpus（95% 违反且无人发现）；因违反主体是 enforcement 出现前的历史快照，主判 P1 |
| F210 | P2 | 维持 r1 弱异议 P2→P1 | 本轮 F240/F243 再加证："单一信源"不仅未接线，已接线检查点的形状/规则值也错 |
| F223 | P2 | 维持 P2，建议修复优先级上调 | 本轮证实污染已发生于真实生产数据（非假设），但后果限于 G4 输入质量，仍属边界缺陷 |
| 其余 31 条 | — | 无异议 | 与决策表逐条对照一致 |

---

## 五、本轮强制角度发现摘要

### (a) producer/consumer 键空间三方对账
- **DecisionsDoc**: schema Literal（basis×4/handling×4/severity×3）vs 生产者（basis 60+ 自由文本值/41% 越界、handling 30+、severity 5 个域外值、revision 文件 10+ 顶层多余键）vs 执行点（g2/g4/写时校验）→ F237；
- **NovelConfig**: str vs 生产代码 list/int + 未声明键 → F240；
- **ProgressDoc**: completed_skill_names 无真实产出（双 writer 分裂）→ F241；
- **legacy.py 归一化分支死活**（全量 74 SKILL.md frontmatter 扫描，r1 计数精确复现）: reads 228 str + 35 dict+fields + 2 dict-nofields（均为 foreshadowing-lifecycle）；writes 87 dict + 0 str（str 分支死）；updates 36 dict；meta mode×123/key×18/no_op×4；fields 非 list[str] 守卫分支死（0 实例）；reads dict 多余键静默丢弃分支死（0 实例）；kind: artifact×41+report×31，ephemeral×0（→F243）；
- **registry 一致性**: 参数化概念覆盖矩阵唯一缺口 review-checklist-N.json → F242；三源计数一致（r2 已证，本轮未推翻）；DepsDoc 对真实 deps.json PASS，phase_of 对漏账/不存在技能不可区分（F231 复证）。

### (b) 真实数据形态对照（novel-output/xinghuo-ranqiong/）
- 89 decisions.json → F237；真实 novel.json → F240；真实 pending_hooks.md → F238；真实 progress.json → F241；35 字段声明 × 真实 truth/style 文件 → F239；真实 rhythm_principles.md → F223 实发证据；真实 genre-config.json → GenreConfig PASS（F232 未被真实数据触发）；1229 个真实文件 resolves() 覆盖扫描 → F242（210 个不可解析，其中非 runtime-infra 的 69 个）。

## 汇总

| 类别 | 数量 | 条目 |
|---|---|---|
| 漏报 | 7 | F237(P1)、F238(P1)、F239(P2)、F240(P2)、F241(M)、F242(P2)、F243(M) |
| 误报 | 0 整条 | 36 条全部成立（4 条获本轮证据加强/范围补充: F210/F211/F222/F223；1 条范围扩: F227） |
| 覆盖空洞 | 6 项 | 见第三节 |
| 严重度异议 | 5 | F201 维持降级异议；F237 弱升 P0；F210 维持弱升；F223 优先级上调；余无 |

### 收敛判定

**未收敛。** 三轮累计: 初审 23（P1×3）→ r1 +7（P1×1）→ r2 +6（P1×1）→ **r3 +7（P1×2、P2×3、M×2）**。对照 r2 提出的闭合条件（"下一轮在 contracts/skills/* 内不再产出 P1 且 P2 增量 ≤2"）: 本轮 P1×2 虽不在 contracts/skills/ 子包（分别在 contracts/schemas/decisions.py 键空间与 ownership/hooks 契约假设），但 P2 增量 3 > 2，条件不满足。

结构性观察: 本轮 7 条新 finding 全部来自前两轮未用过的"代码↔真实数据对账"维度，且全部落在**已有文件**上（decisions.py、ownership.py、fields.py 声明面、novel.py、truth-files.yaml、legacy.py）——说明前三轮的"逐文件语义深读 + 调用方 grep"对该维度有系统性盲区（与 Z3-r3 单轮 5 条的体验一致，该方法在本区同样最高产）。缺陷家族从 r2 的三个扩为四个: ④"**契约 schema ↔ 生产者从未对账**"家族（F237/F238/F239/F240/F241），其修法不是逐条补丁而是建立"真实 corpus 契约健康扫描"防线（覆盖空洞 1 的三个脚本可直接产品化）。

建议下一轮闭合条件: 新角度若不再产出 P1 且 P2 ≤2 可收敛；优先修复顺序建议 F224+F239 联动（先校准字段声明再接线过滤）、F237（词表进 prompt 或放宽 schema）、F238（hooks 格式二选一）——三条都是一次修复消一族的高杠杆点。
