# Spec #105 · 审计发现契约硬化（audit-finding-contract）：severity 词表单源（对齐登记域）六传感换装、词表外 fail-loud、派发完整性语义拆分、聚合条目级 severity 与反馈格式缺口清偿

**日期**：2026-11-15｜ **系列**：评审工艺批（review-craft）｜ **状态**：Design（**r2，2026-11-15 Revised**——价值门驳斥五问修正：T1 改道对齐 enums.Severity 登记域+收编第六消费点/T2 双正则语义显式拆分+generic 分支接线/T3 补 #51 控制流先例/T4 ending 面修入本件+渲染变更同步 longitudinal parser/机械漂移修正）｜ **优先级**：🟠 P1
**动机证据**：`src/shenbi/pipeline/revision_router.py:127-146`（路由只认 BLOCKING/CRITICAL 两档三形态正则）+ `:371-406`（collect_audit_issues if/elif **无 else 分支**——词表外严重度词不命中任一正则即贡献 0 条；机制证实，vol1 613 份 audits + fixtures grep `MAJOR|BLOCKER|[HIGH]|严重度:高` 零实弹命中——**T2 定位为预防性硬化**）；`src/shenbi/pipeline/audit_aggregate.py:37`（_SEV_WORDS=BLOCKING|CRITICAL|MINOR|WARNING|ERROR 五词——与路由词表分家）+ `:167-175`（render_aggregate 条目 `- {u.text}` **不带逐条 severity**——FindingUnit.severity 数据在渲染面丢失，修订技能只见节标题）；`src/shenbi/pipeline/chapter_loop.py:672-683`（_BLOCKING_MARKER_RE **第三套词表**：另收 FAIL 标题/表格粗体形）+ `src/shenbi/pipeline/parallel_dispatch.py:373-386`（第四套：尾巴从 router 导入、主干复制）+ `src/shenbi/pipeline/audit_layer.py:38`（_ERROR_LABEL_RE 裸子串第五套）+ **`tools/report_longitudinal.py:558`（第六套：节头正则 `^## (BLOCKING|CRITICAL|WARNING|ERROR) Findings` 缺 MINOR——render 顺序 MINOR 在 WARNING/ERROR 前，解析遇 MINOR 节即 break，MINOR/WARNING/ERROR 三节静默丢弃=纵向报告腐化；`:525-544` merge_units 复刻聚合去重循环）**；`src/shenbi/contracts/enums.py:9`（**已存在 `Severity = Literal["BLOCKING","CRITICAL","MINOR"]` 单源**）+ `docs/framework/status-vocab.md:21`（AuditSeverity 域已登记且**声称**消费点=escalation 路由 revision_router.py、parallel_dispatch.py——实测两文件零 import，**登记表死线**：比「散布五处」更强的根因证据，r1 漏认）；`novel-xinghuo-vol1/audits/chapter-40-reader-pull.md:44`（实弹：`- [BLOCKING] 派发完整性：请补齐 chapters/chapter-40.md…`——**基础设施失败与正文缺陷共用 BLOCKING 词**，污染 blocking_found/escalation 频次统计）；`src/shenbi/pipeline/dispatch_helper.py:612-624`（_resolve_read_with_fallback 缺 read 返回 `[]`——**缺失输入静默从 prompt 消失**，无预检无 fail-loud）；`src/shenbi/pipeline/chapter_loop.py:3836-3862`（**#51 ghost-chain guard 控制流先例**：draft-consuming 技能派发前存在性预检→不派发→escalation checkpoint——T3 是该守卫对审计技能+contract required reads 全清单的泛化）；`src/shenbi/gates/g4/generic.py:239-260`（审计产物 G4 校验现成挂点；**:252 G4.av. 分支现绑 check_audit_line_refs——新增 G4.av.vocab 须扩此分支**，否则 pwi 复核判 stale 静默吞）+ `src/shenbi/pipeline/llm_output_integrity.py`（同侧扩展位——现有六 check 同构惯例：模式列表+预编译+`G4.<group>.<rule>` issue）；`src/shenbi/pipeline/chapter_loop.py:882`（G4_FORMAT_EXAMPLES **19 键**）——grep `scene_budget` 全文件零命中；`novel-xinghuo-vol1/adjudications/escalation-35-report.md:33-37`（实弹照录 `G4.cp.scene_budget:…` + `(请重新生成此检查的输出以达到标准格式)` 零信息兜底行；#114 记载 scene_budget 跨 ch5/35/39 三次三振非孤例）；`src/shenbi/pipeline/review_checklist.py:539-544`（ending_constraints 实注入 **3 章**：`range(3,0,-1)`+`chapter < 4` 守卫）vs `skills/shenbi-review-group-craft/SKILL.md:166`（自称「近 10 章收尾型历史」——**文档对模型撒谎**；escalation-35-report.md:95 实弹 `ending_constraints | cliffhanger, cliffhanger, other` 恰 3 项佐证）。

