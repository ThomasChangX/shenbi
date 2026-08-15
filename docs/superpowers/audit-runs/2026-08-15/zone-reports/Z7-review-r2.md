# Z7 区独立复核报告（review-r2，fresh-context merge 轮）

- 轮次: 2026-08-15 全项目深度审查 | 复核 agent: Z7-review-r2
- 对象: Z7-a/b/c/d 四段初审（F701–F719, F726–F750, F751–F764, F776–F790）+ Z7-review-r1（F765–F772）
- 本轮强制新角度（与 r1 不复用）:
  - (a) 测试→被测代码漂移对账（stale assertion / Mock 虚构属性形状，F727 同类系统扫描）
  - (b) 真实数据形态对照（测试构造的 progress.json / trace 事件 / decisions.json / 快照布局 vs `novel-output/xinghuo-ranqiong/` 真实磁盘形态）
- 编号段: F791–F797（7 条新发现）
- 方法: 只读。novel-output 仅以只读脚本访问；**调用前逐一 grep 确认目标函数无 write/save/dump 副作用**（`trace/replay.py:48` 含 `safe_write` 撕裂尾截断——按铁则改用自写只读校验脚本 `/tmp/z7r2/verify_trace_chain.py`，未调用仓库 replay）。未执行 pytest（含 --collect-only）；未 git 写操作；脚本只写 /tmp/z7r2/。

## 0. 抽样统计

| 项 | 数量 |
|---|---|
| 真实产物语料全量机械核验 | 89 份 decisions.json 逐一 json 解析分类；pipeline-state.json 全树转储；22 份 gate markers 全读；trace.jsonl 4 事件链验签；snapshots/ 51 文件 + manifest 全读 |
| src 消费端核验 | ~25 处（g2/g3/g4/generic/chapter_loop/dispatch_helper/snapshot_diff/crash_recovery/filelock_utils/triggers/materialize/codex 模式） |
| Mock 属性系统扫描 | 20 个测试文件（脚本 `/tmp/z7r2/mock_attr_audit.py`：函数块内 MagicMock/SimpleNamespace 属性 vs PipelineState/ChapterLoopStateData 真实字段集） |
| 误报复读 | r1 全部 6 条处置核对 + d 段 15 条中 12 条重新实证（含 F781 以内容哈希法独立重验 32/32） |
| 死接线 grep | `_should_run_recall` / `_should_run_drift` / `CONDITIONAL_STEPS` / `skills.*output_files` 写入者 / `_snapshot_chapter_files` 调用者 全量 |

对账基线：四段清单 236+73+445+166=920（r1 已核）；本轮新增对账维度为"真实磁盘 ↔ 测试构造"三方（而非 r1 的"报告声称 ↔ 测试计数"三方）。

## 1. 真实语料形态普查（本轮证据基座）

对 `novel-output/xinghuo-ranqiong/`（星火项目，56 章真实生产运行，PR #19 dd1fc62 入库）的形态普查结果：

| 产物 | 真实磁盘形态 | 测试构造形态 | 分叉？ |
|---|---|---|---|
| decisions.json（89 份） | **三态**：纯 JSON 45 / 有效 JSON+尾随非 JSON 内容 35 / 散文开头（LLM 响应原文）9 | 全部单一形态：干净 JSON（`json.dumps`） | **是**（F791/F795） |
| progress.json | `{current_scorer_agent: "pipeline-g3-scorer-<uuid4hex12>", scoring_history: [...]}`（自铸形态，见 F794） | g3 测试构造 `skills.{skill}.output_files`；codex 测试构造 `completed_skill_names` | **是**（F794） |
| snapshots/ | **legacy 平铺**：51 个 `chapter-NNN-<ts>.md` + 根 `manifest.json {"chapters": {...}}`，零差分子目录 | 差分布局 `chapter-005/snapshot-manifest.json`（test_last_snapshot/test_snapshot_diff）或手工合成目录（test_g4_directory） | **是**（F792） |
| pipeline-state.json chapter_states | `steps_done` 全部旧代步名（55/55 章含 review-anti-ai 等串行审计步；0 章含现行 review-group-*）；audit_results 为聚合 dict | 当代步名 + 手搓嵌套 audit_results | **是**（F797，F726 强化） |
| trace.jsonl（test-validation/ 4 事件） | 与现行 TraceEvent schema 完全一致，hash 链验签 4/4 OK（只读重算） | 一致 | 否（正面） |
| truth/ | 13 个 .md（含 resonance_trend/subplot_board/audit_drift 等现行全集） | fixtures 顶层 5 个；场景声称 11（F763） | 是（F763 强化：真实=13） |
| cost/token-ledger.jsonl | **不存在**（56 章零 token 记账） | 测试断言账本逐行落盘 | **是**（F796） |

