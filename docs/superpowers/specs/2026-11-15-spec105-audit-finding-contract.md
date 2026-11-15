# Spec #105 · 审计发现契约硬化（audit-finding-contract）：severity 词表单源五传感换装、词表外 fail-loud、派发完整性语义拆分、聚合条目级 severity 与反馈格式缺口清偿

**日期**：2026-11-15｜ **系列**：评审工艺批（review-craft）｜ **状态**：Design（r1，2026-11-15）｜ **优先级**：🟠 P1
**动机证据**：`src/shenbi/pipeline/revision_router.py:127-146`（路由只认 BLOCKING/CRITICAL 两档三形态正则）+ `:371-406`（collect_audit_issues 不命中即贡献 0 条——**词表外严重度词对路由静默丢包**）；`src/shenbi/pipeline/audit_aggregate.py:37`（_SEV_WORDS=BLOCKING|CRITICAL|MINOR|WARNING|ERROR 五词——与路由词表分家）+ `:167-175`（render_aggregate 条目 `- {u.text}` **不带逐条 severity**——FindingUnit.severity 数据在渲染面丢失，修订技能只见节标题）；`src/shenbi/pipeline/chapter_loop.py:672-683`（_BLOCKING_MARKER_RE **第三套词表**：另收 FAIL 标题/表格粗体形）+ `src/shenbi/pipeline/parallel_dispatch.py:373-386`（第四套：尾巴从 router 导入、主干复制）+ `src/shenbi/pipeline/audit_layer.py:38`（_ERROR_LABEL_RE 裸子串第五套）；`novel-xinghuo-vol1/audits/chapter-40-reader-pull.md:44`（实弹：`- [BLOCKING] 派发完整性：请补齐 chapters/chapter-40.md…`——**基础设施失败与正文缺陷共用 BLOCKING 词**，污染 blocking_found/escalation 频次统计）；`src/shenbi/gates/g4/generic.py:239-260`（check_audit_completeness/check_audit_line_refs——审计产物 G4 校验现成挂点）+ `src/shenbi/pipeline/llm_output_integrity.py`（同侧扩展位）；`src/shenbi/pipeline/chapter_loop.py:882`（G4_FORMAT_EXAMPLES 23 族）——grep `scene_budget` 全文件零命中（escalation-35-report 实弹照录该族泛化兜底行）；`src/shenbi/pipeline/review_checklist.py:539-544`（ending_constraints 实注入 **3 章**）vs `skills/shenbi-review-group-craft/SKILL.md:166`（自称「近 10 章收尾型历史」——**文档对模型撒谎**）。

**触及的不变量维度**：无（审计发现契约基建——新 check id 族 G4.av.* 为审计产物有效性门，不挂叙事维度；P2 期 check-id 普查面自然覆盖）

---

## 0. 根因

**审计契约是文档约定不是数据契约**：severity 语义散布五处手拼正则（词表/形态各不相同），LLM 审计产物靠正则反解析散文——每多一种报告写法就要多一条正则尾巴，词表外写法静默丢包；BLOCKING 一词承载两种语义（内容缺陷 vs 派发事故）；聚合渲染丢条目级 severity；重派反馈对部分 G4 族只有零信息兜底行。净效果：**路由面的真值依赖审计员的格式纪律，而格式纪律本身无人把关**。

**用户裁定（2026-11-15）**：不考虑在飞项目——本件不含存量 audits 清洗工具；新校验器对既有项目的存量审计文件不回溯改写（回放校验仅出报告，见 §2）。

**备选案已评估并否决**：「severity 词表扩 MAJOR 第四档」——词表扩张面=24 份 review SKILL 词表节+全部消费正则+聚合，先 fail-loud 杀静默丢包、CRITICAL/MINOR 使用分布数据后再议中间档；「审计产物全面结构化（finding() 发射器落 LLM 面）」——#88 单源目标在机器面尚有 ~420 处手拼未清偿，LLM 面全面 JSON 化是大破面，本件先做词表单源+fail-loud 最小核。

## 1. 任务分解

### T1 · severity 词表与传感正则单源化
- 新 `src/shenbi/contracts/severity.py`：`ROUTING_TIERS`/`AGGREGATE_VOCAB` 常量 + 四锚定形态（bracket/bold/cell/key）编译正则单源 + 既有三尾巴（`_SEV_ENUM_TAIL`/`NEGATION_PAYLOAD_TAIL`/`QUOTED_VALUE_TAIL`）迁入；
- 五消费点换装：revision_router（路由双正则）、chapter_loop `_BLOCKING_MARKER_RE`、parallel_dispatch consolidator、audit_layer `_ERROR_LABEL_RE`、audit_aggregate 锚定形族——全部 import 单源符号；
- AST lint（#88 check_id 单源/#91 比较侧守卫先例）：severity 词交替字面量的 `re.compile` 仅允许出现在单源模块，别处出现即 lint FAIL。

