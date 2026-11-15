# Spec #109 · bundle 审计覆盖正确性（audit-bundle-coverage）：follower 章 reads 契约对称化、派发组装双章化、收口/路由 per-n 消费面、占位与失败判定语义拆分

**日期**：2026-11-15｜ **系列**：多专家审计批（expert-audit）｜ **状态**：Design（r1，2026-11-15）｜ **优先级**：🔴 P0
**补充证据（2026-11-15 实验执行）**：`reports/2026-11-15-goodhart-escape-execution.md` F3——A2/B1/B2 在 `chapters/chapter-53.md` 缺失（scene-split 未晋升）时，`shenbi-review-resonance` 仍写入 `truth/resonance_trend.md` 行（63/81/63）。生产管线的 `_pre_dispatch_hooks` 会挡 draft-consuming 派发，但技能级没有「无正文→不评分」硬守卫；补充 #109 的饿死形态：除「待补/通过」外，还包括**看似正常的分数**。
**动机证据**：`skills/shenbi-review-group-craft/SKILL.md` contract 块（reads 只声明 `chapters/chapter-N.md`+`plans/chapter-N-plan.md`，writes 却声明 `chapter-N-*.md` 与 `chapter-{N+1}-*.md` 双路径——group-plan/-factual/-character、review-resonance、review-sensitivity 六技能同构，factual 连 plans 都不读）；`src/shenbi/pipeline/chapter_loop.py:3936-3937`（`build_shared_audit_context(project_dir, chapter)` 单章构造——follower 章正文/真相不进任何缓存）；`src/shenbi/pipeline/dispatch_helper.py:1338-1355`（`generate_review_checklist(project_dir, chapter)` 单章注入——「审查参考数据」预计算值只含 anchor 章）；`novel-xinghuo-vol1/observability/dispatches/00027-shenbi-review-group-craft-ch025-a1.json`（reads manifest **无 chapters/chapter-26.md**；checklist 块 `{"chapter": 25, …}`——follower 盲派发 blob 实锚）；实弹量化（2026-11-15 全量扫描 audits/，判据=饿死标记词族）：588 份章审计中 **147 份为输入饿死产物**，偶数章 158/294（54%）vs 奇数章 7/294（2.4%），**其中 49 份携带「通过」判定**（如 `chapter-48-memo-compliance.md`「通过（附条件）…凡未能以正文证据坐实者一律标注待正文核验」——无正文判过并计入 cascade streak；另见拒绝形 `chapter-2-memo-compliance.md`「0/100 不通过·无法核对」与占位形 `chapter-32-anti-ai.md`「待补（正文未提供）」）；`chapter_loop.py:4066`（consolidation summary 只写 anchor 章）+ `:4151`（`_route_revision_after_resonance` 只对 anchor 调用）+ `:4099-4107`（blocking_found 磁盘兜底只扫 anchor 章任务路径集）→ **follower 章 BLOCKING 零消费面**（147 份含 BLOCKING 条目报告 → 0 次修订/升级触发，run 推进至 ch50）；`chapter_loop.py:4770-4776`（serial 收口环「runs for EVERY bundle chapter」在 wave 拦截 `:3865-3866` 下**不可达**——wave 制度下 audit_layer 复扫/G4 兜底对两章都不跑）；`audits/chapter-1-review-summary.md` 原文（「Reviews executed: 6 / Successful: 1 / Failed: 5 / BLOCKING Issues: 0 → "No BLOCKING or CRITICAL issues found"」——**失败计净**）+ `parallel_dispatch.py:303-340`（consolidate 语义根）；`adjudications/adjudication-010.md`（历史前科自认：并行评审写层 no_files_parsed 丢 5/6 产物，52 份审计人工从 diagnostics 信封抢救落盘）。

**触及的不变量维度**：无（修复的是审计层自身覆盖正确性——不新增叙事维度门检；全维度审计有效性间接受益）

---

## 0. 根因

**spec #72 T9 的 cluster dispatch 只扩了产物面没扩输入面与收口面**：「ONE prompt per skill covers the bundle」把 writes 扩到 `{N+1}`，但契约 reads、shared 缓存、checklist 预计算、consolidation glob、revision 路由全部停留在单章语义。净效果三层：(1) follower 章被**盲派发**——LLM 无正文无预计算，行为分流为拒绝（BLOCKING 派发完整性）/占位（待补·不适用）/**编造通过**（附条件·计划级预核对）三种形态；(2) 三种形态均以「成功派发」身份落盘（步骤标 done、不重试），编造通过还污染 cascade 连跳基线；(3) 即使报告带 BLOCKING，收口/路由四处 anchor-only，**零消费面**。对以「审计门是资产」立身的体系，双章批下 core-circle 审计覆盖率实测 ~46% 且全程静默——这是正确性级空洞，非调参问题。

**用户裁定（2026-11-15）**：不考虑在飞项目——vol1 存量 147 份饿死审计不回补不清洗（历史章补评属维护命令口径，若需要走 #106 T3 resonance-backfill 同款先例另议）；本件只修机制，旧 bundle 形态项目续跑时由新收口面如实报告 follower 缺口（只报不写）。

**备选案已评估并否决**：「废除 bundle 改单章派发」——批粒度本身是 #101 预留候选的用户决策面（容量证据在册），本件以「bundle 保留、reads/组装/收口对称化」为最小正确修，不预裁批粒度；「并入 #105 T3 派发预检」——#105 预检的是**文件在盘否**（chapter-26.md 在盘→预检通过→仍饿死），与本件的**契约声明面缺口**不同层，合并会互相稀释判据。

## 1. 任务分解

