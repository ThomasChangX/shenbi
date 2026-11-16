# Spec #106 · 正向下限接线（resonance-floor-liveness）：动态 floor（P25 clamp）+ decide_revision 生产接线 + role 门 verdict 接线 + shadow 期 + trend 数据卫生三件（完整性告警/补评命令/human_overridden CLI）

**日期**：2026-11-15｜ **系列**：评审工艺批（review-craft）｜ **状态**：Design（r3 · Revised 2026-11-17，设计审查 2C+5I 修复：砍 static 模式+阈值入 thresholds 单源+G0 校验+shadow 持久基底+backfill 无正文守卫+毕业判据去 tautology+cap 悬崖入险；r2 为驳斥复核三修）｜ **优先级**：🟠 P1
**动机证据**：`src/shenbi/pipeline/revision_router.py:180-201`（decide_revision 全 §6.3 树存在）——grep 证实**生产零调用**（仅 tests/unit/pipeline/test_revision_router.py 引用）；`src/shenbi/pipeline/chapter_loop.py:3172-3182`（注释自认 "Full borderline/escalation handling is deferred… below-floor 只 log.warning"）+ `:3137-3140`（章级路由仅由 BLOCKING/CRITICAL issues 决定）；**生产 floor 单源 = `src/shenbi/config/thresholds.py:31` `resonance_global_floor=65`**（`chapter_loop.py:3175` 生产调用传 `state.config.resonance_global_floor`；vol1 `pipeline-state.json` 实弹 65）vs `novel-xinghuo-vol1/truth/resonance_trend.md`（实测 overall 带 74-86——**floor 生产永不点火：min 74 > 65**；`revision_router.py:76` `DEFAULT_RESONANCE_FLOOR=50` 是无生产调用的签名缺省——E11 双常量陷阱 Z6.review3 在案，本件冷启动回落**禁用**此常量）；`skills/shenbi-review-resonance/SKILL.md:103-116`（role 校准门+「阻断规则：框架 revision_router 确定性分流」**声明**）vs `chapter_loop.py:3020/:3079-3081/:3195-3206`（生产只接 pending 判词→ESCALATION；**verdict=阻断 无任何路由效果**——SKILL 声明与接线不符）；`chapter_loop.py:3175/:3181`（state.config.resonance_global_floor——config 键现成挂点）；trend 实弹蛀洞：**偶数章 26-50 共 13 行 pending 未评分**（#72 双章束 follower 章形态——#109 机制件未落地前的制度性状态；另有 5 章无行 6/8/10/20/22）+ human_overridden 列 45 数据行全空（全仓 grep **无框架/CLI 写入方**——`chapter_loop.py:2863/:2865` 写空白、`compute_drift.py:39/:77` 只读排除，escalation 报告建议用它但人无 CLI 可写）；`audit_aggregate.py:15-17`（resonance 报告逐字并入 aggregate——below-floor 修订的写作端反馈管道现成）；**技能级无正文出分实锚**（#109/#115 补充证据：`chapters/chapter-53.md` 缺失时 review-resonance 仍写 trend 行 63/81/63——「无正文→不评分」守卫在技能级不存在，#105 预检只查在盘不查契约声明面）；**r2 驳斥复算**（2026-11-17，fresh-context 子 agent + 协调者独立复算逐字吻合）：trailing-20 P25 **线性插值**约定下 vol1 回放点火 ch14/ch16（score 77 < floor 78.0/77.75）= 2/24 可评估章 = **8.3%**——**校准复现性数字，非效度证明**（#115 置换零假设 mean 21.2%/95%CI 8.3-29.2%，实际值落下缘——点火率是分数斜率 +0.06/章的函数，效度面归 #115 外部锚定）；**最近秩约定 0 点火**（`style_learning/compute_stats.py:69` `compute_percentiles` 即最近秩——约定不同故本件不复用）；ch2=74 在冷启动窗内（前序仅 1 已评分行 <8）**按规则永不触发**（r1 验收「ch2 命中」预期为假，r2 已删）。

**触及的不变量维度**：情绪节奏（弱关联——resonance floor/role 门为该维正向下限接线，不新增 check id）

---

## 0. 根因

**正向门三分量全部劝谏化**：floor 绝对值失准（生产单源 65 vs 分布 74-86，LLM 宽大偏差+四维加权天然拉向中带）；决策树两分支未接线（decide_revision 单测孤岛，§6.3 文档与生产漂移）；role 校准门的阻断 verdict 无消费面。净效果：章级通过的强制力≈「G4 结构过+无 BLOCKING 正则命中」，**合规的无聊章畅通**——对商业连载，无聊章杀伤力大于缺陷章（缺陷掉信任分，无聊直接掉留存）。

