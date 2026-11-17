# Spec #109 · bundle 审计覆盖正确性（audit-bundle-coverage）：follower 章 reads 契约对称化、派发组装双章化、收口/路由 per-n 消费面、占位与失败判定语义拆分

**日期**：2026-11-15｜ **系列**：多专家审计批（expert-audit）｜ **状态**：Design（r3，Revised 2026-11-18——用户裁定 A：计数基线从散文数字改为可执行基准脚本 `tools/audit_starve_baseline.py`（附录 A）+四处修正（T5 论据/期刊限定/T1 判据/语料标签）；**设计审查修订（2026-11-18）**：C1 offset reads wave 条件语义+契约升级声明、I1 生产锚定全判定行/双锚定、I2 词族常量落位 src、I3 回放离线定界、M1-M4；r2 的问题诊断与解法框架存活）｜ **优先级**：🔴 P0
**r3 修订依据**（2026-11-17 价值门第二轮驳斥+协调者亲验，REWRITE×2 熔断后用户裁定）：r2 散文计数被对抗复算击穿（115/158 实为 602 口径而标签写 588；「全偶零奇」仅首锚定行语义成立；31/33 八种解读无一复现）——计数判据不可再以散文形态存在，验收#2 仲裁器改为附录 A 脚本；T5「savepoint 绕过」论据不成立（`wave_completed` 全 src 零消费者=write-only 取证，删除）；「期刊无人读」过强（`g4_post_write_integrity` 读期刊，限定为 wave 路径无 G4 消费点）；T1 判据裸 grep 先于改造即通过（writes 区今日已含 `{N+1}`），改锚契约 reads。
**r3 erratum**（2026-11-18 第三轮驳斥收尾，随裁定 A 意图直办）：①词族并入附录 A 单源（脚本增 `T4_VARIANTS` 常量；T4 散文词族与脚本 FAMILY 不一致将使验收#2 按散文实现必不可复现——删散文列举改脚本引用）；②verdict_pass 奇数位归因修正（实测 8 份中 6 份为合法审计语义 file_level 假阳[『不适用』正当用法：单章窗口/无文言角色/铁律豁免讨论]，真节段饿死仅 2 份 ch45/ch49-reader-pull）；③删「判定为 …语料 13 行」计数（散文计数三轮三值[13/14/15+]，plan 期以实测为准）。
**补充证据（2026-11-15 实验执行）**：`reports/2026-11-15-goodhart-escape-execution.md` F3——A2/B1/B2 在 `chapters/chapter-53.md` 缺失（scene-split 未晋升）时，`shenbi-review-resonance` 仍写入 `truth/resonance_trend.md` 行（63/81/63）。生产管线的 `_pre_dispatch_hooks` 会挡 draft-consuming 派发，但技能级没有「无正文→不评分」硬守卫；补充 #109 的饿死形态：除「待补/通过」外，还包括**看似正常的分数**——该形态 T4 词族不设防，主防线是 T2 的输入面断言（见 T4）。另 r3 新增独立缺陷类：**ch45 形「数据未注入」节段饿死**（`chapter-45-reader-pull.md:51` `**判定**: 无法评估（数据未注入）`——奇数 anchor 章缺 checklist 预计算注入；**erratum 归因修正**：verdict_pass 奇数位 8 份中仅 2 份[ch45/ch49-reader-pull]属此类，其余 6 份为合法审计语义的 file_level 假阳[『不适用』正当用法]；**覆盖面（设计审查 I1 裁定）**：判定行形由 T4 全判定行值段锚定检出，非判定行提及形检测面为零、由 T2 双章 checklist 预防单侧覆盖）。
**动机证据**（锚=HEAD 48fa2c87，#105/#106 合入后漂移全数更新并经协调者逐条亲开）：`skills/shenbi-review-group-craft/SKILL.md:7-24`（reads 只声明 `chapters/chapter-N.md`+`plans/chapter-N-plan.md`，writes 却声明 `chapter-N-*.md` 与 `chapter-{N+1}-*.md` 双路径——group-plan/-factual/-character、review-resonance、review-sensitivity 六技能同构[复核：六文件 reads 区 `chapter-{N+1}` 零命中，factual 连 plans 都不读]）；`chapter_loop.py:4067`（`build_shared_audit_context(project_dir, chapter)` 单章构造，实现 `audit_context_cache.py:60-76`——follower 章正文/真相不进任何缓存）；`dispatch_helper.py:1347-1367`（`generate_review_checklist(project_dir, chapter, …)` 单章注入——「审查参考数据」预计算块只含 anchor 章，注入点 `review_checklist.py:197-240`）；`novel-xinghuo-vol1/observability/dispatches/00027-shenbi-review-group-craft-ch025-a1.json`（reads manifest **无 chapters/chapter-26.md**；checklist 块 `{"chapter": 25, …}`——follower 盲派发 blob 实锚，磁盘三层核验过）；**实弹量化基线=附录 A 脚本**（语料 588 份破折号形维度报告[排除 25 份 review-summary；侧表：14 份 aggregate、21 份其他 md]，manifest `d9a1b5f0…f5c2`）：文件级饿死 114@窄6（even102/odd12）/157@扩12（even144/odd13）；**判定行口径（首锚定行语义）47@窄6/85@扩12——全偶数章零奇数**；verdict_pass∩饿死 30@窄6（even23/odd7）/32@扩12（even24/odd8）——偶数位=编造通过（无正文判过并计入 cascade streak），奇数位构成见 erratum（6 假阳+2 真节段饿死）；抽样逐字核对：`chapter-48-memo-compliance.md`（`**判定**: 通过（附条件）`…「凡未能以正文证据坐实者一律标注「待正文核验」」；另有**词族外变体**「待核」「暂记 85/100 通过」——T4 词族须覆盖，见 c 项）、拒绝形 `chapter-2-memo-compliance.md`（`不通过（无法核对）`·评分 0/100）、占位形 `chapter-32-anti-ai.md`（`待补（正文未提供）`）；收口消费面实证：`chapter_loop.py:4226-4234`（consolidation 与 review-summary 只写 anchor 章；consolidate 文件扫描 glob `chapter-{chapter}-*.md` anchor-only，`parallel_dispatch.py:394`）+ `:4321`（wave 侧 `route_revision_after_resonance` 只对 anchor 调用[serial 侧 :4663 同]；`collect_audit_issues` glob anchor-only `revision_router.py:388-390`）+ `:4258-4271`（blocking_found 写入只落 anchor 的 ChapterState；磁盘兜底扫描集 `task.all_output_paths()` 经 `_offset_sub` 实含 follower 报告路径——真缺口三处=结果归因只落 anchor 州＋传感器查字面 `"## BLOCKING Issues"` H2 串[588 份维度报告实测零含该串，精确 H2 仅 6 份 summary 独有——此析取支恒假，须换 `_BLOCKING_MARKER_RE`/`build_consolidator_sensors`，见 T3-f]＋路由 glob anchor-only）→ **follower 章 BLOCKING 零消费面**（`novel-xinghuo-vol1/pipeline-state.json` 实证：50 章 chapter_states，偶数章 blocking_found=True 计 **0**、revision_route 零记录 vs 奇数章 blocking 6/route 25——全部路由活动在 anchor 位，run 推进至 ch50）；`chapter_loop.py:4938-4943`（serial 收口环「runs for EVERY bundle chapter」在 wave 无条件拦截 `:3995-3996` 下**不可达**——wave 制度下 `_run_audit_close_for_chapter` 的 blocking→重试→修订→复扫对两章都不跑）；`audits/chapter-1-review-summary.md` 原文（「Reviews executed: 6 / Successful: 1 / Failed: 5 / BLOCKING Issues: 0 → "No BLOCKING or CRITICAL issues found"」——**失败计净**）+ `parallel_dispatch.py:305-333/336+`（consolidate 语义根）；`adjudications/adjudication-010.md`（历史前科自认：并行评审写层 no_files_parsed 丢 5/6 产物，52 份审计人工从 diagnostics 信封抢救落盘）。

