# Spec 执行索引

> **最后更新**：2026-11-15（**#92 完结归档**（PR #346——测试与门禁管线卫生：_tool_hashes 217 条整删+lock-tool-hashes.sh 拆双职改名 lock-calibration-hash.sh[G0.14 calibration 链保活]+R3 face 删+判据 git grep 正面清单双零/load_deps 类型化单装载+六读者+REPO_ROOT 单源[import 环断解]+unit 标记退役 option-b[1,298 清扫]+test/test-all 合并+防回归钉/cov-fail-under 四拷归零+just lint·type·test-ci 子配方[无损对账]+hook 构造性子集+例外表/沉积清除[2,408 行]+per-file-ignores 零可整并结论/dispatch_payload 构造器+首批换装；价值门 REWRITE 一轮[PR #345]+设计审查四轮+plan 三轮；8 task 8 audit 全 PASS+终审 Ready）；前次 **异模型元审批三件立项 #115-#117**（B 异血统会话：本会话服务模型 `deepseek-v4-flash` ≠ 产出 #82-#114 的 GLM 血统，按任务 §2 执行「异模型元审」分支；配套外部读者判据预注册落盘 `docs/research/2026-11-15-quality-external-anchor-prereg.md`）：#115 quality-measurement-endogeneity（🟠 P1）——**#106 的 P25 floor 是分位数下限，点火率是分数斜率的函数而非质量的函数**：vol1 真 trend 回放实际点火 **2/24=8.3%**（ch14/16，floor 77-79）vs 同分数打乱章序 5000 次置换零假设 **21.2%（95% CI 8.3-29.2%）**、分数斜率 +0.119/行；**#106 验收「预期 ch2=74 命中」与 T1 冷启动规则（<8 行→静态 50）自相矛盾**（ch2 永不触发）；cap=80 保证通胀到模式带 79+ 后 floor 永久失效；**#103 resonance 高分章做风格学习第四源→注入 drafting→同一判官**闭合回路无 holdout/无阻尼；**全体系无一条把 resonance 与体系外读者判据对账**（「更好」计数 0/32）；修=P25 降级 rank_alarm+绝对 floor 来自外部锚+回路阻尼（shadow）；#116 gate-discriminative-power（🟠 P1）——**真 G4 回放 vol1 50 章：10 项散文门 50/50 全 PASS、13 项零 FAIL**（hook 30% 仅单字张力词且 `还`/`账` 各 38 章=主角账房腔同词表；protagonist 名表中位 93 vs 阈值 3、`他` 单独 50/50 过、名表重复 `['那罕','那罕','他']`；transition 中位 0 vs 阈值 5；simile 56% WARN 不路由；ending 分类器 47/50 None）——**判别力集中在 B 类对账门，A 类散文门是恒真函数**，红测只证「能失败」不证「会失败」；建 gate-power 仪表+恒真登记+六项标定提案（不改门行为，用户逐项裁定）；#117 audit-evidence-verifiability（🟠 P1）——**四要素证据契约（位置/≥20 字原文引述/规则名逐字/严重度）在门禁侧只实现为报告级形态三选一**（`generic.py:125-126`）且行号只验越界（`llm_output_integrity.py:173-192`）；588 份章审计回放：契约形态完备 **10.9%**、≥10 字引述 2883 条中 **28.2% 在全项目文本中找不到逐字来源**、12 个 active review 技能仅 2 个有专用校验器（10 个只验存在/非空/≥50 字）——**编造/陈旧/真实证据在门禁前同价**；修=发现级 parser+逐字/行号/规则名对账+消费三态（validated/unvalidated/invalid））；前次同日（**多专家审计批六件立项 #109-#114**（八专家变身审计，配套 C 逃生率预注册/H 注入 A/B 预注册/B 跨模型复核清单落 `docs/research/2026-11-15-*.md`）——#109 audit-bundle-coverage（🔴 P0）：**双章批 follower 章 core-circle 审计系统性饿死且零消费**——契约 reads 只声明 chapter-N 而 writes 声明 N+N+1（六技能）+shared_ctx/checklist/consolidation/revision 路由四处 anchor-only（`chapter_loop.py:3937/:4066/:4099-4107/:4151`）+serial 收口环 `:4770-4776` 在 wave 拦截下不可达；vol1 实弹：588 份章审计 **147 份饿死**（偶数章 158/294=54% vs 奇数 2.4%）、**49 份无正文「通过」**（编造通过喂 cascade streak）；修=reads 对称化+派发组装双章化+收口 per-n+占位/失败三态判定+resume 补跑（**#105 T3 预检不覆盖**：文件在盘→预检过→仍饿死）；#110 judge-reliability-harness：判官间一致性/效度/分布形状离线仪表（**跨技能 κ≈0·Cronbach α=0.311·resonance×缺陷量 r=+0.068·从不「更好」73/19/0·模值 79×12·通胀 +0.073/章**——判官互不预言）+#106 毕业窗 ≥48 章（12-24 章 CI 宽 0.2-0.4 裁不动 5% vs 20%）+#107 改 McNemar 配对（9 变异/臂 power 0.10-0.25）+#103 confidence 校准前置（high 基率 75% 无校准）；#111 extractor-shape-contract：`extract_threads_overview` 要求 `## 线索详情` 而 producer 从不写——**44 次生产 reads 全部空转降级全文**（B 批长窗保护从未生效，降级仅 log WARN 零计数）+extractor 应用率哨兵+truth 增长曲线（matrix 202KB→3.9MB@1000 章，105 次读仅 9 次走 extractor）+全量读面收编；#112 chapter-loop-properties：12 条 resume/重试/升级不变量文档化+hypothesis RuleBasedStateMachine+已知反例回归收编（E-3 core 波 savepoint 漏传 wave_chapters/E-9 SETTLING_FAILED 全仓无复位/E-11 auto 模式 G4 二次失败放行挂账用户裁定/E-26 trigger 后 mandatory 步跳过）；#113 untrusted-delimiting：wrap 原语六通道扩展（审查参考数据区外注入/G4 引句回灌自我注入回路/escalation 裸拼/exemplar 无转义）+反引号伪围栏防御+注入抵抗力 A/B 预注册随批落盘（≈$0.35 随令）；#114 escalation-triage：**16 份 escalation 中 12 份=确定性 G4 门禁三振**（scene_budget 跨 ch5/35/39 三次独立升级人审重裁同类）——同门首次三振机器反馈升级/重复与内容争议留人审三保留面+裁决书机器可读索引（31 份仅 8 份可正则解析）；**用户裁定不考虑在飞项目**（六件全走机制修复/显式声明路径））；前次同日（**评审工艺批四件立项 #105/#106/#107/#108**——#105 audit-finding-contract：severity 词表单源五传感换装[contracts/severity.py+AST lint+行为保持差分]+词表外 fail-loud[G4.av.vocab——静默丢包变门拦]+派发完整性语义拆分[框架前置预检，输入缺失不再由 LLM 写 BLOCKING]+聚合条目级 severity+反馈缺口清偿[scene_budget 族/ending 窗 3→10]；#106 resonance-floor-liveness：动态 floor[P25 clamp 50-80]+decide_revision 生产接线[单测孤岛接活+§6.3 docstring 归真]+role 门阻断 verdict 接线+shadow 期缺省[行为零变化]+trend 数据卫生三件[完整性 WARN/`just resonance-backfill`/`override-resonance` CLI——human_overridden 死通道复活]——修「正向门三分量全部劝谏化，合规的无聊章畅通」；#107 reviewer-model-tier：executor_config per-skill model 键+单源接线[默认零变化]+评计量表 A/B 预注册[thinking 解禁/第二模型，随用户令]——修「审写同模型+G3.4 独立性止于会话隔离」；#108 audit-recall-canary：确定性变异器目录[9 mutator 含长程承诺漂移缺口探针]+派发探针 harness[dry-run 默认/实弹随令]+召回矩阵报告——**审计召回=体系缺失的第一元指标**（#105/#107 验收的 before/after 底座）；**用户裁定不考虑在飞项目**（四件全走机制先行/shadow/显式声明路径，无迁移工具））；前次同日（**写作工艺批三件立项 #102/#103/#104**——#102 declared-deviation：deviations[] 申报+group-plan 三择一裁定+hook defer-only 硬边界+偏离→计划进化回路（修「计划腔」=AI 味结构根）；#103 highlight-distill：确定性选章（median+5 相对阈值）+三层归因手法卡 playbook+anchors 候选池接读者信号+老化变奏防僵化（修「纯纠偏无正向放大」）；#104 power-system-expansion：power_system.md 双区化（演进台账 keyed append）+TRIGGER_STEPS 卷界插步+G4 expand 四检查（前层不可变/单调性/编年锚定/钩子可达）；**用户裁定不考虑在飞项目**（#104 无迁移工具，走显式声明路径）；#101 缺口=批粒度候选预留）；前次 #91 完结归档（PR #343——状态与并发纪律：gate_passed 单源[status.py 公共判定器+11 判定点换装+五定义删除+SKIP 容忍逐点显式]+比较侧 AST lint 守卫[首跑零红]+classify_dispatch_failure 迁 contracts/failure.py+as-alias re-export+genesis 差异表挂裁定+ledger_archive/outline 合并两处锁窗口闭合[path_lock_held 公共探针+确定性红绿双测 xfail 哨兵]+retry 五存取器接线[双站点事件先增后发]+semaphore 可选化/run_post_draft_pair 正名；REWRITE 一轮[PR #342 r2.3]+r2.3b/c 两轮修订；spec 四轮+plan 四轮收敛；九 task 九 audit 全 PASS+终审 Ready）；前次 #90 完结归档（PR #340——契约数据面单源：G4 checker 名册 shared.py 单源[权威字面量+别名+generic re-export+cli 分支内派生，编辑面 5-6→3 处]/lint 对账面收缩[删三恒真面+R1/R5 非空结构守卫，成员级归运行时三重守卫]/lint_decisions_sources 换源 load_contract+STEM 严格归一派生+值集+G4_DECISIONS_WIRED 第四源/allowlist 外置 JSON[三态 fail-loud+零命中 WARN]/writing-skills 机器契约节；REWRITE 一轮[PR #339 r2.3 载体改判]+r2.3b-d 三轮修订；五 task 全 audit+终审 Ready[AC1 演练三态+行为保持基线差分]）；前次 #89 完结归档（PR #337——门禁内部性修复：CheckContext 一次装载[主函数 805→57 行+22 检查函数+memo 四读归一+scene_hook 双基不归一]/五窄助手 chapter_no+chapter_no_raw+load_facts_oracle+degrade+require_roots[11 前导收敛]/章号单源[20 内联归零+AST lint+零填充 group 原文锚]/shared 出鞘[marker 迁 gate_manifest+文本原语迁 text.cjk+roster 惰性化+七破裂面换源]/declared_history 正名+g4_cross_chapter 非注册表门文档化/G0.12 真实现[GENERIC_ONLY_ROSTER 44 项集合对账+注入红测]；REWRITE 一轮[PR #336]+四轮 spec 审查 r2.7+三轮 plan 审查；六 task 全 audit[两轮首轮 FAIL 修复闭环]+终审 Ready+实弹差分逐字节一致）；前次 #88 完结归档（PR #334）
> **活跃 spec 数**：20