## 2. 漏报（新 findings F791–F797）

### F791 | 生产 decisions.json 三态形态 vs 测试单态：G2 raw_decode 恢复分支零覆盖，G2↔G4 容错语义分裂无任何测试对撞 | 漏报 | P1
- 证据:
  - 真实语料全量分类（`python3` 只读扫描 89 份）：`json.loads` 整文件失败 44 份 = "Extra data"（有效首对象+尾随内容）35 + 散文开头/内部语法错 9（chapter-12/2/22/40-revision 等 5 份以"The revision is complete…"/"The file on disk can't be updated (read-only sandbox)…"等 LLM 响应原文开头）。
  - G2 恢复分支（src/shenbi/gates/g2.py:113-152）：`raw_decode` 截取首对象 + WARN `g2_decisions_multi_json_truncated` 后 **PASS**。`grep -rn "raw_decode|multi_json|trailing" tests/unit/gates/test_g2.py` → **零命中**；全测试树仅 tests/unit/pipeline/test_dispatch_helper.py:366-460（dispatch 层 `_validate_json_output`）覆盖尾随内容。TestG2DecisionsBranch（test_g2.py:393-546）只测 clean/`{not valid json`/multi-json(dec.4)。
  - G4 decisions 校验（src/shenbi/gates/g4/decisions_validator.py:97-101）：`json.loads` 整文件，无恢复 → 同一"有效 JSON+尾随"文件 **G4.dec.invalid_json FAIL**。tests/unit/gates/test_g4_decisions.py 14 个用例无一 invalid-json 用例（grep invalid/corrupt → 0）。
  - 共享 schema canary（tests/unit/contracts/test_canaries.py:43-58，自称同时钉 G2/G4 decisions 分支）也只写 `json.dumps` 干净 JSON。
- 根因: dispatch_helper.py:803 注释自认 "The dominant corruption pattern (verified by filesystem audit) is a valid JSON object followed by trailing markdown"——该"filesystem audit"的对象正是本语料，但修复只落在 dispatch 层；G2 的恢复分支与 G2↔G4 的容错分裂（同一文件 G2 PASS / G4 FAIL）从无测试。
- 验证（实跑）: 上述 89 份分类脚本输出；两个 grep 零命中；`sed -n '96,165p' src/shenbi/gates/g2.py`。
- 影响面: G2 恢复分支为纯死测代码；tiers 流中 agent 自写 round 文件（不经 dispatch 清洗）时 G2/G4 对同一文件给出相反判定，行为契约未定义且被测试遮蔽。
- 建议方向: (1) 补"有效 JSON+尾随内容"用例同时跑 gate_G2 与 g4_decisions，钉死（或修复）语义分裂；(2) 将真实语料 3 份代表性样本（尾随/散文/干净）登记为 fixtures（G0.11 镜像）作为门测试输入。