**触及的不变量维度**：无（修复的是审计层自身覆盖正确性——不新增叙事维度门检；全维度审计有效性间接受益）

---

## 0. 根因

**spec #72 T9 的 cluster dispatch 只扩了产物面没扩输入面与收口面**：「ONE prompt per skill covers the bundle」把 writes 扩到 `{N+1}`，但契约 reads、shared 缓存、checklist 预计算、consolidation glob、revision 路由全部停留在单章语义。净效果三层：(1) follower 章被**盲派发**——LLM 无正文无预计算，行为分流为拒绝（BLOCKING 派发完整性）/占位（待补·不适用）/**编造通过**（附条件·计划级预核对·暂记）/看似正常分数四种形态；(2) 四种形态均以「成功派发」身份落盘（步骤标 done、不重试），编造通过还污染 cascade 连跳基线（`should_skip_audit` `chapter_loop.py:691-721` 只吃 passed bool）；(3) 即使报告带 BLOCKING，收口/路由四处 anchor-only，**零消费面**。对以「审计门是资产」立身的体系，双章批下 core-circle 审计覆盖率实测 ~46% 且全程静默——这是正确性级空洞，非调参问题。

**既有覆盖面清点（r2，#105 交叠入账）**：`check_audit_dispatch_integrity`（`llm_output_integrity.py:376-395`）已在 write 路径对**每个**审计写文件（含 follower 文件）运行（`dispatch_helper.py:2982-2992`），vol1 回放 108/108 真阳——**拒绝形已拦**；但占位形/编造通过形零覆盖（`check_audit_completeness` 只查判定 marker 存在，「待补」「通过」都是合法 marker），且 **wave 路径无 G4 消费点**（findings 进 `.integrity-findings-{n}.jsonl` 期刊——serial 侧 `g4_post_write_integrity` 读它，wave 侧无人消费）。T4 是该族的**词族扩面+第三态+wave 消费点**，非从零新建。

