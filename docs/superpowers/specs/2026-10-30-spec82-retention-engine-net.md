# Spec #82 · 追读引擎之网（retention-engine-net）：把商业节奏从「声明存在」升级为「分布与兑现」

**日期**：2026-10-30 ｜ **系列**：卷一复盘→卷二防复发（与 #83 three-surface-consistency / #84 vol1-repair-vol2-launch 配对：#82 管「读者为什么走」，#83 管「错为什么发生」，#84 管「已发生的怎么修、卷二怎么开」）
**状态**：Active（Revised 2026-10-30 · 终版 r7） ｜ **优先级**：🟥 P0（用户直接痛点：「不够引人入胜，很容易让人弃书」——卷一 36 章实证全指标命中）
**动机证据**：G3.4 全卷终评 85.35（reviews/rubric-score-36.md）＋三段式责编盲审（ch1-12 / ch13-24 / ch25-36，2026-10-30）＋驱动侧台账（vol1-ledger.md）
**修订**：r2 2026-10-30 高精度审核修订——根因一「零存在」断言更正为「存在但失效」（cold_run / check_emotion_proxy 两处既有实现，升格而非重建，免第三套平行实现）；新增 T0 完成时声明快照层（序列门数据源从可变 plan 改固化快照，闭环 relabel 博弈与重派漂移）；T2 数据源改 truth 详情块（总览表无「状态/最后推进章」列，r1 设计为死胎）＋advance 条文化＋挂起预算；T4 补七型钩轮换门、账目钩第一原型、反合理化表调和；新增 T7 retention_anchor 窗口参数化；全部新 FAIL 门 shadow 首束试运行纪律；种子引用行号修正（L893/L897/L1181/L1183）
**修订**：r3 2026-10-30 SDD 阶段 1 驳斥复核修订（fresh-context 子 agent 五问 + 协调者逐条亲验）——**六处证据矫正**：S1 补声明分布实证（微15/章19/大2，ch2/ch30 声明「大」而 G3.4 判零热——真问题=声明大零验真＋无频率下限）；S5 占比数字标注盲审口径；S7 改「后半卷断供」（前半卷 ch5/8/12/16 触点实在，ch21-36 十六章零轮回触点◆）；S8 黑鸟例证伪删除（ch29:119 正文实写）；KR 承接数 14/26→16/36；账目钩归因改「种子七型之一，缺的是轮换执法＋温度分布」。**六处实施补丁**：T0 follower 快照自包含（不依赖 #83 T5 先行）＋快照写入五值词表校验；T1 吸收退役 emotion_band 死键＋check_emotion_proxy 词表外 tone 堵口；T2 清偿锚存在性校验；T4/T5 audit 判温指定 blocking 级（堵低温引句充数残留口）；T6 同批更新 invariants.md 维度 9 行；新增 shadow 转正机器催转。#83 T1 判定器共基措辞改「先落地者建」
**修订**：r4 2026-10-30 熔断快修轮（用户批准）——轮 2 复核 4 实锤+3 补漏：①S1 声明分布「章20」更正「章19」（ch12 plan L15 模板行+L83 bullet 行双计伪影，15+19+2=36 自洽）；②T6 离线对账改**按标记类型分链检验**（并集扩法模拟仍 findings=0，达不到双面一致）；③shadow 催转 lint 增**前置任务**（逐束 shadow WARN 事件落盘+误伤裁定记录面——trace 零 WARN 事件/gate-markers latest-wins/ChapterState 无字段三面确认数据面不存在）；④T6 裁定**本批不 bump CURRENT_PHASE**（bump P2 则维度 9 审计槽 `—` 真洞触发四槽红）；⑤emotion_band 退役补 genre-config SKILL 模板同步；⑥D2 判温钉 `- [BLOCKING]` marker 行形态（_BLOCKING_MARKER_RE 不认 prose）；⑦判温义务明确含 emotion_tone（堵全「喜」词表内绕过）；附 T2 锚解析两代 KR 形态兼容注记
**修订**：r5 2026-10-30 阶段 3 设计审查 R1（1C/7I/5M）清偿——**C1 声明面生产者三件套**：①planning 模板（plan_format v4）新增 `章尾钩型:` 七型词表声明行（词表校验同 emotion_tone 五值模式）——T4 轮换门/T0 快照的数据此前零生产者（plans 36 件 grep「章尾钩型」=0）；②T6 core_motif_touch 数据源改 **volume_map 轮回触点◆标记链**（plans grep「轮回触点」=0；离线分链检验与验收 2 已消费同一标记——单一来源），快照改为完成时摄取本章节点标记集，T3 卷二回填义务扩至◆标记；③T1 引句锚定行格式限定 plan_format v4 生效（卷一 36 章已完结零重跑——显式「无既有工件受影响」声明，AGENTS.md 契约升级纪律）。**I1-I7**：invariants 维度 7/8 行同批更新（含 dim-8 载体文本 emotion_band→cold_streak_cap 族）；regen-accept 2c 滑窗化双面数据源显式声明（gate=快照/验收=plan 读取，relabel 验收面残留记 T5 抽查覆盖）；冷谓词单一信源共享常量（tone∈{悲,惧,平} 且金句位非燃——含 2c 同款金句位例外，三消费方共用）；micro_hook_run 同批改读 T0 快照（L-D 自洽）；T4② 注入近 10 章收尾型历史（自 T0 快照派生）；T2 补章级钩注册完整性审计半边（S4 四例均为章级未注册钩——母钩龄期门不覆盖）；T5 勘误面（快照旁 append-only errata，温度谱读快照+勘误）。**M1-M3**：工件命名指派（T2 锚校验并入 lint_volume_nodes/催转 lint 独立小工具/shadow WARN 事件进 #81 trace 面加 WARN action/shadow 位=market_params 键内子键）；KR 标题形态卷一/**卷十二**（r4 误写卷十）；L-B 措辞（按维度 9 预登记载体 core_motif_touch 进 pacing）
**修订**：r6 2026-10-30 阶段 3 设计审查 R2（13/13 清偿确认 + N1/N2 新发现）——**N1 plan_format v4 兼容三件**（合法值清单加 v4/三处 v3 正则改集合匹配/TDD 回归防熄火）＋在飞运行声明更正（pipeline-state 实停 ch37 planning step——r5「无在飞运行」失实）；**N2 T6 修复者双路径**（planning 补触点拍/volume-outlining 重排◆）+窗口规则（本卷已生成章+卷内首标记前不计间隔）+T3 ◆回填先于卷二首章 dispatch 排序句；**N3-N7 随批**：词表外优先于金句位例外/章级钩 finding 判 blocking+注册并入 settling/快照写时校验扩三枚举字段/滑窗 bootstrap（窗内章数<window 不判 floor）/WARN 级 check id 入维度表或豁免注记
**修订**：r7 2026-10-30 阶段 3 设计审查 R3 清偿——**F1（Critical）七新键三源落地**（schema validator 数值域扩展/SKILL 模板同步/novel-xinghuo-vol1 genre-config.json 数据补丁——r5 C1 镜像复发：门齐装而配置零生产者则全部新门按「配置缺席退 WARN」常驻熄火）；**F2 v4 激活六处单一版本集常量**（PF_GE_V2/PF_GE_V3——含 :251/:259 两处令牌比较，cd:920 是 v2 门不得 `v[3-9]` 误伤）+既有 v4→invalid 测试同批改写；**F3** r5 失实句清除（与 r6 如实声明同口径）；**F4-F8**：状态头更新/冷谓词有序分支/重排◆仅限未生成章/D2 判温顺带判型/T7 可并入 T1（plan 裁量）

