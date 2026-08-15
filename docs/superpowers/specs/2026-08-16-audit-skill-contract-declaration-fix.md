> **Date:** 2026-08-16 | **Status:** Design | **Severity:** 🟠 P1
> **系列:** 2026-08-15 全项目深度审计 · 阶段 5 修复 spec（簇 C20）| **代表 finding:** D104 | **簇规模:** 21 条 | **严重度上限:** P1
> **范围:** skills/*/SKILL.md（约 20 个技能 frontmatter + 正文）、G4 契约 lint（已有雏形扩展）| **证据等级:** 实验佐证（Z8-a/b/c 三分区初审 + d1-03-frontmatter.log 74 skill 全量解析）
> **与既有 spec 关系:** #23（z8-contract-drift）的 reads/writes 补全面（F953/F1002/F1011 等）并入本 spec 统一处置；本 spec 为其 2026-08-15 轮扩展与机制化（对账 lint），#23 待归档合并由协调者执行

# C20 · 技能契约声明面断裂修复（skill-contract-declaration）

## 背景（根因 + 证据）

**根因**：SKILL.md frontmatter 契约（reads/writes/updates）与正文指令、真实产物、truth 词表互不闭合：正文读的文件 reads 没声明、契约声明的 writes 正文零步骤、写模式与 dedup 键错配、meta skill 从未纳入契约迁移范围——声明与行为双向漂移且无对账 lint（G4 只验 schema 不验闭合）。

代表证据（P1 十条）：
- **F803**：book-spine-init reads 未声明 DOT/输出格式必需的 characters/protagonist.md 与 world/rules.md
- **F809**：character-design IRON LAW 引用词表外文件 outline/chapter_outline.md、three_act.md；expand 模式 characters/**/*.md 未声明 reads
- **F811**：context-composing 主产物 context/chapter-N-context.md **写未声明**；近章结尾检查所需 chapter-(N-3..N-1).md 未入 reads（reads 中的 chapter-N.md 组装时尚不存在——时序错位）；volume_summaries 字段漂移
- **F812**：drift-guidance 契约写 truth/drift_guidance.md 但正文零定义；audit_drift_archive.md 写未声明
- **F821**：foundation-review reads 缺 genre-config.json（tropeInventory 评分必需）与 truth/book_spine.md（前置验证必需）
- **F836**：memory-distill L4/L5 读取的 author_intent/book_spine/world/rules 均未声明 reads → L5 书脊滚动复核在 dispatch 契约下拿不到输入（**盲写风险**）
- **F838**：market-radar 唯一 writes 是 decisions.json 但正文零 decisions 指令，且单文件 dispatch 不注入 schema 注记 + 正文输出格式为 markdown → 按正文执行必然 JSON 校验失败
- **F870**：state-settling 正文指示写 characters/protagonist.md（契约外写，字段所有权属他人）
- **F871**：score-volume 声明写 volume_score_trend 但正文零步骤零格式，dedup key=chapter 应为 volume
- **F873 所属簇为 C21**（路由面），本簇取声明面
- **D104**（P2，代表）：2 个 meta skill（using-shenbi、shenbi-writing-skills）无 contract.kind 声明——若应有契约则缺失、若豁免则 lint 无豁免规则（静默不对称）

P2/M 族：F802（anti-detect 触发输入未入 reads + DOT 与铁律 3 不一致）、F805（chapter-drafting style_profile 字段号漂移 + decisions sidecar 写声明无正文指令）、F807（chapter-planning 黄金三章依赖 novel.json 未入 reads）、F825（lifecycle 英文字段名 + genesis 未声明 reads）、F872（score-stratum updates book_spine 正文零说明）、F881（short-drafting 写声明正文零描述——repo 通病）、F882（state-settling mode-rules 列出非本契约文件误导越权写）、F884（truth-sync 多章操作 reads 仅单章 parametric）、F889（sequel-writing 风格指纹所需 style/style_profile.md 未声明 reads）、F892（escalation-review reads 仅覆盖六类信号源中的两类）、F849（M：review-fanfic fanfic.mode 无生产者且 NovelConfig 无该字段——au/ooc/cp 子模式实际不可配置）

## 目标