**用户裁定（2026-11-15，r2/r3 维持）**：不考虑在飞项目——vol1 存量饿死审计不回补不清洗（历史章补评属维护命令口径，若需要走 #106 T3 resonance-backfill 同款先例另议）；本件只修机制，旧 bundle 形态项目续跑时由新收口面如实报告 follower 缺口（只报不写）。

**备选案已评估并否决（r2 复核维持）**：「废除 bundle 改单章派发」——批粒度本身是 #101 预留候选的用户决策面（容量证据在册），本件以「bundle 保留、reads/组装/收口对称化」为最小正确修，不预裁批粒度；「并入 #105 T3 派发预检」——#105 预检的是**文件在盘否**（`missing_audit_reads` 存在性语义，chapter-26.md 在盘→预检通过→仍饿死），与本件的**契约声明面缺口**不同层，合并会互相稀释判据（r2 驳斥独立复核成立）。cursor 跳跃 `chapter + len(bundle_chapters)`（`:2495`）——follower 永无自己的 anchor 回合，leader 侧收口是唯一收口位（T3 必要性论据）。

## 1. 任务分解

### T1 · 契约 reads 对称化（含预检兼容）
- 六技能（group-craft/-plan/-factual/-character、review-resonance、review-sensitivity）reads 补 `chapters/chapter-{N+1}.md`；读 plans 的技能补 `plans/chapter-{N+1}-plan.md`；factual 族按其真实消费面裁定（world-rules 审计读 plans 与否以 SKILL 正文为准，不虚增）；
- **全文形声明（a2 约束）**：follower 正文读用 plain path 形（`chapters/chapter-{N+1}.md`），**禁 dict-form fields 形**——fields 过滤层有把正文滤掉的前科（resonance canary 事故：fields 过滤曾致全章 resonance_pending）；
- **预检兼容（a1 约束，必修）**：`missing_audit_reads._resolve`（`audit_layer.py:328-331`）为朴素 `str.replace("chapter-N", …)`，不识别 `{N+1}`——`chapters/chapter-{N+1}.md` 不含子串 `chapter-N`，probe 落字面花括号路径（磁盘永不存在）→ 每个 bundle wave 在 `chapter_loop.py:4117-4129` ESCALATION 停摆。须同批改 `_resolve` 学 offset 解析（或复用 `resolve_chapter_path`）+ 红测（构造带 `{N+1}` reads 的契约 fixture，断言预检不误报缺失）；
- **offset reads 的 wave 条件语义（设计审查 C1，必修）**：`{N+1}` 类 offset reads 解析后**当且仅当 n+1 ∈ wave_chapters 时为必需**——`bundle_chapters`（`chapter_loop.py:1510-1528`）在无 volume_map、span 末章（卷尾）、span 未覆盖三种形态返回 singleton `[chapter]`，此时 `{N+1}` reads 探测到未起草的下一章必然缺失 → 预检硬停。预检与 T2 manifest 断言两处同语义（singleton 波 follower 条目合法缺席）；红测须含 singleton fixture（无 volume_map 与 span 末章两形态）断言不误报不停摆；
- **契约升级纪律声明（C1 连带，AGENTS.md Contract-upgrade discipline）**：本批为 resumable 在飞项目新增由硬门（预检）执法的必需 reads——**声明「no existing artifacts affected」的论证**：bundle 项目的 follower 章正文由双章起草先行必然在盘（预检波内不缺失）；singleton 波 offset reads 按 wave 条件语义跳过探测；旧契约下的已完产物不受回溯执法；
- `lint_registry_reconcile`/`lint_decisions_sources` 对账面同步（#90 单源机制现成，契约改动自动纳入）；契约 reads 改动必触 `deps.json` 等生成物再生（改契约源头 + `just generate`，幂等 diff；禁手改生成物）与 `just lint-contracts` 面。