**触及的不变量维度**：情绪节奏（8）、承诺与债务（7）、能力活性（9）

---

## 0. 背景与根因

### 0.1 症状清单（卷一实证，全部带出处）

| # | 症状 | 证据 |
|---|------|------|
| S1 | **36 章零热章尾钩**（危机上门型收章）——全部落在物象收束/未答之问/感官余韵/主题句低温区；**r3 实证：机器声明面 微15/章19/大2（r4 更正：章 20 系 ch12 双计伪影）——ch2/ch30 声明「大」而 G3.4 独立判读零热，声明大零验真＋无热钩频率下限双缺失** | G3.4 D6「36 章无一热钩收章」；ch25-36 盲审「热章尾钩 0/12」（盲审口径，未独立落盘）；plans/chapter-{2,30}-plan.md 声明「大」（r3 驳斥复跑+协调者复验） |
| S2 | **主角零实质胜利**——36 章对抗全部「赢的是嘴」：ch33-34 舌战零成本零收益零声望，灰烬零损伤退场，卷一无反派结算 | 盲审 C「两次友好切磋不是宿敌交锋」；盲审 B「12 章净账面=帖兰死+帖木哥赴死+3000 文债+白站 22 个月」 |
| S3 | **冷段超限**：ch26-36 十一章仅 ch33 一章真发热；ch28-31 四连冷 | G3.4 D6；盲审 C「ch25 暖意之后熬过八章观察-记录-感悟」 |
| S4 | **断供钩成灾**：七三一（35 章零提及）、老驼纸条（35 章）、帖木哥线（ch24 后断）、「我见过另一支」第三哨（18 章）、灰烬报价后续（6 章）、经手人笔迹（11 章）、完颜嫂三日钟（立钟后全书零响） | G3.4 D2/D9；盲审三段追读引擎表 |
| S5 | **工序文占比高**（盲审口径 ~45-50%，数字未独立复现）：「抄—问—记」同构骨架 7 章实证（ch14/15/17/19/21/23/24 七章「本章核心任务」行全为抄/记/核/算工序——r3 逐章复跑核验）；ch16+17、ch5+11、ch29+30、ch33+34 成对同构章（G3.4 D4「ch33/ch34 连续两章同构，展示性边际递减」独立佐证） | 盲审 B「特色即枷锁：仪式磨成流水」（引文未落盘）；七章 META 核心任务行一级工件核验；G3.4 D4 |
| S6 | **主角无欲望线**：个人想要什么 36 章从未出口；唯一具体物质目标（路引 300 文）ch5-36 零命中彻底断线（r3 复跑 grep：ch3×3/ch4×9 后 32 章零出现——比「5 章后断线」更彻底）；全部地位变更由外力文书驱动 | 盲审 A「档案里的一个人，不是起点主角写法」（引文未落盘）；chapters/ grep 复跑；outline/volume_map.md Objective 无主角自选目标子句（原文核读） |
| S7 | **金手指后半卷断供＋零功能输出**（r3 矫正：前半卷触点实在——ch5 笃定无来处/ch8:37/ch12:113 要趁早记得她/ch16:89 旧账翻页，每 3-4 章一触点；**ch21-36 十六章零轮回触点◆**——volume_map 触点标记 ch5/8/12/16/20 后中断）；「还没记起来」无进度条、无功能输出贯穿全卷 | outline/volume_map.md:48-73 触点标记链；chapters/ grep 复跑（r3 驳斥+协调者复验） |
| S8 | **AI 味模板族**：章尾复述行（「这一(笔|夜|章)」起手复述）、「冷屋-点灯-数钱-压纸包」收尾六连用、「…呢？」自嘲收尾 12 章 8 次、「这笔我先记下」全卷 26 处（r3 复跑精确吻合）| 盲审 C 出戏点清单（引文未落盘）；G3.4 D5/P2-10 口癖 26 处在盘 |

### 0.2 根因裁定（systematic-debugging Phase 1-3；r2 按代码实况校准）

**根因一（机器面，本 spec 主靶）**：商业节奏的执法面消费的是**规划的自声明标签**——r1 曾断言温度红线「零存在」，核实不实：红线有**两处既有实现，位置与强度失效**才是真相：

