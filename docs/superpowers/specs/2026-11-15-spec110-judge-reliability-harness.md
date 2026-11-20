# Spec #110 · 评审信度测量 harness（judge-reliability-harness）：判官间一致性/分布形状离线报告工具 + #107/#103/#115 消费判据营养接线

**日期**：2026-11-15｜ **系列**：多专家审计批（expert-audit）｜ **状态**：Design（r2 Revised 2026-11-21；r1 2026-11-15）｜ **优先级**：🟠 P1
**Depends on**：无硬依赖；数据卫生消费 #109 T4 口径（已落地 PR #361——`src/shenbi/pipeline/audit_starve_family.py` 单源）；T2/T3 与活跃 #115 T4 交叉对齐（分工见 §0 r2 修订背景）
**动机证据**：vol1 全量离线统计（2026-11-15 审计，脚本判据可重放；r2 协调者+fresh-context 驳斥双重复核，数字逐字吻合）：跨审计技能两两 Cohen κ 除同派发自相关伪影（group-character 族 pov×dialogue×character κ=+1.0、craft 族 reader-pull×texture κ=+0.842——同一次派发的多产物）外全部 |κ|≤0.25、多数 ≈0；Cronbach α=**0.311**（10 个 always-on 审计文件为 items、25 个双净章为 subjects——审计族**不共享「章质量」潜因子**）；resonance overall × 其余审计 issue 总量 **r=+0.068**（n=28——共鸣分与其余全部判官正交）；`truth/resonance_trend.md`（overall=四维简单和 32/32；分布 sd=2.40、极差 74-86、模值 79 出现 12/32；「相对位置」计数 相当73/更差19/**更好0**——判官从不越锚上方；通胀 slope +0.073 分/章 r=0.435 t=2.65 df=30；confidence=high 占 24/32——**校准面存在但从未咬合**：vol1 `truth/resonance_anchors.md` 23 行全 `0|0`（total<`_MIN_ANCHOR_DENOMINATOR=3` 永远 fail-open），`TREND_CONFIDENCE_IDX` 只写不读（resonance_policy.py:386 自述无下游读者））；`skills/shenbi-review-resonance/SKILL.md:70-72 与 :196-218`（锚点先行铁律+Route A「比锚点更好/相当/更差」对照规则——锚定方向的协议根源；r1 误引 :103-116 实为 chapter_role 校准门，r2 修正）；`docs/superpowers/specs/archive/2026-11-15-spec106-resonance-floor-liveness.md`（**已归档**——r3 已把 shadow 毕业判据改为「毕业=用户裁定、触发率降级为观测记录非判据」，r1 引用的「触发率单指标预期带 5-20%」文本已不存在）；`2026-11-15-spec107-*.md` T2（A/B 判据=canary 捕获率差分——9 变异/臂两比例检验 power 0.10-0.25（30pp 效应）、0.10（15pp 效应）；**McNemar 配对**同数 27/臂 0.56-0.60、45/臂 0.78-0.81、63/臂 0.90+——现设计尺寸不足以支撑任何结论）；`2026-11-15-spec103-*.md` T1（选章判据消费 confidence=high——未校准自报）；`2026-11-15-spec115-*.md` T4（已预埋本件义务：报告须同时报分布形状与外部锚定效度、κ/α 不得单独作判官可用性结论+#103 消费面 ρ<0.3 回退闸）；`src/shenbi/gates/g7.py:246`（G7.15 同分向量/双评探针测的是**判官对自己的稳定性**，非判官之间的一致性——信度维度体系级缺席）。

**触及的不变量维度**：无（测量基建——只读消费审计产物与 trend 数据面）

**立项预答（v7.1 ④⑤，r2 补栏——驳斥轮产出）**：
- **④博弈路径清单**：(a) 卫生绕过——实现自写饿死词表不 import 单源 → 堵法：T1 钉死 import 义务（`audit_starve_family` 头注明言「spec prose is a gloss, never authoritative」）；(b) 报告被下游当门禁 → 现状生产代码零读 reports/（grep 实证），软纪律防线（命名+文档「观测面」声明，#108 T3 同款先例）；(c) 同派发伪影 κ 未去伪 → 堵法：分组键机器可读（group 族 SKILL writes 声明单次派发产物）+验收红测反例（r2 新增）；(d) 新卷冷启动（实评行不足）→ 堵法：「样本不足」披露行不输出误导值（先例 MIN_SAMPLES_SIGMA、`_MIN_ANCHOR_DENOMINATOR=3` fail-open）；(e) spec 文本接线被后续修订静默覆盖 → 已实证（#106 r3 于本件立项后两天改判据），r2 即响应；#107 引用行由其 T2 落盘时兑现，「grep 可证」为时点快照属已接受残差。
- **⑤候选机制清单（buy-before-build）**：audit_starve_baseline+audit_starve_family ~35%（卫生 100%/语料遍历 ~80%/统计 0%）｜report_longitudinal（`parse_resonance_trend`）+extract_finding_units ~30%（trend 解析+issue 抽取原语）｜gate_power_replay 骨架 ~25%（回放/落盘/基线纪律）｜external-anchor analyze.py ~15%（ICC≠κ、人类面板、休眠）｜detect_score_decline ~10%（仅下行斜率绊网）｜check_scorer_agreement ~5%（T1 评分面非审计判官）——**无候选覆盖 κ/α 计算本体，新建薄壳**：复用前三者原语，新建仅统计核心。

---

## 0. 根因

**体系测量了判官的一切除了「判官之间对同一对象的意见一致性」与「分数分布的形状」**：一致性有同分向量、塌缩有 flag_score_collapse、置信有锚点命中率，但跨技能 κ/α、共鸣分×缺陷量的效度相关、模值吸引子/从不更好/通胀斜率这些**信号质量元指标**无处生产。后果：resonance 已进生产路由（#106 armed 路由落地，正交信号 r≈0.07 驱动修订分流）而信号退化无仪表可察；#107 的 A/B 按现尺寸跑了也下不了结论；#103 消费未校准的 confidence——在飞 spec 的验收被迫盲飞。

**r2 修订背景（2026-11-21 价值门改道裁定）**：r1 的 T2 前半瞄准 #106 T2 shadow 毕业判据（≥48 章 Wilson 窗+形状哨兵两行）——#106 已于 2026-11-17 完结归档且 r3 把毕业判据改为「用户裁定」（触发率降级观测记录），编辑目标死亡；#115 T4 同时在 #103 消费面设置了 ρ<0.3 外部锚回退闸。r2 三处改道：T2 重构（#106 bullet → #115-T4 对齐双报义务）、T3 两闸合一、T1 吸收驳斥轮 hardening（import 钉死/group 族红测/冷启动披露/薄壳复用面）。

**用户裁定（2026-11-15）**：不考虑在飞项目——报告工具对 vol1 存量数据回放仅产出基线报告（数字入 spec 验收节），不清洗不补评。

**备选案已评估并否决**：「等 #107 C 臂换模型后再测信度」——信度≠准确：同模型判官间的零一致本身就是缺陷证据（不依赖第二模型存在）；「信度并入 #108 canary 报告」——canary 测召回（植入缺陷），信度测一致（自然章跨判官），测量对象与数据面都不同，合并稀释两者判据。

## 1. 任务分解

### T1 · 离线信度报告工具（r2 薄壳形态，复用面钉死）
- `just judge-reliability <dir>`（`tools/judge_reliability.py`，纯确定性统计，零 LLM）。**复用钉死**：卫生=import `src/shenbi/pipeline/audit_starve_family`（禁自写词表）；issue 计数=复用 `extract_finding_units`（`src/shenbi/pipeline/audit_aggregate.py:114`）；trend 解析=复用 `parse_resonance_trend`（`tools/report_longitudinal.py:68`——tools→tools import 若被 lint 拦则上移 src 单源化，plan 期定形）；新建仅统计核心（κ/α/相关/形状）：
  - 跨技能两两 κ + 原始 agreement rate（κ 对 prevalence 敏感，双指标并报；**同派发族产物按技能分组去伪**——group 族四文件/三文件各为一 item，分组键=group-character/craft SKILL writes 声明的单次派发产物族）；
  - Cronbach α（always-on 审计族 items × 章 subjects；「有无硬发现」二值 + 计数两版并报）；
  - resonance 效度相关（overall × 其余 issue 总量；overall × word count 长度偏差负对照）；
  - 分布形状：模值频率表、sd、极差、相当/更差/更好计数、通胀 slope（章号回归）、confidence 基率；
  - 前置数据卫生：剔除 #109 T4 口径的 invalid（饿死形态）审计（import 单源，见上）；
  - **冷启动披露（r2）**：实评行 <8 时分布形状节输出「样本不足」披露行，不输出误导值；
  - **#119 接缝注记（r2，不依赖）**：INDEX 已预告本工具取数口径潜在消费 #119 纯形谓词单源（pre-rev 污染过滤第二卫生面）——#119 落地后接线一行，本批不阻塞。
- 报告落 `reports/judge-reliability-<ts>.md`（canary 报告同目录先例）；**报告须同时含「分布形状」与「外部锚定效度引用」两节**（#115 T4 对齐义务——后者在外部锚数据面未就绪时输出披露行「#115 T3 外部锚定未执行」，κ/α 不得单独作为判官可用性结论）。

**判据**：对 vol1 回放产出基线报告，关键数字与动机证据节一致（α≈0.31、r≈0.07、更好=0、模值 79×12）；红测（同分输入→α=1；独立输入→α≈0；prevalence 极端 κ 警示行；饿死剔除计数；**group 族不分组直两两→伪影警示行（r2 新增）**；**冷启动不足窗→披露行（r2 新增）**）。

### T2 · 在飞 spec 判据营养接线（r2 重构）
- #107 T2 预注册文档义务（保留）：A/B 判据改 **McNemar 配对设计**（同变异两臂同测）+ 功效核算表入文档（27/臂起步、45-63/臂达 0.8+；15pp 效应明示不可检）——#107 spec 文本加本件引用一行（其预注册文档落盘于其 T2 执行时引用本件核算）；
- ~~#106 T2 shadow 毕业判据补两行~~（**r2 删除**：#106 已归档且 r3 毕业判据=用户裁定、触发率降级观测记录——给降级指标加精度无意义）；**替代：#115 T4 对齐义务由 T1 报告模板兑现**（分布形状+外部锚定效度双报，见 T1）。

**判据**：#107 spec 文本含本件引用行（grep 可证）；T1 报告模板含「外部锚定效度引用」节及未就绪披露路径。

### T3 · confidence 校准前置（r2 两闸合一）
- #103 选章函数的前置校准断言：**T1 报告 confidence=high 基率 >50%，或 #115 T3 外部锚 ρ<0.3 回退成立**（两闸任一触发）→ 选章判据 confidence 降权或改用「overall − trailing median 相对阈值」单独承担（#103 T1 现判据已含相对阈值——本件把 confidence 从合取判据降为参考列的裁定路径写入 #103 执行 plan 前置检查单；与 #115 T4 的 ρ 门合一呈现，避免 #103 plan 收到两套冲突指令）；
- resonance SKILL 的 confidence 协议加校准口径（自报 high 须附「本锚点集内可比证据行」——SKILL 文本改动与 #96/#102 的 drafting SKILL 面不同文件，无冲突）。

**判据**：#103 plan 前置检查单条目存在（引用 T1 基率与 ρ 双闸）；resonance SKILL 文本含校准口径行。

## 2. 验收
1. T1-T3 判据全绿；
2. 基线报告落盘且数字可重放（脚本确定性——同输入同输出）；
3. bug-hunt：混入饿死审计→报告前置卫生行命中剔除计数；prevalence 陷阱（全零 flag 技能对）→ κ 行附警示不输出误导值；**group 族不分组→伪影警示（r2）**；**冷启动→披露行（r2）**。

## 3. 风险
- κ/α 低未必是判官病（各技能测不同构念属设计——报告须附方法论注记「低 κ 的一半是分工」；本件不设阈值门只产仪表）；
- α 的 items 混合严重度口径（BLOCKING vs MINOR 计数权重）——首版用「有无硬发现」二值 + 计数两版并报；
- 报告被误当门禁（它是仪表不是 gate）——命名与文档明确「观测面，不进生产读面」（#108 T3 同款纪律）；
- **共享文件面**：`tools/` 新文件为主；#107/#103 spec 文本修订为一行引用级（无代码冲突）；resonance SKILL 与 #96 批次纪律不叠（#96 触 drafting/review_checklist 面）；#119 落地后的接缝见 T1 注记。
