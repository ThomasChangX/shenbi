# Spec #123 · 评审输入对齐批（review-input-alignment）：共鸣领头章计划字段对齐＋节奏审计阈值单源

**日期**：2026-11-24｜ **系列**：实现审计清偿批（expert-panel-implementation-audit · 2026-11-24 八席审计，协调者逐条亲验）｜ **状态**：Design（r1，2026-11-24）｜ **优先级**：🟠 P1
**动机证据**（HEAD `3311a0af`）：
- **T1 面（共鸣审稿看不到它要判的段）**：`skills/shenbi-review-resonance/SKILL.md:16-18`（`file: plans/chapter-N-plan.md` ＋ `fields: [1. 当前任务]`——领头章的计划被字段过滤到只剩第 1 段）vs `:19`（跟班章 `plans/chapter-{N+1}-plan.md` 整读）vs `:229-230`（硬二元检查「§6 章尾改变发生 … `plans/chapter-N-plan.md` §6」「hook 账履行 … §7」）。2026-11-24 复跑（契约过滤函数＋真计划文件）：`leader-N view: H2s kept=['1. 当前任务'], §6 kept=False, §7 kept=False`；真实 ch47 报告对两格均填「已达成」，证据列写的是「§6（章尾钩：信物钩）」「§7（金句位…）」——**判官对没看到的段出具了「已达成」**；
- **T2 面（评审技能引用不存在的配置键）**：`skills/shenbi-review-group-character/SKILL.md:265`（「读取 `genre-config.json` 的 `povMode`」）、`skills/shenbi-review-group-factual/SKILL.md:201`（「连续超过 `genre-config.json` 的 `maxConsecutiveQuest` 章 QUEST 无 FIRE = warning」）、`:230-231`（报告模板 `maxConsecutiveQuest: X/Y`／`maxGapFIRE: X/Y`）vs `skills/shenbi-genre-config/SKILL.md:435`（「顶层仅十二键」）与配置校验器（三键零命中）；真实 `novel-xinghuo-vol1/genre-config.json` 无此三键；`review-group-factual` 契约不读 `outline/rhythm_principles.md`（QUEST／FIRE／CONSTELLATION 词表与阈值的实际所在）；真实 ch49 pacing 报告自述「`genre-config.json` 未设 `maxConsecutiveQuest`…」后照常出具结论——阈值由判官即兴；
- **与 #117 的分工**：#117 管审稿**产出**侧（证据是否成立），本件管审稿**输入**侧（它要判的东西是否看得到、有没有判据）。

**触及的不变量维度**：情绪节奏（弱关联——T2 为节奏审计〔蓄压／释放〕提供阈值单源，不改门检判据；T1 改审稿输入窗口）；叙事纪律（POV/声口）（弱关联——T2 对 `povMode` 引用的处置）

---

## 0. 根因

- **T1**：字段级读（Layer B）接入时，为领头章计划声明了只含 §1 的 fields，而同一技能的硬二元检查引用 §6／§7；跟班章读走的是另一条无 fields 的声明。同一技能内两条读口径不对称，判官在不告知缺段的情况下把「未看到」当成「已达成」。
- **T2**：节奏阈值曾计划放 genre-config 顶层；genre-config 契约收敛为十二键后，评审技能文字没有同步。阈值实际落在项目文件 `outline/rhythm_principles.md`，而 factual 审稿不读它。这是 #93（阈值权威化，已归档）「散文引用 vs 权威来源」的同类残留——#93 的 lint 覆盖 src 常量，不覆盖 SKILL 散文里的配置键引用。

**用户裁定（待裁两项）**：
- (a) **T1 的执行时点**：共鸣分是 #115 T3 人工面板的预测变量；改判官输入＝共享仪器变更（`docs/superpowers/meta-review-protocol.md` 触发面 1）。建议「面板取数完成前不改」（样本章已有分数按现口径测），T1 排在面板取数之后执行；若选择先修，则 #115 T3 样本须在修后重评；
- (b) **T2 的阈值落点**：`outline/rhythm_principles.md`（项目级，已有词表）vs genre-config（框架级十二键）。建议前者＋契约 reads；plan 期确认该文件的 producer 写法稳定。