本页**只追踪活跃（待执行）spec**，按推荐执行顺序排列：优先级 🟥 Critical/🔴 P0 → 🟠 High/P1 → 🟡 Medium/P2 → ⚪ 批量，同级按编号升序。
已完成/合并/驳回的 spec 移至 `archive/`（按日期排序），**本页不追踪归档**——归档历史查 `archive/` 目录与 `git log`。

---

## 执行队列


---

### #109 · bundle 审计覆盖正确性（audit-bundle-coverage）

- **文件**：`2026-11-15-spec109-audit-bundle-coverage.md` ｜ **系列**：多专家审计批 ｜ **状态**：Design（r1，2026-11-15） ｜ **优先级**：🔴 P0
- **依赖**：**#105 → #106 → #109**（chapter_loop/parallel_dispatch/revision_router 同文件链，plan 首步 re-anchor）；T2 checklist 面在 **#96 后**（review_checklist 同 #105 T4 约束）；SKILL 契约面过 lint_registry_reconcile（#90 机制现成）
- **内容**：双章批 follower 章 core-circle 审计系统性饿死（契约 reads 只声明 N 而 writes 声明 N+N+1；shared_ctx/checklist/consolidation/routing 四处 anchor-only；serial 收口环 wave 下不可达）→ T1 六技能契约 reads 对称化；T2 派发组装双章化（shared ctx bundle 语义+checklist 双章+reads manifest blob 级断言）；T3 收口/路由 per-n 消费面（三 anchor-only 点对称化+summary 双章）；T4 占位/失败三态判定（待补/不适用/附条件/无法核对 → invalid；cascade streak 只数 valid；Failed>0 禁止净结论——修 ch1「Successful:1/Failed:5→No BLOCKING」失败计净）；T5 resume 对 invalid/缺产 follower 补跑。vol1 实证：147/588 饿死（偶数章 54%）、49 件编造通过、0 次路由触发
- **对应 plan**：待执行时建
- **触及的不变量维度**：无（审计层覆盖正确性——不新增叙事维度门检）

---


### #93 · 阈值权威化（threshold-authority）