### T1 · 契约 reads 对称化
- 六技能（group-craft/-plan/-factual/-character、review-resonance、review-sensitivity）reads 补 `chapters/chapter-{N+1}.md`；读 plans 的技能补 `plans/chapter-{N+1}-plan.md`；factual 族按其真实消费面裁定（world-rules 审计读 plans 与否以 SKILL 正文为准，不虚增）；
- `lint_registry_reconcile`/`lint_decisions_sources` 对账面同步（#90 单源机制现成，契约改动自动纳入）。

**判据**：`git grep -n "chapter-{N+1}" skills/shenbi-review-*/SKILL.md` reads 区命中六技能；`just check` 契约对账绿。

### T2 · 派发组装双章化
- `build_shared_audit_context` 改造为 bundle 语义（接受 chapters 列表或 wave 侧对 bundle 逐章构造再合并——`chapter_loop.py:3937` 单点）；chapter_text/raw_files/checklist 派生源覆盖 follower；
- `generate_review_checklist` 双章产出（两块 `审查参考数据` 或单块 chapters 数组——plan 期按 prompt 模板定形，`review_checklist.py:194-237` 注入点适配）；reads manifest 须含 follower 章正文条目。

**判据**：构造双章 fixture dry-run（`--dry-run` 或单测直调 build_skill_prompt）：prompt 内 `chapter-{N+1}.md` 正文与两章预计算块均在（blob 级断言）；reads manifest 含 follower 章 path。

### T3 · 收口/路由 per-n 消费面
- wave 路径对 bundle 每个 n 各跑：consolidation 文件扫（glob `chapter-{n}-*.md`）+ `_route_revision_after_resonance(state, project_dir, n)` + blocking_found 写入各 n 的 ChapterState（`:4066/:4099-4107/:4151` 三点对称化；serial 收口环 `:4770-4776` 的 per-n 语义以 wave 等价物复活，`run_audit_layer` 复扫面是否纳入 plan 期裁定）；
- review-summary：per-n 双写或单文件双节（含 bundle 披露行）。

**判据**：红测——构造 follower 章审计含 `[BLOCKING]` 的 fixture 项目跑 wave 收口：该 n 的 `audit_results["blocking_found"]=True` 且路由触发；`git grep` 证明三点不再 anchor-only。

### T4 · 占位/失败判定语义拆分
- 新校验（`llm_output_integrity` 族，#105 T2 同侧扩展位）：审计产物判定行命中饿死形态词族（待补/不适用·正文缺失/无法核对/附条件·待正文核验/不构成通过判定）→ 产物判 **invalid**（非 pass 非 fail 的第三态），G4 FAIL 附「输入缺口——不得出具判定」重派指引；
- `_wave_audit_entry`（`chapter_loop.py:4140-4142`）加 valid 维度：cascade streak 与 `should_skip_audit` 只数 valid-pass；invalid 产物所属步骤不当 done（`:4083-4085` except-failed 语义保留，invalid 等位处理）；
- review-summary 语义修正：Failed>0 或存在 invalid 产物时，**禁止**输出「No BLOCKING or CRITICAL issues found」净结论——代之以显式缺口披露行（`parallel_dispatch.py:303-340` consolidate 结论分支）。

**判据**：红测三条（`判定: 通过（附条件）`+饿死标记→invalid；`Successful:1/Failed:5`→summary 含缺口披露行；invalid 不进 cascade streak——`should_skip_audit` 单测）；对 vol1 全量 audits 回放新校验器：invalid 清单与 147 件口径一致性报告（只报不写）。

### T5 · resume 补跑证明
- resume 路径对 bundle 内 follower 缺产物/invalid 的审计步骤实际重派（`_filter_completed_audit_tasks` 文件存在性过滤 `chapter_loop.py:390-396` 对 invalid 形态产物不视为完成——配合 T4 invalid 标记）；构造 mid-wave crash + follower 缺产 fixture：重放后 follower 审计补跑且带全输入。

**判据**：crash-replay 集成测试（follower 报告缺→重派→产物 valid）；`git grep` invalid 感知过滤证明。

## 2. 验收
1. T1-T5 判据全绿；
2. 差分回放：对 vol1 全量 audits 新收口面输出 follower 缺口报告，计数与 147/588、49 编造通过口径一致（**首次体系能看见这个洞**）；
3. bug-hunt：三饿死形态（拒绝/占位/编造通过）均被 T4 拦；follower BLOCKING 触发修订路由（T3）；
4. 双章 fixture dry-run 全链：prompt 双章输入（blob 断言）→ 产物 valid → 收口双章各得路由记录；
5. T2 生成测试 ≥94（双章审计产物质量）。

## 3. 风险
- wave prompt 尺寸上升（双章正文+双 checklist ≈ +40-60% 审计 prompt；按 vol1 审计族 27% 调用/16.7% 成本面估算全链 +7-10%——预算核算入 plan，超预算时按 #95 T3③ 降级序处置）；
- 与 #105/#106 同文件（chapter_loop/parallel_dispatch/revision_router）——施工序 **#105 → #106 → #109**（每 plan 首步 re-anchor）；SKILL 契约改动与 #102（drafting sidecar 面）不同文件、与 #96（review_checklist 预计算面）共享 `review_checklist.py`——**#96 先**（#105 T4 同款约束）；
- 占位词族误伤（正文合法讨论「待补」语义）——校验只锚**判定行**形态（`判定[：:].*(待补|不适用…)`），散文提及豁免（#105 T2 同款口径）；
- #101 批粒度裁定时若改单章批，T2/T3 的 bundle 逻辑仍以「bundle=N 单章」退化成立——设计按 chapters 列表参数化，不绑死 2。
