# Spec #118 · 门标定落地批（gate-calibration-landing）：七项裁定执行＋content_uniqueness P1 修＋三残行红测补

**日期**：2026-11-20｜ **系列**：spec #116 裁定落地（用户 2026-11-20「全部同意」）｜ **状态**：Design（r2.1，2026-11-20——阶段 3 设计审查修订：C-1/I-1..I-8/M-1..M-6 全采纳＋重审两新问题清偿，见 task report）｜ **优先级**：🔴 P0（12-20 升格锚前 T8 须落地）

**裁定来源**：`docs/framework/gate-calibration-proposals.md` 裁定记录节（2026-11-20 用户逐项裁定）；分类回填已在 `docs/framework/gate-power-baseline.md`（29/32 行）。本件执行全部**行为改动**类裁定——每项四栏（现状/提案/红测/回滚）以提案文档为权威，本件只做任务分解与验收。

**动机证据**：50 章回放（`reports/2026-11-20-gate-power-vol1.md`）＋Goodhart r1/r2——voice_density 14/50 must_fix＋r2 15/18 主导失败（词表阈值与真实散文 0-1 个/章错位）；hook 15/50 仅单字过门且 `还`=38/`账`=38 与账房腔同词表；protagonist roster 双 append（`chapter_drafting.py:495`/`:508`）＋仅代词 `他` 50/50 ≥3；transition 中位 0 vs 阈 5；simile 56% WARN 使劝谏通道失聪且计量吃 PRE/POST；ending 47/50 None；**content_uniqueness 生产从未运行**（门读 `rd/project-output/chapters` 而真实章在 `rd/chapters/`——50 章回放 0 行发射，#116 仪表挖出的死门）；三残行（payoff_density/quote_type/provenance_anchor）无红测无法诚实分类。

**触及的不变量维度**：门检面（threshold-authority #93 单源纪律适用——所有阈值/词表改动走既有单源，不另立副本）；无载体/声明面改动。

## 立项预答栏（v7.1 义务）

**④ 博弈路径清单**（假设本件全部实施，根因「阈值按单书调参且方向被『不过就放宽』主导」能否复发）：
- 新阈值再失配（新语料分布漂移）→ 复发路径存在，但 mitigated：gate-power 仪表＋baseline 期望点火带列＋恒真哨兵构成复发可见面（本批每 task 验收含「重跑 gate-power 刷新点火带」义务）；
- 落地批自身「不过就放宽」惯性 → voice_density B 是**两级化**非放宽（hard 臂收紧到在场性、密度降劝谏）、hook A 是收紧（单字降级）；transition B 是收紧（封顶贴近观测）；无一项走纯放宽方向；
- 红测随阈值同步改钉被跳过 → 每 task 判据显式含红测改钉＋带内/带外双向样本（C1 义务继承）；
- 裁定被静默扩大（顺手改未裁定门）→ 验收含「`git diff` 面止于裁定七门＋content_uniqueness＋三残行红测」。
- **结论（r2 修正：原「无仍通路径」过强）**——三条 visible-but-unenforced 路径收窄处置入判据：①新阈值不在 #93 lint 覆盖面 → T1/T4 以单源断言测试执法（见 ⑤ 修正）；②回放镜像漂移 → T2 镜像↔门等价钉两例（PASS/WARN 两态；FAIL 全灭态由门红测改钉承担）；③逐书 config 清零在场臂 → T1 新在场键 validator 域 [1,5]（0 非法）。