- **文件**：`2026-11-01-spec93-threshold-authority.md` ｜ **系列**：架构复审批次 A ｜ **状态**：Design（r2.2） ｜ **优先级**：🟠 P1
- **依赖**：无
- **内容**：lint_threshold_reconciliation 改 import 执法器读常量（**r2 前置：先提取 CONSTELLATION_HARD_BAND 常量**；**r2.2：判定式改包含式**——原相交式仍放行带内漂移）+ 删 allowlist bounds 第三源 + **新增 `--strict` 并接线**（现不存在）+ **散文↔门裕度决策入 docs/framework/gates.md + g4 注释回指（不改 SKILL.md 散文——束4 验收后窗口 prompt 行为红线）** + pricing 模型契约 import 单源 + executor 派生集 mtime 失效 + **trend 列契约常量覆盖三消费者（writer/escalation_bridge/confidence_calibration；r2.2 更正：compute_drift 按表头名读、无 cells[6]）**
- **对应 plan**：待执行时建
- **触及的不变量维度**：情绪节奏（弱关联——pacing 域阈值声明单源化，不新增门检）

---

### #102 · 声明式计划偏离（declared-deviation）

- **文件**：`2026-11-15-spec102-declared-deviation.md` ｜ **系列**：写作工艺批 ｜ **状态**：Design（r1，2026-11-15） ｜ **优先级**：🟠 P1
- **依赖**：**#96 落地后施工**（同碰 drafting SKILL+review_checklist 面——批次纪律）；其余独立
- **内容**：decisions schema 加 optional `deviations[]`（plan_section/kind/quote≥20 字 verbatim/replacement_summary/rationale/hook_ids）+G4.dec 扩展（quote 在 plan 逐字存在[quote_verbatim 共基复用]/每章 ≤max/hook defer 语义）+genre-config `deviation_policy`（max 2/§8 禁偏/hook_mode=defer_only；shadow 期未声明行为与现状逐字节一致）+drafting 申报协议（反合理化首条 group-plan:195 **改写非删除**——未声明=推翻承诺/纯 omission 永远 error）+group-plan reads 加 sidecar+三择一裁定（endorse/neutral/reject——reject 照旧 BLOCKING 走既有 revision 回路，**路由零改动**）+硬边界三条（hook drop 一律 reject 且 N+1 承接行程序校验/§8 钉死/超限 G4 FAIL）+反馈回路（reject 率超阈→planning 纠偏；同类 endorsed≥3 章→备忘制度化提示——计划通过实弹偏离进化）。与 #96 互补：#96 修表层 tell，本件修服从性结构层
- **对应 plan**：待执行时建
- **触及的不变量维度**：承诺与债务（钩）（弱关联——defer 偏离消费 hook_age/承接行校验，不新增门检）；情绪节奏（弱关联——备忘 1/6 段豁免裁定面，三硬闸语义不变）

---

### #104 · 力量体系卷界扩容（power-system-expansion）

- **文件**：`2026-11-15-spec104-power-system-expansion.md` ｜ **系列**：写作工艺批 ｜ **状态**：Design（r1，2026-11-15） ｜ **优先级**：🟠 P1
- **依赖**：无硬依赖（triggers.py/gates/g4 不在批次 A 共享表）；建议 #102/#103 实弹后施工（expand 上下文构造更准）
- **内容**：power_system.md 双区化（前部现行生效区[group-factual 4 字段锚点原样——extractor 切片逐字节一致红测]+后部演进台账 keyed append[key=volume/`### 卷N层` 详情/重解释声明]）+contract 写模式 init/expand 两面（genesis 整建语义保留）+TRIGGER_STEPS 卷界扩容群插步（五技能后 genre-config 前；expand 上下文=现有层全文+本卷力量高度[current_state 尾窗+主角 matrix 行]+下一卷 volume_map 节点+力量类母钩）+「主要人物阶位」表刷新并入 expand 步+G4.ps.expand 四检查（P1 前层不可变[.bak 逐字节对账]/P2 单调性[纯增量或重解释声明——只许重解释不许改史]/P3 编年锚定[铁律 6 程序化]/P4 钩子可达[TRIGGERED 钩兑现窗口]）+VOLUME_BOUNDARY 检查点带层 diff 摘要（人审=重解释终闸）+invariants.md 同批登记 G4.ps.* 族（改表即改 lint）；全史回放明确不建（次卷 group-factual 审计兜底）；**用户裁定不考虑在飞项目**（无迁移工具，旧单区形态运行时 FAIL 附结构转换指引）
- **对应 plan**：待执行时建
- **触及的不变量维度**：无现有维度行（世界规则/力量面无普查行——T3 含 invariants.md 登记义务，形态 plan 期定）

---

### #105 · 审计发现契约硬化（audit-finding-contract）