- `G4.cd.micro_hook_run`（chapter_drafting.py:928-957）读前章 memo 自评的「微|章|大」，只封底（连续微≤2）**不封顶**（无大钩/热钩频率下限）→ 36 章零热钩合法通过；
- 温度红线既有两处、双双失效：`recall_weight.cold_run`（text/recall_weight.py:204-236；3 连冷注入节点/5 连 CHECKPOINT，chapter_loop.py:466 消费）是动作级注入**不拦章**；`regen_accept.check_emotion_proxy`（tools/regen_accept.py:192-217；全卷最长冷连击 >3 FAIL）在验收位，被「金句位燃」短路与 memo 标签失真两条逃生口架空——卷一机器面收官全绿而 ch28-31 四连冷照样出货；
- `G4.cp.emotion_tone`（chapter_planning.py:365-368）单章声明值存在性；`payoff_density`（chapter_drafting.py:958-983）WARN 级、只验「轴登记」存在不验量级（schema 有 `min` 键但消费端只读 window，genre_config.py:86-87——配置存在≠被消费的前车之鉴）；
- `G4.cp.retention_anchor`（chapter_planning.py:375-388）窗口硬编码 1-30 章（注释自认 "fixed 30"）——卷一 ch31-36 已在窗外，卷二全卷（37-91）更全在窗外：留存门对留存主题自己熄火；
- 种子七型钩「轮换使用，连续两章不得同型」（outline-example.md:1178）机器零执法（r3 反查：全域 grep hook_type/钩型/轮换/rotation 仅注释命中）；账目钩判定（chapter_drafting.py:810-831，末 8 段 ≥2 处数字串即算钩）忠实执行种子七型定义（账目钩=七型之一）——**真正的洞是轮换零执法＋无温度分布门**：数钱收尾可无限连用而门全绿（r3 归因矫正）；
- `meme_quota` 旋钮经 regen-accept 判据 4（checkpoint 时 chapter+volume 双模式，regen_accept.py:235-247）有消费，但**只查梗位下限**——口癖超用（「这笔我先记下」26 处 vs 建议值 12）零执法（r3 矫正：非「卷末才消费」）；
- **第三逃生口（r3 驳斥发现）**：`check_emotion_proxy` 除金句位燃短路、memo 标签失真外还有**词表外 tone 通道**——ch5「安」/ch12「暖」/ch15「快」被 proxy 当暖章斩断冷连击（plans 一级工件实证）；且这三份 plan 现态过不了 `cp.emotion_tone` 五值门——**plan 过门后被改写的漂移真实在盘**，T0 快照的直接证据；
- **emotion_band 死键（r3 驳斥发现）**：`market_params.emotion_band`（schema window/min，contracts/skills/genre_config.py:88-90 校验存在）**零消费**——`emotion_band_warnings`（text/recall_weight.py:215）不读任何配置键，schema 有 min 键但消费端只读 window 的前车之鉴在本键整体复现；T1 须一并裁定归宿（吸收或退役），否则落成第三个同语义死旋钮；
- **共性根因（r2 新增裁定）**：①标签真伪无人验——relabel 不动一个字正文即可过门；②历史标签存于**可变 plan 文件**——checkpoint REJECT/MODIFY 重派 planning（pipeline/cli.py:101-112）会改写已生成章的 plan，序列门读到的历史可被事后重写（pipeline-state 无完成时快照，state.py:143-150 仅六字段）。

**根因二（大纲面，本 spec 副靶）**：卷纲 KR 的衡量标准是**状态性/关系性**，KR2/KR3 节点大半承接型（r3 复跑核正：卷一 KR 表 36 行中承接型 16 行——过半弱化「大半」表述为「近半」，方向不变）——工序章被大纲合法化；且 KR 节点无「主角获得」槽、卷级无胜利预算、Objective 无主角自选目标，追读三要素（欲望/阻力/回报阶梯）在规划源头就不存在。

**根因三（种子面，记录不立项）**：回报引擎按种子排期在卷三开账、卷五首兑（outline-example.md L893/L897/L1181/L1183——还账进度表/必胜渡排期）——卷一卷二整段是设计上的「零回报区」。**不重排卷三+的兑现曲线**（那是对种子叙事的改写），但卷二必须有自己的微回报层（见 T3）。

一句话：**「记账」被当成了情节本身，而不是情节的引擎**——发现→记录的循环没有「兑现」臂，记下的账从不炸响（盲审 A：「记下是集邮，不是布局」）。

### 0.3 铁律

- **L-A 声明需对账**：新增的一切分布约束（钩温度/冷段/胜利量级）在门层消费自声明标签的同时，必须在卷末检查点协议（T5）有人工复核面——自评+人评双通道，杜绝「自评标签漂移成为新的声明面失真」（#83 同期问题）。
- **L-B 只加旋钮不写死数值**：新阈值进 `genre-config.json` 既有分块（默认 market_params；core_motif_touch 按维度 9 预登记载体进 pacing 块），按平台带可调（起点直发 vs 番茄组更的温度谱不同），代码只读配置——与 #72 平台带同纪律（r5：retention_anchor `to_ch: null` 需 market_params 数值域校验器扩 null 容忍）。
- **L-D 声明快照铁律（r2 新增）**：一切跨章序列门消费**完成时快照**（T0：chapter_states 固化的当章过门声明），不读可变 plan 文件；新增 FAIL 门一律带 `shadow` 配置位，首束 WARN 试运行零误伤后转正（#83 L-D 同纪律）。

---

## 1. T0 · 完成时声明快照层（一切序列门的数据基座）

**修什么**：根因一共性面——序列门读可变 plan = 两条失效路径：无恶意漂移（重派改写历史标签）与 relabel 博弈（门卡住时回改前章标签解卡，白嫖分布约束——正是「机器自声明执法」的复发路径）。与 #83 T5 同代码位点（`_complete_chapter` 束完成写全 bundle status 的同一改动面），建议同批同 PR。