### F792 | 快照布局分叉：生产实际布局（legacy 平铺+根 manifest）与全部测试布局（差分目录）不同；legacy 写入分支零测试覆盖 | 漏报 | P2
- 证据:
  - 真实磁盘：`snapshots/` 51 个 `chapter-005-20260715T232231.md` 式平铺文件 + 根 `manifest.json {"chapters": {"5": ["chapter-005-….md"], …}}`；`find … -type d` → 除根外零子目录。命名格式与 chapter_loop.py:1678-1682 legacy 分支（`f"chapter-{chapter:03d}-{timestamp}.md"`）逐一吻合。
  - 当前默认：`_snapshot_chapter_files`（chapter_loop.py:1641）默认 `use_legacy_snapshot=False` → 差分目录 `snapshots/chapter-NNN/` + `snapshot-manifest.json`（snapshot_diff.py:125）。全部快照测试（test_last_snapshot.py:17-39、test_snapshot_diff.py、test_adaptive_triggers.py:42-46、test_g4_directory.py:30-44 手工合成 `snapshots/chapter-100/` + 手写 `manifest.json`）只覆盖差分布局；`grep -rn "use_legacy_snapshot=True" tests/` → **零命中**。
  - legacy 分支 68 行（chapter_loop.py:1672-1739：manifest 记账、中文内容守卫、_get_core_snapshot_files 聚合）零覆盖；该函数本体标注 `pyright: ignore[reportUnusedFunction]`，src 内唯一调用是 crash_recovery.py:154 的**另一个简化孪生**（无时间戳/不更新 manifest）。
  - git 考古：snapshot_diff.py 与其测试与生产运行同批入库（dd1fc62/PR #19）——差分设计从未在真实运行中执行过。
- 根因: 布局迁移（legacy→差分）只迁移了测试，未迁移（或登记）生产语料；closure 期望 `snapshots/chapter-{total:03d}/`（test_g4_directory.py:69-77 钉死），真实项目（纯平铺）在当前代码下到 closure 时该目录不存在 → G4 not_found。
- 验证（实跑）: `ls snapshots/`、manifest 转储、`find -type d`、两处 grep、`git log --diff-filter=A`。
- 影响面: 真实项目无法平滑进入 closure；legacy 分支回归（manifest 记账/保留清理互操作）无护栏。
- 建议方向: 二选一定为规范并删除另一分支；若保留 legacy，补 `use_legacy_snapshot=True` 正向用例 + closure 对平铺布局的处置测试。

### F793 | CONDITIONAL_STEPS 为零消费者死常量；_should_run_recall/_should_run_drift 死函数被 test_adaptive_triggers 直接测试（F727/F730 模式的系统化确认） | 漏报 | P1
- 证据:
  - `grep -rn "CONDITIONAL_STEPS" src/ tests/` → 仅定义处 chapter_loop.py:266 与注释 :131。注释声称 "Conditional: intent-management, drift-guidance, snapshot-manage moved to CONDITIONAL_STEPS (invoked only when gates open)"——**"gates open" 调用机制不存在**。当前 CHAPTER_STEPS（实测打印 16 步）不含这三个技能；drift-guidance 仅存卷级 trigger（triggers.py:262），intent-management 仅存 genesis（genesis.py:76），snapshot-manage 走 checkpoint 后 cli.py:820。
  - `grep -rn "_should_run_recall\b|_should_run_drift\b"` → src 零调用者（各带 `pyright: ignore[reportUnusedFunction]`），唯一引用是 tests/unit/pipeline/test_adaptive_triggers.py:10-37 对两个死函数的直接断言。
  - 连带死钩子：chapter_loop.py:3085-3088 的 `step.skill == "shenbi-foreshadowing-recall"` / `"shenbi-drift-guidance"` manifest 更新分支——当前步表中无此二步名，永不触发（真实 manifest.json 无 last_recall_chapter/last_drift_chapter 键，与之一致）。
