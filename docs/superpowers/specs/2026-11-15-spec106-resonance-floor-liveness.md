# Spec #106 · 正向下限接线（resonance-floor-liveness）：动态 floor（P25 clamp）+ decide_revision 生产接线 + role 门 verdict 接线 + shadow 期 + trend 数据卫生三件（完整性告警/补评命令/human_overridden CLI）

**日期**：2026-11-15｜ **系列**：评审工艺批（review-craft）｜ **状态**：Design（r1，2026-11-15）｜ **优先级**：🟠 P1
**动机证据**：`src/shenbi/pipeline/revision_router.py:193-214`（decide_revision 全 §6.3 树存在）——grep 证实**生产零调用**（仅 tests/unit/pipeline/test_revision_router.py 引用）；`src/shenbi/pipeline/chapter_loop.py:3133-3143`（注释自认 "Full borderline/escalation handling is deferred… below-floor 只 log.warning"）+ `:3098-3099`（章级路由仅由 BLOCKING/CRITICAL issues 决定）；`revision_router.py:76`（DEFAULT_RESONANCE_FLOOR=50）vs `novel-xinghuo-vol1/truth/resonance_trend.md`（实测 overall 带 74-86——**floor 生产中永不点火**）；`skills/shenbi-review-resonance/SKILL.md:103-116`（role 校准门+「阻断规则：框架 revision_router 确定性分流」**声明**）vs `chapter_loop.py:2985-3013`（生产只接 pending 判词→ESCALATION；**verdict=阻断 无任何路由效果**——SKILL 声明与接线不符）；`chapter_loop.py:3136`（state.config.resonance_global_floor——config 键现成挂点）；trend 实弹两蛀洞：偶数章 26-48 共 12 行 pending 未评分（趋势统计在半壁数据上跑）+ human_overridden 列 58 行全空（全仓 grep **无写入方**——`chapter_loop.py:2824` 写空白、`compute_drift.py:39/:77` 只读排除，escalation 报告三处建议用它但人无 CLI 可写）；`audit_aggregate.py:15-17`（resonance 报告逐字并入 aggregate——below-floor 修订的写作端反馈管道现成）。

**触及的不变量维度**：情绪节奏（弱关联——resonance floor/role 门为该维正向下限接线，不新增 check id）

---

## 0. 根因

**正向门三分量全部劝谏化**：floor 绝对值失准（50 vs 分布 74-86，LLM 宽大偏差+四维加权天然拉向中带）；决策树两分支未接线（decide_revision 单测孤岛，§6.3 文档与生产漂移）；role 校准门的阻断 verdict 无消费面。净效果：章级通过的强制力≈「G4 结构过+无 BLOCKING 正则命中」，**合规的无聊章畅通**——对商业连载，无聊章杀伤力大于缺陷章（缺陷掉信任分，无聊直接掉留存）。

**备选案已评估并否决**：「floor 常量直接改 75」——绝对值仍随通胀失真（spec #103 选章已证同类病症并改相对阈值），P25 相对阈抗通胀；「borderline→escalation 照原树接线」——escalation 实弹频次已 37 次/50 章（checkpoint_history，reject 22/approve 14），再加人审负载雪上加霜，borderline 降级为 drift 信号非人审事件。

## 1. 任务分解

### T1 · 动态 floor + decide_revision 生产接线
- `_effective_resonance_floor(project_dir, chapter, config)`：读 truth/resonance_trend.md 已评分行（排除 human_overridden——compute_drift 同过滤语义），trailing window（默认 20 章）**P25**，clamp [50, 80]；已评分行 <8 → DEFAULT_RESONANCE_FLOOR（冷启动，行为=现状）；
- `state.config` 加 `resonance_policy: {mode: "static"|"shadow"|"armed", percentile: 25, window: 20, cap: 80}`（**缺省 shadow**——仅计算+log 不路由；既有项目无此键 → 行为与现状逐字节一致，contract-upgrade 走显式声明路径）；
- `_route_revision_after_resonance` 生产调用 `decide_revision`（把单测孤岛接活）：route==NO_REVISION ∧ decision==REVISION → SPOT_FIX（reason=resonance，反馈=aggregate 内嵌 resonance 报告——管道现成）；verdict=阻断（围栏解析）同接线（reason=role_gate）；§6.3 docstring 树同步改写为生产真实语义（文档树=单一源，borderline 分支改记 drift 信号）；
- **armed 后 escalation 护栏**：resonance 路由耗尽 cap → 升级前二次 resonance 采样确认（两次均 below → escalation 带双报告；否则 pass）——防单次评分噪声驱动人审。

**判据**：单测（P25/clamp/冷启动/排除 overridden/shadow 不写 route/armed 写 route+reason/二次采样两分支）；`git grep -n "decide_revision" src/` 命中生产调用点（chapter_loop）；docstring 与生产一致（grep borderline 新语义）。

### T2 · shadow 期与毕业机制
- shadow 期事件 `resonance_would_route`（floor/score/reason/would_route 全量字段）+ 卷界 drift-guidance 汇总行（本卷 would-route 计数与分布）；毕业 = 用户裁定（#102 shadow 先例），判据 = shadow 触发率数据（预期带 5-20% 章，超预期高→先校准 floor 参数再议武装）。

**判据**：shadow 期 log 事件存在且 `audit_results[_REVISION_ROUTE_KEY]` 不被 resonance 改写；drift-guidance SKILL reads/汇总行接线测试。

### T3 · trend 数据卫生三件
- **完整性告警**：`check_trend_completeness`（挂 drift 面或独立）——窗口内 pending/空白 overall 行 → WARN（趋势统计禁静默半壁）；
- **`just resonance-backfill <dir> [--chapters a-b|c,d]`**：pending 章逐章补派 review-resonance（维护命令，ledger_archive/volume-budget 先例；resonance_trend append_dedup 按 chapter 键 upsert，报告覆写 audits/）；
- **`shenbi-pipeline override-resonance <dir> <chapter> --overall N [--dims 情感落地=a,…] [--note …]`**：写 trend 行 + `human_overridden=true`（drift 排除消费面现成）——人因放行弱章的回流通道 CLI 化，escalation 报告三处建议终于有落点。

**判据**：红测（pending 行→WARN；backfill 后行有分且 confidence 列合规；override 后该行被 compute_drift 触发统计排除——用 `_OVERRIDE_HEADERS` 语义直接验证）。

## 2. 验收
1. T1-T3 判据全绿；
2. shadow 期既有项目行为零变化（对 vol1 续跑窗差分：route/日志新增面仅 would_route 事件）；
3. **数据面验证**：对 vol1 全量 trend 回放动态 floor——输出 would-route 章清单（预期 ch2=74 等低分章命中、众数带 77-84 不命中）——floor 首次有牙的证明；
4. T1 生成测试 ≥94。

## 3. 风险
- **floor 追涨棘轮**（分数通胀→P25 升→修订压力升）→ cap=80 上限钉死 + MAX_AUTO_REVISIONS/escalation 既有兜底 + shadow 触发率先导；
- armed 后修订量上升 → 毕业由用户裁定，shadow 数据先行；
- 二次采样成本（~$0.004/次，仅 armed 的 cap 耗尽路径）；
- **共享文件面**：revision_router.py/chapter_loop.py 与 #105 同文件（**#105 → #106** 顺序，本件 plan 首步 re-anchor——INDEX 行号锚纪律）；
- backfill 补评旧章用的是**当前** style_profile/anchors（历史章当时的画像不在盘）——维护语义可接受，报告注明口径。