- `_complete_chapter`（chapter_loop.py:2034-2095）在章通过全部门后，把当章声明标签固化进 `chapter_states[n].declared`：`emotion_tone`（悲|喜|怒|惧|平）、`章尾张力拍` 档位（微|章|大）、`章尾钩型`（七型，**r5：生产者=plan_format v4 模板新声明行**，见 T4）、`payoff` 档（小|中|大）、`金句位燃`、`本章节点标记集`（**r5：完成时从 volume_map 摄取本章节点的轮回触点◆等标记**——T6 数据基座，生产者=volume_map 非 memo）；
- 快照=「当时过门的声明」：事后 plan 重写（重派路径 cli.py:101-112）不回改快照；**束成员（follower 章）快照由本任务自带最小实现**（r3 补丁：`_complete_chapter` 束感知分支内对 bundle 成员逐章写 `declared`——不依赖 #83 T5 先行；若 #83 T5 同批落地则合并为对 `_complete_chapter` 的一次触碰，seam=导出可复用的单章快照函数供其批量循环调用，spec 仅「建议同批」不构成硬依赖——避免 #83 迟到时 2 章束制下奇数章永远无快照、序列窗出洞）；
- **快照写入词表校验（r3 补丁；r6/N5 扩三枚举字段；r6/N3 定优先级）**：写入时校验 `emotion_tone` ∈ 五值词表（悲|喜|怒|惧|平）及三个枚举字段的对应词表（章尾张力拍 微|章|大、payoff 档 小|中|大、章尾钩型 七型）——词表外值（安/暖/快类，实证 ch5/12/15）记 WARN 并**按冷章处理**（堵第三逃生口的数据面：过门后被改写成词表外的 plan 不得借快照洗白为暖章）；**词表外判定优先于金句位例外**（词表外+金句位燃仍判冷——与 T1 冷谓词常量的分支定义一致，消除两规则在「词表外+燃」上的分叉）；钩型/张力拍/payoff 词表外记 WARN 并按 absent（轮换门对 absent 跳过）；
- 消费者：T1/T6/T7 序列门、T5 检查点取数；（后续可选）context 组装面改读快照，消 context↔truth 漂移族（实证：context/chapter-36-context.md:122 写「最后推进章 24」vs truth 侧 `last_reinforced: 第36章`，pending_hooks.md:88）；
- **TDD**：快照写入单测（leader+follower 双路径）；红测=完成后重写 plan 文件，快照与序列门判定不变。

## 2. T1 · 跨章序列门（升格既有计算＋快照数据源＋引句锚定）

**修什么**：S1/S3。r2 三处修正：cold_streak 升格既有实现而非第三套平行造轮；序列门数据源改 T0 快照；标签验真挂引句锚（章级延迟，不再等 10 章检查点）。

- **新键三源落地（r7/F1——生产者纪律，镜像 r4 ⑤ 对新增键施加同等纪律）**：本 spec 全部新配置键（market_params 四键＋T2 `hook_max_age`/`hook_defer_budget`＋T7 `retention_anchor`＋pacing `core_motif_touch`）须三面同批写入：①schema validator 数值域扩展（contracts/skills/genre_config.py `_market_params_structure`——现状三态：纯数值新键被静默忽略不拒、null/字符串值在 Pydantic 类型层拒——`retention_anchor.to_ch:null` 需 null 容忍、`payoff_magnitude_floor.min:"中"` 需字段类型放宽 str|int、`shadow:bool` 侥幸过 bool⊂int——三处均须显式域定义，勿依赖侥幸）；②`skills/shenbi-genre-config/SKILL.md` 模板同步（契约三源纪律）；③`novel-xinghuo-vol1/genre-config.json` 数据补丁写入（现 market_params 仅旧五键、pacing 无 motif 键——不写则全部新门按「配置缺席退 WARN」常驻熄火，验收 2 实弹落空；平台带注记按 L-B）；
- `genre-config.json market_params` 新增四键：
  - `cold_streak_cap: {max: 3}`——冷集={悲,惧,平}（#79 判据 2c 同口径）；
  - `hot_hook_floor: {window: 10, min: 1}`——「大」级章尾张力拍每 10 章窗 ≥1；
  - `payoff_magnitude_floor: {window: 6, min: "中"}`——payoff 拍兑现档每 6 章窗 ≥1 次「中兑现」及以上；
  - `temperature_profile: {window: 10, hot_ratio_min: 0.2}`（**WARN 级**）——热章占比下限（热章=张力拍∈{章,大} 或 emotion_tone∈{怒,喜}），堵「3冷1温」循环 mush——cold cap 与 hot floor 两门皆不触发的空隙。