1. 约 20 个技能的 frontmatter ↔ 正文 ↔ 真实产物三方闭合：正文提到的每个输入文件都在 reads、每个输出都有 writes/updates 且正文有对应步骤与格式
2. 建立**契约闭合 lint**（G4 扩展或独立工具）：机械对账"正文文件引用 ⊆ frontmatter 声明"与"声明 writes ⇒ 正文有产出步骤"，使漂移在 PR 期被拦
3. D104 的 meta skill 二义性裁决落文：豁免则 lint 写豁免规则，不豁免则补契约

## 任务分解

### T1 · 契约闭合 lint（先立防线）
1. 扩展 G4（或 scripts/lint_contract_graph.py 族——注意与 C25 的 CI 接线缺口协同）加两条机械规则：
   - **R1 正文→声明**：解析 SKILL.md 正文中的相对路径引用（`[a-z-]+/[\w.-]+` 模式 + 代码块内路径），不在 reads/writes/updates 声明中的即 WARN/FAIL（白名单机制：词表公认路径）
   - **R2 声明→正文**：writes/updates 的每个文件，正文须含其文件名或等价产出节引用（防 F812/F871/F881 类"声明了但正文不知道"）
2. R1/R2 对 74 skill 跑基线，输出违规清单——作为 T2 修复的机械验收底单

### T2 · P1 十技能修复（读不到输入 = dispatch 断粮，最优先）
3. 补 reads 族：F803/F809/F811(前半)/F821/F836/F889/F892——以 Z8 分区报告的文件级清单为准逐技能补 frontmatter
4. 时序修正：F811 chapter-(N-3..N-1).md 进 reads、chapter-N.md 从 reads 移除（组装时不存在）
5. 写声明补正文：F812（drift_guidance 产出节）、F871（volume_score_trend 步骤+格式+dedup key 改 volume）、F838（market-radar 二选一：正文加 decisions 指令并改 JSON 输出，或 writes 改 markdown 报告——**推荐前者**，保住 decisions-sidecar 链）
6. 越权写拆除：F870 state-settling 删 protagonist.md 写指令（字段所有权归 character 域技能）；F882 mode-rules 节剔除非本契约文件

### T3 · P2/M 批量与 D104 裁决
7. D104：裁决 meta skill 契约地位——建议豁免 + lint 显式 `meta_exempt` 名单（不对称从静默变声明）
8. P2 族按 T1 基线清单批量修（F802/F805/F807/F825/F872/F881/F884）
9. F849（M）：fanfic.mode 不可配置——正文删 au/ooc/cp 子模式描述或 NovelConfig 加字段（推荐删描述，YAGNI）

### 批量清理（M 级成员）
- **F849**（M，升级证据已具备建议复评 P2）：如上 T3.9

## 验收标准（真实数据可复验）

1. 契约闭合 lint 对全仓 74 skill 跑批：R1/R2 违规 = 0（基线报告与修复后报告同口径对照，附 PR）
2. 抽查 P1 十技能（F803/F809/F811/F812/F821/F836/F838/F870/F871 + D104 裁决）：dispatch dry-run（dispatcher 过滤链）可见其正文所需全部输入注入（F836 的 L5 复核输入不再被过滤掉）
3. `shenbi-validate G4 <skill> <files>` 对修复后技能 PASS；market-radar 按正文执行产出的 decisions.json 过 G2 decisions 校验（F838 红灯验证）
4. meta 豁免成文：lint 输出显式列出 2 个 meta skill 豁免条目（D104）
5. `just check` 全绿（lint 新规则不产生存量误报——白名单调整记录在案）

## 风险与回滚

- **风险**：R1 正文路径解析有假阳性（示例代码、反例文本）——白名单 + 先 WARN 一轮收集再升 FAIL，分两步收紧
- **风险**：补 reads 会扩大 dispatcher 注入 token 量（F836 类多文件）——与 C29 截断披露协议协同，超预算文件按字段级 reads（Layer B，C2 簇）裁剪
- **风险**：F838 改 JSON 输出破坏现有消费者——对账 decisions 下游（G2/G4 路由，C4 簇）后实施
- **回滚**：lint 规则可独立关闭（WARN 级回退）；每技能修复独立 commit，74 个 SKILL.md 改动走 codemod + 人工复核，可按技能 revert

## 簇成员清单（21 条，自查用）

D104, F802-F803, F805, F807, F809, F811-F812, F821, F825, F836, F838, F849, F870-F872, F881-F882, F884, F889, F892（代表 D104）