**⑤ 候选机制清单**（buy-before-build；r2 修正两处复用主张——阶段 3 驳斥复核实证）：
- 阈值单源 → #93 lint 为 CONSTELLATION 单带工具（对本批阈值**零覆盖**，复用主张撤回）——r2 改为**可执行单源断言**：单测钉 `DEFAULT_VOICE_DENSITY_MIN`/transition 封顶常量＋仓内 grep 无裸副本（T1/T4 判据）；`lint_threshold_reconciliation --strict` 照跑（对其既有面不回归）；
- 变异负例红测 → **#116 T4 变异引擎 `tools/gen_gate_power_fixtures.py` MUTATIONS 注册表扩展**（T8＋各 task 改钉）——覆盖 ~100%，不新建；
- 回放取数/点火带刷新 → **`just gate-power`**（#116 T1）——覆盖 100%；
- SKIP 显式化（T7）→ **复用同文件既有 SKIP 行先例**（`_check_protagonist` chapter_drafting.py:1244-1252 SKIP-with-reason 同构发射，replay SKIP 桶现成可消费）——最小应用非新建；
- ending 扩分类器 → 无既有机制（`ending_archetype_of` 单函数四分支）——最小扩表。
- **结论（r2.1 计数修正）：两件复用（变异引擎/gate-power）＋lint 照跑非复用＋一件最小应用（SKIP 行）＋一件最小扩表（ending）＋一件最小新建（单源断言测试，I-2 处置），无 ≥60% 重叠的既有物可整件升格。**

---

## 0. 根因

spec #116 已证：门禁以「形态可过」为设计目标、阈值按单书逐次调参且方向被「不过就放宽」主导；A 类散文门恒真、判别力外包给无判别力的 LLM 判官。用户已逐项裁定修法（2026-11-20）；本件是裁定的机械执行面——**不重开裁定、不扩大范围**。

## 1. 任务分解（每 task：实现＋红测改钉/新增＋重跑 gate-power 刷点火带＋baseline 行同步）

### T1 · voice_density 两级拆分（裁定 B）
- `voice_lexicon.py`/`chapter_drafting.py:1391-1439`：hard 臂改「声口信号在场 ≥1」——**操作数＝`distinct_voice_signals`（r2/I-4 钉死：口癖精确串∪账房动词任一∪自嘲反则三类同计，absent＝三类全零，与 Goodhart 证据口径一致）**；密度下限（原 ≥2 语义）降 WARN 报告行；genre config 覆盖键两级化（r2/C-1 三条钉死）：
  - **(a) 旧键映射**：`voice_density_min.min_per_chapter`（存量活覆盖，如验收语料 vol1=2）读入**仅填充密度/WARN 臂**并 structlog WARN deprecate；在场/hard 臂由新键（`voice_density_min.presence_min`）治理、缺省 1——禁把旧键映射进 hard 臂（会使裁定在验收语料上静默不生效）；
  - **(b) 值域**：新在场键 validator 域 **[1,5]**（0 非法——堵逐书清零 hard 臂面）；旧键域维持 [0,5] 不变；
  - **(c) 触面**：`src/shenbi/contracts/skills/genre_config.py:146-148` validator 同步扩展＋`tools/lint_voice_meme.py:123-127`（旧键第二消费方）跟随密度键口径；契约升级纪律声明：存量 config 兼容读、无迁移工具需求（不新增必填键）。
- 判据：红测 `test_voice_stripped_fails_voice_density_gate` 改钉（0 个→FAIL）；新增三态样本（≥1 过 / 0 FAIL / 密度带外 WARN）；**单源断言测试**（钉 `DEFAULT_VOICE_DENSITY_MIN` 与新在场缺省 1＋仓内 grep 无裸副本，替代空转 lint 判据）＋`lint_threshold_reconciliation --strict` 照跑不回归；**实现首日离线重算 signals 分布把预期新 FAIL 数写进 task report（M-2：同义反复判据的校准钉）**；50 章重跑——新 hard 臂 FAIL 数＝离线重算预期数（缺席章）；其余 14→WARN；baseline 行期望点火带＋归因同步。

### T2 · hook 多字/结构臂（裁定 A）
- `_check_chapter_end_hook`（`chapter_drafting.py:1161-1235`）：窗口命中改「多字张力词 ∨ ？ ∨ 账目行」任一为 hard；单字-only 命中降 WARN 报告行；`tools/gate_power_replay.py` 诊断镜像（`HOOK_TENSION_RE`/`SINGLE_CHAR_TENSION`）同步改（回滚栏义务）；
- 判据：红测改钉（单字-only 样本→WARN 非 FAIL；多字/？/账目行样本→PASS；全灭→FAIL 三态）；**镜像↔门等价钉两例（r2/I-6：single-only fixture → 门 WARN ∧ `attribution.single_char_only` 真；多字/？/账目行 → 门 PASS ∧ 对应臂真——验收核数本身来自镜像归因，镜像漂移则数字失真）**；50 章重跑——15 单字-only 章转 WARN；baseline 同步。

