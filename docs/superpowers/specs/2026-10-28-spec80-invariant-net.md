# Spec #80 · 不变量之网：规范事实库、四槽门检、变异测试覆盖（invariant-net）

> **来源**：regen-vol1 运行（ch1-24）G3.4 评分 83.5 CONDITIONAL 暴露的五类跨章缺陷根因分析
> （裁决 #031 + rubric-score-24.md 五维伤口；系统性调试会话）。根因三层：L1 模型行为偏离；L2 五个「write-only oracle」
> 维度（有台账无门检）；L3 门体系反应式生长、从未做不变量普查。
> **方法**：declare-then-verify（钩系统 24 章零漂移的配方）推广到全部维度 + 变异测试闭环。
> **优先级**：🔴 P0（内容修复的 gate 保障依赖 P1）。
> **Status**: Active（rev1 驳斥七项；rev2-4 R1-R3 审查修正 30 项；rev5 R4 修正：facts_ops schema enforcement 触点/identity 对账比较面+重生成=陈旧行重写/severity=HARD/空种子语义/mutant 义务域限定/F16s 纯读者/--chapter 相关性语义——2026-10-28）

**触及的不变量维度**（T10 自补——普查表 `docs/framework/invariants.md`）：恒等 identity／持有与经手 props／枚举计数 counters（P1 到期三行，facts 承载+mutant 义务）＋ 能力活性（P2 F18 core_motif_touch）。P3 迁移面（promises/情绪等）见 §6。

## 0. 背景与根因（浓缩）

| 缺陷 | L1 直接原因 | L2 系统缺口 |
|---|---|---|
| ch20 骨哨双源 | drafting 发明交付拍（备忘写的是钥匙+哨响一下） | prop_registry 是 write-only oracle；G4.xc 物象环对母题物象**四重失效**（旧格式豁免 13/24 备忘、registry 首列键非正文子串、转移动词闭集不覆盖「抽出/揣着」、伤口章备忘无 `- 物象:` 声明行——注 rev2/R5-M2：11/24 备忘有声明行，其中 ch15/16 全角｜形态与 #75 ASCII 管解析器失配，余 9 份可解析）；审计单章视野 |
| ch19/20「林烽」回退 | planning 被关系档「林烽-X」键污染 | 叙事名约定无载体无门检；XC 只验白名单 |
| 《鉴录》计数互斥 | 相邻束 planning 各自猜数 | 计数无规范载体、无声明位、无单调门 |
| 金手指休眠 22 章 | 节点表 ch3-28 零轮回拍 | 卷级体感未分解为章级触点；无节奏门 |
| settle 把断裂炼成事实 | 分叉出第二把哨吞下矛盾 | 无状态机合法性校验 |

**统一结构：凡四槽（载体/声明/门检/审计）齐备的维度零漂移（MH 钩系统、红纸包链）；缺任一槽全部出事。**

## 1. 规范事实库与唯一查询面（facts store）

### 1.1 结构