- 根因: 步表重构（MERGE-1/2 + conditional 迁移）后遗留半拆除机制；测试反而为死分支提供绿色覆盖，使"自适应触发已测"成为假象——真正在跑的触发逻辑在 triggers.py，其与这两个死函数的语义等价性无人对账。
- 验证（实跑）: 上述 grep ×3；`uv run python -c "from shenbi.pipeline.chapter_loop import CHAPTER_STEPS; …"` 逐条打印。
- 影响面: recall/drift 的"章内自适应调度"整层不存在于生产路径；测试文件名（test_adaptive_triggers）与被测物名实不符。
- 建议方向: 删除 CONDITIONAL_STEPS 与两个死函数及其测试，或真正接线并在 triggers.py 侧补语义对账测试（triggers 版 vs 死函数版对同一 truth 输入的判定一致性）。

### F794 | G3 独立性证据自铸：run_gate_g3 自造 progress.json 见证 + G3.3 的 output_files 键全 src 无写入者 → 生产中 G3 三项实质检查全部空转，测试分层构造理想形状掩盖 | 漏报 | P1（附 P0 讨论）
- 证据:
  - 自铸（src/shenbi/pipeline/dispatch_helper.py:1972-1988）：`run_gate_g3` 在 `round_dir/progress.json` 不存在时写入 `{"current_scorer_agent": f"pipeline-g3-scorer-{uuid4().hex[:12]}", "scoring_history": [{"agent": "pipeline-skill-generator", …}]}`。三个生产调用点（genesis.py:364 / closure.py:310 / chapter_loop.py:2946）**全部传 project_dir 作 round_dir**。
  - 真实磁盘铁证：`novel-output/xinghuo-ranqiong/progress.json` = `current_scorer_agent: "pipeline-g3-scorer-66b27075583e"`——12 位小写 hex，精确匹配 `uuid4().hex[:12]` 模板。该文件不是独立记录，是 G3 流程自己铸造的证据。
  - 空转链：G3.3（g3.py:153）读 `progress["skills"][skill]["output_files"]` ——**全 src 无任何写入者**（codex.py:65-72 写 `{score,status}`；materialize.py 写三 pending 结构；均无 output_files）→ 生产恒 SKIP "no output_files"。G3.4（g3_independence.py:33-39）：自铸 scorer 存在 + 无 agent_trace → 按规则 PASS（空转）。G3.5：自铸 history 的 agent ≠ scorer → PASS。即生产 G3 = SKIP + 两个无证据 PASS。
  - 测试分层掩盖：test_g3.py:118/220 手工构造 `skills.{skill}.output_files`（生产不可能出现的形状）使 G3.3 PASS 分支可测；tests/unit/pipeline/test_dispatch_helper.py:113-146 的 run_gate_g3 测试 mock 掉子进程，`grep -rn "pipeline-g3-scorer|progress_json_created" tests/` → 零命中——自铸分支的内容从未被断言。
- 根因: G3 的 fail-closed 修复（g3_independence 模块，docstring 自述纠正"空转 bug"）只堵了"缺 scorer 证据"方向，没有堵"自铸 scorer 证据"方向；而 G3.3 消费的键从未有过生产写入端。
- 验证（实跑）: 上述三处 grep；progress.json 原文读取；g3.py/g3_independence.py/codex.py/materialize.py 段落阅读。
- 影响面: AGENTS.md 硬契约"Scoring MUST use an independent subagent"在主管线中由自铸见证背书；评分独立性门对真实生产零拦截能力（若某轮 generator 与 scorer 同源，G3 照样 PASS）。
- 建议方向: progress.json 的 scorer 证据应由真实评分动作写入（record scorer identity at scoring time），run_gate_g3 删除自铸；G3.3 要么接真实 output_files 写入端要么显式降级删除。
- 严重度说明: 按 §8.1 P1"测试失效掩盖真实缺陷"成立；若终审将"独立性证据"视为契约本体，则命中 P0"生产契约静默违反"——提请终审裁量（复核 agent 无权单方定 P0）。

