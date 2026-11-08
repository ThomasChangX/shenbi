# Spec #100 · 草写字数带首派达成（drafting-band-first-pass）：POST 自检虚报的死线接通

**日期**：2026-11-08 ｜ **系列**：生产运行慢族根治批（束4-束7 三窗实锤；spec #98 束7 分叉落点件） ｜ **状态**：**Done (PR #316)**（r7·2026-11-09——r6 收敛订正（线 3 指标替换：第一次重派 POST 声明双边偏差 ≤2%[基线 4.6%/2.8%]+monitor_rewind RETRY 计数[基线 6，bundle 级]——原「loop 8→2→3→8」系 issue 数非 loop 数且第二轮带内率 2/2 无 headroom；helper 改返回 `list[int]` 保行为；INDEX 内容行同步；3200 示例删；M1 主句/P3 理由/§3 回退/§2 三线）。**r6** 2026-11-09——阶段 3 设计审查修复（C1 T3 三线拆归因+线3=①机制线；C2 新增 `parse_post_wordcount_declarations` 单源助手；最小性采纳=precision 句并入既有 word_band 报文[零新 id/零新解析面/零族坍缩]；I1 触发覆盖 4/6+① 重定性；I3 ② 只留净新增；I4/M1-M6 全落）。**r5** 2026-11-09——阶段 2 事实核实机械订正（「带中值」→default 起点/ch45 口径 2881/「逐字」→数值逐位/成本账源）。**r4** 2026-11-09——r3 收敛订正（manifest 计数 34 entry/13 唯一 WARN、漂移 2.1-15.5%；T0 三证化；报文触发收窄为「实测<下限」；INDEX 内容行同步）。**r3** 2026-11-09——r2 delta 复核三处契约级钉死（F1 触发条件改「声明在带∧实测出带」=天然与 word_band 同批；F2 预算语义改为「不升 HARD、仍计 monitor-rewind 预算」；F3 报文带 word_band token+分叉措辞；F4/F6/F9/F10 低优先落）；H4 措辞修正「函数能力 100%、首派 bundle 面未接线」。**r2** 2026-11-09——价值门驳斥复核改道：H1/H2/H3 三假设全驳斥（plan 预算已在首派 prompt+EXEMPLAR 锚已落地+plan 预算 3200-3400 不贴下沿）；真根因改判为 **POST 自检回显 PRE/plan 而非实测正文**（ch47 声明 3210/实测 2288 虚 40%、ch48 3250/1646 虚 97%）；候选①②③全弃（信息面已存在/前提不成立/范畴错误），改道=关闭 `cd.post_wordcount_precision` 死线+教学禁照抄；优先级 P2→**P3**。r1 立项 2026-11-08） ｜ **优先级**：🟡 P3（**降级理由**：欠带现象真实但机器环 2 派收敛可忍（ledger 束7 实测 $0.2405/23 派全窗、drafting 单派 ≈$0.008-0.016；#18 裁「可留机器环」——r5 去掉无账源的 $0.03-0.05 估算）；主修=小面反馈补充句（非关闭死线），不开新机制）
**依赖**：无硬依赖；**与 #96 共用 1 处文件**（`skills/shenbi-chapter-drafting/SKILL.md`——#96 主战场为 SKILL×3 含此件）→ **#96 施工期本 spec 让行**（plan 首步 re-anchor）；证据源=novel-xinghuo-vol1 运行工件（trace monitor_rewind+首派 blob+章文件）。
**动机证据**（三窗同族链；r2 修正）：①束4 裁决 #11：四派约束交换（trace seq 1070 首派 ch43 2256/ch44 **1788**——ledger 摘要写 2391 系 loop 2 值，r2 以 trace 为准）；②束5 裁决 #14：手工手术扩写收束；③束7 裁决 #18：loop 振荡熔断→缺口算术反馈 **2 派收敛**（8→1→PASS）。实测六章首派：2256/1788/2881/2052/2288/1646（word_band 口径；ch45 的 2889 系场景和/chapter_band 口径——r5 勘误）vs 带 [2800,4000]——**5/6 章总额欠带（-18%~-41%）、ch45 例外（总额 2881 在带但场景 2/3 落灰域 <900）**。

**触及的不变量维度**：无（prompt/反馈教学面——字数带硬闸 [2800,4000] 与平台档位承诺均不动）。

---

## 0. 根因假设（r2 全量重写）