- `truth/facts/<dimension>.json`——按维度分文件（identity / props / counters / knowledge / promises(钩) / emotion），schema 校验（pydantic 或 jsonschema）。
- **增量 op 协议**：settle 只发结构化事件（`{op: prop.transfer, prop: 骨哨(旧线), from: 帖木哥, to: 那罕, evidence: "chapter-20.md L218"}`），facts store 应用 op 并校验**状态机合法性**（无来源的二次获得=拒收）。这同时根治 matrix/整档 content_dropped 族（模型不再重写整档）。**拒收语义**（rev2 I2）：op 校验失败 → typed exception（exceptions.py 家族）+ settle 门 FAIL，走既有 attempts/escalation 协议；**fail-fast 在 Markdown upsert 之前**（双写下 Markdown 行不落盘，无半写态）。**写路径分期**（rev2 C1）：P1 起 settle 对三维**双写**（结构化 op 供 facts 应用 + 既有 Markdown 行 upsert 照旧），P3 才退役 Markdown 整档重写——不存在 facts 陈旧窗口。**双写分叉语义**（rev3 R2-I2，裁定方案 b）：Markdown 行仍由 settle 模型面照旧自写（契约零改动，向后兼容最大化）；G4.ss 增 **op↔row 一致性断言**（facts 为 canonical，声明面与事实面不一致即 FAIL）——**双写目标逐维钉死**（rev4 R3-M4）：props=registry 行（唯一真双写面）、identity=对账检查（facts↔name_registry，非双写）、counters=纯 facts 新面（无 Markdown 孪生），故 G4.ss 断言范围=props + identity 对账；op→row 机械渲染=P3 投影层实现形态（届时分叉面消失）。**gate 纯度边界**（rev2 I3）：op 应用是有状态写侧，住 facts 模块；门检是纯读者（AGENTS.md 幂等律）。**op 传输通道**（rev4 R3-M7）：op 走 state-settling decisions sidecar 的**加性键 `facts_ops`**（decisions-v1 schema 加性扩展不 bump 版本）；P2.5 rationale 交互=routine op 免 rationale、拒收/manual_override 必带；`lint_decisions_sources` 三源同批登记。
- **投影层**：现有 truth/*.md 变成从 facts 渲染的投影（渲染器 `src/shenbi/facts/projection.py`——rev2 I8 订正：框架侧模块，非项目数据目录；Markdown 面向人/LLM 的可读性不变，投影头部带 `> projected from facts/<dim>.json — do not edit`）。迁移分两期（见 §6），存量 Markdown 表在迁移前保持现状不阻塞。
- **查询面**：`shenbi-facts query --dim props --chapter 20 [--as-of N]`——返回该维事实（含 as-of 历史态，供跨章审计回放；**`--as-of` 消费方=P2**（canary/F19 审计回放），P1 查询面=现态紧凑视图——rev4 R3-M6；`--chapter` P1 语义=**相关性范围**（本章相关实体子集），非历史点——rev5 R4-M5；op log 即 P1 真实产物，P2 落地平凡）。**planning 投影**（rev2 I4）：planning 上下文装配消费**现态紧凑视图**（当前 owner + 本章相关实体，extractor 哲学复用），token 面有界；完备历史/`--as-of` 仅供审计/金丝雀。消费方：chapter-planning 上下文装配（替代猜）、G4 门检 oracle、审计契约 reads、金丝雀审计。

### 1.2 首批入库维度（P1）

props（owner+事件链+状态机）、counters（鉴录名数等单调计数）、identity（人物别名→叙事名映射+当前叙事名）。promises(钩) 迁移=P3 期（rev3 R2-I1 对齐 §6——钩系统四槽已齐备零漂移，迁移优先级最低；pending_hooks 证据行届时保留 Markdown 投影，规范态进 facts）。

### 1.3 种子真值源（rev2 I6）

facts 种子从**修复后章节正典**（fixed chapters as canonical）派生；truth registry prose 单元格不作为种子源——已核实 registry 陈旧（name_registry 赵三行与 prop_registry《鉴录》行仍记 pre-fix「第三个名字」，与修复后 chapter-9.md:151「第一页三个名字」矛盾）。registry 在 backfill 后重生成——**重生成=陈旧行重写**（rev5 R4-I2：赵三行/《鉴录》行/「临」备注行等已核实陈旧的行），**绝不整文件重生成**（72 行 settle 撰写的 prose 备注是确定性工具不可再派生的内容，保护）。**identity 对账比较面**（rev5 R4-I2）：别名/旌名行 ↔ facts 别名集；登记名行的 prose 备注（「全卷一致」等与 narration_name 相悖的注记）显式出范围——对账不得永久红。

### 1.4 接线清单（rev2 I3）

- `docs/framework/truth-files.yaml`：注册 `truth/facts/*.json` glob（新 concept 行——PR 可见决策点）
- `docs/framework/status-vocab.md`：注册 facts op/状态枚举——**权威层级**（rev4 R3-I3 订正方向）：Python StrEnum（`src/shenbi/facts/`，值集唯一定义）为主信源 → status-vocab.md 注册行 → `docs/framework/invariants.md` 普查表**只引用不定义**字面量集（doc↔code 双源漂移即 lint 红）；`tools/lint_status_strings.py` 校验 StrEnum↔vocab 值集全等
- **plan_format 决策**（rev3 R2-I4）：F16/F17 新增备忘硬门字段（`物件@op`/`计数:`）走既有 `plan_format` token 机制（chapter_planning.py:155-163，现行 v3）——v4 bump 或 v3 内可选，plan 阶段钉死并同批 backfill；禁止第三 bespoke 工具（AGENTS.md）
- **G4_CHECK_MAP 注册**（rev3 R2-I4）：F15/F16/F17 新 check ids 进 `src/shenbi/pipeline/chapter_loop.py` G4_CHECK_MAP（severity=**HARD**——rev5 R4-M1 钉词，mutant 验收蕴含硬门）
- **共享转移动词表**（rev3 R2-M2）：F16 动词族与 XC fallback 闭集抽为单一词汇模块双路径消费（防两表漂移）
- 写路径：facts 写入走 `src/shenbi/pipeline/truth_io.py` 既有 path-keyed `.lockfile` flock + append-helper 纪律（无第二套事务机制）
- `pyproject.toml` 新 entry point `shenbi-facts` + justfile targets（query 面向人/CI）
- state-settling decisions-sidecar 覆盖规则扩至 facts 写（C1 双写落地后）。**schema enforcement 触点**（rev5 R4-I1）：`facts_ops` 加性键须同批改 `src/shenbi/contracts/schemas/decisions.py`（DecisionsDoc `extra: "forbid"` 下未声明键=G2/G4 必炸）+ `docs/framework/decisions-schema.md` + settle SKILL:417 顶层键白名单扩行；P2.5 规则扩展（op 条目 rationale 必带情形）在 decisions 校验器同批落地
- **SKILL 契约面**（rev4 R3-M8）：`skills/shenbi-chapter-planning/SKILL.md`（声明行模板 `物件@op`/`计数:` + 查询面产物 reads）与 `skills/shenbi-state-settling/SKILL.md`（`facts_ops` 发射契约）——契约三源同步 `just lint-contracts` + `just generate` 同批
- **regen-vol1 种子工具**（rev3 R2-M5）：确定性 backfill 工具派生 facts 种子+声明行（`tools/plan_craft_backfill.py` 先例模式），禁手写 JSON（CI 可重复性）

## 2. 不变量普查（四槽契约）

`docs/framework/invariants.md`：13 维×四槽表——恒等(identity)、时间、空间(location)、持有与经手(props)、枚举计数(counters)、知识态(who-knows-what)、承诺与债务(钩)、情绪节奏、能力活性(金手指/体感)、叙事纪律(POV/声口)、字量结构、发布卫生、防剧透。**载体列逐行命实载体**（rev4 R3-M9：时间=timeline.md、字量=G2 检查等既有面——非 13 维全 facts 承载，「facts 库」仅为 facts-backed 维的载体）。每维四槽：载体/声明（memo 结构化行）/门检（check id）/审计（审计契约 reads）。**期相列**（rev3 R2-M3）：普查表每行带 P1/P2/P3 期相标记——即「缺槽=文档化的已知洞」的声明形，也是 lint_invariant_coverage 判定 P1 子集的机制（**当前期=lint 内 `CURRENT_PHASE` 常量**，rev4 R3-M10——随批次 bump，离线确定性；无期相标记或期相≤当前期而缺槽=红）。**任何维度缺槽=文档化的已知洞**。

`tools/lint_invariant_coverage.py`（进 just check）：扫全部 check id + facts schema + 审计契约，对照普查表——缺槽即红。**mutant 义务谓词**（rev4 R3-I1）：mutant 义务只挂「F15+ 族新引入 check id 的维度或 facts 承载维」（P1=identity/props/counters 三行）；既有 XC 门控维度（时间/POV/卡属性等）由既有红测文档化覆盖、普查表该行注记覆盖证据——13 维 ≠ 13 mutant，「全期 8 mutant」口径不变。

INDEX 活跃 spec 新增必填登记节：「触及的不变量维度」（rev3 R2-I3 订正锚点：登记约定落 `docs/superpowers/specs/INDEX.md` 登记模板——附录 A 是 progress 模板非 spec 模板；**同批为 #80/#81 补该节消除自绊**；lint 校验对象=INDEX 活跃项该节存在性，P1 只校 P1 期相维度）。

## 3. 变异测试式门检覆盖（CI 环——不打地鼠的核心机制）

`tests/fixtures/invariant-mutants/`：每维一个破坏语料（从本次运行真实伤口导出 + 合成变异体）。mutant 计数口径（rev1）：表 6 行实含 8 体（time-regress/pov-flip/gender-flip 三合成体）；**P1 交付 3 体**（name-swap/prop-chain-break/counter-dup），余 5 体随 P2 维度落地：

| mutant | 来源 |
|---|---|
| name-swap（叙事名回退） | ch20 原始语料（林烽×12）——已入库 `ch20-name-swap-prop-break.md` |
| prop-chain-break（无源交付） | ch20 L218 原始拍——已入库（同上文件） |
| counter-dup（计数互斥） | ch8+ch9 原始计数行拼接——ch9 半份已入库 `ch09-counter-dup.md`；**rev1：矛盾在 ch8↔ch9 跨文件（ch8:247「第三个名字」vs ch9 pre-rev「第一页两个名字」），单文件内部自洽不可判红，P1 须补 ch8 计数行基线 fixture 或 facts/counters 种子（count=3 基线 vs ch9 声明 2+1）** |
| time-regress / pov-flip / gender-flip | 合成（已有红测先例；P2） |
| motif-dormant（体感窗口休眠） | ch3-8 备忘序列（P2） |
| settle-illegal-op（分叉吞矛盾） | ch19-20 settle 的骨哨双条目（P2，依赖 F16s） |

`tests/gates/test_invariant_mutants.py`：**per-mutant check-id 断言**（rev2 I5——合并语料不掩盖死门：name-swap ⇒ F15 判红、prop-chain-break ⇒ F16 判红、counter-dup ⇒ F17 判红，各自独立断言，非「至少一门红」）。**mutant 种子 fixture 格式**：每个 mutant 携带最小 facts 态种子（name-swap=identity 别名表+当前叙事名；counter-dup=counters 基线 count=3；prop-chain-break=props 现态），测试内构造（G0.9 构造性结构输入豁免）或 fixtures 侧文件。**新增维度义务域=§2 谓词域**（rev5 R4-M3）：「新增任何不变量维度必须同时新增 mutant」限定为 §2 mutant 义务谓词覆盖的维度（新引入 check id 或 facts 承载），XC 门控新维度由红测覆盖注记即可。变异体全被拦=网眼无洞的机器证明。

## 4. 六个门检/机制修复（F15-F20，挂在 facts store 上）

- **F15 叙事名**：facts/identity `narration_name`（本卷=那罕，携带 `from_ch` 生效章界——rev2 M5，卷中合法改名留路径）+ 别名集（林烽）——name_registry 现状无法派生（登记名「临」备注「全卷一致」与实际叙事名相悖、旌名行含两个不同人物），显式载体必要；G4.xc `narration_name`——剥对白叙述段出现别名即 FAIL（备忘 `[旧名回溯]` 豁免闪回）。**快照豁免**（rev2 M1）：`*pre-rev*`/`*snapshot*` 文件不扫（G2 快照豁免先例；pre-rev 快照叙述名=林烽属修复前正史）。**facts 缺席降级**（rev4 R3-I2）：facts/identity 缺席 ⇒ skip + WARN 可见（XC.registry 先例），不硬 FAIL 无 facts 项目；新项目 bootstrap=pipeline-init 空种子（P1 钉此一途）；**空种子语义**（rev5 R4-M2）：键缺失 ≡ 维缺失 ⇒ WARN（防空洞 vacuous pass——write-only oracle 死法不复现）。
- **F16 物象经手链**：memo 母题物象行结构化 `物件@op`（持有/传递/获得/遗失）；G4.cp 声明对 facts 现态合法；G4.cd 正文「非 owner 人名+物件+交接动词共现」未声明传递即 FAIL（动词族须覆盖「抽出/揣着」形态——#75 闭集对本伤口假阴性）；settle op 经状态机校验（F16s——**纯读者形态**，rev5 R4-M4：对 sidecar ops 做 simulate/inspect 对照 facts 现态，无 mutation，幂等律无虞；写侧拒收=§1.1 fail-fast）。**XC 关系**（rev2 I1）：facts 在场时 G4.cd（F16）吸收 XC 不变量 4 的 prose 扫描职责（键=facts 实体名，动词族扩容）；facts 缺席时 XC 不变量 4 保留为无 facts 回退层**全 severity 运行**（rev4 R3-M5 订正——回退检查不降级；WARN 仅指 facts 缺席事实本身可见，XC.registry 先例）。**facts 缺席降级**（rev4 R3-I2）：与 F15 同律——skip 新检查 + WARN，不硬 FAIL。**实体副本语义**（rev1）：同母题新实体（修复后 ch20 帖木哥之哨与老驼之哨并存）与非法再获得必须可区分（机制留 plan；硬约束：修复后 ch20 双实体并存语料必须全绿）。**契约升级纪律**（rev1）：新备忘必填字段对 in-flight regen-vol1（24 章已结算）须同批带 backfill/生效策略，旧备忘豁免必须 WARN 可见——禁止静默跳过（#75 旧格式豁免 13/24 静默死法不重演）。**声明词汇超集**（rev2 I7 订正）：既有 `- 物象:` 行（11/24 备忘）与「**母题物象**:」散文并存——G4.cp 解析目标与 backfill 范围（11 声明行备忘键形态归一 + 13 旧格式备忘）plan 阶段钉死。
- **F17 计数器**：facts/counters 单调；memo 必须声明 `计数: <名> N+1`（planning 从查询面读）；G4.cd 正文计数词=声明值。**计数词法**（rev2 M2）：序数族「第N个名字」+ 总数族「N个名字/N名字」两形态，计数名从 facts/counters 键派生（P1 仅《鉴录》名数一计数）；页范围总数锚（「第一页三个名字」类）与全局计数器的 scope 锚定处理（忽略或页键页内计数）plan 阶段钉死——rev5 R5-M3。**三方对账**（rev4 R3-M11）：prose 总数族 ≡ facts 现值（counter-dup 的击杀面——ch9 pre-rev「第一页两个名字」vs 基线 3）；memo `N+1` ≡ facts 现值+1；prose 序数 ≡ memo 声明值。**facts 缺席降级**（rev4 R3-I2）：与 F15/F16 同律。
- **F18 体感触点节奏**：genre-config `pacing.core_motif_touch: {motif, max_gap:5}`（rev2 M4：随同 genre-config schema/validator 注册）；volume_outlining 增「卷级体感→章级触点拍」分解步；G4.cp 滑窗检查。
- **F19 审计视野**：continuity/foreshadowing 契约 reads 增 facts 查询面产物（props/identity/counters 完备集）。
- **F20 术后全门**：`just gates-sweep <dir> --chapter N`（全门+叙事名清扫+物象/计数检查）；监控侧绕行手术后强制。
- **F21 dispatch 归档**：→ **spec #81 §1**（归档层归观测域管辖；本 spec 的 mutant 重放、金丝雀、`--as-of` 审计回放消费其产物）。

## 5. 运行环：金丝雀审计

每束 per-chapter 检点（rev3 R2-M4 钉单一节奏——与 bundle 步进机对齐，双章束≈每 2 章；「每 10 章」措辞废弃）：独立 subagent 拿 `shenbi-facts query` 完备答案 + 章节全文做全链核对（G3.4 模式制度化）；入 driver-prompt 附件协议。

## 6. 分期

- **P1（本次 SDD 代码交付边界）**：facts store 骨架（props/counters/identity 三维）+ 查询面 + F15/F16/F17 + 普查文档 + lint_invariant_coverage + **真实伤口 mutant 导入**（含 rev1 的 counter-dup ch8 基线补全）。**种子源**（rev2 I6）：从修复后章节正典派生（§1.3），registry 陈旧不入境。**settle 双写自 P1 起**（rev2 C1；**双写面=props 唯一**——rev5 R5-M1 呼应 §1.1 R3-M4：identity=对账、counters=纯 facts）：settle 对三维发结构化 op（facts 应用+状态机校验）并照旧写 Markdown 行；settle 契约变更按契约升级纪律同批带 regen-vol1 backfill（op 追补种子）。验收：三 mutant 全 FAIL；ch20/ch9 修复后语料全绿（F947 离线化：fixtures 断言，不涉真实 dispatch；**绿语料口径=修复章节 + backfill 声明备忘/facts op 证据**，非裸章节——rev2 I6）。**契约升级合规**：备忘新字段 backfill/生效策略同批交付。
- **P2**：F18/F19/F20 + 金丝雀 + 体感触点拍生成 + P1 复评通过的后续束实弹验证。**运行验证阶段**（rev1 明确）：验收 4（ch25-26 实弹束）与验收 5（G3.4 复评 round 2 ≥86）属本阶段运行侧动作（付费 dispatch + 写项目状态），不在 SDD 代码交付边界内——P1 交付其**框架就绪**（planning 可读查询面、memo 契约已扩、门检零误报由 mutant+修复语料双证）。
- **P2 前置（全分支审查 2026-10-29 发现——backfill `--apply` 后真仓重跑门检的交叉实验，P1 离线边界内不触发，P2 gates-sweep/历史重检前必须处置）**：
  1. **F16 历史语料精度**：78-prop 全量种子下 `cd.prop_handoff`（HARD）对已收束 24 章中 17 章误报（ch20 即 4 处——短形匹配「红纸」↔「帖兰的半张红纸」、段级共现无动词挂靠、代词 owner 不在场）。处置选项：句窗共现+动词挂靠距离 / 代词 owner 容忍 / 扫描面收窄至 memo 触及集 / 实测精度前降 SOFT——P2 F20 `gates-sweep` 开工前裁定并实弹校准；
  2. **F17 as-of 水位**：回填工件对（终态种子 鉴录名数=4 + ch9 备忘 `- 计数: 鉴录名数 3+1`）在历史重检时自红（4 ≠ 4+1；总数 3 ∉ {4}）——终态种子+历史声明行天然时点错位。P2 需 as-of 机制（种子记录 `backfilled_through` 水位跳过激活，或从 ops_log 派生逐章前置态；`--as-of` CLI 已在 plan R1-C3 预留 P2）；
  3. **registry 注记键与 `ss.prop_row_match` 对账**：exact-key 匹配下，backfill 的裸键（火纹骨哨）对 registry 注记行（火纹骨哨（老驼所授·主线））永不对账=对账面静默 no-op。P2 前置=归一匹配器（剥全角括注、·副本键保持区分）或 bare-key 行重写，二择一随 P2 投影化裁定。
- **P3**：promises/情绪等剩余维度迁入 facts；Markdown 全投影化；settle 增量 op 全面替代整档重写。

## 7. 验收（P1-P3 全期完成定义；P1 本次 SDD 验收=条 1-3）

1. `uv run pytest tests/gates/test_invariant_mutants.py` 全绿（P1 三 mutant 全被拦；全期 8 mutant）
2. `lint_invariant_coverage` 进 just check 且绿（普查表无未声明缺槽；mutant 覆盖=维度覆盖——P1 校验 P1 维度子集，全量随 P2/P3 扩）
3. regen-vol1 修复后语料过 F15/F16/F17（ch20 叙事名零别名+双实体并存全绿、骨哨声明合法、计数链单调）——fixtures 驱动离线断言
4. （P2 运行侧）一个新束（ch25-26）实弹：planning 读查询面、memo 带结构化声明、门检零误报
5. （P2 运行侧）G3.4 复评 round 2 ≥86 且跨章不变量维度 ≥80