### F795 | 章循环 G4 文件集只含 .md 主产物：decisions.json sidecar 永不进入主管线 G4——AGENTS.md 声称的 decisions schema/P2.5 校验在主路径不发生（44/89 损坏 sidecar 与 22 个 PASS marker 并存的机制解释） | 漏报 | P1
- 证据:
  - `_resolve_g4_files`（chapter_loop.py:565-584）→ `_resolve_g4_path`（:548-562）只返回 `step.output_path` 单文件；实测 CHAPTER_STEPS：chapter-drafting/revision 的 output_path 均为 `chapters/chapter-N.md`。composite（decisions_validator.py:143-176）按扩展名分区——.md 给结构 checker，json_files 恒空 → g4_decisions 收到 `[]` → `SKIP "no files"`（decisions_validator.py:109）。
  - 真实铁证：44/89 份损坏 decisions.json 与 22 个全 PASS 的 `gate-markers/G4-*-generative.json`（含 G4-shenbi-chapter-drafting/revision）在同一磁盘共存。
  - 测试遮蔽：test_g4_decisions.py 与 test_canaries.py 全部**显式传入** json fps 测 checker 本体；无任何测试断言"章循环路由到达 checker 的文件集"契约（_resolve_g4_files 本身零直接测试）。
- 根因: G4 接线的文件集契约（单 output_path）与技能契约（writes 含 sidecar）脱节；decisions 校验只在 tiers/CLI 流（run_gate_g4 显式传文件）生效。
- 验证（实跑）: `_resolve_g4_files`/`_resolve_g4_path` 段落阅读；CHAPTER_STEPS output_path 实测打印；gate markers 全量转储。
- 影响面: 主管线每章产出 2 份 sidecar（decisions + revision-decisions），其 schema/P2.5/预算校验在生产主路径上从不执行——F791 的三态损坏因此无门拦截。
- 建议方向: `_resolve_g4_files` 为声明了 decisions 写入的技能追加 sidecar 路径；补一条 wiring 测试断言 drafting 步的 G4 文件集包含 `chapter-N-decisions.json`。

### F796 | IDE dispatch 路径零 token 捕获 + TokenLedger chapter 列恒 0：真实 56 章生产运行无 cost/ 目录，token 记账整体未发生 | 漏报 | P2
- 证据:
  - `_dispatch_via_ide`（dispatch_helper.py:1716-1790）：段内 grep "usage" → 0 命中；调用 `_write_parsed_outputs` 不传 state——无 token 捕获、无账本写入。
  - 真实磁盘：`novel-output/xinghuo-ranqiong/cost/` **不存在**（56 章、数百次 dispatch 后仍无）。
  - chapter 列缺陷：`_record_token_usage`（dispatch_helper.py:1340）`getattr(state, "chapter", 0)`——PipelineState（state.py:162-183）无 `chapter` 字段（章号在 `state.chapter_loop.current_chapter`）→ 账本 chapter 恒 0；tests/pipeline/test_dispatch_helper_ledger.py:26-31 只断言 skill/token 数，chapter 字段无断言（SimpleNamespace 替身同样无该属性，同形掩盖）。
- 根因: token 记账只在 API 路径实现（dispatch_helper.py:1583/1639），测试（test_dispatch_helper_ledger、test_dispatch_usage_capture）全押 API 路径；账本列取值属性名从未与真实 state 对账。
- 验证（实跑）: 三处 grep/阅读；`ls cost/` → 不存在；测试断言段落阅读。
- 影响面: 成本观测（AGENTS.md 语义下的预算治理输入）在 IDE 生产路由整体缺失；历史运行不可回溯。
- 建议方向: IDE 路径至少从 CLI 输出解析 usage 或显式记"unknown"行；chapter 列改取 `state.chapter_loop.current_chapter` 并补断言。