**判据**：`git grep -n "BLOCKING|CRITICAL" src/shenbi/pipeline/` 正则字面量仅命中 contracts/severity.py；五消费点 import 证明；**行为保持差分**——对 tests/fixtures 全量真实审计产物回放，路由 issues/聚合 FindingUnit 计数与换装前**逐项一致**（差分基线先冻结，#99 先例）；AST lint 红测（新手拼正则→FAIL）。

### T2 · 词表外 fail-loud（G4.av.vocab）
- `llm_output_integrity.check_audit_severity_vocab(content)`：锚定形态行（bracket/bold/cell/key 四形之一）所载 severity 词 ∉ AGGREGATE_VOCAB → 违规条目（如 `- [MAJOR]…`/`**BLOCKER**`/`严重度: 严重`）；散文提及（非锚定形）不报；
- 接线 `gates/g4/generic.py` 审计产物校验位（:239-260 侧）：违规 → G4 FAIL + 重写指引文案（「词表外严重度：用 BLOCKING/CRITICAL/MINOR 重写本条」）——静默丢包变门检拦截。

**判据**：红测三条（`- [MAJOR] x`→FAIL／`**BLOCKER**`→FAIL／`严重度: 严重`→FAIL）；绿测（`[MINOR]`→PASS／prose "major"→PASS）；对 vol1 存量 audits 回放新校验器出报告（命中数与清洗清单，不自动改写）。

### T3 · 派发完整性语义拆分
- **框架前置预检**：审计技能派发前确定性校验 contract required reads 存在（剔除 OPTIONAL_READS 与本技能 writes/updates——escalation 报告 reads 可用性三态判定逻辑 :268-303 同构复用）；缺失 → 走既有 dispatch failure 路径（retry/escalation），**不派发 LLM**——「输入缺失」从 LLM 的 BLOCKING 语义域里整体消失；
- G4 侧兜底规则：审计报告中 payload 匹配派发完整性模式（`派发完整性|请补齐|输入缺失`）的 BLOCKING 条目 → 报告判无效 FAIL（该形态出现即派发完整性 bug，须修框架不应由审计员表达）。

**判据**：红测——审计派发时 chapter 文件缺失 → 派发失败（零 API 调用、零审计产物落盘、走 retry 路径）；含「派发完整性」payload 的 BLOCKING 报告 → G4 FAIL。

### T4 · 反馈与聚合卫生（写作端）
- G4_FORMAT_EXAMPLES 补缺族：盘点 g4 checker 名册 vs EXAMPLES 键差集（一次性 diff 入 plan），首批补 `G4.cp.scene_budget`（示例文案取该 checker 失败消息期望格式）；
- aggregate 渲染条目携带 severity（`- **{sev}** · {text}` 形态——节标题保留，条目级不再依赖继承）；下游 chapter-revision 解析差分验证；
- ending_constraints 注入窗口 3→10 章（`review_checklist.py:539-544` `range(3,0,-1)`→`range(10,0,-1)`；纯 regex 分类零 LLM 成本），消灭 SKILL.md:166 文档/实现漂移——「连续≥3 章同型收尾」规则在 10 章窗内才有意义。

**判据**：`git grep -n "scene_budget" src/shenbi/pipeline/chapter_loop.py` 命中 EXAMPLES；aggregate 渲染含条目级 severity（红绿测试）；注入块 ending_constraints 长度=10（SKILL 文案零改动即重新为真）。

## 2. 验收
1. T1-T4 判据全绿；
2. 差分基线：换装前后对 fixtures 全量审计产物，路由/聚合输出逐项一致；
3. bug-hunt：词表外 finding（MAJOR/BLOCKER/严重）均被 T2 门拦（现状=静默丢包对照）；输入缺失场景走框架失败路径不再产 LLM BLOCKING；
4. T1 生成测试 ≥94（单源模块重构质量）。

## 3. 风险
- 五传感换装行为漂移 → 差分基线先行 + 逐项一致红测（最大风险面，T1 判据钉死）；
- T2 对存量报告误伤 → 只校锚定形态（散文提及豁免）+ 回放报告先行；
- T3 预检误判（glob/可选读）→ 复用 escalation reads 可用性三态判定既有逻辑；
- **共享文件面**：revision_router.py/chapter_loop.py 与 #106 同文件（**#105 先施工**）；review_checklist.py 面在 **#96 后**（T4 该面顺延，T1-T3 不受限）；dispatch_helper.py 预检面与 #92 在飞 T2a 同文件（#92 先）。