**备选案已评估并否决**：「floor 常量直接改 75」——绝对值仍随通胀失真（spec #103 选章已证同类病症并改相对阈值），且 G0.cc threshold_mismatch 门把 config 静态值钉死在单源默认（静态改值死路）；「borderline→escalation 照原树接线」——escalation 实弹频次已 37 次/50 章（checkpoint_history，reject 22/approve 14/modify 1），再加人审负载雪上加霜，borderline 不路由（docstring 只记「不路由、见 would_route 事件」，不新建 drift 信号面——写而无读者即死线）；「static 兼容模式」——r2 曾设，r3 砍除：shadow 的 would_route 事件是 static-dormant WARN 的严格超集（同计算更全字段），缺省 shadow 已保证路由面零变化，static 唯一差异=关日志，无人显式需要（回滚目标应是 shadow 非 static）。

## 1. 任务分解

### T1 · 动态 floor + decide_revision 生产接线
- `_effective_resonance_floor(project_dir, chapter, config)`：读 truth/resonance_trend.md **前序**已评分行（章号 < 当前章，不含当前章——当前章先落盘的生产时序下，含自身即自拉低 P25 自证通过偏置），排除 human_overridden（compute_drift 同过滤语义），trailing window（默认 20 章）**P25 = 线性插值分位（`statistics.quantiles(method='inclusive')` 口径——分位约定钉死进实现与测试，禁最近秩漂移）**，clamp [50, 80]；已评分行 <8 → **回落 `state.config.resonance_global_floor`（单源 65）——禁回落 `DEFAULT_RESONANCE_FLOOR=50`（E11 双常量复活+低于现状）**；**override 饿死护栏**：<8 由 override 排除导致（非真空冷启动）→ 同回落 config 值 + WARN `resonance_window_starved`（带窗口/override 计数）——禁静默回落；
- `state.config` 加 `resonance_policy: {mode: "shadow"|"armed", percentile: 25, window: 20, cap: 80}`（**缺省 shadow**——仅计算+事件不路由；既有项目无此键 → 路由行为与现状一致，contract-upgrade 走显式声明路径；**无 static 模式**——r3 砍除，见 §0）；**数值阈值入 `config/thresholds.py` QualityThresholds 单源**（percentile/window/cap/冷启动窗 8——模块自述即数值阈值单源，E11 教训）；**mode 字面量入 `contracts/enums.py`**（状态字面量单一信源）；**G0 config coherence 校验新键**（mode ∈ 枚举、percentile∈(0,100)、cap∈[50,100]、window≥1）；PipelineConfig 三触点同步（dataclass 字段/`to_dict` 显式键表/`from_dict` 过滤天然兼容）；armed 进入通道=用户毕业裁定后显式改 state.json config（无 CLI——毕业随令，文档注明）；
- `_route_revision_after_resonance` 生产调用 `decide_revision`（把单测孤岛接活）：route==NO_REVISION ∧ decision==REVISION → SPOT_FIX（reason=resonance，反馈=aggregate 内嵌 resonance 报告——管道现成）；verdict=阻断（围栏解析）同接线（reason=role_gate）；**两者均 armed-only 路由——shadow 期只发 would_route 事件不改 route**；§6.3 docstring 树同步改写为生产真实语义（borderline 分支改记「不路由、见 would_route 事件」）；
- **armed 后 escalation 护栏**：resonance 路由耗尽 cap → 升级前二次 resonance 采样确认（两次均 below → escalation 带双报告；否则 pass）——防单次评分噪声驱动人审。

**判据**：单测（P25 插值口径/前序窗口口径/clamp/冷启动回落 65 非 50/排除 overridden/shadow 不写 route/armed 写 route+reason 含 role_gate 面/二次采样两分支/override 饿死 WARN/thresholds 单源与 G0 校验）；`git grep -n "decide_revision" src/` 命中生产调用点（chapter_loop）；docstring 与生产一致。

### T2 · shadow 期与毕业机制
- shadow 期事件 `resonance_would_route`（floor/score/reason/would_route 全量字段）**双落点持久化**：`cs.audit_results["resonance_would_route"]`（state.json chapter_states 落盘——毕业数据可回放）+ trace 通道（`emit_shadow_warn_trace` 先例形态，append-only）——**禁 ephemeral-only**（structlog stderr 不可回放，毕业判据会成死线）；卷界 drift-guidance 汇总行（本卷 would-route 计数与分布，落进 drift-guidance 既有卷界产物——其 reads 已含 resonance_trend.md，具体文件 plan 期按其 SKILL writes 定形）；
- **毕业 = 用户裁定**（#102 shadow 先例），判据数据如实报告但**触发率单独不构成毕业依据**——#115 已证触发率是分数斜率函数（置换零假设 mean 21.2% vs 实际 8.3% 落下缘），毕业裁定须结合 #115 外部锚定路线（人工盲评/体系外判据）一并呈报用户；r1 的「预期带 5-20%」降级为观测记录非判据。

**判据**：shadow 期持久键+trace 事件存在且 `audit_results[_REVISION_ROUTE_KEY]` 不被 resonance 改写；drift-guidance SKILL reads/汇总行接线测试；`just lint-contracts` 绿 + `just generate` 生成物 diff 空（触 drift-guidance 契约时）。