### F797 | 真实 pipeline-state 的 steps_done 全部为旧代步名（55/55 章）：跨代 resume/对齐无测试、无迁移逻辑 | 漏报 | P2
- 证据: 真实 `pipeline-state.json` 量化（只读脚本）：含旧串行审计步名（shenbi-review-anti-ai 等）的章节 55/55、含现行 review-group-* 步名的章节 **0**；shenbi-intent-management / shenbi-foreshadowing-recall 出现在 56/56 章（两者均不在当前 CHAPTER_STEPS，见 F793）。`_validate_state_consistency`（state.py:469+）只查空/越界，不校验 steps_done 步名与当前步表的对齐。
- 根因: 步表两代重构（串行审计→review-group 合并、conditional 迁移）后无状态迁移层；测试（test_state_machine_heal 等）只构造当代形态。
- 验证（实跑）: 上述量化脚本输出；state.py 校验段阅读。
- 影响面: 真实项目以当前代码 resume 时，step_index 语义错位（旧代表 index 9 ≠ 新步表 index 9），已完成步骤按新表重跑或跳错；无任何守卫报警。
- 建议方向: `_validate_state_consistency` 增加 steps_done ⊆ 当前步表∪已知历史步名的白名单校验（或迁移映射），并补旧代 state 的 resume 测试。

## 3. 误报/事实修正

**零整条误报。** r1 的 6 条与 d 段 15 条复核处置：

| Finding | r2 复验方式 | 结果 |
|---|---|---|
| F765 | `grep -rn "book_spine_init" tests/ --include=*.py` → 仍零命中 | 成立（未修复，符合预期） |
| F766 | `grep -rln "ChapterPlanning\|ContextComposing\|VolumeOutlining" tests/` → 仍仅 test_skill_integration.py | 成立 |
| F767 | 处置核对（并入 F716） | 无异议 |
| F768 | 未重跑（r1 已三组对照失败）；不影响任何 finding 结论 | 维持"验证声明不可复现" |
| F769 | `find docs -name "*.md" \| wc -l` → **413**（d1 时 371 → r1 时 390 → 本轮 413） | 成立且持续恶化，单调增长再证 |
| F770 | pyproject.toml:420-424 addopts 含 `--cov=shenbi` | 成立 |
| F776 | `grep -rln "黑石饼" novel-output/` → 空 | 成立 |
| F777/F778 | 7/8/9-example 哈希重算 → df81acba ×3 | 成立 |
| F779 | manifest.md:7-8 → `sha256:abc123`/`sha256:xyz789` 原样在案 | 成立 |
| F780 | 4 对 truth↔snapshot 哈希重算 → 4/4 MATCH | 成立 |
| F781 | **内容哈希法独立重验**（按 sha256 在 tests/tiers 全树反查，非文件名匹配）：32/32 精确副本 | 成立（注：按文件名匹配会误判 0/32——tiers 侧文件名不同；r1 的映射法正确） |
| F782 | baseline G0.json checks id 转储 → 无 G0.13-16 | 成立 |
| F783 | mutation-score.txt 首行注释 + grep "BASELINE NOT YET ESTABLISHED" =1 | 成立 |
| F784 | 4 词干抽查（arc-example/book-spine-example/world-rules-example/stop_words_zh）→ 全 0 引用 | 成立 |
| F786/F787/F788/F789 | sensitive 3 词原文；genre-config 键差分（英文 vs 中文键、tropeInventory 真3假3 无）；README "No anchors"=1 vs 实 27 锚点；skill-triggering-prompts 仅 .gitkeep | 全部成立 |

**事实强化（不构成新编号，供终审引用）**：
1. **F726 升级证据**：真实 chapter_states 的 `audit_results` 是聚合 dict（`{"blocking_found": bool, "audit_reports": [...], "revision_route": ...}`，ch42 实测 11 份审计报告路径）；当前写入端（chapter_loop.py:2641-2642、2970-2972）**从不写任何 per-skill passed/hard_failures 键**。即级联断裂不止于"扁平 vs 嵌套"接线错位——数据源层面 per-skill 审计结果从未被采集，修复 `_get_audit_history` 形状也无法恢复语义。
2. **F763 强化**：真实 `truth/` 为 **13** 个 .md（fixtures 5、场景声称 11 之外的第 4 个数字）。
3. **F755/F758 关联**：真实 genesis skills_done 16 项含 book-spine-init/intent-management 等，与 deps genesis 前置（11 项）也非同集——步表演进后 deps/seed/state 三方各自停在 different 时点。
4. **trace 正面结论**：真实 trace.jsonl（4 事件）与现行 schema/签名链完全一致（只读重算 4/4 OK）。方法论注记：事件 `ts` 以 `Z` 结尾存储、签名按 datetime.isoformat()（`+00:00`）计算——直读字符串重算会假报 BAD，为本轮踩过并修正的坑，后续复核者须先归一化再验签。