### T3 · protagonist roster 去重＋名字下限（裁定 A＋B；C 推迟）
- `_load_protagonist_names`（`:483-516`）去重双 append（`:495`/`:508` 二选一）；名字（非代词）单独 ≥1 下限（或 POV 声明替代——实现取 ≥1 简单面）；C（阈值重标定）明示推迟至本 task 后重跑取数；
- 判据：roster 单测（frontmatter＋YAML 双源只入表一次）；红测改钉（名字 0/代词 ≥3 样本→FAIL）；**误报预期声明（r2/I-5）：50 章重跑名字缺席章数＝实测 X（预期 0；非 0 则记 finding 回裁，不放宽）**；50 章重跑刷中位/最小；baseline 同步。

### T4 · transition per-1000 密度重标定（裁定 B）
- `_check_transitions`（`:929-954`）：绝对阈 `max(5, wc//1000)` → per-1000 密度封顶。**封顶＝1.0/千字（r2.2 修正：阶段 3 审查员的 0.5 建议基于 82 章口径；协调者用门的精确口径（`word_count_md` 叙事体 CJK 分母＋`strip_narrative_body` 计数面）50 纯章形重算——median=0.000/max=0.809/top5 [0.343..0.809]，0.5 会对 max 章开火违反「零新 FAIL」；取 1.0＝max·1.24 裕度且贴近观测分布；P95≈0.36 作参照入注释；flooded 样本密度 ≫1 仍 FAIL；定标依据注释写死同次重跑数据，分母＝验收 4 同一次重跑）**；vol1 定标跨书重跑复核（B5）；
- 判据：红测改钉（flooded 样本仍 FAIL；正常章 PASS）；50 章重跑零新 FAIL（观测带内）；**单源断言测试**（钉封顶常量＋无裸副本）；`lint_threshold_reconciliation --strict` 照跑不回归；baseline 同步。

### T5 · simile 计量换装＋路由（裁定 C＋A；B 推迟）
- `_check_simile_band`（`:1289-1313`）：计量面 `ctx.content`→`strip_narrative_body` 口径（M7 对照列转正）；WARN→报告行（不进 WARN 通道）——**报告行形态＝`s=PASS`＋`per_1000` 载荷（r2/M-3：同 scene_concreteness 报告先例；baseline 行维持 discriminating 的依据迁移为「红测可捕获（改钉后）」，期望点火带填「WARN 通道 0 行」）**；B（重设带）推迟注释；
- 判据：红测改钉（flooded→报告行存在且 WARN 通道无行）；50 章重跑 28 WARN 归零（转报告行）；baseline 同步。

### T6 · ending 扩分类器（裁定 A，限工作量）
- `ending_archetype_of`（`:519-536`）：采样 vol1 47 个 None 收尾（维护者侧采样清单入 task report），归纳 ≤4 新 archetype 形态扩表；**若扩后 None 率仍 >50% → 停手出 retire 提案回裁（不自行退役）**；
- 判据：扩表红测（每新 archetype 至少 1 真实章样本归类；**样本载体＝`tests/fixtures/gate-power/` 真实章尾窗拷贝（r2/M-4：provenance 头义务＋整拷贝哈希一致，G0.9/G0.11——禁内联硬编码真实章文本）**）；50 章重跑 None 率数字入报告；baseline 同步。

### T7 · content_uniqueness P1 修（裁定二）
- git 考古 `project-output/chapters` 断链时点（task report 记结论：坏了/从未活过）；门比对目录对齐 `rd/chapters/`；目录缺席/基数 ≤1 时发射显式 SKIP 行（含原因，不再静默）——**SKIP 行复用 `_check_protagonist`（chapter_drafting.py:1244-1252）既有 SKIP-with-reason 同构形态（r2/M-1），replay SKIP 桶现成可消费**；修后重跑 50 章 gate-power 取**史上首份真实点火数据**；
- 判据：SKIP 显式红测（空目录→SKIP 行非静默）；**fixture 重摆（r2/I-1：`tests/fixtures/gate-power/project-output/chapters/` 下 chapter-1-duplicated.md＋donor chapter-3.md 移至 `FIX_DIR/chapters/` 并经 `gen_gate_power_fixtures.py --donor` 维护者侧重生成——G0.9 禁手造、G0.11 哈希纪律；旧路径残件删除）**；重跑数据落 baseline（期望点火带首填）；若首份数据显示高误报 → 记 finding 不放宽（回裁）。