**触及的不变量维度**：无（审计发现契约基建——新 check id `G4.av.vocab` 为审计产物有效性门【G4.av 族第二员，既有 G4.av.stale_line_ref】，不挂叙事维度；P2 期 check-id 普查面自然覆盖）

---

## 0. 根因

**审计契约是文档约定不是数据契约**：severity 语义散布**六处**手拼正则（词表/形态各不相同），且**已登记的单源（enums.Severity）零消费**——status-vocab.md 声称 router/parallel_dispatch 消费、实测两文件零 import，登记与现实脱节；LLM 审计产物靠正则反解析散文——每多一种报告写法就要多一条正则尾巴，词表外写法静默丢包；BLOCKING 一词承载两种语义（内容缺陷 vs 派发事故）；聚合渲染丢条目级 severity（且纵向 parser 因 MINOR 缺词丢弃后三节）；重派反馈对部分 G4 族只有零信息兜底行。净效果：**路由面的真值依赖审计员的格式纪律，而格式纪律本身无人把关**。

**用户裁定（2026-11-15）**：不考虑在飞项目——本件不含存量 audits 清洗工具；新校验器对既有项目的存量审计文件不回溯改写（回放校验仅出报告，见 §2）。

**备选案已评估并否决**：「severity 词表扩 MAJOR 第四档」——词表扩张面=24 份 review SKILL 词表节+全部消费正则+聚合，先 fail-loud 杀静默丢包、CRITICAL/MINOR 使用分布数据后再议中间档；「审计产物全面结构化（finding() 发射器落 LLM 面）」——#88 单源目标在机器面尚有 ~420 处手拼未清偿，LLM 面全面 JSON 化是大破面，本件先做词表单源+fail-loud 最小核；「平行新造第三 severity 常量族」——r2 改道否决：enums.Severity 登记域已存在（spec #34 纪律：新状态域必须先在登记表立域再落定义），单源模块必须从该域派生并对齐，不得另起炉灶。

## 1. 任务分解

### T1 · severity 词表与传感正则单源化（对齐 enums.Severity 登记域）
- **前置（spec #34 纪律——先改登记表再落码）**：`docs/framework/status-vocab.md` AuditSeverity 域行修订——显式拆两列声明：**RoutingTiers**（BLOCKING/CRITICAL，legacy `[ERROR]` 硬档别名）与 **AggregateVocab**（BLOCKING/CRITICAL/MINOR/WARNING/ERROR——WARNING/ERROR 为聚合面 legacy 词）；消费点声明修真（六消费点换装后实际 import 单源）
- 新 `src/shenbi/contracts/severity.py`：**从 `enums.Severity` import 派生**（Literal 值元组化+legacy 词扩展），`ROUTING_TIERS`/`AGGREGATE_VOCAB` 常量 + 四锚定形态（bracket/bold/cell/key）编译正则单源 + 既有三尾巴（`_SEV_ENUM_TAIL`/`NEGATION_PAYLOAD_TAIL`/`QUOTED_VALUE_TAIL`）迁入；
- **六消费点换装**：revision_router（路由双正则）、chapter_loop `_BLOCKING_MARKER_RE`、parallel_dispatch consolidator、audit_layer `_ERROR_LABEL_RE`、audit_aggregate 锚定形族、**tools/report_longitudinal.py `:558` 节头正则（连带修 MINOR 缺词分家——MINOR 节不再中断解析）**——全部 import 单源符号；
- AST lint（#88 check_id 单源/#91 比较侧守卫先例，`_pattern_arg` 只认 ast.Constant 字面量的既定强度即可）：severity 词交替字面量的 `re.compile` 仅允许出现在单源模块（扫描域 `src/shenbi/pipeline`+`src/shenbi/contracts`+`tools`），别处出现即 lint FAIL。