**备选案已评估并否决**：「去掉 fields 整读计划」——8 段整读徒增 token，只需 §1／§6／§7；「把 §6／§7 检查降为非硬」——与技能设计意图相反；「新增 genre-config 键」——十二键契约刚收敛（#93），再开键面是倒退。

## 1. 任务分解

### T1 · 共鸣领头章计划字段对齐（时点受裁定 a 约束）
- `review-resonance` 契约：领头章 `plans/chapter-N-plan.md` 的 fields 改为「1. 当前任务／6. 章尾必须发生的改变／7. 本章 hook 账」（节名以 planning 输出模板为准——与 #111 同款的「producer 模板 vs 消费契约」对齐检查）；跟班章同口径（或保持整读，plan 期按 token 差定）；
- 「未看到不得判已达成」的兜底：SKILL 检查表加一行——所引计划段不在输入中 → 该格填「无法核对」而非「已达成」（与 #109 的饿死词族同向）；
- 判据：`just lint-contract-fields` 过；dry-run manifest 显示领头章计划 resolved_fields 含三段；fixture 测试：领头章 §6／§7 的内容进入派发 prompt。

### T2 · 节奏审计阈值单源
- 阈值与词表单源：`maxConsecutiveQuest`／`maxGapFIRE` 及 QUEST·FIRE·CONSTELLATION 词表落 `outline/rhythm_principles.md`（或裁定 b 的落点）；`review-group-factual` 契约 reads 加该文件（字段级）；未设值时的缺省与披露文案写明；
- `povMode` 引用处置：改引 genre-config 既有 POV 相关键，或删引用改读角色声口档案——plan 期按现有键面定；
- 新 lint（小面）：SKILL 散文里「`genre-config.json` 的 `<key>`」形态引用的键必须存在于 genre-config 契约键集（#93 lint 包含式向散文面的延伸，不新建工具）；
- 判据：三键幻影引用零残留（`git grep`）；lint 红测（造一个幻影键引用 → FAIL）；dry-run manifest 显示 factual 派发含 rhythm_principles 字段。

## 2. 验收
1. T1–T2 判据全绿；
2. 行为面（随令，≥3 章实弹对照）：resonance 报告 §6／§7 格的证据列引用计划原文；pacing 报告的阈值行引用 rhythm_principles 的数值。

## 3. 风险
- **T1 会改变判官输入** → 共鸣分分布可能下移（领头章 §6／§7 从「已达成」变为如实判定）。这正是修的目的，但它是一次仪器变更：所有以 resonance 分为输入的机制（#106 floor、#115、#103）须在变更日志登记；面板取数先于本件 T1（裁定 a）；
- **共享文件面**：`review-resonance/SKILL.md` 与 #115 T4 同文件——re-anchor；`review-group-factual`／`review-group-character` 的 SKILL 与 #117（声明不改 review SKILL 文本）无冲突；genre-config SKILL 与 #102 无交集；
- **在飞项目**：T2 的缺省值须对 vol1 现有 `rhythm_principles.md` 做一次只读核对（已有 QUEST／FIRE 词表），不重写项目文件。

## 4. 立项预答（价值门 ④⑤ 前置）

**④ 博弈路径清单**：
- fields 改了但 planning 输出的节名漂移 → 缺段走逃逸舱（整读＋WARN）而非静默只剩 §1——可接受的降级，且 manifest 可见；
- 判官仍把缺段判「已达成」→ SKILL 兜底行＋#117 T2（位置／引述校验）兜底；
- 阈值单源后项目文件不写值 → 缺省值＋披露；
- lint 只查反引号形态 → 散文变体漏网（登记为已知边界；报告侧由 #117 T1 的 parser 覆盖）。

**⑤ 候选机制清单**（buy-before-build）：字段级读（Layer B，既有）与逃逸舱 WARN（既有）；`outline/rhythm_principles.md`（既有项目文件，升格为阈值权威源）；#93 的阈值对账 lint 包含式（延伸到 SKILL 散文面，不新建工具）；planning 输出模板的节名单源（#99 已做的标题语法单源化）。无新建机制。
