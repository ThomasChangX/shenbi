# Spec #121 · 实弹续跑解堵批（resume-unblock-batch）：结算预算降级序保住本章审计＋重派两处升检查点补打暂存标记

**日期**：2026-11-24｜ **系列**：实现审计清偿批（expert-panel-implementation-audit · 2026-11-24 八席审计，协调者逐条亲验）｜ **状态**：Design（r1，2026-11-24）｜ **优先级**：🔴 P0
**动机证据**（HEAD `3311a0af`；实弹数据＝vol1 截至 2026-11-09 最后一次真实派发）：
- **T1 面（结算看不到伏笔审计）**：`src/shenbi/pipeline/dispatch_helper.py:1392-1393`（`_BUDGET_DROP_TIERS` 首层 `("audits/",)  # 先弃：审计参考面`——spec #95 T3③ 降级序）＋`:319`（`SKILL_TOTAL_CHAR_BUDGET = {"shenbi-state-settling": 72_000}`）vs `skills/shenbi-state-settling/SKILL.md:151`（「本章钩子增量的唯一确证来源是 `audits/chapter-N-foreshadowing.md`……引用与该审计对不上 = 结算与审计互相矛盾，G4 会拒」）。真实派发归档回放（只读重组 prompt 面）：ch41 三次 settle 首派 95,850–97,000 token、零弃面 → **ch43 起 9/9 次首派弃面均含本章伏笔审计与 `truth/prop_registry.md`**，prompt 降至 49,266–53,350 token；超预算是结构性的（`name_registry` 13,145 字符＋`prop_registry` 15,987 字符，各涨约 300 字符/章，合计约为 72K 预算的 40%）。台账 `novel-xinghuo-vol1/vol1-ledger.md:472` 当时记「settle_budget_degraded 按设计 WARN」；现行停机面＝`pipeline-state.json` 的 pending_re_dispatches——ch49 settle 重派 `G4.ss.hooks_structure … content_dropped:3行（钩子基底行被丢…）`。`tests/unit/pipeline/test_settle_total_budget.py:56-66`（`test_priority_face_drop_before_tail_cut`）把「audits 面先弃」钉成预期。
- **T2 面（重做产物被退出清理删除）**：`src/shenbi/pipeline/cli.py:384-396`（重派 `shenbi-state-settling` 成功后 `set_checkpoint(STATE_SETTLE)`）与 `:397-409`（重派 `shenbi-chapter-planning` 后 `set_checkpoint(CHAPTER_MEMO)`）均未调用 `_mark_staged_for_checkpoint`（全仓调用点仅 `chapter_loop.py:2706/:2742/:4654`）；`src/shenbi/pipeline/crash_recovery.py:202-209`（退出清理 `clear_staging(project_dir, preserve_checkpointed=True)`——只保留带标记产物）；`:34-50`（`reset_emergency_state` 全仓零调用方——钩子经 `chapter_loop.py:4107-4109` 启动后，进程存续期不解除）；`cli.py:766-774`（「无暂存真相」告警只在 PER_CHAPTER 分支，STATE_SETTLE/CHAPTER_MEMO 批准为静默空提交）。**三臂复现**（真实 `_execute_pending_re_dispatches`／`_emergency_cleanup`／`_commit_staging_for_checkpoint`，仅替换 LLM 调用与两处门检；两处各跑一次）：钩子未启动→批准后提交新产物；**钩子已启动→暂存被清、批准后 live 仍为修订前旧事实／旧备忘、零告警**；同前＋补标记→恢复正常。接缝缺口：`tests/pipeline/test_staging_lifecycle.py:39-60`（标记产物活过清理）与 `tests/unit/pipeline/test_audit_routed_settle_redispatch.py:43`（重派会执行）各盖半边，无测试走「重派→升检查点→退出清理→批准提交」整链。**未确认项**：是否已在真实运行造成过损失——`pipeline-resume.log` 中两次真实重做结算后均无退出清理日志、`snapshots/` 无 emergency 快照，证据不足，不下结论。

