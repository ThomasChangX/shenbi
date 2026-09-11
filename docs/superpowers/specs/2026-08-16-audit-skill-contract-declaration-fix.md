> **Date:** 2026-08-16 | **Status:** Design (Revised 2026-09-11 · SDD #58 价值门/事实核实：F838/F881/F882 已由 main 等效修复退出、F805/F807/F825 收窄、F825 增补 bridge_tracker 新发现、lint 路径与验收面修正) | **Severity:** 🟠 P1
> **系列:** 2026-08-15 全项目深度审计 · 阶段 5 修复 spec（簇 C20）| **代表 finding:** D104 | **簇规模:** 21 条 | **严重度上限:** P1
> **范围:** skills/*/SKILL.md（约 20 个技能 frontmatter + 正文）、契约闭合 lint（雏形：gates/g0_skill_contract.py + tools/lint_contract_graph.py 族扩展）| **证据等级:** 实验佐证（Z8-a/b/c 三分区初审 + d1-03-frontmatter.log 74 skill 全量解析）
> **与既有 spec 关系:** #23（z8-contract-drift）的 reads/writes 补全面（F953/F1002/F1011 等）并入本 spec 统一处置；本 spec 为其 2026-08-15 轮扩展与机制化（对账 lint），#23 已归档（Rejected 2026-08-30，PR 归档见 archive）

# C20 · 技能契约声明面断裂修复（skill-contract-declaration）

## 背景（根因 + 证据）

**根因**：SKILL.md frontmatter 契约（reads/writes/updates）与正文指令、真实产物、truth 词表互不闭合：正文读的文件 reads 没声明、契约声明的 writes 正文零步骤、写模式与 dedup 键错配、meta skill 从未纳入契约迁移范围——声明与行为双向漂移且无对账 lint（G4 只验 schema 不验闭合）。

代表证据（P1 九条，2026-09-11 复核存活八条——F838 已修退出）：
- **F803**：book-spine-init reads 未声明 DOT/输出格式必需的 characters/protagonist.md 与 world/rules.md
- **F809**：character-design IRON LAW 引用词表外文件 outline/chapter_outline.md、three_act.md；expand 模式 characters/**/*.md 未声明 reads
- **F811**：context-composing 主产物 context/chapter-N-context.md **写未声明**；近章结尾检查所需 chapter-(N-3..N-1).md 未入 reads（reads 中的 chapter-N.md 组装时尚不存在——时序错位）；volume_summaries 字段漂移
- **F812**：drift-guidance 契约写 truth/drift_guidance.md 但正文零定义；audit_drift_archive.md 写未声明
- **F821**：foundation-review reads 缺 genre-config.json（tropeInventory 评分必需）与 truth/book_spine.md（前置验证必需）
- **F836**：memory-distill L4/L5 读取的 author_intent/book_spine/world/rules 均未声明 reads → L5 书脊滚动复核在 dispatch 契约下拿不到输入（**盲写风险**）
- ~~**F838**~~：**已修退出（main · e92ea482，2026-09-11 复核确认）**——market-radar 正文现有完整「decisions sidecar 必填字段」节（SKILL.md:119-126，写 context/market-radar-decisions.json），markdown 报告仅为呈现层，不构成契约外写
- **F870**：state-settling 正文指示写 characters/protagonist.md（契约外写，字段所有权属他人）
- **F871**：score-volume 声明写 volume_score_trend 但正文零步骤零格式，dedup key=chapter 应为 volume
- **F873 所属簇为 C21**（路由面），本簇取声明面
- **D104**（P2，代表）：2 个 meta skill（using-shenbi、shenbi-writing-skills）无 contract.kind 声明——若应有契约则缺失、若豁免则 lint 无豁免规则（静默不对称）

P2/M 族（2026-09-11 收窄后）：F802（anti-detect：仅 DOT 与铁律 3 不一致 + 铁律 6 引用 anti-ai-reference.md 未入 reads 存活——触发输入子项正文未点名文件弱化）、F805（收窄：仅字段漂移存活且定位到**生产者侧**——style-learning 输出模板 8 节（无对白占比）vs 消费方声明与 fixture 11 节分裂，lint 以 fixture 为真值故漏检；novel.json 子项正文零命中不成立、decisions 子项已由 e92ea482 闭合）、F807（收窄：仅黄金三章 novel.json 未入 reads 存活 :117；plan-decisions 断链子项已由 e92ea482 闭合）、F825（收窄：genesis 读 outline/story_frame.md 未声明存活 + **新发现** Cross-Volume Bridge 读写 truth/bridge_tracker.md 契约三处均未声明 :120-126；「英文字段名」子项语义不明弃核）、F872（score-stratum updates book_spine 正文零说明）、F884（truth-sync 多章操作 reads 仅单章 parametric——低严重度：占位模式表达缺口，R1 白名单设计时一并处置）、F889（sequel-writing 风格指纹所需 style/style_profile.md 未声明 reads）、F892（escalation-review reads 仅覆盖六类信号源中的两类）、F849（M：review-fanfic fanfic.mode 无生产者且 NovelConfig extra:forbid 无该字段——au/ooc/cp 子模式实际不可配置）；~~F881~~（已修退出 e92ea482：short-drafting :235-242 decisions 节在位）、~~F882~~（已修退出 c112a95a：state-settling mode-rules 与契约一致，resonance_trend/audit_drift 零残留）

## 目标

1. 约 20 个技能的 frontmatter ↔ 正文 ↔ 真实产物三方闭合：正文提到的每个输入文件都在 reads、每个输出都有 writes/updates 且正文有对应步骤与格式
2. 建立**契约闭合 lint**（独立工具挂 lint-contracts/ci 双面，见 T1.1）：机械对账"正文文件引用 ⊆ frontmatter 声明"与"声明 writes ⇒ 正文有产出步骤"，使漂移在 PR 期被拦
3. D104 的 meta skill 二义性裁决落文：豁免则 lint 写豁免规则，不豁免则补契约

## 任务分解

### T1 · 契约闭合 lint（先立防线）
1. 扩展契约闭合 lint（`tools/lint_contract_graph.py` 族 + `gates/g0_skill_contract.py` 雏形——**CI 承载事实（2026-09-11 核实）**：CI 直调底层命令不经 just，新规则须同时挂 justfile `lint-contracts`（:74）与 ci.yml 契约 lint 步（:53-57）；该步现漏跑 lint_contract_graph.py 本体，接线时一并补）加两条机械规则：
   - **R1 正文→声明**：解析 SKILL.md 正文中的相对路径引用（`[a-z-]+/[\w.-]+` 模式 + 代码块内路径 + **glob 形态 `dir/**/name-*` 与裸文件名**——2026-09-11 审查补：`characters/**/*.md` 类 glob 的 `*` 不在 `\w` 内、`:101` 类裸名无 `/` 前缀，纯正则漏抓 F809 形态；规范化须 glob-aware，可复用 `lint_contract_graph.py` 的 `dag_key` glob/超集匹配语义），不在 reads/writes/updates 声明中的即 WARN/FAIL（白名单机制：词表公认路径）
   - **R2 声明→正文**：writes/updates 的每个文件，正文须含其文件名或等价产出节引用（防 F812/F871/F881 类"声明了但正文不知道"）
2. R1/R2 对 74 skill 跑基线，输出违规清单——作为 T2 修复的机械验收底单
3. **WARN→FAIL 升级归属（2026-09-11 审查补）**：R1/R2 初始以 WARN 跑基线收集误报 → 白名单收敛 → T2/T3 修复清零后**切 FAIL 阻断，同一 PR 内完成**（验收 5 断言 FAIL 级别生效，防"永久 WARN 的零阻断安全网"）

### T2 · P1 技能修复（存活八条；读不到输入 = dispatch 断粮，最优先）
4. 补 reads 族：F803/F809/F811(前半)/F821/F836/F889/F892——以 Z8 分区报告的文件级清单为准逐技能补 frontmatter
5. 时序修正：F811 chapter-(N-3..N-1).md 进 reads、chapter-N.md 从 reads 移除（组装时不存在）
6. 写声明补正文：F812（drift_guidance 产出节——注意 pipeline 侧 triggers.py:268-273 volume 触发器期待该产物而正文永不产出，产出节须与该消费面定义对齐）、F871（volume_score_trend 步骤+格式+dedup key 改 volume——key 声明在 SKILL.md:19，无集中注册处，改后 `just generate` 重生视图）——F838 已由 e92ea482 等效闭合，退出本 task
7. 越权写拆除：F870 state-settling 删 protagonist.md 写指令（字段所有权归 character 域技能）——F882 mode-rules 子项已修退出（c112a95a），勿重复修

### T3 · P2/M 批量与 D104 裁决

> T2/T3 全部契约变更（reads/writes/updates/key/mode）后统一义务：`just lint-contracts` 绿 + `just generate` 幂等 diff 空——不依赖 CI 兜底
8. D104：裁决 meta skill 契约地位——建议豁免 + 豁免名单**单一信源化**（收编 tools/lint_contracts.py:23 既有 `META_SKILLS` 常量为本 spec lint 与既有 lint 共用的唯一名单，禁止并行第二份可漂移列表——不对称从静默变声明）
9. P2 族按 T1 基线清单批量修（F802/F805[生产者模板对齐 style-learning]/F807/F825[含 bridge_tracker 读写声明补全]/F872/F884[白名单或 reads 措辞]）——F889/F892 归 T2.4 补 reads 修复，本 task 仅回归核对；F881/F882 已修退出
10. F849（M）：fanfic.mode 不可配置——正文删 au/ooc/cp 子模式描述或 NovelConfig 加字段（推荐删描述，YAGNI）

### 批量清理（M 级成员）
- **F849**（M，升级证据已具备建议复评 P2）：如上 T3.10

## 验收标准（真实数据可复验）

1. 契约闭合 lint 对全仓 74 skill 跑批：R1/R2 违规 = 0（基线报告与修复后报告同口径对照，附 PR）
2. 读侧存活技能抽查（F803/F809/F811/F821/F836）：以 `dispatch_helper._build_skill_prompt` 过滤链的**单元级断言**验证其正文所需全部输入注入（F836 的 L5 复核输入不再被过滤掉）——离线 tmp_path 项目驱动（先例 `tests/pipeline/test_dispatch_helper_keys.py:38-54`）、fixtures 引用 `tests/fixtures/` 真实产物（G0.9 溯源）、F947 规则禁真实 dispatch（「dry-run」能力 main 不存在、不新建）；写侧发现（F870/F871/F812）由验收 1/3 的 R2/G4 覆盖，D104 由验收 4 覆盖
3. `shenbi-validate G4 <skill> <files>` 对修复后技能 PASS；market-radar decisions.json 现行形态（e92ea482 已闭合）过 G2/G4 decisions 校验作回归确认（原 F838 红灯验证不适用）
4. meta 豁免成文：lint 输出显式列出 2 个 meta skill 豁免条目（D104）
5. `just check` 全绿且 R1/R2 已切 **FAIL 级阻断**（见 T1.3——终态非 WARN）；白名单调整记录在 lint 工具内的具名 allowlist 数据结构（逐条附一行理由），PR 描述附基线→清零对照；新 lint 同步挂 ci.yml 契约 lint 步（CI 不经 just，见 T1.1）

## 风险与回滚

- **风险**：R1 正文路径解析有假阳性（示例代码、反例文本）——白名单 + 先 WARN 一轮收集再升 FAIL，分两步收紧
- **风险**：补 reads 会扩大 dispatcher 注入 token 量（F836 类多文件）——与 C29 截断披露协议协同，超预算文件按字段级 reads（Layer B，C2 簇）裁剪
- **风险**：F838 改 JSON 输出破坏现有消费者——对账 decisions 下游（G2/G4 路由，C4 簇）后实施
- **回滚**：lint 规则可独立关闭（WARN 级回退）；每技能修复独立 commit，74 个 SKILL.md 改动走 codemod + 人工复核，可按技能 revert

## 簇成员清单（21 条，自查用）

D104, F802-F803, F805, F807, F809, F811-F812, F821, F825, F836, F838, F849, F870-F872, F881-F882, F884, F889, F892（代表 D104）

> 2026-09-11 复核注记：F838/F881/F882 已由 main 等效修复（e92ea482 / c112a95a）——ledger 回写时按「closed (C-20 spec #58，已修 elsewhere：PR #120/#117)」注明实际修复 PR；F805/F807/F825/F884 收窄后仍归本 spec；F825 增补 bridge_tracker.md 契约外读写（同文件同类缺陷）。
