# Spec #98 · 模型分档实验（model-tier-experiment）：多约束持有容量归因与高档验证

**日期**：2026-11-06 ｜ **系列**：#95 §3 预留件（模型契约对齐的运行侧收口） ｜ **状态**：Done（PR #298/#304；束7 判定=**PASS（强）**主判据 1 派收敛[对照束6 三派熔断]/副判据 FAIL[接骨 3，残余族均非 planning 族]；生产模型决策交用户——卷二停机面 ch49-0 待令。r2.5 用户改令：实验档 pro→`deepseek-flash`（V4.1-Flash-1017）——T0-补三形探针全通、预注册启用口径维持（见 §1 ④与 T0 报告 §10）；pro 降为 T3 FAIL 升档出口档；planning 补 max_tokens=32768 头寸；T2 实弹需用户新实弹令） ｜ **优先级**：🟠 P1（**生产解堵**：卷二停机面 ch47 规划二次熔断，续跑被模型问题阻塞——先于批次 A 的 #86 执行；代码面极小（pricing/配置接线），不抢 `chapter_loop.py` 最热文件）
**依赖**：**PR #295（失败报文逐字化）已合并**——教面确认投递且被消费是本实验归因干净的前提；与批次 A 无文件域冲突；**T0 档位探测先行**（MiniMax-M3.1-Flash 连通性教训：thinking:disabled 被拒——先探测后锁定档位）。
**动机证据**（束5+束6 双窗归因链）：①束5（ch45/46）：累积机制在场（6 族史+防回退令）模型仍失败，卡形逐字差一字（「记账」vs「算账」）；②束6（ch47/48，PR #295 逐字化后）：**逐字教面确认被消费**——chapter_role『承接』→「推进」一次修复且三派持存、激活方案模板逐字照抄、a5 锚全修（0 锚失败）；但失败面 **5→7→8 振荡不收敛**（trace RETRY 事件：a4=5×清偿锚；a5=锚全修+payoff_axis×2/voice_line/冷三连/s7 回退+预算 4>3；a6=锚回退×6+冷三连/voice_line 持存）——防回退令在场压不住修一漏一。**结论：每个被点名的族都能修，6 检查族·8-13 并发约束实例×双章约束集同时持有超出 flash 容量**（「>8 族」系实例数误计为族数，r2 勘误；升级证据：a6 锚回退发生在 a5 失败反馈不含锚项时——累积史在场仍丢，持有容量证据更强）；框架侧（路由/累积/逐字化/预算重置）束6 全绿（ledger :418 自带注记：retry 计数器 consumed 4 含熔断路径一次、界定待查=#86 候选——不影响派级计数口径，r2.2）。

**触及的不变量维度**：无（运行侧实验——不动门检判据与 truth 结构；唯一 src 面=PRICING＋MODEL_CONTEXT_LIMITS 双表加键，另含 executor_config 配置适配与测试用例——r2.2 措辞精确化）。

---

## 0. 假设与判据

**H1（主假设；r2.5 重述）**：控制组（V4.1-Flash-1017+planning thinking disabled）的同时硬约束持有容量 < 卷二双章计划的约束族数（束6 实测 6 检查族·8-13 并发实例：6×清偿锚+冷三连+voice_line+payoff_axis+s7+挂起预算；实例计数出处=trace seq 1182/1186/1190，r2.2）；**同模型启用 thinking（effort high）后容量 ≥ 该集**。原「同提供方高档模型」表述因控制组别名发现（退役 v4-flash 实跑 V4.1 同代）+用户改令 flash 档而重述——tier 假设降为 T3 FAIL 升档出口（pro 档），主假设纯化为 thinking 政策假设。

**H0（对照已成立）**：教面已排除——束6 证明逐字报文被消费且单族可修；框架放大回路已排除——束4/束5（PR #291/#292）。

**主判据**：同窗（ch47/48 规划步）≤2 派无人工收敛（对照=束6 flash 三派 5→7→8 振荡+二次熔断；「派」计数基准=trace DISPATCH 事件/ledger 派发行数，非 retry 预算计数器——熔断路径窗口终点以二次熔断落定为准，r2.2；**窗口派数上限=3（束6 实测口径）——计数路径异常出现第 4 派按熔断=FAIL 处置并记 deviation+#86，r2.3；超时截断派经人工复核确认后不计入派数与预算、其复核不计接骨（基础设施截断不惩罚模型，与 §4 风险行同口径，r2.3/r2.4）**）。**三结局预注册（r2.2）**：≤2 派收敛=PASS（强）；第 3 派（预算内）收敛=PASS 附 capacity-margin 保留意见（H1 容量≥集成立但裕量为零，生产模型决策须附此注）；熔断=FAIL（**熔断若系基础设施类失败（配额/鉴权/网络——非计划质量面），该窗作废重开，不计 FAIL 与接骨，记 deviation；重开 ≤1 次，再遇交用户；剔除行支出（kill 臂/作废窗/诊断行）计入 $10 停析线，r2.3/r2.4**）。
**副判据（#95 验收 3 口径）**：实验窗全程 ≤1 接骨（实验首派前的 escalation 处置计 1，余程须 0）。
**成本判据**：实验全窗（T2 采集面）总成本 <$10（停析线）；单章成本对照 flash ≤30×（卷二预算承载判定）——降级模式（§4 只测规划步）下 30× 基数换束6 规划口径 $0.023/双章窗（r2.2）。