**触及的不变量维度**：承诺与债务（钩）（弱关联——T1 保住钩子增量的证据面，不改判定判据；T2 为暂存生命周期基建，无叙事维度触面）

---

## 0. 根因

两处都是「框架改动只经单测与离线回放验证、未经实弹」留下的回归，共同形态是**保护机制各自成立、衔接处无人测**：

- **T1**：spec #95 T3③ 为 settle prompt 无界膨胀（68→96k）建了 72K 预算与分级降级序；「先弃审计参考面」对一般技能合理，但 state-settling 的审计不是参考面而是它自述的唯一确证来源——降级序没有「本步证据恒保」的概念。于是让模型盲写钩子增量，再用它没看到的审计去验它（G4.ss）。#95 归档当晚（2026-11-05）ch43 起 100% 中招。
- **T2**：C30 R1（F318）建了「升检查点时给暂存产物打标记→退出清理只留带标记产物」的机制，标记点只加在 chapter_loop 的三个正常升检查点点；cli 重派队列里两个同构的升检查点点（probe2 matrix-D 修复与 #53 memo redo 共用同一队列）被漏掉。

**用户裁定**：无——纯缺陷修复，行为变化仅限两条缺陷路径；零付费派发（回放用既有派发归档与只读组装）。

**备选案已评估并否决**：
- 「降级序整体反转（audits 最后弃）」——对非 settle 技能无证据；且超预算是结构性的，反转只是把损失挪给别的面。本件只把**本次结算章号范围内的审计**列为恒保面，与既有恒保面（chapters／pending_hooks／current_state）同列；
- 「给两份登记表接窗口切片器腾预算」——是根治，归 #111 T4；但不保证本章审计永不进弃面（预算仍可能不足），两者不互斥，本件先保证据面；
- 「退出清理不再清暂存」——C30 R1 的清理是为防陈旧暂存污染，方向相反；补标记才是与既有设计一致的修法；
- 「重派路径不升检查点、直接并入 PER_CHAPTER」——改变 probe2 matrix-D／#53 的既定评审语义（重做产物须单独过审），超范围。

## 1. 任务分解

### T1 · 结算预算降级序：本章审计恒保
- 降级循环加恒保谓词：路径属于**本次结算章号**（bundle 成员章一并）的 `audits/chapter-{N}-*` 不进任何弃面层；超预算时由其余面按既有层级降级。谓词复用审计路径的既有单源（`audit_relative_path`／章号占位符解析），不新造第二套路径规则；
- 测试：改写 `test_priority_face_drop_before_tail_cut`——同输入下本章伏笔审计必须保留（先红后绿），另增「构造超预算仍保本章审计」用例；**非本章**审计（旧章 audits）仍首弃（行为不变差分）；
- 回放报告（只读、零派发）：对 vol1 ch43–50 的 9 次首派输入（派发归档 blob）做 dry-run 组装，输出修后弃面清单；
- 判据：`git grep -n "BUDGET_DROP_TIERS" src/` 可见恒保谓词；红测转绿；非 settle 技能降级行为差分零变化；回放报告显示本章伏笔审计 9/9 保留；`just check` 全绿。

### T2 · 重派两处升检查点补打标记＋整链回归
- `cli.py` `_execute_pending_re_dispatches` 两处 `set_checkpoint` 之后调用 `_mark_staged_for_checkpoint(project_dir, <对应 ChapterStep>, ch)`——step 按技能名自 `CHAPTER_STEPS` 解析，不新建第二个标记实现；
- STATE_SETTLE／CHAPTER_MEMO 批准时若无对应暂存产物 → WARN（对齐 `per_chapter_no_staged_truth` 的 #39 观测面，文案点名检查点类型与章号）——让「静默空提交」至少可见；
- 整链回归测试（新接缝）：参数化重派条目两类型（`per-chapter` settle 条目、`chapter-memo` redo 条目）× 钩子两态（启动／未启动），走真实 `_execute_pending_re_dispatches` → `_emergency_cleanup` → `_commit_staging_for_checkpoint`，断言 live 文件为重做产物；
- 判据：两处 `set_checkpoint` 后均可见标记调用（`git grep`）；整链测试四格全绿，且撤掉修复必红（回归红绿回撤验证）；既有 `test_staging_lifecycle.py`／`test_audit_routed_settle_redispatch.py` 零改动通过；`just check` 全绿。