- **H1（r2 驳斥）**「场景预算与字数带脱钩」**不成立**：`目标字数 3200` + `场景1 1050/场景2 1100/场景3 1050` 就在首派 user prompt 原文（读面 `## 1. 当前任务` 的 H2 body 含 `### 场景预算与收束钩`；blob 实测行 299/310-313）；模型 PRE 自检也引用了同量级数字（1090/1090/1030=3210）。信息面 100% 在场。
- **H2（r2 驳斥）**「无首派目标锚」**不成立**：首派已有双重锚——①plan 逐场景预算（同上）；②**上一通过章全文 EXEMPLAR**（spec #95 T5，`chapter_loop.py` 例章注入，首派常驻；blob 实见 `## EXEMPLAR CHAPTER`）。
- **H3（r2 降级为结构备注）**「带下限贴沿」**不构成操作性根因**：六章 plan 预算实测 3200-3400（不贴 2800 下沿）；`3×900=2700<2800` 的算术张力是真实常量（场景合法域下限合计可低于带下限），但 5/6 首派连 2700 都没到——记 SKILL 备注即可，不修 planning 分配规则。
- **H4（r2 新增，主根因）**：**首派 POST 自检回显 PRE/plan 预算而非实测正文**——ch47 POST 声明「场景1 1093/场景2 1090/场景3 1027；总计 3210（2800–4000 带内）」实测 2288（虚 40%）；ch48 声明 3250 实测 1646（**虚 97%**）；束5-7 四章 POST≈PRE（ch45/46 的**数值逐位相同**——PRE 1140/1170/1050 vs POST 同值，整行文本不同/r5 措辞订正）。模型不是「不知道该多长」，而是**自检虚报后自认达标**——故首派不自修正。既有检测 `check_post_wordcount_precision`（`gates/g4/post_declarations.py`，声明 vs 实测差 >2% 即报）**函数能力 100%**，但**首派 bundle 面未接线**：G4.cd 只在 promotion 之后对 `chapters/chapter-n.md` 跑，首派短 bundle 在 `validate_split` 即被 word_band 拒、promotion 不发生 → **被 word_band 拒的首派短 bundle** 从未执行该函数；已晋升章可检出但只落 G4 **WARN**（manifest 实测 **34 个 gate entry / 13 条唯一 WARN**，漂移 **2.1%-15.5%**，如 ch37 4.4%/ch38 6.6%/ch45 2.8%/ch46 6.8%/ch48 2.9%），不进 rewind 反馈。三证合起来=典型**检测能力在场、首派消费死线**（证据面：manifest 34 entry/13 唯一 WARN + rewind issues 无 precision 行 + 被 word_band 拒的首派短 bundle 未跑 G4.cd[通过 validate_split 的首派在 promotion 后仍跑 G4、只是 WARN 不进反馈]）。**触发覆盖实测 4/6**（false in-band claim：ch43 2885/2256、ch46 3400/2052、ch47 3210/2288、ch48 3250/1646；ch44 声明本就出带不触发、ch45 实测在带不触发）——故 ① 的真实效力=**在已触发的重派反馈里补一句对自检虚报的当场反驳**，不是「关闭死线」，也非 no-op。

## 1. 任务分解（r2）

- **T0 数据面（半天，无实弹）**：三窗六章首派 POST 声明 vs 实测逐章表（虚报率分布）+ POST≈PRE 逐字回显率统计（ch45/46 逐字相同核）+ `cd.post_wordcount_precision` **三证核**（manifest 34 entry/13 唯一 WARN 分布 + rewind issues 无 precision 行 + 首派短 bundle 未跑 G4.cd——非 trace 面，trace 不记一般 WARN）+ 场景合法域合计-带下限张力核算。产出 `docs/research/` 报告（含 H1/H2/H3 驳斥证据表+H4 成立证据）。
- **T1 修复面（branch+PR，r2 两候选同批）**：
  ①**重派反馈补自检反驳句（主；r6 按最小性改道）**：**不新增 issue 行/不新增 id**——把「POST自检申报 {X}（在带内）而实测 {Y}<{下限}——自检虚报，须逐段真实点数补足缺口，禁照抄计划/PRE 预算」**追加到既有 `word_band` 报文尾部**（`validate_split` 内，同一 `total` 口径），零新解析面、零 id 语义问题、零族坍缩风险（自然继承 `word_band` 的族命中/前稿注入/预算语义——**不新增计数、不新增轮次**；`retry_budget_consumed` 按轮自增与该轮 issue 条数无关）。
     - **前置助手（C2 钉死）**：新增纯助手 `parse_post_wordcount_declarations(content: str) -> list[int]`（单一解析面，**返回全部声明行值**——原函数遍历行为零变；`validate_split` 取**最后一条**判 F1；用既有 `_POST_WORDCOUNT_DECL_RE`，**落 `post_declarations`**（pipeline→gates 单向依赖允许，正则与助手同文件不产生第二解析面；不落 shared 以避正则随迁））——`check_post_wordcount_precision` 重构为消费它（行为/严重度/id **全不变**）。**禁止**从返回串反解数字或复刻私有正则；**禁止**透传旧串（其尾注「改声明一行」与「补足缺口」互斥）。
     - **触发条件（F1 钉死）**：仅当「declared ∈ 带 ∧ actual < 下限」时追加该句；纯声明漂移（actual 在带）维持既有 G4 WARN、不进 rewind；**over-band 的 false claim 不在本批域**（r4 收窄保持）。
  ②**教学面（只留净新增，I3 钉死）**：`skills/shenbi-chapter-drafting/SKILL.md:110` 篇幅契约段**净新增两句**（既有「逐段计数合计/禁止整段估数」不重炒）——「**不得以 PRE 自检行或计划场景预算的总计充作 POST 总计**，POST 必须重新点数（实测六章虚报 16-97%）；目标值=`chapter_word.default`（符号引用；带下限只是硬底线，不得按底线思维铺量）」——**不硬编码 3200**（通用 SKILL 不得写死项目值；`chapter_word.default` 是既有符号引用，:175 同款）。
  ③（弃案声明）原候选①逐场景目标字数显式化=信息面已存在（plan 预算已入首派 prompt）→不重复建设；原候选②planning 预算对齐=前提不成立（预算 3200-3400）；原候选③现值前移=范畴错误（实际值只在正文后存在）。**字数带硬闸与 [2800,4000] 档位值不动**。
