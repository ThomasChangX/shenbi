# Spec #118 · 门标定落地批（gate-calibration-landing）：七项裁定执行＋content_uniqueness P1 修＋三残行红测补

**日期**：2026-11-20｜ **系列**：spec #116 裁定落地（用户 2026-11-20「全部同意」）｜ **状态**：Design（r1，2026-11-20）｜ **优先级**：🔴 P0（12-20 升格锚前 T8 须落地）

**裁定来源**：`docs/framework/gate-calibration-proposals.md` 裁定记录节（2026-11-20 用户逐项裁定）；分类回填已在 `docs/framework/gate-power-baseline.md`（29/32 行）。本件执行全部**行为改动**类裁定——每项四栏（现状/提案/红测/回滚）以提案文档为权威，本件只做任务分解与验收。

**动机证据**：50 章回放（`reports/2026-11-20-gate-power-vol1.md`）＋Goodhart r1/r2——voice_density 14/50 must_fix＋r2 15/18 主导失败（词表阈值与真实散文 0-1 个/章错位）；hook 15/50 仅单字过门且 `还`=38/`账`=38 与账房腔同词表；protagonist roster 双 append（`chapter_drafting.py:495`/`:508`）＋仅代词 `他` 50/50 ≥3；transition 中位 0 vs 阈 5；simile 56% WARN 使劝谏通道失聪且计量吃 PRE/POST；ending 47/50 None；**content_uniqueness 生产从未运行**（门读 `rd/project-output/chapters` 而真实章在 `rd/chapters/`——50 章回放 0 行发射，#116 仪表挖出的死门）；三残行（payoff_density/quote_type/provenance_anchor）无红测无法诚实分类。

**触及的不变量维度**：门检面（threshold-authority #93 单源纪律适用——所有阈值/词表改动走既有单源，不另立副本）；无载体/声明面改动。

## 立项预答栏（v7.1 义务）

**④ 博弈路径清单**（假设本件全部实施，根因「阈值按单书调参且方向被『不过就放宽』主导」能否复发）：
- 新阈值再失配（新语料分布漂移）→ 复发路径存在，但 mitigated：gate-power 仪表＋baseline 期望点火带列＋恒真哨兵构成复发可见面（本批每 task 验收含「重跑 gate-power 刷新点火带」义务）；
- 落地批自身「不过就放宽」惯性 → voice_density B 是**两级化**非放宽（hard 臂收紧到在场性、密度降劝谏）、hook A 是收紧（单字降级）；transition B 是收紧（封顶贴近观测）；无一项走纯放宽方向；
- 红测随阈值同步改钉被跳过 → 每 task 判据显式含红测改钉＋带内/带外双向样本（C1 义务继承）；
- 裁定被静默扩大（顺手改未裁定门）→ 验收含「`git diff` 面止于裁定七门＋content_uniqueness＋三残行红测」。
- **结论：无仍通路径**——复发可见面（仪表+哨兵）正是 #116 的交付物，本批是它的第一个消费者。

**⑤ 候选机制清单**（buy-before-build）：
- 阈值单源/allowlist/strict → **#93 threshold-authority 既有机制全复用**（`tools/lint_threshold_reconciliation.py --strict` 执法新阈值一致性）——覆盖 ~90%，不新建；
- 变异负例红测 → **#116 T4 变异引擎 `tools/gen_gate_power_fixtures.py` MUTATIONS 注册表扩展**（T8 三残行＋各 task 改钉）——覆盖 ~100%，不新建；
- 回放取数/点火带刷新 → **`just gate-power`**（#116 T1）——覆盖 100%；
- SKIP 显式化（T7）→ 无既有机制（门现路径是静默 return）——最小新建（一个 SKIP check 行发射）；
- ending 扩分类器 → 无既有机制（`ending_archetype_of` 单函数四分支）——最小扩表。
- **结论：五件复用两件最小新建，无 ≥60% 重叠的既有物可整件升格。**

---

## 0. 根因

spec #116 已证：门禁以「形态可过」为设计目标、阈值按单书逐次调参且方向被「不过就放宽」主导；A 类散文门恒真、判别力外包给无判别力的 LLM 判官。用户已逐项裁定修法（2026-11-20）；本件是裁定的机械执行面——**不重开裁定、不扩大范围**。

## 1. 任务分解（每 task：实现＋红测改钉/新增＋重跑 gate-power 刷点火带＋baseline 行同步）

### T1 · voice_density 两级拆分（裁定 B）
- `voice_lexicon.py`/`chapter_drafting.py:1391-1439`：hard 臂改「逐字口癖在场 ≥1」（absent=0 才 FAIL）；密度下限（原 ≥2 语义）降 WARN 报告行；genre config 覆盖键同步两级化（`voice_density_min.min_per_chapter`→在场键＋密度键，向后兼容旧键读入并 WARN deprecate）；
- 判据：红测 `test_voice_stripped_fails_voice_density_gate` 改钉（0 个→FAIL）；新增三态样本（≥1 过 / 0 FAIL / 密度带外 WARN）；50 章重跑——14 FAIL 章中新 hard 臂 FAIL 数＝口癖完全缺席章数（预期小部分），其余转 WARN；`lint_threshold_reconciliation --strict` 绿；baseline 行期望点火带＋归因同步。