- **文件**：`2026-11-15-spec105-audit-finding-contract.md` ｜ **系列**：评审工艺批 ｜ **状态**：Design（r1，2026-11-15） ｜ **优先级**：🟠 P1
- **依赖**：无硬依赖；**与 #106 同文件序（#105 先）**[revision_router/chapter_loop]；T3 预检面 dispatch_helper 在 **#92 在飞 T2a 后**；T4 review_checklist 面在 **#96 后**（其余 T 不受限）
- **内容**：severity 词表与传感正则单源化（新 `contracts/severity.py`：ROUTING_TIERS/AGGREGATE_VOCAB+四锚定形态+三尾巴迁入；五消费点换装[router 双正则/chapter_loop `_BLOCKING_MARKER_RE`/parallel_dispatch/audit_layer/aggregate 锚定形族]+AST lint 禁新手拼[#88/#91 先例]+**行为保持差分**[fixtures 全量审计产物回放，路由/聚合计数逐项一致]）+词表外 fail-loud（`llm_output_integrity.check_audit_severity_vocab`：锚定形 severity 词∉词表→G4.av.vocab FAIL 附重写指引——**静默丢包变门检拦截**；散文提及豁免；vol1 存量回放仅出报告不自动改写）+派发完整性语义拆分（审计派发前框架确定性预检 required reads[escalation reads 三态判定复用]——缺失走既有 failure 路径**不派 LLM**；「派发完整性」payload 的 BLOCKING→报告无效 FAIL——输入缺失从 LLM 语义域整体消失，实弹根因 chapter-40-reader-pull.md:44）+反馈与聚合卫生（G4_FORMAT_EXAMPLES 补 `G4.cp.scene_budget` 族+名册差集盘点/aggregate 渲染条目 `- **{sev}** · {text}` 携带 severity——修节标题继承丢失/ending_constraints 注入窗 **3→10 章**——消灭 group-craft SKILL:166 文档对模型撒谎）。**MAJOR 档明确不建**（fail-loud 先杀静默丢包，CRITICAL/MINOR 使用数据后议中间档）
- **对应 plan**：待执行时建
- **触及的不变量维度**：无（审计发现契约基建——新 check id 族 G4.av.* 为审计产物有效性门，不挂叙事维度；P2 期 check-id 普查面自然覆盖）

---

### #106 · 正向下限接线（resonance-floor-liveness）

- **文件**：`2026-11-15-spec106-resonance-floor-liveness.md` ｜ **系列**：评审工艺批 ｜ **状态**：Design（r1，2026-11-15） ｜ **优先级**：🟠 P1
- **依赖**：**#105 后施工**（revision_router/chapter_loop 同文件序；plan 首步 re-anchor——行号锚纪律）
- **内容**：动态 floor `_effective_resonance_floor`（trend 已评分行[排除 human_overridden——compute_drift 同过滤]trailing 20 章 **P25** clamp[50,80]；<8 行冷启动=50 现状行为）+state.config `resonance_policy{mode:static|shadow|armed, percentile, window, cap}` **缺省 shadow**（既有项目无键→行为逐字节一致，显式声明路径）+**decide_revision 生产接线**（route==NO_REVISION ∧ decision==REVISION→SPOT_FIX reason=resonance；role 门 verdict=阻断同接线 reason=role_gate；§6.3 docstring 归真=文档树单一源——修 :193-214 单测孤岛+chapter_loop:3133-3143 自认 deferred）+armed escalation 护栏（cap 耗尽→**二次 resonance 采样确认**，双 below 才升级带双报告——防单次评分噪声驱动人审）+shadow 期（`resonance_would_route` 事件+卷界 drift-guidance 汇总行；毕业=用户裁定[#102 shadow 先例]，触发率先导）+trend 数据卫生三件（pending/空白行完整性 WARN——修 26-48 偶数章 12 行 pending 蛀洞静默/`just resonance-backfill` 补评命令[ledger_archive 先例，append_dedup upsert]/`shenbi-pipeline override-resonance` CLI——**human_overridden 58 行 0 使用死通道复活**，drift 排除消费面现成）。修「正向门三分量全部劝谏化：floor=50 vs 实测带 74-86 永不点火/决策树两分支未接线/role 门阻断 verdict 无消费面——**合规的无聊章畅通**」
- **对应 plan**：待执行时建
- **触及的不变量维度**：情绪节奏（弱关联——resonance floor/role 门为该维正向下限接线，不新增 check id）

---

### #110 · 评审信度测量 harness（judge-reliability-harness）

- **文件**：`2026-11-15-spec110-judge-reliability-harness.md` ｜ **系列**：多专家审计批 ｜ **状态**：Design（r1，2026-11-15） ｜ **优先级**：🟠 P1
- **依赖**：独立可先行（新工具+spec 文本修订三处一行级）；数据卫生面消费 #109 T4 invalid 口径（可先以饿死词族粗口径落地，#109 落地后换装）
- **内容**：体系有判官的一切元指标（自稳定性/塌缩/置信）唯独没有**判官间一致性与分数分布形状**——T1 `just judge-reliability <dir>` 离线确定性报告（跨技能 κ+agreement 双报/α/resonance×缺陷效度 r/分布形状三哨兵[模值频率·sd·相当更差更好计数·通胀 slope·confidence 基率]——vol1 基线：κ≈0 除同派发伪影/α=0.311/r=+0.068/更好=0/模值 79×12/slope+0.073）；T2 在飞 spec 判据营养接线（#106 毕业最小窗 ≥48 章+形状门槛；#107 A/B 改 **McNemar 配对**+功效表义务[9 变异/臂 power 0.10-0.25，27/臂起步]）；T3 #103 confidence 校准前置+resonance SKILL 校准口径。观测面不进生产读面（#108 T3 同款纪律）
- **对应 plan**：待执行时建
- **触及的不变量维度**：无（测量基建）

---

### #111 · extractor 形状契约与长跑哨兵（extractor-shape-contract）

- **文件**：`2026-11-15-spec111-extractor-shape-contract.md` ｜ **系列**：多专家审计批 ｜ **状态**：Design（r1，2026-11-15） ｜ **优先级**：🟠 P1
- **依赖**：**#92 → #105/#107 → #109 → #111**（dispatch_helper 读组装面链尾，plan 首步 re-anchor）；read_extractors.py 无在飞冲突（#87 已完结）
- **内容**：extractor 是消费者单方形状假设、降级仅 log WARN 零计数——`extract_threads_overview` 要求 `## 线索详情` 而 producer（plot-thread-weaver）从不写该节：**44 次生产 reads 全部空转降级全文**（B 批千万字长窗保护从未生效）。T1 容形修复（两形状并认+vol1 真文件 fixture 红测）；T2 应用率哨兵（escape-hatch 计数聚合+降级率>50% CI 红）；T3 truth 增长曲线哨兵（KB/章斜率表+@1000 章外推对照阈值——matrix 202KB→3.9MB/current_state→2.0MB 在册）；T4 matrix/current_state 全量读收编（8 读者逐一裁定，matrix_scoped 105 次读仅 9 次真用）。CPU 非风险（实测线性 17ms/MB）——风险全在 LLM 载荷面
- **对应 plan**：待执行时建
- **触及的不变量维度**：无（读面基建）

---

### #112 · chapter_loop 状态机性质测试（chapter-loop-properties）

- **文件**：`2026-11-15-spec112-chapter-loop-properties.md` ｜ **系列**：多专家审计批 ｜ **状态**：Design（r1，2026-11-15） ｜ **优先级**：🟠 P1
- **依赖**：**#109 → #112**（chapter_loop 链尾；收编 #109 修复面反例，plan 首步 re-anchor）；error_handler/cli 无在飞冲突
- **内容**：单测盖路径、性质层缺席（历史反例全靠事故驱动修补）。T1 12 条不变量文档化（游标跳跃≡bundle 快照/done⊆实产物/SETTLING_FAILED 可复位/resume 幂等不双计/budget 键章号一致/escalation resolve 只清其章/staging 不吞 checkpointed/cascade 只数 valid/savepoint 覆盖 bundle 全员/trigger 不跳 mandatory 步…——各注现状成立/悬置）；T2 hypothesis RuleBasedStateMachine（真 state.py 类+mock 派发结果枚举，规则=步进/失败/G4/escalation resolve/任意点 crash-resume）；T3 已知反例回归收编（E-3 core 波 savepoint 漏传 wave_chapters·P1 先修/E-9 SETTLING_FAILED 无复位·P1 先修/E-10 budget 键/E-16 staging 时序/E-18 revision_count 重放双计/E-26 trigger 跳步/E-24 chapter=None 全清——修复与收编分离，其余 xfail 哨兵挂账）；T4 auto 模式 G4 二次失败放行语义**挂账用户裁定**（`:4728-4749` auto 放行 vs per-chapter escalation 同因异果）
- **对应 plan**：待执行时建
- **触及的不变量维度**：无（状态机基建）

---

### #115 · 质量测量内生性（quality-measurement-endogeneity）

- **文件**：`2026-11-15-spec115-quality-measurement-endogeneity.md` ｜ **系列**：多专家审计批（B 异模型元审） ｜ **状态**：Design（r1，2026-11-15） ｜ **优先级**：🟠 P1
- **依赖**：**#105 → #106 → #109 → #115**（chapter_loop/revision_router 同文件链，plan 首步 re-anchor；T1 覆盖 #106 T1 的分位语义——#106 先落 shadow 接线，armed 前必须经本件）；resonance SKILL 面 **#110 → #115**；drift/style 面 **#103 → #115**（只加 shadow 仪表）；T3 人工面板实弹随令（预注册 `docs/research/2026-11-15-quality-external-anchor-prereg.md`）
- **内容**：质量测量三重内生——P25 floor 分位语义（点火率=分数斜率函数：实测 8.3% vs 置换零假设 21.2%；#106 验收 ch2 期望与冷启动规则矛盾；cap=80 饱和）、风格学习回路（#103 第四源+playbook→drafting→同一判官）、外部效度缺席（无读者判据；「更好」=0/32）→ T1 语义拆分（rank_alarm vs quality_floor_abs+饱和哨兵）；T2 回路 holdout+自增强哨兵（shadow）；T3 外部锚定预注册（3 人盲评 12 章，ICC+Spearman ρ，$0 API）；T4 #106/#103/#110 消费面收编
- **对应 plan**：待执行时建
- **触及的不变量维度**：情绪节奏（弱关联——resonance floor 为该维正向下限接线面，不新增 check id）

---

### #116 · 门禁判别力（gate-discriminative-power）

- **文件**：`2026-11-15-spec116-gate-discriminative-power.md` ｜ **系列**：多专家审计批（B 异模型元审） ｜ **状态**：Design（r1，2026-11-15） ｜ **优先级**：🟠 P1
- **依赖**：独立可先行（新工具+文档+fixture，不改门行为）；**justfile 面 #92 → #93 → #116**；T4 变异器 **#108 落地后换装**（此前本地最小变异器）；回放只读，不依赖 #109-#115
- **内容**：真 G4 回放 vol1 50 章——**10 项散文门 50/50 全 PASS、13 项零 FAIL**；hook 30% 仅单字张力词（`还`/`账` 各 38 章=主角账房腔同词表）、protagonist 名表中位 93 vs 阈值 3（名表重复+`他` 单独 50/50 过）、transition 中位 0 vs 阈值 5、simile 56% WARN 不路由、ending 分类器 47/50 None；红测 40 处只证「能失败」不证「会失败」→ T1 `just gate-power` 离线回放（state-free/full 双口径+触发归因）；T2 恒真登记+`just check` WARN 哨兵；T3 六项标定提案（hook/protagonist/transition/scene/simile/ending，不改行为，用户逐项裁定）；T4 真语料变异负例（复用 #108 变异器）
- **对应 plan**：待执行时建
- **触及的不变量维度**：无（测量/标定面——不改任何载体/声明/门检 id）

---

### #117 · 审计证据可验证性（audit-evidence-verifiability）

- **文件**：`2026-11-15-spec117-audit-evidence-verifiability.md` ｜ **系列**：多专家审计批（B 异模型元审） ｜ **状态**：Design（r1，2026-11-15） ｜ **优先级**：🟠 P1
- **依赖**：**#105 → #117**（`llm_output_integrity.py` 同文件）；justfile **#92 → #116 → #117**；#109 T4 invalid 口径复用（三态之一）；SKILL 文本不改（四要素契约已有，缺的是执行）
- **内容**：四要素证据契约（位置/≥20 字原文引述/规则名逐字/严重度）在门禁侧只实现为**报告级形态三选一**（`generic.py:125-126`），行号只验越界（`llm_output_integrity.py:173-192`），12 个 active review 技能仅 2 个有专用校验器（10 个只验存在/非空/≥50 字）；588 份章审计回放：契约形态完备 10.9%、≥10 字引述 2883 条中 **28.2% 在全项目文本中找不到逐字来源**、28 份全部引述不可解析；`audit_layer.py:253/:256` 以 `"BLOCKING" in content` 路由 → T1 发现级 parser（group 四要素/表格/legacy 三形态）；T2 `G4.av.evidence_*` 校验（location/quote/rule/severity/stale 三态，复用 quote_verbatim）；T3 消费三态（validated/unvalidated/invalid，unvalidated 不路由+summary 披露）；T4 vol1 只读回放+与 #109 invalid 交叉表
- **对应 plan**：待执行时建
- **触及的不变量维度**：无（审计产物有效性基建——新 check id 族 G4.av.evidence_*，不挂叙事维度）

---

### #94 · 接口诚实批（interface-honesty）

- **文件**：`2026-11-01-spec94-interface-honesty.md` ｜ **系列**：架构复审批次 A ｜ **状态**：Design（r2.2） ｜ **优先级**：🟡 P2
- **依赖**：T4（trace 累积器）须 #87 后施工；**T6 须 #85 后**（split_frontmatter）；其余独立
- **内容**：modes 清障（codex_api 死桩/internal 戏服删除，**不建 DispatchRoute Protocol**；错误移 `dispatch()` else 非 detect_mode）+ dispatcher.md 真三路由重写 + cli.py 引擎出鞘 **orchestration/checkpoint_flow.py**（~950 行搬家——**含 cmd_review 决策体才达 <900**）+ scoring argparse 子命令化与归一化单源（**补 codex 调用方迁移/shim；差异 4 项**）+ **DispatchContext 收拢 + legacy 参数文档化（test_type/round_dir/skip_reads）**（原 #87 T6 并入）+ _DispatchOutcome 累积器（4 trace 块/账目双拷归一，characterization 四出口**归一化白名单**）+ 文档诚实小批（AGENTS phase_runner 行/ADR 0004/行号注释 **6 处（src）**/now_iso 双拷；**_record_gate_manifest 三拷只登记不盲合**）+ 杂项微接口（write mode Literal/asdict/角色名单解析器/closure context_kind）
- **对应 plan**：待执行时建
- **触及的不变量维度**：无（接口/文档诚实层）

---

### #96 · 反 AI 检测体系方法论对齐（anti-ai-tell-alignment）

- **文件**：`2026-11-04-spec96-anti-ai-tell-alignment.md` ｜ **系列**：文笔面强化批（humanizer 对标） ｜ **状态**：Active（**r2** 2026-11-04——吸收第二源 Humanizer-zh＋实弹过滤） ｜ **优先级**：🟡 P2
- **依赖**：**#95 T1（词表/枚举常量单源）落地后施工**（先动=双源复发；#85 已完结）；**批次 A 清偿后启动**（主战场 SKILL.md×3＋review_checklist.py 预计算，不抢 chapter_loop 最热文件）；验收搭卷二实弹后续章不开新探针
- **内容**：双源对标（blader/humanizer v3.1.0＋op7418/Humanizer-zh 中文改编版，调研全录 docs/research/2026-11-04-humanizer-skill-analysis.md 与 -zh-skill-analysis.md）——已覆盖 7 条不重做＋**五缺口**：G1 机制层解释缺失/G2 证据分级聚集规则缺失（口癖帽×voice 互斥即 over-enforcement 实案）/G3 结构 tell 缺口/G4 anti-detect 工艺薄弱（无例证+无人味保留清单+不读 #71 正向资产）/G5 事实守恒无显式复核＋**r2 实弹过滤（novel-xinghuo-vol1 42 章 15.8 万字测频，§0.4）**：zh F 组中文 tell 四剔除（层叠的/进行+动词/被字句/随着——零真阳性）两弱化（排比堆叠仅语义判定+真枚举/声口排比豁免；中段收束降弱 tell）一撤销（重复句首——62 处全为跟拍合法形态）；吸收三件套体例（改写前/改写后/保留）+六维改写安全核对（施事者/时间/条件/范围/否定/归因+确定性传递防认知态漂移）+样本防污染+结构保护比对；不跟随 zh 三宽松化（删分级/删机制模型/破折号条件化）＋四任务：T1 D3 机制段+强/弱 tell 分级（**机器面硬闸一律不动**）+ T2 结构 tell 两条进 D3（参考计数不设硬阈值）+ T3 anti-detect 工艺升级（10 手法三件套/人味保留/reads 接声口指纹+金句位/六维对照/整段重述第 10 手法）+ T4 技能测试+实弹回归（audits 误报不升、剔除面零误报、金句位零丢失）。**根本裁定**：humanizer「不以过检测器为目标」对 shenbi 不适用（平台 AIGC 检测=商业约束）——检测器导向硬闸全保留，两目标并存
- **对应 plan**：待执行时建（`../plans/2026-11-04-spec96-*.md`）
- **触及的不变量维度**：叙事纪律（POV/声口）（弱关联——T3 人味/声口保留面）；其余为审计/改写工艺层

---

### #103 · 高光复盘与成功传染（highlight-distill）

- **文件**：`2026-11-15-spec103-highlight-distill.md` ｜ **系列**：写作工艺批 ｜ **状态**：Design（r1，2026-11-15） ｜ **优先级**：🟡 P2
- **依赖**：独立；消费管道现成（drafting 已读 style_profile/anchors——**dispatch 零改动**）
- **内容**：确定性选章（弧窗 ch%12 top-1 ∧ confidence=high ∧ 非 human_overridden ∧ overall≥全书 running median+5[相对阈值抗高分通胀]；卷界卷 top-1；compute_stats 同款代码侧零 LLM 判断）+`style/highlight_playbook.md`（append_dedup key=playbook_id；手法卡四要素：出处章+引文 verbatim≤200 字/三层归因[结构蓄放·节奏拍位·语言句式]/复用条件/使用计数+最近命中+状态列；**活跃卡上限 12**）+G4 结构门（四要素+引文在出处章逐字存在——quote_verbatim 共基复用）+新技能 shenbi-highpoint-distill（kind: artifact；arc/volume **双 entry 同 skill 双 mode**——style-learning triggers:226/:264 先例；卷界重合按 :493-498 抑制弧 entry）+drafting reads 加 playbook（manifest 消费可证）+style-learning anchors 半操作化候选池加**第四源**（本窗 resonance top 章段落优先——把读者信号接进 #71 已有范文环）+老化（2 卷未命中→highlight_playbook_archive.md，ledger_archive 同构）+**变奏提示**（计数≥3 间隔<6 章→planning 注入——手法卡是变量集不是模板，与 #96 tell 面天然联动）+drift-guidance 卷界命中汇总；（可选 T3b）planning reads 活跃卡复用条件。修「全链纯纠偏系统」：成功探测器从结构统计指标换成读者侧共鸣信号
- **对应 plan**：待执行时建
- **触及的不变量维度**：情绪节奏、能力活性（均弱关联——消费 resonance/母题信号面与注入面，不新增门检）

---

### #107 · 审评分档（reviewer-model-tier）

- **文件**：`2026-11-15-spec107-reviewer-model-tier.md` ｜ **系列**：评审工艺批 ｜ **状态**：Design（r1，2026-11-15） ｜ **优先级**：🟡 P2（机制先行；采用门槛=用户配置第二模型端点）
- **依赖**：**#92 后**（dispatch_helper 同文件——#92 T2a 在飞）；A/B 实弹与端点配置随用户令；C 臂测量器=#108 canary（或降级人工 bug-hunt 束）
- **内容**：executor_config `[overrides]` 增 `model` 键+`_get_skill_model`（结构平行 `_get_skill_thinking`；None→env 单源缺省[SHENBI_LLM_MODEL/deepseek-v4-flash]；空串/非 str→派发前 ValueError fail-loud）+dispatch_helper:3713 单点接线（API 双调用点经同一变量）+cost 面 model 分组确认（api_dispatch_start 已 log model——观测面免费）+**评计量表 A/B 预注册**（docs/research/2026-11-15-spec107-reviewer-tier-ab.md，#98 T0 预注册先例：A 现状[disabled+0.1]/B thinking=low+49152 头寸[预算根因由头寸解]/C 第二模型[model 键]；对象=review-resonance+group-character；判据=canary 捕获率差分+audits 误报不升+成本；停机条件预注册全文先落盘）+明确不建（codex CLI 模式模型域文档化即可/任何默认档位变更——**默认行为零变化差分钉死**）。修「审与写同模型同端点[executor_config 无 model 键]+评计量表=预算权宜[thinking 全禁，:188-195 自注 revisit with post-rollout data]而 G3.4 独立性止于会话隔离——训练分布盲点共享」
- **对应 plan**：待执行时建
- **触及的不变量维度**：无（执行器配置面）

---

### #108 · 审核灵敏度探针（audit-recall-canary）

- **文件**：`2026-11-15-spec108-audit-recall-canary.md` ｜ **系列**：评审工艺批 ｜ **状态**：Design（r1，2026-11-15） ｜ **优先级**：🟡 P2
- **依赖**：独立可先行（dry-run 零成本）；实弹=付费派发**随用户令**（单束 ≈6 技能×10 变异≈60 派发≈$0.35 量级）
- **内容**：变异器目录 `pipeline/canary/mutators.py`（确定性纯函数 9 个，实弹 P1 清单[escalation 真缺陷形态]取材：POV 人称换装→XC pov_break/保留名劫持→XC reserved_name_hijack/时间锚回拨→XC timeline_rollback/计数漂移→cd.counter/current_state 字段矛盾→group-factual/字数带击穿→G4.cd 地板/章末钩缺席→cd.chapter_end_hook/AI tell 注入→group-craft D3 预计算面/**长程承诺措辞漂移——期望检出面=无，缺口数据落地**[>5 章语义一致性无审核面的伤害实证，未来立项依据]；期望面标注对 invariants.md 门检列 check id 逐字）+探针 harness（`just audit-canary <dir|fixture> [--chapters N] [--dry-run]`：变异副本→review 固定六步+G4.XC 派发→召回矩阵 `reports/canary-report-<ts>.md`；**dry-run 默认** CI 可零成本跑构造正确性；cascade-skip 技能纳入派发面——验跳过不漏检[chapter_loop:686-709 现无抽样验证]；变异副本只进 /tmp round dir——项目 truth/chapters mtime 不变红测）+消费（召回 0 期望面→WARN 挂账；报告=**#105/#107 验收的 before/after 底座**——体系第一次能回答「审改之后审得更好了吗」）。修「体系测了判官的一致性[G7.15/双评]/塌缩[flag_score_collapse]/置信度[锚点命中率]，唯独不测召回——G7 全文不读 audits，审者假阴性零测量面」
- **对应 plan**：待执行时建
- **触及的不变量维度**：恒等 identity、时间、持有与经手 props、枚举计数 counters、叙事纪律（POV/声口）、情绪节奏（均只读消费——测既有门检/审计召回率，不改载体/声明/门检任何槽）

---

### #113 · 不可信文本定界加固（untrusted-delimiting）

- **文件**：`2026-11-15-spec113-untrusted-delimiting.md` ｜ **系列**：多专家审计批 ｜ **状态**：Design（r1，2026-11-15） ｜ **优先级**：🟡 P2
- **依赖**：chapter_loop 链 **#105→#106→#109→#112→#113**；review_checklist 面 **#96 → #105 → #113**；A/B 实弹随令（预注册 `docs/research/2026-11-15-spec113-injection-resistance-ab.md` 已随批落盘，≈$0.35）
- **内容**：R1 wrap 原语正确但只覆盖契约 reads 一通道（17 通道普查）——T1 六通道扩展（审查参考数据区外 ```json 注入/G4 corrective feedback 逐字引句无包裹=**自我注入回路**/escalation FAILURE DETAILS 裸拼/previous_draft+exemplar 伪标签无转义/wave stderr 回灌/人审 feedback 授权标注）；T2 反引号伪围栏防御（docstring 自认不转义——entity-escape 或围栏计数，vol1 全量回放零误伤）；T3 注入抵抗力 A/B（10 载荷×2 技能×2 臂，判据=带偏率+**误伤率不升**+成本≤3%/通道，44 派发）；T4 IDE 路由无角色边界文档化（结构改造明确不建，等 T3 数据）
- **对应 plan**：待执行时建
- **触及的不变量维度**：无（管线安全基建）

---

### #114 · escalation 自动分诊（escalation-triage）

- **文件**：`2026-11-15-spec114-escalation-triage.md` ｜ **系列**：多专家审计批 ｜ **状态**：Design（r1，2026-11-15） ｜ **优先级**：🟡 P2
- **依赖**：G4_FORMAT_EXAMPLES 面在 **#105 T4 后**；chapter_loop `_escalate_step_failure` 面链尾（#112 后）；独立数据面（escalation 报告/adjudications 只读）
- **内容**：escalation 单一出口把机器可愈与必须人裁混同通道——**16 份 escalation 触发 12 份=确定性 G4 门禁三振**（scene_budget 跨 ch5/35/39 三次独立升级、人审重裁同类；planning G4 ×4/settle g4 ×3）。T1 分诊矩阵（同 check id 首次三振∧声明/数值/结构族 → 机器反馈升级重派一轮[G4_FORMAT_EXAMPLES 差集补齐前置]；内容争议/重复三振/未分类 → 人审三保留面——防机器死循环；报告头机器可读行 `triage:`）；T2 裁决书机器可读索引（adjudications/INDEX.md append_dedup，31 份存量回放建索引，只读不改源）；T3 vol1 回放分诊报告（machine-feedback/human 两清单+可省人审次数估算，只报不写）
- **对应 plan**：待执行时建
- **触及的不变量维度**：无（人审带宽基建）

---

### #97 · pre-commit hook rev 落地链（precommit-rev-landing）

- **文件**：`2026-11-06-spec97-precommit-rev-landing.md` ｜ **系列**：工具链卫生批（PR #288 后件） ｜ **状态**：Active（**执行完毕待归档**——T0-T3 落地 2026-11-06［PR #293］＋首跑验收三指标全过 2026-11-09［run 42549398259：success·零 bot PR·C13 守卫绿·分支零残留，§首跑验收结果］；站点数勘误 7 非 6［archive.py:195 保留 noqa］+uv.lock ruff/mypy 双对齐为 spec 未预判的第 5 组 bump） ｜ **优先级**：🟠 P1（死线已达成——周 bump 管线稳态）
- **依赖**：**T0 前置 = PR #288 合并**（守卫/两遍验证执法面）；与批次 A 无文件域冲突，**先于批次 A 执行**（小件+死线，不触最热文件）
- **内容**：四组 rev 落地（ruff 0.15.17→0.17.3/mypy 2.1.0→2.4.1/pre-commit-hooks 4.5.0→6.0.0/shellcheck→-1）＋C13 理由迁移（**RUF100×6 判死实锤**——`uvx ruff@0.17.3` 干跑确认；六站点 noqa 删指令留纯注释理由，pyproject 治理注释同步演进，`grep -rc "C13 allowlist" src/` ≥6 红测）＋**冻结单源**（#288 的 hook 级 ruff-format exclude 收敛为 pyproject `[tool.ruff]` 单源——干跑实锤直接 `ruff format` 面不认 hook 级；活面残留仅 2 md 顺手清零）＋新规 fallout（**PLR0917×29 ignore 挂账批次 A 后**不做签名重构；tests 非法 noqa 1 处修）＋首跑验收观察点。回测基线 7725f002（173 文件污染批，已删）。干跑证据：format 面 169（archive 166＋活 2＋audit 1）/lint 面 35 零 md
- **对应 plan**：已建 `../plans/2026-11-06-spec97-precommit-rev-landing.md`（T0-T3+首跑验收全落，含 §首跑验收结果）
- **触及的不变量维度**：无（工具链卫生）

---

## 批次 A 共享文件面与施工顺序（2026-11-02 r2.2 审计增补）

同一文件同一时间只允许一个 spec 施工；跨 spec 共享文件的建议顺序（与各 spec 依赖字段不冲突时以本表为准）：

| 共享文件 | 触及 spec | 建议顺序 |
|---|---|---|
| `gates/shared.py` | #88 finding/#89 出鞘/#90 别名 | **#89 → #88/#90** |
| `justfile` check 面 | #95 T1 lint/#93 --strict/#92 子配方 / **#116 gate-power 配方 / #117 evidence-replay 配方** | **#95 → #93 → #92 → #116 → #117** |
| `tools/lint_registry_reconcile.py` | #90 T2/#92 T1 | **#90 → #92** |
| `phase_runner.py` | #92 T2 loader/#94 T5 now_iso | **#92 → #94** |
| `pipeline/chapter_loop.py`（最热） | #86 T3/#87 T3/#88 T3/#91 T4/#93 T5（批次 A 已清偿至 #91）/ **#105 T1/T4 · #106 T1（评审工艺批）** / **#109 T3/T4 · #112 T2/T3 · #113 T1 · #114 T1（多专家审计批）** / **#115 T1/T2（异模型元审批）** | 批次 A 序如旧；评审工艺批接续 **#105 → #106**；审计批接续 **#109 → #115 → #112 → #113 → #114**（每 plan 首步 re-anchor） |
| `pipeline/revision_router.py` | #105 T1 单源换装 / #106 T1 接线 / #109 T3 per-n 消费 / **#115 T1 floor 语义拆分** | **#105 → #106 → #109 → #115**（severity 换装先行，floor 接线 re-anchor，per-n 收口其次，语义拆分最后） |
| `pipeline/dispatch_helper.py` | #92 T2a（在飞）/ #105 T3 预检 / #107 T1 model 键 / #109 T2 双章组装 / #111 T2 哨兵 | **#92 → #105/#107 → #109 → #111** |
| `pipeline/parallel_dispatch.py` | #109 T3/T5 收口与过滤 / #113 T1 stderr 通道 | **#109 → #113** |
| `pipeline/read_extractors.py` | #111 T1 容形 | #111（无在飞冲突——#87 已完结） |
| `gates/g4/chapter_drafting.py` · `gates/shared.py` | #116 T3 标定提案（不改行为）/ T4 真语料负例 | #116（无在飞冲突——#88/#89 已完结） |
| `pipeline/llm_output_integrity.py` | #105 T2 词表/完整性扩展 / #117 T2 证据校验 | **#105 → #117** |
| `pipeline/review_checklist.py` | #96 预计算面 / #105 T4 ending 窗 / #109 T2 双章 / #113 T1 注入面 | **#96 → #105 → #109 → #113**（#109/#113 仅注入面受限） |
| `skills/shenbi-review-group-*/SKILL.md`（六技能契约面） | #109 T1 reads 对称化 | #109（契约改动过 lint_registry_reconcile 单源对账） |
| `pipeline/cli.py` | #94 T2 | #94（cli→orchestration/checkpoint_flow.py） |
| `skills/shenbi-chapter-drafting/SKILL.md` | #96 T3/#102 T2 | **#96 → #102**（#102 依赖字段已钉） |
| `src/shenbi/pipeline/triggers.py` | #103 T2/#104 T2 | **#103 → #104**（TRIGGER_STEPS 两处插步不并发） |

**总序**：#85 → #95（T1-T6 实现落地）→ 束4 验收 → #86 → #87 → 其余批次 A（#88/#89/#90/#91/#92/#93/#94 按上表与依赖插入）；#84 的 T0-14 已补落（PR #325，2026-11-10 归档）；#96（humanizer 对标批）批次 A 后启动——依赖 #95 T1 词表单源先行；**#97（工具链卫生小件）死线驱动插队先行——2026-11-09 修复版工作流首跑前清偿，T0 前置 #288 合并（已达成：首跑验收三指标全过，待归档）**；**#98 已完结（2026-11-08 归档）——束7 判定 PASS（强）：flash+thinking 启用规划 1 派收敛，卷二解堵；残余族（草写字数/settle matrix 增量）另议**。**写作工艺批（#102/#103/#104，2026-11-15 立项，用户裁定不考虑在飞项目）：#102 须 #96 后（drafting SKILL 同文件面）；#103 独立可插（消费管道现成）；#104 无硬依赖、建议 #102/#103 实弹后施工；#101 缺口=批粒度候选预留（未立项，不重编号不复用——2026-11-15 多专家审计批补充正确性侧证据：双章批 follower 审计饿死 147/588，见 #109）。** **评审工艺批（#105/#106/#107/#108，2026-11-15 立项，用户裁定不考虑在飞项目——四件全走机制先行/shadow/显式声明路径）：#105 → #106（revision_router/chapter_loop 同文件序；#105 T4 的 review_checklist 面顺延 #96 后）；#107 机制独立、dispatch_helper 面 #92 后、A/B 实弹随令；#108 独立可先行（dry-run 零成本，实弹付费随令）——#105/#107 验收可引其召回矩阵为 before/after 底座。** **多专家审计批（#109-#114，2026-11-15 立项，用户裁定不考虑在飞项目，八专家变身审计产出）：#109（P0）接 #106 后施工（chapter_loop 链）；#110 独立可先行（新工具+数据卫生粗口径先行，#109 T4 invalid 口径落地后换装）；#111/#112 排 chapter_loop/dispatch_helper 链尾（#109 → #112 → #113 → #114）；配套预注册两件+C 跨模型复核清单已随批落盘 `docs/research/2026-11-15-{goodhart-escape-rate-prereg,spec113-injection-resistance-ab,cross-model-review-checklist}.md`（实弹全随令）；#107 A/B 判据经 #110 升级为 McNemar 配对后其 T2 预注册文档落盘时须引用。** **异模型元审批（#115-#117，2026-11-15 立项，B 异血统会话：本会话服务模型 deepseek-v4-flash ≠ GLM 产出线；用户裁定不考虑在飞项目、零付费派发）：#115 接 #109 后施工（chapter_loop/revision_router 链尾；#106 先 shadow 接线，armed 前经其语义拆分 + #115 T3 外部锚定）；#116 独立可先行（新回放工具+文档+fixture，不改门行为；六项标定提案用户逐项裁定）；#117 接 #105 后（llm_output_integrity 同文件；#109 T4 invalid 为三态之一）；配套外部锚定预注册已落盘 `docs/research/2026-11-15-quality-external-anchor-prereg.md`（人工盲评 12 章×3 人，ICC+Spearman ρ 判据，6 人时/$0 API，实弹随令）。**

## 登记与编号约定

- 新增 spec 时在此登记：`### #NN · <title>` + 文件/系列/状态/优先级/方法/依赖/内容/对应 plan 字段；编号 = 现有最大号 +1
- **行号锚纪律（r2.2 新增）**：spec 内行号为立项/修订时点快照（本批已按 2026-11-02 当前树全量对码，含 #275 后 +3 漂移）；**每一份 plan 首步必须按函数/符号 re-anchor**，不得直接沿用行号——#85/#95 落地后 chapter_loop/dispatch_helper 的绝对行号必然再漂。
- **「触及的不变量维度」必填节**（spec #80 T10）：每个活跃 spec 的登记块须含一行 `- **触及的不变量维度**：<清单 或 无>`——引用 `docs/framework/invariants.md` 普查表的维度名（如 `恒等 identity/持有与经手 props`）；不触及任何维度写 `无`。`lint_invariant_coverage` 校验活跃项该节存在性（P1 只校 P1 期相维度）
- spec 完成（Done）或驳回（Rejected）→ 移 `archive/` 并从本页删行；**编号是历史唯一标识，不重编号、不复用**（系列/依赖字段按编号交叉引用，重编号会断链）
- 本页不维护归档计数与归档分类汇总