- **T2 离线验收（r6）**：fixture=seq248 首派 blob **解包 `files[0].content`**（24KB JSON 信封非裸 bundle）存 `tests/fixtures/spec100/ch47-48-first-pass-bundle.md`；ch48 真实章文件（无 `===CH:===`）用 `SplitChapter(number=48, body=…, scenes=…)` 直构（M5 钉死）。
  ①**false in-band 正例**：ch47 首派 bundle → `validate_split` 的 `word_band` 报文**含**「POST自检申报 3210」+「实测 2288」+「补足缺口」且**不含**「改声明一行」（红绿：改前无该句→改后有）；
  ②**in-band 负例**：final ch48（声明 3006/实测 3093=2.9%）→ `validate_split` 的 issues **无**「POST自检申报」句（不 rewind）、既有 G4 WARN 仍产出；
  ③**over-band 负例（M4）**：构造 declared 3200/actual 4100 → issues **无**「POST自检申报」句（r4 收窄锁死）;
  ④SKILL 净新增存在性（禁抄 PRE/计划总计句 + `chapter_word.default` 符号引用），并断言旧「改声明一行」不出现在新通道；
  ⑤`parse_post_wordcount_declarations` 单源直测（多声明 返回 list[int]（文档序，validate_split 取最后一条）/无声明 []/与 `check_post_wordcount_precision` 同源）；
  ⑥既有 drafting/scene-split 测试零翻转。
- **T3 实弹验收（搭卷二续跑窗；**r6 拆三线归因**——C1 钉死）**：
  - **线 1（② 的指标）**：累计首派带内率（≥3 窗，记每窗分母；基线六章 1/6）——② 进 system prompt，是唯一能移动首派的件；
  - **线 2（② 的指标）**：首派 POST 声明**双边偏差** `max(declared/actual, actual/declared) ≤ 1.05`（基线 1.16-1.97；测首派=②之效）；
  - **线 3（① 的指标，r7 指标替换）**：**第一次重派的 POST 声明双边偏差 ≤2%**（G4 同口径；基线实测 ch47 声明 3358/实测 3511=4.6%、ch48 3100/3015=2.8%——① 的句子正作用于该量，headroom 真实）+ **每 bundle `monitor_rewind` RETRY 计数**（基线束7=6，`payload.reason.kind` 稳定计数；**loop 是 bundle 级**非每章——原「loop 8→2→3→8」系 issue 数简写非 loop 数，r7 勘误）。「第二轮带内率」降为**天花板防回归指标**（基线 2/2 已满，仅防退不可作改善判据）；
  - 三线分记**不得互读**；窗口须钉模型+thinking 设置（账本混用 deepseek-flash/v4-flash 别名，换代混淆首派率）。线 1/2 未达而线 3 改善 → 记「自检反驳生效、首派长度仍需机器环」交用户裁（不硬修）。

## 2. 验收（r2）

1. T0 分布报告落 `docs/research/`（含 H1/H2/H3 驳斥证据+H4 成立+死线零消费实证）；
2. T1 PR 合并（CI 全绿+① precision 句并入 word_band 报文的离线断红→绿+②教学在场+零翻转）；
3. T3 三线记录落 vol1-ledger（束级条目）。

## 3. 风险与回退（r2）

- prompt/反馈面改动回退=还原 SKILL 两句+`validate_split` 的 precision 追加分支+助手/原函数重构两处代码（约 3 处），无运行态迁移；
- ①只对 false in-band 触发且必与 word_band 同批——**不新增派发轮次**；纯声明漂移维持 WARN 不进 rewind（manifest 13 条唯一 WARN 的已通过章不受影响）；
- ②教学若被模型读成「必须写到 3200」→过冲风险（>4000）：正例取 default（3200）且带双向门不动；
- 与 #96 共用 drafting SKILL 文件域——执行序避让（#96 施工期本 spec 不动同文件）。
