> **Date:** 2026-08-16 | **Status:** Design (Revised 2026-08-30 · SDD #27 阶段 2 事实核实修订) | **Severity:** 🟥 Critical | **方法:** systematic-debugging 四阶段
> **Ledger:** 本 spec 全部 F 编号属 `docs/superpowers/audit-runs/2026-08-15/findings-ledger.md`（与 2026-08-14 ledger 撞号且语义不同；specs #8/#16 等 commit 引用的是 08-14 族，与本 spec 无重叠）
> **系列:** 2026-08-15 全项目深度审计 · 阶段 5（簇 C1，67 条）| **代表 finding:** F462 | **严重度上限:** P0（F340）| **涉及文件面:** src/shenbi/gates/（g0-g7、g_reconcile、cli）、scoring.py、pipeline/（chapter_loop、phase_runner、parallel_dispatch、audit_context_cache、trace/materialize）、新增 lint 对账工具

## 2026-08-30 修订（阶段 1 驳斥复核 + 阶段 2 事实核实结论，main HEAD 17c5d67）

**已核销（被 main 后续合并吸收，本 spec 不再实施）**：
- F104/F757 解析面 — spec #9 R4 已实施 `load_applicability` 双表形解析（scoring.py:73-112）；本 spec 仅保留其对账 lint 面（T7 输入）
- F238/F373 — specs #11 R5 + #21 R2 已实施 `truth_readers.read_pending_hooks` 单源解析（pipeline/truth_readers.py:217-280）；残留：chapter_loop.py:1311 局部 TRIGGERED-count regex 并入 T5 清理
- F342 — 读方已用 `style/style_profile.md` 正确路径（audit_context_cache.py:63、context_assemble.py:56）
- F1103 — revision_count/resonance_score 已接线（chapter_loop.py:1712-1721、:1040-1065）
- F1107 — blocking 汇总已为显式契约（chapter_loop.py:2540-2543，spec #4 聚合层）

**部分修复（re-scope 至残存面）**：
- F458：`find_report` 多后缀已修（gates/shared.py:156-175，spec #8）；残存 = G7.14（g7.py:182）、G7.15（g7.py:207）、G0.10（g0.py:450）仍 glob 不匹配 codex 写方 `*-scores-subagent.json`（dispatcher/modes/codex.py:75）→ 并入 T1
- F130：G3.2 已有 `_compute_rubric_weighted_score` 回退（g3.py:26-60）；T4 仅核对其覆盖 canonical `final_score`+嵌套 `dimensions` 形状，不匹配则补
- F435：`cmd_post_skill` 已重构（phase_runner.py:247-261 derive_output_files + exists/size 过滤）；T4 仅核对其对 Route C 侧车索要在新形状下的行为
- F524：`parse_trend` 已重写（compute_drift.py:163-200，spec #11）；T5 仅做三方消费者表头契约对账断言
- F222：`glob` 字段已有消费者（contracts/graph.py:20,35 `normalize_to_glob`）；T6 仅核销
- F1111：覆写面已由 gate_manifest 串行化解决（C32 R4）；空转面并入 T2（F121/F463）

**孤儿归宿钉死（阶段 3 审查 C1 补）**：F340（P0）明确归 T5（`_any_audit_has_findings` 扫描名单收敛，与级联词表同一改动面）；F349/F406/F419 归 T1（死检查/死分支族）；F511 归 T5（avg G3 分数抓取噪声，src/shenbi/cost/report.py:16-36（_try_avg_g3_score））；F240/F241/F629 归 T6（写而不读/三方矛盾裁决）。

**存活确认（抽查 file:line）**：F340/F369/F370/F349（chapter_loop.py:1601-1626 扫描名单 13 型 + group-*/era/fanfic/highpoint 缺席）、F121/F463（scoring.py:249-428 marker 读方 vs gates/cli.py:121 硬编码 generative 唯一写方）、F449/F710（g_reconcile.py:40,65 `== "DONE"` vs codex.py:53 `"done"`）、死检查族全存活、T7 lint 工具不存在。约 50/67 条结构存活。

## T7 lint 工具设计（阶段 3 审查 I5 补，防 dead-wire）

- **读键清单枚举**：常量表驱动——`tools/lint_key_reconciliation.py` 内置 `READ_KEY_REGISTRY: list[ReadKey]`，每条 = `{check_id, file:line锚点, read_pattern(命名族 glob 或字面键), writer_sources: list[写方锚点]}`。新增读键时同步登记（PR 纪律由 G4/契约 lint 相邻面共同约束，不引入 AST 扫描复杂度）。
- **写方清单来源**：grep 可复核的静态锚点——dispatcher modes（`dispatcher/modes/*.py` 的产物键/文件名构造）、scoring 写路径（marker 常量）、`gate_manifest`、truth/staging 写方。每条 writer_source 是 file:line + 产出形状注释。
- **断言形态**：对每条 ReadKey 断言 (a) writer_sources 非空且锚点文件中模式仍存在（grep 复核）；(b) read_pattern 与 writer 产出命名族样本集交集非空。样本集取 `tests/fixtures/` 真实产物 + 写方代码构造的字面量。
- **输出**：违规按 check_id 列出「读键 → 期望写方族 → 实际匹配数 0」；exit 1。
- **WARN→FAIL 开关**：`--strict` flag；首周期接入 `just check` 时以 WARN 模式（exit 0 但打印）运行，一个合并周期后去 flag 升 FAIL（退役时点：本 spec PR 合并后的下一个涉及 gates/ 的 PR）。首批登记 T1-T5 涉及的 40+ 读键。
- **前置依赖**：spec #48（gate-runner 路径协议，INDEX 记其为 C1 对账 lint 验收地基）——本 lint 的执行入口形状以 #48 落地形态为准；#48 未归档期间以独立 CLI 形态先行，不阻塞。

# 读方↔写方键空间/命名族/格式对账（audit-reader-writer-key-reconciliation）

## 背景

gate 检查器、管线解析器、词表触发器各自硬编码了对上游数据（marker 文件、状态 JSON、truth 文件、审计报告）的读键/命名族/格式假设，但这些假设从未与真实写方对账，也没有任何对账 lint。结果分两类：检查结构性空转（读的键全仓无写方 → 恒 PASS/SKIP 的死检查）与假 FAIL（写方实际产出与读方假设错配 → 合法数据被判失败）。这是本审计最大簇（67 条，P0×1 + P1×22，横跨 Z1-Z6/Z11/T1），也是阶段 4 认证的最大候选元根因 A。

关键证据（finding ID → 现象）：

- **P0**：F340——修订步条件门控扫描旧版审计文件名族，group-* 审计报 BLOCKING 时 chapter-revision 被静默跳过（生产实证）。
- **marker 协议错配**：F121/F129/F131/F463——bug-hunt/clean 的评分 marker 命名族无写方，`shenbi-score --test-type bug-hunt|clean` 结构性 MARKER_MISSING exit 3（实跑）。
- **死检查族**（读键无写方）：F450/F451/F452/F453/F454/F455/F458/F464-F470——G3.3/G3.5/GT.1/GT.3/G0.5b/G0.7/G1.6/G7.14/.gate-lock/t1_scores/scoring_history 等读的全仓零写入方；G0/GT 面同族：F406（G0.12 豁免计数 22≠实际 31 恒 PASS）、F419（G0.4 missing_dirs 恒空死分支）、F639（gate_blockers 恒 []，GT.3 空转）。
- **假 FAIL 族**（读键与写方形状错配）：F104/F757（18 份 rubric 的 Dimension Applicability 表不被 load_applicability 解析）、F449/F710（GR.1/GR.2 状态词表与 `done/DONE` + `-scores` 后缀双源错配）、F130（G3.2 读键 vs scoring 输出形状）、F435（T2 post-skill 对每个传入文件索要 Route C 侧车）、F122（scope 区间只取端点）、F372（resonance 三模式解析 55/55 全 None）、F465（G7.14 glob 漏 codex 命名族——F458 同族第 4 读方）。
- **词表/格式触发器永不命中或恒误触发**：F238/F373（pending_hooks 表格格式零命中）、F303/F341/F342/F369/F370（审计级联键族+词表+裸子串）、F375/F643（audit_drift 正则对三种真实写方格式零匹配）、F374（style_profile 自愈恒误触发）、F349（`state.drift_alerts` 幽灵字段恒 False）、F524（parse_trend 第三消费者表头契约与写入侧互斥、解析恒空）、F511（avg G3 分数抓取噪声）。
- **写而不读/三方矛盾数据**：F222/F225/F229/F469/F527/F640（glob 字段、write_semantics key、read_keys、materialize 12 键仅 4 键被消费）、F240（NovelConfig 与 seed_parser 生产代码 + 真实 novel.json 三方矛盾）、F241（ProgressDoc 键空间对齐）、F629（trace INIT/MARK_DONE 读而不写——materialize 派生源恒空）。
- **测试面掩盖**：F726（审计级联测试各自为政掩盖生产形状不匹配）、F727（drift-guidance 死接线 + MagicMock 虚构属性自证）——测试改写归 C14 簇，本 spec 修生产形状后解除 pin。

证据细节见 zone-reports/Z1/Z2/Z3/Z4/Z5/Z6-review-*、Z7-a/Z7-b/Z7-c、Z11-a 与 thread-reports/T1.md（phase4-clustering.md §2 C1 行）。

## 修复目标

1. 消灭"死检查"：每个 gate 检查/管线读键要么有活跃写方，要么删除——不允许读全仓无写方的键。
2. 消灭"假 FAIL"：读方的键空间/命名族/格式与真实写方一致，合法生产数据 100% 通过。
3. 建立**读键↔写键对账 lint**（新增 `tools/lint_key_reconciliation.py`），机械拦截未来漂移——这是防止 67 条同根因复发的唯一防线。

## 任务分解

- **T1 · 死检查清剿（F340 的 F349/F406/F419 子面、F450-F455、F458 残存（G7.14/G7.15/G0.10 glob）、F464/F465/F466、F467/F468/F470、F639）**：逐条二选一——补写方（若该数据确需产生）或删除检查（若数据已废弃）。修复形状建议：优先删检查与数据面（死数据 + 死检查一起清，与 C37 死代码簇衔接但本 spec 只处理"读键无写方"面）；.gate-lock（F467）裁决后落地——当前全仓无写方即无互斥效果，与 C11 并发簇联动。约束：触碰 gate 检查器时保持纯函数/幂等/structlog（AGENTS.md）。
- **T2 · marker 协议单源（F121/F129/F131/F463/F1111 空转面）**：marker 文件命名族（`G4-<skill>-<test-type>.json`）收敛为单一模块常量，写方（评分路径）与读方（marker 强制检查）都从该常量取值；bug-hunt/clean 类型补写方（含 G4 CLI `--test-type` flag 扩展——当前 gates/cli.py:121 硬编码 generative）。读方兼容双命名族过渡（历史产物不破坏），旧命名族退役时点 = 下一涉及 scoring/marker 面的 PR。验收锚点：`shenbi-score --test-type bug-hunt` 不再 MARKER_MISSING exit 3。
- **T3 · rubric 适用性残面（F122/F128/F137；F104/F757 解析面已由 #9 R4 核销，仅剩 T7 lint 面）**：scope 区间解析改全区间展开（"3-7"→{3..7}）；F128/F137 按 08-15 ledger 逐条对账（缺格默认语义、表头残面）；以真实 18 份 rubric 全量对账断言收尾。
- **T4 · g_reconcile/评分读键对齐（F449/F710/F130/F435/F462）**：GR.1/GR.2 状态词表对齐唯一写方 `done`（消除 `DONE` 大小写死线）；G3.2 读键对齐 scoring 实际输出形状——`_compute_rubric_weighted_score` 回退（g3.py:26-60）是否覆盖 canonical `final_score`+嵌套 `dimensions`，不匹配则补；F435 在 cmd_post_skill 新形状（phase_runner.py:247-261）下核对 Route C 侧车索要行为。
- **T5 · 管线触发器格式对账（F340/F369/F370、F303/F341、F372、F374、F375/F643、F511、F891/F309/F312/F322/F364、F524 对账面、F238/F373 残面 chapter_loop.py:1311）**：`_any_audit_has_findings` 扫描名单从 `audit_suffix()` 单源派生（group-*/era/fanfic/highpoint 补入，消除 F340 P0 与 F369）；`"FAIL" in text` 改精确标记匹配（F370）；每个触发器/解析器以 `novel-output/xinghuo-ranqiong` 真实产物为基准写对账断言（解析非空/触发可达）；审计级联 CORE/CASCADABLE 词表补 group-* 短名与 era/fanfic/highpoint 维度；resonance 解析器按技能自产格式实样对齐；avg G3 分数抓取（cost/report.py:18-34）改为只取明确契约键（F511）。
- **T6 · 写而不读数据裁决（F222 核销/残面、F225/F229/F469/F527/F640、F240/F241/F629）**：逐字段裁决保留（补消费者）或删除；与 C37 联动。每字段终态 = 有消费者（grep 复核锚点）或已删除，二选一落验收。
- **T7 · 对账 lint 落地**：`tools/lint_key_reconciliation.py`——对每个 gate/管线读键做"写方存在性"静态断言（读键命名族 ∈ 写方产出命名族），接入 `just check` 与 ci.yml lint 面（与 C25 联动）。
- **T8 · 生产面修复验证**：F1103（revision_count/resonance_score 死字段）、F1107（BLOCKING 汇总抑制）、F1111（marker 空转/被覆写）、T105（context-decisions 断产静默落空）在修复后以 xinghuo-ranqiong 树复验。

## 批量清理（纯 M 成员）

- F136（gate_markers_verified 空转记 true）、F353（triggers G3 失败不写 last_trigger_failure，stage 值族补 "g3"）、F444（memory-distill L5 把 book_spine 当蒸馏产物校验→文件族改对）——随 T1/T5 批量处置，不逐条开修复项。

## 验收标准

1. `uv run shenbi-score <rubric> <scores.json> --test-type bug-hunt --round-dir <round>` exit 0（round 目录由 T2 实施时经 `shenbi-validate G4 <skill> <files> --test-type bug-hunt` 真实产出 marker 后构成——G0.9 禁手写 fixture；rubric/scores 引用 tests/ 既有真实样本），不再 MARKER_MISSING（F463 断言——marker 检查仅在 --round-dir 传入时执行）；历史 marker 样本（`tests/baselines/gate-outputs/G4-genre_config.json`）经读方解析不破坏（T2 双命名族过渡断言）。
2. `uv run shenbi-validate G_RECONCILE <dir>` 对真实 `*-scores-subagent.json`（codex 写方产物；测试以 dispatcher/modes/codex.py 输出构造逻辑驱动的回归样本表达）报告零 `status=?` 假 FAIL（F449/F710 断言）。
3. `uv run python tools/lint_key_reconciliation.py` exit 0（首周期 WARN 模式可 exit 0 但零 WARN 输出），且对 gate/管线读键清单（本 spec T1-T5 涉及的 40+ 读键）全量断言写方存在。
4. 死检查清单复核：`git grep -n "G0.7\|GT.3\|\.gate-lock"` 确认删除或已接线，无恒 PASS 死分支残留。
5. T6 字段终态：F225/F527/F640/F469/F240/F241/F629 每字段 grep 有消费者锚点或代码面已删除（逐字段清单落 plan 验收表）。
6. `just check` 全绿；对 xinghuo-ranqiong 生产树重跑章节循环触发器单测（resonance/audit_drift/style_profile 解析非空断言，F372/F375/F643 复验）。

## 风险与回滚

- 风险：删除死检查可能移除"未来才接线"的占位门禁（如 .gate-lock 若 C11 需要锁标记文件）；T1 每条删除前核对 C11/C22 簇 spec 是否依赖同面。**依赖**：spec #48（gate-runner 路径协议）是 T7 对账 lint 验收的地基——#48 未归档期间 T7 以独立 CLI 先行（见 T7 设计节）。命名族收敛改动写方会破坏历史产物兼容——采用读方兼容双命名族过渡，退役时点见 T2。
- 回滚：T1-T6 逐任务独立提交（`fix: ...`），对账 lint（T7）单独 PR，可独立 revert；lint 先 WARN 一个周期再升 FAIL（开关形态见 T7 设计节）。

## 簇成员清单（与 phase4-clustering.md §2 机械对照）

C1（67 条，代表 F462）：

F104 F121 F122 F128 F129 F130 F131 F136 F137 F222 F225 F229 F238 F240 F241
F303 F309 F312 F322 F340 F341 F342 F349 F353 F364 F369 F370 F372 F373
F374 F375 F406 F419 F435 F444 F449 F450 F451 F452 F453 F454 F455 F458
F462 F463 F464 F465 F466 F467 F468 F469 F470 F511 F524 F527 F629 F639
F640 F643 F710 F726 F727 F757 F891 F1103 F1107 F1111 T105