### T3 · trend 数据卫生三件
- **完整性告警**：`check_trend_completeness` **挂 drift-guidance 卷界聚合行**（每卷一次，带 pending/缺行计数与章清单+束 follower 语境注记——#109 未落地前偶数章 pending 属 #72 双章束制度性状态，**禁逐章 WARN** 制造告警疲劳；与 #109「如实报告 follower 缺口」分工：本件报 trend 数据面，#109 报审计机制面）；
- **`just resonance-backfill <dir> [--chapters a-b|c,d]`**：pending 章逐章补派 review-resonance（维护命令，ledger_archive/volume-budget 先例；resonance_trend 按 chapter 键 upsert——truth_io `insert_markdown_row` + `key_field="chapter"` 生产在用形态，报告覆写 audits/）；**无正文守卫**：补评前置 #105 审计预检面（目标章 `chapters/chapter-N.md` 在盘）+ 派发后产物校验（readiness 面复用）——**预检不过即拒绝补评该章并报告，不写 trend 行**（技能级「无正文→不评分」守卫不存在，63/81/63 无正文出分实锚在案；#109 落地后契约 reads 对称化自然覆盖 bundle 面）；
- **`shenbi-pipeline override-resonance <dir> <chapter> --overall N [--dims 情感落地=a,…] [--note …]`**：写 trend 行 + `human_overridden=true`（**小写 `true`**——`report_longitudinal.py:105` 消费面只认小写；drift 排除消费面现成）；**行合并语义=cell-patch**：目标章已有富行（role/四维/confidence 含校准补丁 cell）时**只翻 human_overridden cell**，禁整行重建覆写（`upsert_markdown_row` 整行替换语义的坑）；行不存在时才按 9 列全行写——人因放行弱章的回流通道 CLI 化，escalation 报告建议终于有落点。

**判据**：红测（卷界聚合行含 pending 计数与章清单；backfill 对缺正文章拒绝且不写 trend 行；backfill 后行有分且 confidence 列合规；override 对富行仅翻 flag cell 不覆写维度分；override 后该行被 compute_drift 触发统计排除——用 `_OVERRIDE_HEADERS` 语义直接验证）。

## 2. 验收
1. T1-T3 判据全绿；
2. shadow 期既有项目行为零变化（**离线回放差分**：route 面确定性可离线重算——trend+磁盘审计报告重算 route 序列，diff 仅新增 would_route 持久键/trace/卷界汇总行，route 值零变化；**禁为差分触发付费续跑**）；
3. **数据面验证（校准复现，非效度证明）**：对 vol1 全量 trend 回放动态 floor（插值约定）——(a) **冷启动边界**：前 8 个已评分章（ch1/2/3/4/5/7/9/11）一律不触发；(b) 点火清单 = ch14/ch16（77 < 78.0/77.75）；(c) 众数 79 章（12/32）不命中；(d) 点火率 2/24=8.3%——与 #115 预注册置换基线同口径复现（**效度面（floor 是否测真质量）归 #115 外部锚定，本验收只证机制算出所声称的数**）；
4. T1 生成测试 ≥94——**付费派发，实弹随用户令**（域约束：SDD 禁为验证触发付费派发；未获令时以离线差分替代交付，G3.4 独立评分子 agent 挂账用户裁定——#105 同款先例）。

## 3. 风险
- **cap 悬崖双态**（#115 饱和推演：模式带 79、sd 2.40、斜率 +0.06/章 → **约 15 章 P25 触 cap 80**）：armed 后众数 79 章（79<80）批量点火 → 点火率跳升 ~35%+；通胀越过 80 后触发率趋 0——floor 永久熄火（E11 的 P25 版）→ 缓解：shadow 期触发率先导观测 + 毕业门绑定 #115 外部锚定 + #115 T1 饱和哨兵（点火率 <5% 且 mean 升 → `floor_saturated_or_inflated` WARN）消费本机制数据；
- **floor 追涨棘轮**（分数通胀→P25 升→修订压力升）→ cap=80 上限钉死 + MAX_AUTO_REVISIONS/escalation 既有兜底 + shadow 触发率先导；
- armed 后修订量上升 → 毕业由用户裁定，shadow 数据先行（触发率+外部锚定双面呈报）；
- 二次采样成本（~$0.004/次，仅 armed 的 cap 耗尽路径）；
- **共享文件面**：revision_router.py/chapter_loop.py 与 #105 同文件（#105 已核销 PR #351；本件 plan 首步 re-anchor——INDEX 行号锚纪律）；
- backfill 补评旧章用的是**当前** style_profile/anchors（历史章当时的画像不在盘）——维护语义可接受，报告注明口径；
- **P25 helper 协调**：本件插值约定与 `style_learning/compute_stats.py:69` `compute_percentiles`（最近秩）约定不同故不复用；#103 median+5 若实施应共享分位 helper——勿建第三套分位数实现（跨 spec 协调点，两件 plan 期对齐）。
