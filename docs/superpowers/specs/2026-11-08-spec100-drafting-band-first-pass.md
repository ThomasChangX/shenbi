# Spec #100 · 草写字数带首派达成（drafting-band-first-pass）：POST 自检虚报的死线接通

**日期**：2026-11-08 ｜ **系列**：生产运行慢族根治批（束4-束7 三窗实锤；spec #98 束7 分叉落点件） ｜ **状态**：Active（**r5** 2026-11-09——阶段 2 事实核实机械订正（「带中值」→default 起点/ch45 口径 2881/「逐字」→数值逐位/68 条残句/成本账源）。**r4** 2026-11-09——r3 收敛订正（manifest 计数 34 entry/13 唯一 WARN、漂移 2.1-15.5%；T0 三证化；报文触发收窄为「实测<下限」；INDEX 内容行同步）。**r3** 2026-11-09——r2 delta 复核三处契约级钉死（F1 触发条件改「声明在带∧实测出带」=天然与 word_band 同批；F2 预算语义改为「不升 HARD、仍计 monitor-rewind 预算」；F3 报文带 word_band token+分叉措辞；F4/F6/F9/F10 低优先落）；H4 措辞修正「函数能力 100%、首派 bundle 面未接线」。**r2** 2026-11-09——价值门驳斥复核改道：H1/H2/H3 三假设全驳斥（plan 预算已在首派 prompt+EXEMPLAR 锚已落地+plan 预算 3200-3400 不贴下沿）；真根因改判为 **POST 自检回显 PRE/plan 而非实测正文**（ch47 声明 3210/实测 2288 虚 40%、ch48 3250/1646 虚 97%）；候选①②③全弃（信息面已存在/前提不成立/范畴错误），改道=关闭 `cd.post_wordcount_precision` 死线+教学禁照抄；优先级 P2→**P3**。r1 立项 2026-11-08） ｜ **优先级**：🟡 P3（**降级理由**：欠带现象真实但机器环 2 派收敛可忍（ledger 束7 实测 $0.2405/23 派全窗、drafting 单派 ≈$0.008-0.016；#18 裁「可留机器环」——r5 去掉无账源的 $0.03-0.05 估算）；主修=小面死线接通，不开新机制）
**依赖**：无硬依赖（主战场 `src/shenbi/pipeline/scene_splitter.py`/`skills/shenbi-chapter-drafting/SKILL.md`，不抢 #96 文件域——若 #96 同期施工则本 spec 让行）；证据源=novel-xinghuo-vol1 运行工件（trace monitor_rewind+首派 blob+章文件）。
**动机证据**（三窗同族链；r2 修正）：①束4 裁决 #11：四派约束交换（trace seq 1070 首派 ch43 2256/ch44 **1788**——ledger 摘要写 2391 系 loop 2 值，r2 以 trace 为准）；②束5 裁决 #14：手工手术扩写收束；③束7 裁决 #18：loop 振荡熔断→缺口算术反馈 **2 派收敛**（8→1→PASS）。实测六章首派：2256/1788/2881/2052/2288/1646（word_band 口径；ch45 的 2889 系场景和/chapter_band 口径——r5 勘误）vs 带 [2800,4000]——**5/6 章总额欠带（-18%~-41%）、ch45 例外（总额 2881 在带但场景 2/3 落灰域 <900）**。

**触及的不变量维度**：无（prompt/反馈教学面——字数带硬闸 [2800,4000] 与平台档位承诺均不动）。

---

## 0. 根因假设（r2 全量重写）