**判据**：**契约测试断言**（非裸 grep——writes 区今日已含 `{N+1}`，裸 grep 先于改造即通过）：`load_contract(<六技能>)` 的 reads 含 `chapters/chapter-{N+1}.md`（读 plans 者另含 `plans/chapter-{N+1}-plan.md`）；`just check` 契约对账绿（含 `just generate` 幂等 diff）；预检回归测试绿（a1 红测转绿 + singleton 两形态红测转绿）。

### T2 · 派发组装双章化
- `build_shared_audit_context` 改造为 bundle 语义（接受 chapters 列表或 wave 侧对 bundle 逐章构造再合并——`chapter_loop.py:4067` 单点；drafting 侧 per-n 双章 context 先例 `:4001-4004` 可循）；chapter_text/raw_files/checklist 派生源覆盖 follower；
- `generate_review_checklist` 双章产出（两块 `审查参考数据` 或单块 chapters 数组——plan 期按 prompt 模板定形，`review_checklist.py:197-240` 注入点适配）；reads manifest 须含 follower 章正文条目——派发组装层 `resolve_or_skip_ctx → resolve_contract_path`（`contracts/paths.py:109-204`，`_FAMILY_N_OFFSET`+`_offset_sub`）**原生支持 `{N+1}` 全文读**（T1 契约一改 manifest 自动含 follower 条目，无需新解析器）；双章 checklist 同步消 ch45 形「数据未注入」节段饿死（anchor 章缺预计算注入面）；
- **主防线断言（M2 执行位置）**：reads manifest 含 follower 章 path 是本 spec 的第一道硬闸——执行链三层：契约声明（T1）→ **预检硬门**（a1 修后的 wave 条件语义：n+1 ∈ wave_chapters 且 follower 章缺失 → 派发前 ESCALATION，生产回归兜底）→ 测试断言（fixture dry-run blob 级，护实现形态）；singleton 波 follower 条目合法缺席（C1 语义）。（c 项博弈路径的对策锚点——词族可绕，输入断言不可绕）。

**判据**：构造双章 fixture dry-run（`--dry-run` 或单测直调 build_skill_prompt）：prompt 内 `chapter-{N+1}.md` 正文与两章预计算块均在（blob 级断言）；reads manifest 含 follower 章 path。

### T3 · 收口/路由 per-n 消费面
- wave 路径对 bundle 每个 n 各跑：consolidation 文件扫（glob `chapter-{n}-*.md`）+ `route_revision_after_resonance(state, project_dir, n)` + blocking_found 写入各 n 的 ChapterState（`:4226-4234/:4258-4271/:4321` 三点对称化；serial 收口环 `:4938-4943` 的 per-n 语义以 wave 等价物复活）；
- **复扫面裁定（钉死：不纳入）**：`run_audit_layer` 会重新派发 genre/boundary 审计（`audit_layer.py:231-274`，wave 2 已派发过→每 bundle 重复派发）且其约定路径扫描对 grouped 技能是 phantom（`audit_report_paths` 文档自证）——wave 侧 per-n 收口**复用 wave 任务路径集/consolidation 面**，不调 `run_audit_layer` 复扫（d1/d2 对策）；
- **传感器换装（f 约束，必修）**：`:4266-4271` 磁盘兜底查字面 `"## BLOCKING Issues"` H2——588 份维度报告实测零含该串（精确 H2 仅 6 份 summary 独有），该析取支恒假；per-n 化的同时换 `_BLOCKING_MARKER_RE`/`build_consolidator_sensors` 单源传感器，否则 per-n 漏报×2；
- review-summary：per-n 双写或单文件双节（含 bundle 披露行）。

