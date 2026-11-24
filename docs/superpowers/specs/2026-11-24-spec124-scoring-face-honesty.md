# Spec #124 · T1 评分面诚实化（scoring-face-honesty）：G3.4 比较真实执行体＋kill switch 结构化归零＋G3.2 复用评分校验

**日期**：2026-11-24｜ **系列**：实现审计清偿批（expert-panel-implementation-audit · 2026-11-24 八席审计，协调者逐条亲验）｜ **状态**：Design（r1，2026-11-24）｜ **优先级**：🟡 P2
**动机证据**（HEAD `3311a0af`）：
- **G3.4「评分员≠生成者」恒 PASS**：`src/shenbi/gates/g3_independence.py:23-28`（`gen = agent_trace.get(skill_name)`；`gen is not None and str(gen) == str(scorer)` → FAIL，否则 PASS）；`src/shenbi/pipeline/genesis.py:694-695`（`scorer_route=f"genesis-dispatch:{step.skill}"`、`generator_routes={s: f"genesis-dispatch:{s}" …}`——两边都是「阶段名＋技能名」拼出的标签，比的是技能名而不是执行体）。2026-11-24 复跑：31 个 `requires_independent_agent` 技能在真实项目状态下 `{'PASS': 31, 'FAIL': 0}`；构造「generator=model-A，scorer=model-A」仍 PASS；与评分标签相等的生成标签集合为空——比较在构造上不可能为真。AGENTS.md 的「Scoring MUST use an independent subagent (G3.4)」由一道不可能 FAIL 的门守着；#105／#109 归档时各留一项「G3.4 验收随令」；
- **kill switch 没有自动路径**：`src/shenbi/scoring.py:433`（`kill_switch_triggered = "--kill-switch" in sys.argv`——唯一开关是命令行旗标）、`:242-245`（归零逻辑本身存在）；唯一的程序化调用方 `src/shenbi/dispatcher/modes/codex.py:291`（`shenbi-score` 位置参数调用）不传该旗标，评分员的输出契约（整数键）也带不了这个信号。复跑：rubric 的三条 kill switch 规则被工具解析，但未声明时 `final=92.33 classification=PASS`；双评分 `SHENBI_DUAL_SCORER`（`codex.py:317`）默认关；塌缩哨兵 `collapse_suspected` 的唯一消费是 `log.warning`；
- **G3.2 把 NaN／缺维当 PASS**：`src/shenbi/gates/g3.py:168-170`（`score = min(flat_dims.values())`；`if score < threshold:`——`nan < 90` 为 False），且只按已打分维度加权；`src/shenbi/scoring.py:213`（`validate_scores`——对同一张表会 REJECT）。复跑：`nan.json` → G3 status=PASS；`partial.json` → PASS；
- **范围**：T1 测试评分路径（`shenbi-score`／G3），不影响小说流水线门。

**触及的不变量维度**：无（T1 评分与门禁诚实层——不改任何叙事维度门检）

---

## 0. 根因

三道门的失败分支都存在但不可达：G3.4 比较的两段标签按构造永不相等；kill switch 的归零逻辑只能由人手传旗标触发，评分员的输出契约带不了这个信号；G3.2 自己算加权而不走评分器的校验。AGENTS.md 的阈值体系（≥94／≥90／100）建立在这三道门之上。

**用户裁定（待裁一项）——G3.4 的「独立」口径**：会话级独立（另一次派发、无共享上下文）即算 PASS，还是要求异模型。本件缺省取「会话级 FAIL 语义＋同模型 WARN 披露」：行为保持 PASS，但报告如实写明「认知独立性未建立」；异模型要求作为 #107 T2 C 臂通过后的升格选项。用户若裁定严格口径，缺省翻转为 FAIL。

**备选案已评估并否决**：「直接要求异模型」——第二模型端点未配置（#107），会让全部 T1 立即 FAIL；「删 G3.4」——AGENTS.md 明文 MUST，应使其诚实而非移除；「kill switch 继续靠人工旗标」——漏检植入缺陷的 bug-hunt 记 PASS 是 T1 最坏的假阳性。