- **H1（r2 驳斥）**「场景预算与字数带脱钩」**不成立**：`目标字数 3200` + `场景1 1050/场景2 1100/场景3 1050` 就在首派 user prompt 原文（读面 `## 1. 当前任务` 的 H2 body 含 `### 场景预算与收束钩`；blob 实测行 299/310-313）；模型 PRE 自检也引用了同量级数字（1090/1090/1030=3210）。信息面 100% 在场。
- **H2（r2 驳斥）**「无首派目标锚」**不成立**：首派已有双重锚——①plan 逐场景预算（同上）；②**上一通过章全文 EXEMPLAR**（spec #95 T5，`chapter_loop.py` 例章注入，首派常驻；blob 实见 `## EXEMPLAR CHAPTER`）。
- **H3（r2 降级为结构备注）**「带下限贴沿」**不构成操作性根因**：六章 plan 预算实测 3200-3400（不贴 2800 下沿）；`3×900=2700<2800` 的算术张力是真实常量（场景合法域下限合计可低于带下限），但 5/6 首派连 2700 都没到——记 SKILL 备注即可，不修 planning 分配规则。
- **H4（r2 新增，主根因）**：**首派 POST 自检回显 PRE/plan 预算而非实测正文**——ch47 POST 声明「场景1 1093/场景2 1090/场景3 1027；总计 3210（2800–4000 带内）」实测 2288（虚 40%）；ch48 声明 3250 实测 1646（**虚 97%**）；束5-7 四章 POST≈PRE（ch45/46 的**数值逐位相同**——PRE 1140/1170/1050 vs POST 同值，整行文本不同/r5 措辞订正）。模型不是「不知道该多长」，而是**自检虚报后自认达标**——故首派不自修正。既有检测 `check_post_wordcount_precision`（`gates/g4/post_declarations.py`，声明 vs 实测差 >2% 即报）**函数能力 100%**，但**首派 bundle 面未接线**：G4.cd 只在 promotion 之后对 `chapters/chapter-n.md` 跑，首派短 bundle 在 `validate_split` 即被 word_band 拒、promotion 不发生 → 该函数在首派阶段**从未执行**；已晋升章可检出但只落 G4 **WARN**（manifest 实测 **34 个 gate entry / 13 条唯一 WARN**，漂移 **2.1%-15.5%**，如 ch37 4.4%/ch38 6.6%/ch45 2.8%/ch46 6.8%/ch48 2.9%），不进 rewind 反馈。三证合起来=典型**检测能力在场、首派消费死线**（证据面：manifest 34 entry/13 唯一 WARN + rewind issues 无 precision 行 + 首派短 bundle 未跑 G4.cd）。

## 1. 任务分解（r2）