## 1. 实验设计（变量隔离）

| 面 | 控制组（已完成） | 实验组 |
|---|---|---|
| 窗口 | ch47/48 规划步（束5 停机面→束6） | 同（ch47 规划二次熔断 escalation 处置起） |
| 模型 | deepseek-v4-flash（`_DEFAULT_MODEL`；**退役别名——实由 V4.1-Flash-1017 服务，2026-10-17 起，控制组=V4.1 同代**，r2.5） | **主变量重定（r2.5 用户令）**：`SHENBI_LLM_MODEL`＝`deepseek-flash`（V4.1-Flash-1017，与控制组同代同模）——tier 变量归零，实验纯化为 **thinking 政策（启用-high vs 控制 disabled）＋单形化反馈** 双因素同模对照；pro（deepseek-v4-pro）降为 T3 FAIL 升档出口档 |
| 教面 | PR #295 main（逐字报文+活锚样例） | 同 commit |
| 反馈机制 | 累积+防回退令+enrich=False 人审透传 | 同 |
| 预算 | max_audit_retries=3 | 同 |
| 证据 | trace.jsonl RETRY 事件（5→7→8） | 同口径采集，落 ledger 对照表 |

**已知混杂与处置**：①束6 #15 人审反馈模板自缺陷（B 节 bullet 形锚 vs 表格形推进方式列、C 节激活方案独立行——形差致 a4-a6 部分失败）→ 实验首派反馈**单形化**：锚入推进方式列+激活方案行并存逐字模板（此为实验-setup 修正，ledger 已记）；**混杂①残留反驳证据在案（r2.2）**——a5 双形并满足（锚 0 败）仍败于 payoff_axis×2/voice_line/冷三连/s7/预算共 6 项，失败质量在单形化触及面之外（T3 判定书「混杂①反驳」段引用）；可选 kill 臂（flash+单形化 ≤2 派，≈$0.02 束6 实测单价量级）随 T2 实弹令一并交用户裁——跑则计入实验前置 setup 不占实验窗（**kill 臂自身的开窗/退出 escalation 与派发不计入副判据接骨计数与主判据派数——setup 面 ledger 单列；副判据「计 1」仅指主窗首派前那一次，r2.3**）；**kill 臂 ≤2 派收敛=混杂①杀死 H1——束6 归因翻转为反馈形，主窗中止交用户（r2.3）**；②双章批粒度——若高档仍失败，T3 分叉含拆单章批的框架侧候选（不预支）；③**thinking 政策混杂（r2 增；r2.1 补裁决准则与豁免）**——planning 步现配置 `thinking="disabled"`（executor_config.toml:221-222，flash 期调定冻结，:219 注释自证 "revisit with post-rollout data"）：保持 disabled→高档容量被人为压低，FAIL 会误判「瓶颈在约束集」；翻启用→模型+thinking 双变量。**处置：档位定义必须含 thinking 政策**（档位定义=模型+thinking 政策整体单元，非单变量漂移）——T0 探测高档 planning thinking 可用性并在 T0 报告**预注册**实验口径（disabled=严酷对照／启用=容量满配，两口径择一记录在案）；**两口径皆可用时默认启用（容量满配）——H1 测模型真实持有容量，disabled 系 flash 特有成本调优非能力属性（r2.1）**；T3 FAIL 判定前须核对所跑口径——disabled 口径 FAIL 先补一次启用口径规划步单派再判，**该补派=判定阶段诊断派：预注册豁免接骨计数、不入窗口成本主对照表（单列诊断行，r2.1）；**诊断段（补派＋其新窗）整体豁免接骨计数、成本单列诊断行（r2.3）**；补派收敛=判定翻 PASS——主判据自补派起新窗 ≤2 派单独计数；补派不收敛=维持 FAIL（诊断段即止——新窗续派预算随之取消，r2.2/r2.4）**。

## 2. 任务分解