**判据**：红测——构造 follower 章审计含 `[BLOCKING]` 的 fixture 项目跑 wave 收口：该 n 的 `audit_results["blocking_found"]=True` 且路由触发；`git grep` 证明三点不再 anchor-only；传感器单测（维度报告 BLOCKING 标记 → blocking_found=True）。

### T4 · 占位/失败判定语义拆分
- 新校验（`llm_output_integrity` 族，#105 T2 同侧扩展位——`check_audit_dispatch_integrity` 拒绝形已拦，本任务扩占位/编造通过形）：审计产物**判定行**（锚定形态以附录 A 脚本 `VERDICT_LINE` 正则为准：行首粗体 `**判定**：`、只评估捕获值段）命中饿死形态词族 → 产物判 **invalid**（非 pass 非 fail 的第三态），G4 FAIL 附「输入缺口——不得出具判定」重派指引；**生产门锚定=全部判定行值段**（设计审查 I1：ch45 形饿死标记在第 8 判定行、ch49 在非判定行——首行语义对第五缺陷类零检出；全判定行值段扫描对 6 份合法奇数文件实测零误伤[ch9 假阳在散文行非判定行]，plan 期以红测钉死）；**回放比对口径=首锚定行语义不变**（基线 47/85 的可比性锚）；**词族单源（erratum+I2）**：生产门词族=`NARROW6 ∪ T4_VARIANTS`（变体含「数据未注入」），回放比对口径=`NARROW6`/`WIDE12`——常量**落位 `src/shenbi/`**（如 `pipeline/llm_output_integrity.py` 或新 `audit_starve_family.py`，plan 期定），`tools/audit_starve_baseline.py` 改为 import 自 src（tools→src 与全仓方向一致；pyproject 仅打包 src/shenbi，禁 src→tools 反向依赖首例），**值不变 manifest 不变**，禁散文列举/禁另写词表；无冒号变体形（`判定为 …`）是否入锚 plan 期以实测裁定（基线口径不含）；
- 词族可绕（实弹样本「暂记 85/100 通过」在窄词族外）——**词族是发生率压减器不是防线**，防线=T2 reads manifest 断言（spec 级声明）；
- `_wave_audit_entry`（`chapter_loop.py:3075-3091`，resonance_pending 第三态 entry 先例直接仿写）加 valid 维度：cascade streak 与 `should_skip_audit`（`:691-721`）只数 valid-pass；invalid 产物所属步骤不当 done（`:4241-4252` except-failed 语义保留，invalid 等位处理）；
- review-summary 语义修正：Failed>0 或存在 invalid 产物时，**禁止**输出「No BLOCKING or CRITICAL issues found」净结论——代之以显式缺口披露行（`parallel_dispatch.py` consolidate 的 cascade_skipped 披露行+failed_count 统计为现成模板与改造点）；
- **差分回放（验收#2 面）**：以附录 A 脚本判据对 vol1 全量 audits 回放新校验器，产出 invalid 清单与基线一致性报告（只报不写）。**定界（设计审查 I3/M1/M4）**：回放=plan 期**离线仲裁**（人工跑脚本+`--verify-manifest`，语料 gitignored 不入 CI；T4 红测用构造 fixture——G0.9 结构性输入豁免）；生产配置（`NARROW6∪T4_VARIANTS`×全判定行）计数**只报告不设阈值**（基线可比口径=窄6/扩12×首锚定行）；**差分回放零意外是 FAIL 门合入的前置**（时序条款——先校准后执法）。

**判据**：红测三条（`判定: 通过（附条件）`+饿死标记→invalid；`Successful:1/Failed:5`→summary 含缺口披露行；invalid 不进 cascade streak——`should_skip_audit` 单测）；回放报告计数与附录 A 基线一致。

### T5 · resume 补跑证明
- resume 路径对 bundle 内 follower 缺产物/invalid 的审计步骤实际重派——`_filter_completed_audit_tasks` 文件存在性过滤（`chapter_loop.py:393-399`）对 invalid 形态产物不视为完成（配合 T4 invalid 标记）；步骤 done 面（`:4250-4252` 只排除 `result.success==False`）同步 invalid 感知——invalid-but-successful 产物既不重派也不阻止 done 的洞须闭合；
- 构造 mid-wave crash + follower 缺产 fixture：重放后 follower 审计补跑且带全输入。

**判据**：crash-replay 集成测试（follower 报告缺→重派→产物 valid）；`git grep` invalid 感知过滤证明（存在性过滤+done 面两处）。