## 2. 验收
1. T1–T2 判据全绿；
2. 对 vol1 只读重放：按 ch49 现存 pending_re_dispatch 条目 dry-run 一次 settle 组装，弃面不含 `audits/chapter-49-foreshadowing.md`；全程零派发、项目目录零新增文件；
3. 实弹验收（随用户令，≈1 章以内）：ch49 重做结算首派过 G4.ss；承载它的进程退出后 `staging/truth/` 仍在；批准后 live truth 含本次增量。

## 3. 风险
- **预算压力去向**：恒保本章审计后，超预算时其余面被多截——披露行如实列出被弃／被截面（既有【截断告知】机制）；回放报告须核对 `pending_hooks`／`current_state`（恒保面）可见量不劣于修前（修前它们本就在弃面或被截）；
- **恒保只挡「整块弃」**：若尾截断仍能切到本章审计，恒保形同虚设——恒保面须同时排除在尾截断候选之外（或设保底字符数），plan 期二选一并红测；
- **标记后的语义**：带标记产物在 reject 路径由 `_reject_staging_scoped` 清理（既有语义，正确）；modify 路径不变；「标记集＝批准时会提交的集」这一 `_mark_staged_for_checkpoint` docstring 不变式由整链测试守门；
- **共享文件面**：`dispatch_helper.py` 降级序与 #111 T4（读面收编）／#113 T1（wrap 通道）同文件，`cli.py` 重派函数与 #94 T2（引擎出鞘搬家）／#112（性质测试收编）同文件——**本件排在这四者之前**，后四者 plan 首步 re-anchor；
- **在飞项目**：零迁移（不改任何运行工件格式）；vol1 现存 `staging/truth/` 为上次运行遗留，续跑时由既有 resume 清理按标记处置。

## 4. 立项预答（价值门 ④⑤ 前置）

**④ 博弈路径清单**（假设修法全部实施，根因能否复发）：
- 恒保谓词只认 `audits/chapter-N-` 字面，将来审计文件改名 → 恒保失效而测试仍绿 → 缓解：谓词走路径单源，测试用真文件名；
- 预算仍不足时尾截断切到本章审计 → 缓解：见风险第 2 条（恒保面排除在尾截断之外）；
- 将来新增第三处重派升检查点再次漏标 → 缓解：把「升检查点＋打标记」收成一个 helper，重派两处与 chapter_loop 三处都走它（AST lint 候选登记 P2）；
- 退出钩子未启动的进程（自非 step 0 处续跑）本就不受影响——非缺陷路径。

**⑤ 候选机制清单**（buy-before-build）：
- 既有恒保面机制（chapters／pending_hooks／current_state 恒保）＝直接升格：多加一类恒保面，不新建机制（覆盖 100%）；
- `_mark_staged_for_checkpoint`（`chapter_loop.py:1947`）＝直接复用（覆盖 100%）；
- `per_chapter_no_staged_truth` WARN（#39 观测面）＝文案与落点先例；
- 回放脚本先例＝#119 的 review 预算回放与 #116 的 gate-power 回放（只读重组＋真产物输入），入库时按 G0.9 用真产物副本。无新建机制。

**测量语义回执（v8.1 L1–L5，触及面：预算阈值）**：L1 构念与口径——弃面／截面一律以字符计，披露行与预算同单位，不换算成「信息损失率」；L2 未触及；L3 活性与负荷去路——恒保后预算压力落到其余降级层与尾截断，回放报告须给出「被多截的面及字符数」（不允许压力去向不可见）；L4 可判别性——整链测试四格（两类型×钩子两态）互斥穷尽；L5 时点保真——回放输入取自在线派发时刻的归档 blob，不用磁盘现状倒推。