- **T0 档位探测（半天，无实弹成本或 ≤$0.5 探针）**：候选清单连通行探测（provider 档位目录；thinking/max_tokens 行为探测——**planning `thinking="disabled"` 与 drafting `thinking="low"` 两面**；超时面观察：900s base 对高档慢派的截断风险）；**thinking 政策预注册**（§1 ③处置）；锁定 1 主 1 备两档——**主档=提供方谱系最高档（按定价/产品定位排序非营销名，r2.1）**；**探测不过则回用户重定档**。
- **T1 接线小批（branch+PR）**：`src/shenbi/cost/pricing.py` PRICING 补**主+备两档** rates（**r2 论据勘误**：unknown model 的 ValueError 被 `_safe_estimate_cost`（cost/ledger.py:22-33）捕获降级 cost=0.0/pricing_status=unknown-model——派发不崩，但**成本护栏静默失效**（>$10 停析与 ≤30× 对照读到全 $0）——必须先接线；**备档回退路径若缺键将重演同款失明——主备同批入表，r2.2**）；`src/shenbi/cost/estimate.py` MODEL_CONTEXT_LIMITS 补**主+备两档**上下文限（防 F523 128K 保守回退致告警失真，r2 增）；executor_config 档位适配（若 T0 探明需要；全局共享面——见 T3 回滚条款）；`test_pricing` 补**两档**用例；既有 unknown-model 红测夹具（tests/unit/test_pricing_fail_loud.py `deepseek-v4-pro`）若与档位名撞名→夹具改 guaranteed-unknown 名（r2.2）。
- **T2 实验窗实弹（需用户新实弹令）**：单形化反馈 reject 二次熔断 escalation → `SHENBI_LLM_MODEL=deepseek-flash`（r2.5 改令档）resume → ch47/48 全链（规划→草写→scene-split→评审→settle）；trace 采集；接骨计数+成本护栏（>$10 停析报告）。**planning max_tokens=32768 头寸（r2.5）**：thinking-high 下推理与内容共享完成预算（本族已证——2026-10-24 drafting 探针在 1017 后实测 effort-high 独食 30-50K），planning 无 override 时 [default] 16384 有截断风险——只补 max_tokens 不设 thinking 键（启用口径与 unpinned 测试均保持）。
- **T3 判定与分叉**：对照表（flash vs 高档失败面演化/派数/接骨/成本）落 ledger——**判定书骨架列（r2.2；r2.3 补全）：口径（thinking 政策/反馈形）/派数与逐派 trace seq/接骨/成本（主表＋诊断行＋kill 臂/截断剔除行（若有））/**判定结局（强 PASS／margin PASS 附保留意见／FAIL／中止——kill 臂杀死 H1 主窗中止交用户，r2.4）**/kill 臂行（若跑）/混杂①反驳段/分叉落点**；分叉——**PASS**：#95 验收 3 在高档口径闭环成立→生产模型决策交用户（全换/分步分档：低约束步留 flash）；**FAIL**：束6 模型侧归因被推翻→瓶颈在约束集/批粒度设计→框架侧拆批实验另立 spec（**r2.1：若备档未测且提供方谱系存在更高档，FAIL 判定附升档出口——用户裁决是否二窗，不径跳框架侧拆批**）；**两分叉均附 executor_config 处置条款（r2.2）**——thinking 改动系全局共享（按 skill 键非按模型键）：启用口径落地后至判定前 flash 生产派发同受影响（session30 实测 ~18% 成本回归面），PASS 附生产迁移评估、FAIL 附回滚评估。

## 3. 验收

1. T0 探测报告（候选连通性+thinking 行为+**thinking 政策预注册**）落 `docs/research/` 或 spec 附录；
2. T1 PR 合并（CI 全绿）；
3. T2 trace 对照表+判定书落 `novel-xinghuo-vol1/vol1-ledger.md`（束7 条目）；
4. 分叉落点登记（生产模型决策记录 or 新 spec 编号）。

## 4. 风险与回退

- 高档候选不可用（连通性/配额）→ 备档→回用户重定档（不降级回 flash 重跑——控制组证据已足）；
- 高档显著变慢/变贵 → 只测规划步（主判据面）即可出归因结论，草写链可选（副判据降级为规划步口径，ledger 记 deviation）；
- 实验窗 PASS 但成本超卷二预算 → 生产模型决策不能只按可行性，须附单章成本对照（**r2 勘误**：flash 束5 14 派 727,668 tokens、当日 token-ledger 实测 ≈$0.17（18 行窗口；14 派=trace 派级口径、18 行=ledger 行级含评审链/escalation 步，r2.2）≈$0.08/章为基数——原「$0.02」系束6 3 派 $0.023 张冠李戴）。
- 高档慢派 900s base 超时截断（`_compute_dispatch_timeout` dispatch_helper.py:126-153；`_handle_timeout_gracefully` 仅 WARN 留部分输出，r2 增）——截断计划过不了 G4，表象与容量不足不可分；T2 观察点=**structlog `dispatch_timeout` WARN／`api_call_timeout` ERROR（日志面，dispatch_helper.py:163/:3956；r2.1 勘正——trace 失败派仅呈现 TRANSIENT failure_class 无 timeout 专属分类）**；命中即人工复核该派，确认截断则剔除容量归因单列记账。