- **T0 数据面（半天，无实弹）**：三窗六章首派 POST 声明 vs 实测逐章表（虚报率分布）+ POST≈PRE 逐字回显率统计（ch45/46 逐字相同核）+ `cd.post_wordcount_precision` **三证核**（manifest 34 entry/13 唯一 WARN 分布 + rewind issues 无 precision 行 + 首派短 bundle 未跑 G4.cd——非 trace 面，trace 不记一般 WARN）+ 场景合法域合计-带下限张力核算。产出 `docs/research/` 报告（含 H1/H2/H3 驳斥证据表+H4 成立证据）。
- **T1 修复面（branch+PR，r2 两候选同批）**：
  ①**死线接通（主，r3 三处契约钉死）**：在 `validate_split` 逐章校验处（输入=该章 body+`total_chars_md_text`，`scene_splitter.py:211-236`、`:91-97` 口径单源）复用 `check_post_wordcount_precision`，但：
     - **触发条件（F1 钉死）**：**仅当「声明总计在带内 ∧ 实测 total 出带」**（**r4 收窄：实测 < 下限**——全部证据与「补足缺口」动作同向；over-band 的 false claim 不在本批域）时把 precision 行并入 issues → 进 rewind。**纯声明漂移（实测在带、声明差 2.1-15.5%）维持既有 G4 WARN、不进 rewind**——manifest 13 条唯一 WARN（已通过章）不得被误杀，也不新增任何派发轮次（false in-band 必然与 word_band 同批，天然合并）。
     - **报文形（F3/F4 钉死）**：前缀带长度族 token——`word_band:ch{N}:POST自检申报 {X}（在带内）而实测 {Y}<{下限}——自检虚报，须逐段真实点数补足缺口，禁照抄计划/PRE 预算`（token 使 `classify_retry_family` 命中长度族→自动获得前稿注入与定向附录）；**不写「只改声明」**（此时实测量已出带，动作=扩写+改声明，措辞单一不会诱导 in-band 章扩写）。
     - **预算语义（F2 钉死）**：**不升 G4 HARD；仍计入 monitor-rewind 重试预算**（`retry_budget_consumed`，>3 可 ESCALATION）——与 word_band 同一 durable 计数器，二者不可兼得，此处选择保留修复力。
  ②**教学面**：`skills/shenbi-chapter-drafting/SKILL.md` 篇幅契约段（:110 区）追加——「POST 字数自检必须逐段**重新点数**，**禁止复制 PRE 预算行或计划场景预算数字**（实测六章虚报 16-97%）；目标值=plan 场景预算逐场景锚定（之和 ≥3200（`chapter_word.default` 起点；[2800,4000] 的算术中值是 3400，3200 系 default 非中值——r5 勘误）；≥2800 仅为硬底线，不得按底线上限思维铺量），写作按目标铺量而非按叙事自然长度」。
  ③（弃案声明）原候选①逐场景目标字数显式化=信息面已存在（plan 预算已入首派 prompt）→不重复建设；原候选②planning 预算对齐=前提不成立（预算 3200-3400）；原候选③现值前移=范畴错误（实际值只在正文后存在）。**字数带硬闸与 [2800,4000] 档位值不动**。
- **T2 离线验收**：fixture 回放（束7 ch47/48 首派 blob 复制入 `tests/fixtures/spec100/`，G0.9）——①false in-band 虚报报文可产出且进 issues 列表（红绿：改前 issues 无 precision 行→改后有，且带 `word_band` token）；②**in-band 漂移用例（F10）**：取 manifest 真实反例 final ch48（声明 3006/实测 3093=2.9%）→ 断言 **issues 无 precision 行（不 rewind）**、既有 G4 WARN 仍在；③SKILL 教学存在性断言（禁照抄句+逐段点数句+≥3200 口径在场）；④既有 drafting/scene-split 测试零翻转。
- **T3 实弹验收（搭卷二续跑窗）**：**双观测线**——线 1（首派带内率）：后续束窗 ≥1/2 章首派总额入带（对照六章基线 1/6）；线 2（虚报率）：**双边偏差** `max(declared/actual, actual/declared) ≤ 1.05`（对照六章 1.16-1.97；单边比值会被少报绕过）；线 1 用**累计**首派带内率并记每窗分母（单窗 n=2 统计力不足，累计 ≥3 窗后裁定）；两线分记。若线 2 达标而线 1 未达 → 记「自检保真已修、首派长度仍需机器环」并交用户裁后续（不硬修）。

## 2. 验收（r2）

1. T0 分布报告落 `docs/research/`（含 H1/H2/H3 驳斥证据+H4 成立+死线零消费实证）；
2. T1 PR 合并（CI 全绿+①进 rewind 通道的离线断红→绿+②教学在场+零翻转）；
3. T3 双观测线记录落 vol1-ledger（束级条目）。

## 3. 风险与回退（r2）

- prompt/反馈面改动回退=还原文本与一行接线，无运行态迁移；
- ①只对 false in-band 触发且必与 word_band 同批——**不新增派发轮次**；纯声明漂移维持 WARN 不进 rewind（manifest 13 条唯一 WARN 的已通过章不受影响）；
- ②教学若被模型读成「必须写到 3200」→过冲风险（>4000）：正例取 default（3200）且带双向门不动；
- 与 #96 共用 drafting SKILL 文件域——执行序避让（#96 施工期本 spec 不动同文件）。