## 4. 覆盖空洞（本轮新增，均已被 F791-F797 承载）

| 空洞 | 承载 |
|---|---|
| G2 decisions 恢复分支（g2.py:113-152） | F791 |
| G4.dec invalid_json 路径 | F791 |
| `_snapshot_chapter_files` legacy 分支（chapter_loop.py:1672-1739） | F792 |
| `_resolve_g4_files` 文件集契约（含 sidecar 与否） | F795 |
| `run_gate_g3` 自铸 progress.json 内容分支 | F794 |
| `_dispatch_via_ide` usage 捕获 / TokenLedger chapter 列 | F796 |
| 旧代 steps_done 的 resume 对齐 / 状态迁移 | F797 |
| triggers.py 自适应逻辑 vs 死函数语义对账 | F793 |

r1 已闭合的空洞清单（book_spine_init、contracts/skills×3、memory_distill 等）本轮无新增条目；`filelock_utils`（本轮专查，tests/unit/pipeline/test_filelock_utils.py 存在，flock 语义下 lockfile 常驻属设计）**不构成**空洞。

## 5. 严重度异议表

| 对象 | 现级 | r2 意见 |
|---|---|---|
| F708/F709/F710/F757 | 台账已升 P1（r1 F771 采纳） | **确认采纳正确**。本轮 F794/F795 提供同类第三例证（门的实质检查在生产空转），佐证"死检查=不发射"与"死接线=不执行"同级成立 |
| F794（本轮新） | 自评 P1 | 提请终审考虑 P0：若"独立性证据"视为 AGENTS.md 契约本体，自铸见证=生产契约静默违反（§8.1 P0 第二例）。复核 agent 不单方定 P0 |
| F791 vs F795 | 各 P1 | 同一症状语料（44/89 损坏）的两个独立机制（容错分裂 / 文件集路由），不合并降级 |
| F751（P0） | 维持 | 本轮无新反证；F791/F795 的真实语料三态从产物侧进一步佐证"场景↔fixture 内容断链"系统性 |
| F772（F777 P1 张力） | 维持 r1 记录 | 本轮无新证据介入 |
| F705（P2 borderline，r1 注） | 维持 | xdist 窗口论证不变 |

## 6. 收敛判定

- 本轮新增 **7 条**（P1×4：F791/F793/F794/F795；P2×3：F792/F796/F797），误报 **0**，r1+d 段复验全部成立。
- **未达硬收敛**：硬标准（本轮零新增 P0/P1）不满足——4 条新 P1 均有真实磁盘铁证，非边际发现。
- **软收敛可判**：r1（+6，含 4 项 P1 升级）与 r2（+7）的全部新发现可归约为**两个系统性根因**：
  1. **证据链自铸/死接线族**（F726/F727/F726 强化/F793/F794/F795）——门的消费端与生产写入端从未对账；
  2. **真实形态未入库族**（F751/F763/F787/F791/F792/F796/F797）——测试构造形态与 novel-output 真实形态分叉。
  两族修复面集中（一次"生产接线对账 + 真实语料 fixtures 化"专项可覆盖），非散射性缺陷。若下一轮（r3）在既定抽样框架内不再出现**新根因类**发现，即可判收敛；本轮建议将上述两族列为终审优先修复项而非继续扩轮。
- 方法披露: 本轮未运行 pytest（含 --collect-only），未触发 coverage 重写；novel-output 访问全部经由只读脚本；唯一仓库写入为本报告文件。