## 1. 任务分解

### T1 · G3.4 比较真实执行体
- 派发时在 progress.json 记录生成派发与评分派发的执行体标识（会话／agent id＋model；标识取自运行时事实，不接受 prompt 传入）；`gate_G3` 比较执行体而非「阶段:技能」标签：同会话／同执行体 → FAIL；执行体不同但 model 相同 → PASS＋WARN（`cognitive_independence_unestablished`，进 G3 报告）；严格开关 `--require-distinct-model` 下同模型 → FAIL；
- 判据：单测三分支；对 vol1 progress.json 的重放报告如实列出 31 个技能的 FAIL 数与 WARN 数；#105／#109 留下的「G3.4 验收随令」由本件一并核销。

### T2 · kill switch 结构化
- 评分员输出契约加结构化字段（触发与否＋所引 rubric 规则 id＋证据），`shenbi-score` 解析后强制归零；评分员对任何 kill switch 都未作判定 → 报告标 `kill_switch_undeclared`（不得静默按未触发）；命令行旗标保留为人工覆盖；
- 判据：红测（声明触发 → total=0；未声明 → 报告带标记）；`codex.py` 调用路径的集成测试；规则 id 与 rubric 解析器一致。

### T3 · G3.2 复用评分校验
- `gate_G3` 的评分读取复用 `validate_scores`（拒 NaN／inf／bool／越界／缺维），并按报告所属技能的 rubric 校验维度集；
- 判据：`nan.json`／`partial.json` → FAIL；现有合法报告夹具零回归。

## 2. 验收
1. T1–T3 判据全绿；
2. 三道门各有一条「能红」的回归测试（撤掉修复必红）；
3. `just check` 全绿。

## 3. 风险
- **progress.json 记录面变化**：新增字段，向后兼容——旧记录无执行体标识 → WARN `executor_identity_unknown`，不 FAIL；
- **评分员输出契约变化**：`tests/tiers/t1-skill/_template/rubric.md` 与评分员 prompt 同批改；历史 scores.json 不回填；
- **共享文件面**：`scoring.py`／`dispatcher/modes/codex.py` 与 #94 T3（scoring 子命令化、归一化单源）同文件——**#94 T3 → 本件 T2／T3**，或两件同批施工（plan 期定）；`g3.py`／`g3_independence.py` 无在飞冲突。

## 4. 立项预答（价值门 ④⑤ 前置）

**④ 博弈路径清单**：
- 执行体标识仍由派发器自填、与真实会话无关 → 标识取自运行时（会话 id／进程 id）；
- 评分员把 kill switch 全填「未触发」→ 框架无法证伪（判官自报的固有边界）——缓解＝以 #108 canary 的植入缺陷 ground truth 作外部对照，登记为依赖；
- WARN 被长期忽略 → WARN 进 G3 报告与观测报告（`observe_report`），重放报告是验收项；
- G3.2 改用 `validate_scores` 后误拒历史合法报告 → 夹具回归。

**⑤ 候选机制清单**（buy-before-build）：`record_scorer_evidence`（既有写点，升格为记执行体标识）；`validate_scores`（既有，直接复用）；`collapse_suspected`／`flag_score_collapse`（既有哨兵，把消费面并入 `observe_report`）；#108 canary（测量器，跨 spec 消费）。无新建机制。

**测量语义回执（v8.1 L1–L5，触及面：门与评分）**：L1 构念与口径——「独立」被操作化为「执行体标识不同」（会话级），与「认知独立」（异模型）是两个量，报告分列、不混称；L2 闭环与污染——kill switch 的触发声明须引 rubric 规则 id（可核），不是无依据自评；L3 活性与负荷去路——G3.4 的 FAIL 分支在重放数据上点火率须 >0 才算复活，若仍为 0 则说明夹具未覆盖同执行体分支；L4 可判别性——三分支互斥穷尽（同执行体／异执行体同模型／异模型）；L5 未触及。