- **cold_streak 升格而非新建**：`recall_weight.cold_run` 已算冷连击、注入管线已在 chapter_loop.py:466——升格为 planning 门 FAIL（连击 > cap 时拦章，注入动作保留）；**冷谓词单一信源（r5；r7/F5 有序分支化）**：共享常量按序判定——①tone ∉ 五值词表 → **冷**（词表外优先，堵第三逃生口）；②tone ∈ {悲,惧,平} 且金句位非燃 → **冷**（含 2c 同款金句位例外——r4 的裸词表冷集会让 gate 在 2c 判暖的 悲+燃 章上 FAIL，谓词分叉）；③否则暖。planning gate / regen-accept / T0 写入校验三消费方共用同一常量；`regen_accept.check_emotion_proxy` 同步滑窗化（全卷一次性判定改 10 章滚动窗）**并堵词表外 tone 通道（r3 补丁）**：tone ∉ 五值词表时按冷章计、不再默认当暖章（ch5/12/15 实证通道）；**双面数据源显式声明（r5）**：planning gate 读 T0 快照；regen-accept 2c 滑窗化保留 plan 读取（卷一历史回放必需——快照对 ch1-36 不存在）——relabel 在验收面的残留=T5 抽查覆盖（记 deviations）；**micro_hook_run 同批改读 T0 快照（r5）**：chapter_drafting.py:928-957 现读前章可变 plan memo——L-D 铁律对被升格门族自身生效（解析交换，字段级值不变）；
- **emotion_band 死键吸收退役（r3 补丁）**：`market_params.emotion_band`（schema 校验存在、零消费）随 cold_streak_cap 落地**一并退役**——schema 必填键列表移除该键或迁移 alias 至 cold_streak_cap（升格既有而非留第三死旋钮；存量项目含该键时迁移提示）；**同步 `skills/shenbi-genre-config/SKILL.md` 模板（r4 补漏：:125 键例与 :326「三键块在场必齐」文本）——契约三源同步纪律，不同步则 SKILL↔schema 漂移、新项目继续量产死键**；
- `G4.cp.hot_hook_window` / `G4.cp.payoff_magnitude`：滑窗读 **T0 快照**，不解析 plans/*.md；
- **引句锚定（标签验真，章级）**：章尾张力拍声明行升级为 `章尾张力拍: 大｜『<章尾句原文引句>』`（**r5：行格式属 plan_format v4 模板，引句锚定门只对 v4+ 生效**——卷一 36 章已完结零重跑；在飞运行影响见 v4 兼容段的如实声明（r7/F3 清除 r5 失实句）：停 ch37 planning、plan 未生成零回填、门 v4+ 生效无既有工件受影响）——(a) 引句逐字存在性机器判（**与 #83 T1 verbatim 判定器共基，先落地者建**：#82 队头先行则本任务建、#83 复用——r3 措辞矫正，勿各造一份；回查本章正文）；(b) 温度语义判定交 per-chapter audit close（shenbi-review-group-craft D2 章尾检查点加温度维度——审计是独立技能输出，非 plan 自声明）**且命中即为 blocking 级 finding（r3 补丁），finding 须以 `- [BLOCKING]` 行形态写出（r4 补漏：管道 `_BLOCKING_MARKER_RE` 只认 `## BLOCKING` 标题/`|**BLOCKING` 表格/`- [BLOCKING]` 行三种 marker 形态，prose「判定: error」不可见）**；**判温义务含 emotion_tone 声明（r4 补漏）**——词表内谎言（如全卷声明「喜」）绕过词表校验与 cold_streak/temperature_profile 双门，D2 判温是唯一拦截面（等价替代：tone↔张力拍一致性机器检查——喜＋微拍即疑点 WARN），否则低温引句充数与全喜绕过两条残留口仅剩 T5 抽样拦截；
- **plan_format v4 兼容（r6/N1；r7/F2 扩六处+版本集常量）——v4 令牌引入的既有版本门债，先于一切 v4 消费者落地**：①`G4.cp.plan_format` 合法值清单加 v4（chapter_planning.py:244-249——现 v1/v2/v3，v4 memo 直接触 invalid_token 硬 FAIL）；②**六处版本条件统一为单一版本集常量**（`PF_GE_V2={v2,v3,v4}`/`PF_GE_V3={v3,v4}`，消费点：chapter_planning.py:123 scene_budget 正则 `v3\b`→`v[3-9]\b`、:247 合法清单、:251 `in ("v2","v3")`→PF_GE_V2（voice_line 声口要求行义务）、:259 `=="v3"`→PF_GE_V3（tension_tier/payoff_axis 义务）、chapter_drafting.py:920 `v[23]`→`v[2-9]`（**v2 门——`v[3-9]` 会把 v2 memo 踢出 #76 检查族**）、:925 `v3\s*$`→`v[3-9]\s*$`——不改则 v4 memo 静默豁免 scene_budget/voice_line/payoff_axis 且 #76/#78 检查族整族熄火，正是根因一要消灭的「配置存在≠被消费」失效类）；③TDD 回归：v4 memo 仍触发 scene_budget 缺块 FAIL + #76/#78 检查在场 + 缺声口要求行 FAIL + 缺 payoff 轴量行 FAIL；既有 `tests/unit/gates/g4/test_spec76_voice_quote.py:96-99` 的 v4→invalid 断言同批改写（v4 转合法后的真值表翻转）；**在飞运行如实声明（r6 更正 r5 失实句）**：pipeline-state 现停 ch37 `shenbi-chapter-planning` step_index 1（resumable）——ch37 plan 未生成，恢复即按 v4 模板出 plan、零回填需求；但 v4 兼容必须先于该运行恢复落地，否则首章 invalid_token 硬 FAIL；
- **滑窗 bootstrap 语义（r6/N6）**：卷二首 10 章窗内快照稀疏（ch1-36 无快照）——窗内已生成章数 < window 时 floor 类判定不生效（shadow 试运行期首束恰好落在此段，误伤裁定须知道该语义）；
- 卷首三章豁免（黄金三章另有约束）；回卷窗口跨卷界时只取本卷已生成章；
- **消费端红测**：每个新键断言「门真读了 min/floor 值」（`payoff_density.min` 键存在但消费端只读 window 的前车之鉴）；
- **shadow 纪律**：新 FAIL 门默认 `shadow: true`，卷二首束（ch37-38）WARN 试运行，零误伤后升 FAIL；**前置任务（r4；r5 定工件位）**：shadow WARN 事件逐束落盘走 **#81 trace 面（trace.jsonl 加 WARN action——零新记录面）**＋误伤裁定记录面（vol1-ledger 同款台账段）；催转 lint=独立小工具 `tools/lint_shadow_promotion.py`；shadow 配置位=各 market_params 键内 `shadow: bool` 子键；现有三面皆无逐束 WARN 数据（trace 零 WARN 事件/gate-markers latest-wins 单记录/ChapterState 六字段），不建则 shadow 纪律不可机核；**invariants 维度 7/8 行同批更新（r5/I1；r6/N7 补 WARN 级清单）**：本任务新增 cp.hot_hook_window/cp.payoff_magnitude（维度 8）＋T2 hook_age/T4 轮换门/T4 ending_diversity＋temperature_profile（维度 7/8 域，**WARN 级哨兵同入门检列**——P2 期 lint 扫全仓 check id 对照表，不入列即红）——维度表门检列同步，且维度 8 载体文本 `pacing/emotion_band`→`cold_streak_cap 族`（emotion_band 退役的登记侧）；
- **TDD**：四连冷 FAIL/三连冷+暖 PASS、10 章窗零大 FAIL、6 章窗全小兑现 FAIL、热占比 WARN 触发、卷首豁免、配置缺席退 WARN（scene_budget 版本门先例）、完成后改 plan 不改判定、min 消费断言、shadow 位生效。

## 3. T2 · 钩龄门（hook_age：truth 详情块数据源＋挂起预算）

**修什么**：S4 的机制化。r2 修正两处落空：①r1 设计解析总览表「状态/最后推进章」列——该列**不存在**（总览实为 8 列：当前生命周期/种植章/兑现章/类型/微妙度/max_distance/升级曲线；头注明言「不登记章级 last_reinforced」，pending_hooks.md:10），按 r1 实现将永久命中「缺列 WARN」兼容分支=门死胎；②「由 foreshadowing-lifecycle 更新」不实——字段写者是 state-settling（shenbi-foreshadowing-lifecycle/SKILL.md:122 明文），生命周期迁移归 foreshadowing-track。

- `G4.cp.hook_age` 数据源=**truth 详情块** per-hook `last_reinforced: 第N章` bullet（同钩多 bullet 取 max）＋总览行 `当前生命周期` 列判 RELEVANT——`last_reinforced` 由 settling 以 `audits/chapter-N-foreshadowing.md` 为**唯一确证来源**更新（state-settling SKILL.md:145）：**审计锚定**而非 plan 自声明，天然满足「付息=新信息、复读不计」语义；
- **advance 条文化**：state-settling SKILL 增一行铁律（把 pending_hooks.md:70 判例升为条文）——「物品层在场不等于约定层推进；只有审计判 advance 的在场才发 last_reinforced 增量」（r1 所引「既有语义保证」此前只有判例散文、无 SKILL 依据）；
- `当前章 - last_reinforced > max_age`（默认 8，market_params `hook_max_age: {max: 8, shadow: true}`——dict 形态（r7/plan 裁定：shadow 子键归宿），消费侧读 .max）的每个 RELEVANT 钩：要求本章 plan 钩账行 touch **或** 挂起声明；缺两者 → FAIL（修复者：planning）；
- **挂起预算（堵新合法化通道）**：挂起行强制带预定清偿锚（`- 挂起: MH05 至卷三·KR2` 形态）**且锚存在性机器校验（r3 补丁；r5 定工件位：并入 `tools/lint_volume_nodes.py` 新子检查）**——锚中的卷/KR 引用须在 volume_map 命中（**r4 注记：KR 行两代形态并存须兼容**——卷一/卷十二 `#### KRn:` 标题形态与卷二~卷十一 `N. KRn（第 X–Y 章完成）：` 列表行形态（r5 更正：r4 误写卷十），另须中文卷号归一「卷三→第三卷」），空锚/悬空锚 FAIL（堵「锚可空写不兑现」残留口）；卷级挂起数预算 market_params `hook_defer_budget: {per_volume: 3}`，超预算 FAIL；T5 检查点必答挂起清单（挂而不排=红）——防「35 章债挂卷二、卷二再挂卷三」的承接合法化复发；
- **章级钩注册完整性半边（r5/I6；r6/N4 补判定与注册动作）**：母钩龄期门只覆盖 pending_hooks 已注册的 14 个 MH 母钩——S4 四例（七三一/老驼纸条/帖木哥线/完颜嫂三日钟）均为**章级钩未注册**（正文在场面无钩行），龄期门对此类显示为绿。补审计半边：shenbi-review-foreshadowing 增检查点「正文存在钩性在场面（种下后承诺悬置的物/事）但 pending_hooks 无对应行 → finding，**判 blocking（`- [BLOCKING]` 行形态）**；注册动作并入 state-settling 钩增量（以该审计 finding 为确证来源，与既有 `audits/chapter-N-foreshadowing.md` 唯一确证铁律同构）」——注册完整性是龄期门的前提，不查注册则 S4 复发不可见；
- **TDD**：超龄未触达 FAIL / 触达 PASS / 带清偿锚挂起 PASS / 无锚挂起 FAIL / 悬空锚（卷/KR 不在 volume_map）FAIL / 超挂起预算 FAIL / 龄期 8 内 PASS / 多 bullet 取 max / 详情块零 bullet（种植后零推进）按总览种植章起算。

## 4. T3 · 卷纲追读三槽（获得槽/胜利预算/欲望线）＋卷二回填

**修什么**：S2/S5/S6 的大纲源头（r2 核实：volume_map KR 节点表仅 章节/节点角色/具体定位 三列，无获得槽；全 outline/ 无「胜利预算」——断言属实）。

- `volume_map.md` KR 节点表增列 **「本章主角获得」**（信息/资源/关系/地位/情感五类 + 量级 小|中|大）；「无获得」承接章允许但连续 ≤2（lint 校验）；
- 每卷头增行 **「胜利预算：本卷 N 次实质获得（≥1 大），量级递增」**——卷二建议 ≥4 次、至少 1 大（对照卷一 0 次）；
- 每卷 Objective 增 **主角自选目标**子句（主角主动要做的事 + 倒计时锚）——卷一教训：全部变更由外力文书驱动；
- `tools/lint_volume_nodes.py` 扩展：获得列非空校验 + 连续无获得 ≤2 + 胜利预算行存在（缺 → findings）；
- **卷二节点回填**（数据补丁，#74 数据型先例）：37-86 章节点逐个补获得槽与胜利预算**及轮回触点◆标记（r5：T6 数据基座——卷一标记链 ch20 后中断即此标记断供，回填须按 max_gap≤6 密度排布；r6/N2：◆回填必须先于卷二首章 dispatch——#84 开卷协议的硬前置）**；主角自选目标 = 「开春替萤把整张饼吃回来」落地为「南下第一站+船票钱 X 文」的具体倒计时（与还账进度表卷三开账衔接——卷二的微回报层=五条欠账的**局部小兑**，如 ch36 立账五条中「完颜嫂赊账页年下结」就是天然的卷二早段兑现点）。
- **TDD/取证**：lint_volume_nodes 新检查单测 + 卷二回填后 `just volume-nodes` 跑绿贴 progress。

## 5. T4 · 收尾模板多样性与钩型轮换（评审契约＋词法哨兵＋七型轮换门）

**修什么**：S8＋S1 的钩型面。r2 修正：skill 实名 `shenbi-review-group-craft`（r1 误写 shenbi-review-craft）；原型清单第一原型=账目钩形态；补七型轮换门；调和反合理化表与新体制的正面冲突。分三层：

- **评审契约层（主）**：`shenbi-review-group-craft` 提示词改三处——
  ① 新检查点：章末段落与本章已有内容 ≥60% 语义重述（「章尾复述行」）→ finding；
  ② 新检查点：连续 ≥3 章同型收尾（冷屋-点灯-数钱-压纸包 / 呢？自嘲 / 主题句）→ 卷级 finding——**注入收尾型历史（r5/I5）**：该判定的跨章上下文由 dispatcher 审查参考数据块注入「近 10 章收尾型历史」（自 T0 快照派生——skill 契约只读 N/N+1 章，无注入则此检查点空心）；
  ③ **反合理化表调和**：「章尾可以平静收束」反驳项改为「平静收束有预算（每 10 章窗 ≤3 章），超预算才判过」——与 hot_hook_floor 对齐，评审员不再拿旧盾牌挡新矛。
- **七型钩轮换门**：种子明文「轮换使用，连续两章不得同型」（outline-example.md:1178）此前零执法——`G4.cd.hook_type_rotation`：连续两章 `章尾钩型` 同型 → FAIL（读 T0 快照）；**生产者（r5/C1）**：`章尾钩型` 声明行由 plan_format v4 planning 模板新增（`章尾钩型: <悬念钩|危机钩|情感钩|反转钩|账目钩|信物钩|对位钩>` 七型词表——词表校验同 cp.emotion_tone 五值模式，G4.cp 存在性+词表检查），T0 快照摄取该行；**存量兼容显式声明**：卷一 36 章已完结零重跑、plans 现况零「章尾钩型」行（grep 实证）——无既有工件受影响；v4 前旧 plan 无该行时快照记 absent、轮换门对 absent 跳过（不计同型）；
- **词法哨兵层（辅，WARN）**：`G4.cd.ending_diversity`——末场景末 3 句命中原型模式（**账目形态第一**（数字串 ≥2 处的数钱收尾——机器面认钩/读者面读冷的错位族）/ `呢？`收尾 / `他在心里.*一遍` / 复述句起手「这一(笔|夜|章)」）连续 3 章同型时 WARN；**钩型 relabel 残留处置（r7/F7）**：轮换门消费声明值、改声明不改正文即可过门——D2 判温检查点顺带判型（声明钩型与章尾实况形态明显不符 → `- [BLOCKING]` finding，镜像 r4 ⑦ emotion_tone 先例）；
- 口癖频率帽：`tools/lint_voice_meme.py` chapter 模式增 per-catchphrase 卷配额（默认每 3 章 ≤1，「这笔我先记下」卷一 26 处 vs 建议值 12），超配 → 卷末 FAIL（#79 判据 4 消费面已有）；
- **TDD**：轮换门红测（连续同型 FAIL/异型 PASS/首章豁免）；lint_voice_meme 配额单测；ending_diversity WARN 单测（含账目形态正例）。

## 6. T5 · 检查点协议升级（温度谱/胜利账/钩龄表/挂起清单四行必答）

**修什么**：L-A 铁律——机器消费自声明，人工校准自评。

- `docs/regen-vol1-continue-prompt.md` 的 10 章检查点协议（及后续卷驱动 prompt 模板）增四行必答：
  1. **温度谱**：近 10 章开篇/章尾钩温度分布（热/温/冷计数）——零热尾即红（取数自 T0 快照，不重解析）；
  2. **胜利账**：近 10 章主角实质获得清单（对 plan 获得槽，漏报/虚报即红）；
  3. **钩龄表**：RELEVANT 钩龄期 Top5——超龄未挂起即红；
  4. **挂起清单**：本卷全部挂起声明（钩 ID＋预定清偿卷/章）——挂而不排即红（T2 预算的人工面）。
- 驱动侧（监控 agent）每 10 章对账 machine 声明 vs 正文实况抽查 ≥2 章（G3.4 式抽读，不为全量）；**抽读发现声明温度与正文温度背离 → blocking（r3 补丁）**——处置=当章 revision（正文面修复）**＋勘误面登记（r5/I7）**：快照旁 append-only errata 记录「第 N 章声明 X 与实况 Y 背离」，温度谱取数=快照＋勘误（快照不可变原则不破——回修声明改的是 plan 而 T0 不回改，勘误面是显式修正通道）。
- 文档变更 + 驱动 prompt 模板化（后续卷复用），无代码。

## 7. T6 · 金手指供给下限（能力活性维度 F18 接线）

**修什么**：S7。invariants.md 维度 9（能力活性）三槽全标「现为洞」（invariants.md:21，r2 核实属实）——本任务落地它：

- `genre-config.json pacing` 增 `core_motif_touch: {max_gap: 6}`（金手指/母题核心拍最大间隔章数；维度 9 预登记载体键位）；
- `G4.cp` 滑窗检查读 **T0 快照 `本章节点标记集`**（r5/C1：数据源=volume_map 轮回触点◆标记链，完成时摄取——**非 memo 新声明行**：plans grep「轮回触点」=0、invariants 维度 9 备忘槽是预登记洞，强造 memo 行=无生产者的死键；离线分链检验与验收 2 消费同一标记，单一来源）：距上次◆标记章 > max_gap → FAIL（**修复者双路径 r6/N2**：planning——本章为◆标记节点时 plan 补触点拍；volume-outlining——标记排布本身违例（间距>6/卷首密度塌陷）时重排◆，**重排仅限未生成章节点（r7/F6——已生成章的完成时快照不回改，重排触已生成章会造成门（快照）与 lint（直读 volume_map）双源漂移）**——门数据面在 volume_map，planning 单路径改不动它，不写双路径即修复环死锁）；**窗口规则（r6/N2）**：同 T1 本卷已生成章口径＋卷内首标记前不计间隔（卷首密度由 lint 分链 span 检查兜底）；
- **纪律不变**：供给=「进度感拍」（新碎片/新规则/新代价），**不是机制解释**——悬念纪律（轮回机制不解释）与供给下限不冲突，卷一已有合规样例（ch5 笃定无来处/ch12 要趁早记得她）；
- **同批更新 invariants.md（r3 补丁；r4 裁定 bump 时机；r5 槽位语义随数据源修正）**：落地时维度 9 行更新——数据源槽 `pacing.core_motif_touch`、门检槽 `G4.cp 滑窗` 改「已接线」；**声明槽（备忘体感触点拍）改记 `volume_map 轮回触点◆标记（T3 回填义务）`**（r5：数据源已定 volume_map，非 memo 行）；审计槽 `—` 保持；mutant 义务 motif-dormant 激活——invariants 表是 lint_invariant_coverage 的协约面，改门不改表=登记失真；**本批不 bump `CURRENT_PHASE`（保持 P1）**——lint 对期相 > 当前 P1 的维度整体不校验，本批只改文本不触发校验变化；若 bump P2 则维度 9 四槽到期、审计槽现值 `—（P2 随 F18 接线）` 为真洞即红——bump 须与 core_motif_touch 的审计 reads 面接线同批（或登记豁免依据），留后续批次；
- **离线对账同批（r3 补丁；r4 改法矫正）**：`tools/lint_volume_nodes.py` `_check_touches` 既有 gap≤8 链检只认萤回触不认轮回触点◆（卷一 ch20 后 16 章断链而 lint 绿——r3 驳斥发现）——扩法为**按标记类型分链检验**（轮回触点◆单独成链跑 gap/span 检查，萤回触链保持现状；并集扩法无效：模拟验证轮回+萤回触并集链 max gap=7 仍 findings=0，断链被萤回触掩盖——与章级门按快照「轮回触点◆」单母题链计数的口径一致）。
- **TDD**：间隔 7 章 FAIL / 6 章 PASS / ◆标记缺席章（非标记节点）不计间隔 / 卷一 ch21-36 断供标本回放（16 章零◆标记 → FAIL）/ shadow 位。

## 8. T7 · 既有留存门升级（retention_anchor 窗口参数化；r7/F8：与 T1 同检查族同配置块同 shadow 纪律，plan 阶段可并入 T1 作同批子项）

**修什么**（r2 新增）：`G4.cp.retention_anchor`（chapter_planning.py:375-388）窗口硬编码 1-30 章——卷一 ch31-36 已无留存锚声明要求，卷二全卷更全在窗外。留存是本 spec 主题词，现存留存门 30 章后自己熄火；参数化是最便宜的一刀。

- market_params 增 `retention_anchor: {from_ch: 1, to_ch: null}`（null=全卷）——卷二起全卷恢复留存锚声明要求；
- **TDD**：30 章后缺声明 FAIL / 窗口边界（from/to 生效）/ 配置缺席沿用旧硬编码（存量兼容）。

## 9. 非目标（防过度工程）

- **不做**正文级钩强度分类器（词法判定误报率高——热钩语义判定交引句锚定的 audit 判温＋T5 人工抽读）；
- **不动**卷三-卷十二的兑现曲线与还账进度表排期（种子叙事结构，只有卷二加微回报层）；
- **不做**「赢大了」的机器判定（胜利量级=自声明+人评双通道，机器只管分布下限）；
- 不重写 #76 声口体系（口癖只加频率帽）；
- **不建** relabel 事后检测器（T0 快照从源头使 relabel 无效，不做二次取证面）。

## 10. 验收（=卷二防复发判据）

1. 全部新门红测→绿 + `just check` exit 0；新 FAIL 门 shadow 位默认 true，首束零误伤后转正（转正动作记台账）；**shadow 转正机器催转（r3 补丁；r4 前置化）**：前置=T1 的「shadow WARN 事件逐束落盘+误伤裁定记录面」先行交付，lint 读该数据面检查「shadow 门连续 2 束零误伤未转正」→ red（治遗忘性 shadow 永久化——门停在 WARN=没建）；
2. 卷二首 10 章实弹：热章尾钩 ≥1、四连冷零发生、超龄钩零（带清偿锚挂起除外）、金手指供给间隔 ≤6 章（**双源度量**：volume_map 轮回触点◆标记 + 正文 grep，ch21-36 断供为红测标本）、获得槽全非空且连续无获得 ≤2、七型钩零连续同型、留存锚声明覆盖全卷——regen-accept 新增判据行（或并判据 2c/4 扩展）；
3. 10 章检查点四行必答首跑对账无红；
4. G3.4 卷二段评：D6 情绪拍 ≥85（卷一 83）、D2 悬念 ≥86（断供钩类扣分清零）；
5. **词表外 tone 零洗白（r3）**：快照写入校验红测（词表外 tone WARN+按冷处理）；check_emotion_proxy 滑窗化后词表外章不再斩断冷连击（ch5/12/15 型标本回放）。