**判据**：`git grep -nE "BLOCKING\|CRITICAL" -- src/shenbi/pipeline tools/ | grep -E "re\.compile|_RE ="` 正则字面量仅命中 contracts/severity.py；六消费点 import 证明；**行为保持差分**——对 tests/fixtures 全量真实审计产物回放，路由 issues/聚合 FindingUnit 计数与换装前**逐项一致**（差分基线先冻结，#99 先例+tools/gen_provenance_baseline.py 基建）；AST lint 红测（新手拼正则→FAIL）。**已知豁免口（对抗回放 ④ b 承认）**：四锚定形态外的第五形态（圆括号/callout 等）不在传感域——SKILL 模板锚定 bracket 形态是现行纪律面，本件不扩张形态域。

### T2 · 词表外 fail-loud（G4.av.vocab）
- `llm_output_integrity.check_audit_severity_vocab(content)`：**校验正则与传感正则语义显式分离**——传感正则（T1）= 词表内锚定计数；校验正则（本 task）= **形态槽位通配捕获**（bracket `- [(\S+?)]`/bold `\*\*(\S+?)\*\*` 行锚定/cell `\|\s*(\S+?)\s*\|`/key `(?:severity|严重度)\W{0,6}(\S+)`）后查表 AGGREGATE_VOCAB——词表外即违规。**禁止从传感正则推导校验正则**（传感正则只捕词表内词，复用则 fail-loud 永不触发——r1 最大实施歧义，r2 钉死）；
- 锚定形态行所载 severity 词 ∉ AGGREGATE_VOCAB → 违规条目（如 `- [MAJOR]…`/`**BLOCKER**`/`严重度: 严重`/`严重度: 高`——**中英双红测**）；散文提及（非锚定形）不报；
- 接线 `gates/g4/generic.py:239-260` 审计产物校验位：违规 → G4 FAIL + 重写指引文案（「词表外严重度：用 BLOCKING/CRITICAL/MINOR 重写本条」）；**generic.py:252 G4.av. 分支扩展**——vocab 规则的 pwi 复核路由（不扩则新 finding 被 pwi 判 stale 静默吞）。

**判据**：红测四条（`- [MAJOR] x`→FAIL／`**BLOCKER**`→FAIL／`严重度: 严重`→FAIL／`严重度: 高`→FAIL）；绿测（`[MINOR]`→PASS／prose "major"→PASS）；对 vol1 存量 audits 回放新校验器出报告（命中数与清洗清单，不自动改写）。

### T3 · 派发完整性语义拆分
- **框架前置预检**（控制流先例=#51 ghost-chain guard `chapter_loop.py:3836-3862`：派发前存在性预检→不派发→escalation checkpoint；reads 可用性语义先例=escalation reads 三态判定 `revision_router.py:268-303`：OPTIONAL_READS fnmatch 剔除/本技能 writes-updates 剔除/glob 展开/存在性）：审计技能派发前确定性校验 contract required reads 存在；缺失 → 走既有 dispatch failure 路径（retry/escalation），**不派发 LLM**——「输入缺失」从 LLM 的 BLOCKING 语义域里整体消失（修 dispatch_helper `_resolve_read_with_fallback:612-624` 缺 read 静默返回 [] 的吞输入面）；
- G4 侧兜底规则（**次防线定位**——主防线框架预检不依赖措辞；兜底 pattern 本身是又一则手拼匹配，措辞改写（如「无法访问输入文件」）可绕，对抗回放 ④ c 承认）：审计报告中 payload 匹配派发完整性模式（`派发完整性|请补齐|输入缺失`）的 BLOCKING 条目 → 报告判无效 FAIL（该形态出现即派发完整性 bug，须修框架不应由审计员表达）。