### T8 · 三残行红测补＋分类收口（r2/I-7 收窄）
- **`MUTATIONS` 必建＝payoff_density 一件**（memo_v3 前置物章删 payoff 段——唯一零行为测试覆盖行）；**quote_type/provenance_anchor 以既有测试为证据链回填**（`test_spec76_voice_quote.py::test_g4cd_quote_type_three_point_sync` 走真实 g4 管线三场景点火；`test_spec83_provenance_anchor.py::test_provenance_mismatch_warns_and_match_green` 直调真实 helper——裁定依据：裁定记录要求「补负例后分类」，两行既有行为测试已满足分类证据义务，12-20 工期前不为 M-1 形态同源重复建测）；
- 判据：payoff_density 红测 PASS；baseline 三行分类清偿（payoff=红测链接；quote/provenance=既有测试文件链接＋注记）；**升格锚前完成则 12-20 CI 无红**（本 task 是全件时限约束项）；若本件整体晚于 12-20，ESCALATION_DATE 按裁定周期顺延须回裁。**执行序（r2/M-5）：本 task 独立于 T1-T7，宜最先实施（时限风险前置；任务编号不变）。**

## 2. 验收
1. T1-T8 判据全绿（每 task 含红测双向＋50 章重跑＋baseline 同步三件套）；
2. `git diff` 面止于裁定范围——**期望触面枚举（r2/I-8，核验＝hunk 落点全在枚举内）**：`chapter_drafting.py` 限定 `_check_voice_density`/`_check_chapter_end_hook`/`_load_protagonist_names`/`_check_protagonist_presence`/`_check_protagonist`/`_check_transitions`/`_check_simile_band`/`ending_archetype_of`/`_check_content_uniqueness` 九函数相关 hunk（r2.1 补 protagonist 检查处——名字下限臂的实现位在检查器非 loader）＋`voice_lexicon.py`＋`contracts/skills/genre_config.py`＋`tools/gate_power_replay.py`＋`tools/gen_gate_power_fixtures.py`＋`tools/lint_voice_meme.py`＋测试文件（negatives/replay 一致性/新增单源断言）＋fixture 重摆＋baseline/提案 docs＋`reports/`——无未裁定检查被顺手改；
3. `just check` 全绿（含 threshold reconciliation strict 照跑不回归＋单源断言测试＋恒真哨兵零 WARN 残行）；
4. 50 章重跑报告落 `reports/`（前后对照：14→? FAIL/15 单字转 WARN/28 WARN 归零/None 率/首份 uniqueness 数据）；
5. 提案文档裁定表逐项标记「已执行」＋baseline 期望点火带列首填。

## 3. 风险
- **共享文件面**：`chapter_drafting.py` 独占（#116 已核无在飞冲突）；`voice_lexicon.py` 与 #96 反 AI 批潜在同面——#96 仍 Active 未开跑，先落子权在本件；`justfile`/`tools/` 与 #116 产物共用（本件是同一谱系）；
- **genre-config 键迁移（r2/M-6）**：旧键映射错臂（→hard 臂则裁定在验收语料静默不生效——T1(a) 钉死映射＋测试断言）/ 新在场键域含 0（逐书清零 hard 臂——T1(b) 域 [1,5]）；
- **T7 fixture 重摆（r2/M-6）**：目录切换后旧布局 fixture 失联＋重生成须维护者侧跑变异引擎（G0.9/G0.11 纪律，禁手改）；
- 单书语料（B5）：全部新阈值标注「vol1 定标，跨书重跑复核」；voice_density 两级化后的 hard 臂在新语料可能过严——回滚单 commit（提案文档回滚栏为权威）；
- 红测改钉丢旧断言：每 task 改钉保留「原 FAIL 方向样本」防全绿漂移（C1 双向义务）；
- T6 扩分类器工作量失控：限 ≤4 新形态，超出即停手出提案回裁。