## 2. 验收
1. T1-T5 判据全绿；
2. 差分回放（**仲裁器=附录 A 脚本，离线仲裁**）：对 vol1 audits 语料（`--verify-manifest d9a1b5f0…f5c2` 通过）跑 T4 新校验器，invalid 清单计数与附录 A 基线一致——判定行口径 47@窄6/85@扩12（全偶数章）、文件级 114/157、verdict_pass 偶数位 23/24（编造通过）；词族口径=常量单源（落位 src，禁散文词表，erratum+I2）——**首次体系能看见这个洞**；
3. bug-hunt：五饿死形态均被覆盖——拒绝/占位/编造通过由 T4 判定行拦截；看似正常分数由 T2 输入断言拦；**第五形态「数据未注入」节段饿死**：判定行形（ch45 形）由 T4 全判定行值段红测拦、非判定行提及形（ch49 形）由 T2 双章 checklist 预防（检测面显式为零，设计审查 I1）；follower BLOCKING 触发修订路由（T3）；
4. 双章 fixture dry-run 全链：prompt 双章输入（blob 断言）→ 产物 valid → 收口双章各得路由记录；
5. T2 生成测试 ≥94（双章审计产物质量）。

## 3. 风险
- wave prompt 尺寸上升（双章正文+双 checklist ≈ +40-60% 审计 prompt；按 vol1 审计族 27% 调用/16.7% 成本面估算全链 +7-10%——预算核算入 plan，超预算时按 #95 T3③ 降级序处置）；**b 项**：今日 review 技能无 `SKILL_TOTAL_CHAR_BUDGET` 条目（仅 state-settling 72k）截断不可触发，但 plan 期一旦配预算，`_enforce_skill_total_budget` 保头截尾会把 reads 段尾部的 follower 正文/第二 checklist 块最先进截断窗（F3 形态复发）——配预算与 follower 输入断言须同批（断言在截断后仍须成立）；
- 与 #105/#106 同文件（chapter_loop/parallel_dispatch/revision_router）——施工序 #105 → #106 → #109 已满足（两前序已合入）；SKILL 契约改动与 #102（drafting sidecar 面）不同文件、与 #96（review_checklist 预计算面）共享 `review_checklist.py`——**裁定：#109 按文件序队头先行（INDEX 文件序权威），review_checklist.py 冲突登记，后执行者 #96 plan 期 re-anchor**（v6.1 资源冲突条款；#109 施工期间 #96 未启动，无在飞冲突）；
- 占位词族误伤（正文合法讨论「待补」语义）——校验只锚**判定行**形态（附录 A 首锚定行语义），散文提及豁免（#105 T2 同款口径）；变体扩充（待核/暂记/数据未注入）以判定行值段为界，不外溢到散文；
- #101 批粒度裁定时若改单章批，T2/T3 的 bundle 逻辑仍以「bundle=N 单章」退化成立——设计按 chapters 列表参数化，不绑死 2。

## 附录 A · 计数基线仲裁器（r3，唯一权威）

**脚本**：`tools/audit_starve_baseline.py`（随本 spec 同批入库；纯读）。语料规则=破折号形维度报告 `chapter-<N>-<dim>.md` 排除 review-summary（侧表不计入：25 份 review-summary、14 份 aggregate、21 份其他）。判定行语义=行首粗体 `**判定**：`、**每文件首锚定行**、只评估捕获值段（散文同行假阳类[ch9 形]与无冒号变体[判定为]不入锚）。**基线值=脚本输出，散文不复述**——本 spec 正文中的数字仅为脚本 2026-11-18 于语料 manifest `d9a1b5f011127306bd38d2cdfe17c4571fc09c9fb402d1a7056f6ef9ae20f5c2` 上的产出快照，任何复算以重跑脚本为准（manifest 不符=语料漂移，须重新钉基线后方可仲裁）。**单源条款（erratum+设计审查 I1/I2 收口）**：词族常量（`NARROW6`/`WIDE12`/`T4_VARIANTS`）与判定行正则的**家=src/shenbi**（T4 落地时迁入，值不变 manifest 不变），脚本 import 自 src（tools→src 方向）；**双锚定合法**——基线/回放比对=首锚定行语义（可比性锚），生产门=全部判定行值段（第五缺陷类检出），两锚共用同一正则、以「取首行」/「取全部」两种消费形态区分，禁第三种锚定形态。