**判据**：红测——审计派发时 chapter 文件缺失 → 派发失败（零 API 调用、零审计产物落盘、走 retry 路径；红测基建先例 `tests/pipeline/test_redispatch_g4_and_draft_precheck.py:106` `_must_not_dispatch` 同构）；含「派发完整性」payload 的 BLOCKING 报告 → G4 FAIL。

### T4 · 反馈与聚合卫生（写作端）
- G4_FORMAT_EXAMPLES（**19 键**）补缺族：盘点 g4 checker 名册 vs EXAMPLES 键差集（一次性 diff 入 plan），首批补 `G4.cp.scene_budget`（示例文案取该 checker 失败消息期望格式——escalation-35-report.md:33-37 实弹兜底行对照）；
- aggregate 渲染条目携带 severity（`- **{sev}** · {text}` 形态——节标题保留，条目级不再依赖继承）；**同步改 `tools/report_longitudinal.py` `_parse_aggregate_sections:547-567`**（条目解析剥离 severity 前缀+节头正则单源化已含 MINOR 修复）；下游消费差分验证（grep `.aggregate.md` 全消费面）；
- ending_constraints 注入窗口 3→10 章（`review_checklist.py:539-544`：`range(3,0,-1)`→`range(10,0,-1)` + **连带** `chapter < 4`→`chapter < 11` + docstring「last 3 chapters」/注释同步；纯 regex 分类零 LLM 成本），消灭 SKILL.md:166 文档/实现漂移——「连续≥3 章同型收尾」规则在 10 章窗内才有意义。**r2 顺序裁定：本面修入本件执行范围**——原 r1「review_checklist.py 面在 #96 后」经核为批次文件面纪律（spec96 全文零命中 ending_constraints/收尾型，其 review_checklist 面为 paragraph_cv/transition_count/ai_marker_hits 预计算，零逻辑重叠）；PR #349 重排后 #105 队头/#96 第 14 位+SDD 串行纪律下无并发面；且验收 1 要求 T1-T4 全绿——顺延将留 SKILL.md:166 对模型撒谎 13 个队列位。#96 施工时按其 §121 re-anchor 规约处理。

**判据**：`git grep -n "scene_budget" src/shenbi/pipeline/chapter_loop.py` 命中 EXAMPLES；aggregate 渲染含条目级 severity（红绿测试）；longitudinal parser 新格式红绿（含 MINOR 节不再中断）；注入块 ending_constraints 长度=10（SKILL 文案零改动即重新为真）。

## 2. 验收
1. T1-T4 判据全绿；
2. 差分基线：换装前后对 fixtures 全量审计产物，路由/聚合输出逐项一致；
3. bug-hunt：词表外 finding（MAJOR/BLOCKER/严重/高）均被 T2 门拦（机制对照=现状 elif 静默丢包）；输入缺失场景走框架失败路径不再产 LLM BLOCKING；
4. T1 生成测试 ≥94（单源模块重构质量）。

## 3. 风险
- 六传感换装行为漂移 → 差分基线先行 + 逐项一致红测（最大风险面，T1 判据钉死）；
- T2 对存量报告误伤 → 只校锚定形态（散文提及豁免）+ 回放报告先行；
- T2 校验正则形态槽位过宽（cell 形 `| x |` 误捕非 severity 单元格）→ 判据绿测含表格非 severity cell 不报 case；误报处置=回放报告零误伤后接 G4 FAIL（shadow 先行）；
- T3 预检误判（glob/可选读）→ 复用 escalation reads 可用性三态判定既有逻辑（OPTIONAL_READS/produces/glob 展开）；
- **共享文件面**：revision_router.py/chapter_loop.py 与 #106 同文件（**#105 先施工**，#106 plan 首步 re-anchor）；dispatch_helper.py 预检面 #92 已归档（1ff91d2d 仅 load_deps 换装 5 行，无冲突面）；review_checklist.py ending 面**r2 修入本件**（裁定理由见 T4，#96 后续 re-anchor）。