### T2 · hook 多字/结构臂（裁定 A）
- `_check_chapter_end_hook`（`chapter_drafting.py:1161-1235`）：窗口命中改「多字张力词 ∨ ？ ∨ 账目行」任一为 hard；单字-only 命中降 WARN 报告行；`tools/gate_power_replay.py` 诊断镜像（`HOOK_TENSION_RE`/`SINGLE_CHAR_TENSION`）同步改（回滚栏义务）；
- 判据：红测改钉（单字-only 样本→WARN 非 FAIL；多字/？/账目行样本→PASS；全灭→FAIL 三态）；50 章重跑——15 单字-only 章转 WARN；baseline 同步。

### T3 · protagonist roster 去重＋名字下限（裁定 A＋B；C 推迟）
- `_load_protagonist_names`（`:483-516`）去重双 append（`:495`/`:508` 二选一）；名字（非代词）单独 ≥1 下限（或 POV 声明替代——实现取 ≥1 简单面）；C（阈值重标定）明示推迟至本 task 后重跑取数；
- 判据：roster 单测（frontmatter＋YAML 双源只入表一次）；红测改钉（名字 0/代词 ≥3 样本→FAIL）；50 章重跑刷中位/最小；baseline 同步。

### T4 · transition per-1000 密度重标定（裁定 B）
- `_check_transitions`（`:929-954`）：绝对阈 `max(5, wc//1000)` → per-1000 密度封顶（初值按观测分布定标：中位 0 → 封顶取现语料 P95 量级，实现期从重跑数据取值并写死依据注释）；
- 判据：红测改钉（flooded 样本仍 FAIL；正常章 PASS）；50 章重跑零新 FAIL（观测带内）；`lint_threshold_reconciliation --strict` 绿；baseline 同步。

### T5 · simile 计量换装＋路由（裁定 C＋A；B 推迟）
- `_check_simile_band`（`:1289-1313`）：计量面 `ctx.content`→`strip_narrative_body` 口径（M7 对照列转正）；WARN→报告行（不进 WARN 通道）；B（重设带）推迟注释；
- 判据：红测改钉（flooded→报告行存在且 WARN 通道无行）；50 章重跑 28 WARN 归零（转报告行）；baseline 同步。

### T6 · ending 扩分类器（裁定 A，限工作量）
- `ending_archetype_of`（`:519-536`）：采样 vol1 47 个 None 收尾（维护者侧采样清单入 task report），归纳 ≤4 新 archetype 形态扩表；**若扩后 None 率仍 >50% → 停手出 retire 提案回裁（不自行退役）**；
- 判据：扩表红测（每新 archetype 至少 1 真实章样本归类）；50 章重跑 None 率数字入报告；baseline 同步。

### T7 · content_uniqueness P1 修（裁定二）
- git 考古 `project-output/chapters` 断链时点（task report 记结论：坏了/从未活过）；门比对目录对齐 `rd/chapters/`；目录缺席/基数 ≤1 时发射显式 SKIP 行（含原因，不再静默）；修后重跑 50 章 gate-power 取**史上首份真实点火数据**；
- 判据：SKIP 显式红测（空目录→SKIP 行非静默）；重跑数据落 baseline（期望点火带首填）；若首份数据显示高误报 → 记 finding 不放宽（回裁）。

### T8 · 三残行红测补＋分类收口
- `MUTATIONS` 扩三变异：payoff_density（memo_v3 前置物章删 payoff 段）、quote_type（引号型破坏）、provenance_anchor（来历锚违例构造）；红测绿后回填三行分类（预期 floor-untested）；
- 判据：三红测 PASS；baseline 三行分类清偿——**升格锚前完成则 12-20 CI 无红**（本 task 是全件时限约束项）；若本件整体晚于 12-20，ESCALATION_DATE 按裁定周期顺延须回裁。

## 2. 验收
1. T1-T8 判据全绿（每 task 含红测双向＋50 章重跑＋baseline 同步三件套）；
2. `git diff` 面止于裁定范围（七门＋content_uniqueness＋三残行＋镜像/测试/baseline/docs）——无未裁定门被改；
3. `just check` 全绿（含 threshold reconciliation strict＋恒真哨兵零 WARN 残行）；
4. 50 章重跑报告落 `reports/`（前后对照：14→? FAIL/15 单字转 WARN/28 WARN 归零/None 率/首份 uniqueness 数据）；
5. 提案文档裁定表逐项标记「已执行」＋baseline 期望点火带列首填。

## 3. 风险
- **共享文件面**：`chapter_drafting.py` 独占（#116 已核无在飞冲突）；`voice_lexicon.py` 与 #96 反 AI 批潜在同面——#96 仍 Active 未开跑，先落子权在本件；`justfile`/`tools/` 与 #116 产物共用（本件是同一谱系）；
- 单书语料（B5）：全部新阈值标注「vol1 定标，跨书重跑复核」；voice_density 两级化后的 hard 臂在新语料可能过严——回滚单 commit（提案文档回滚栏为权威）；
- 红测改钉丢旧断言：每 task 改钉保留「原 FAIL 方向样本」防全绿漂移（C1 双向义务）；
- T6 扩分类器工作量失控：限 ≤4 新形态，超出即停手出提案回裁。
