> **Date:** 2026-08-16 | **Status:** Design | **Severity:** 🟥 Critical | **方法:** systematic-debugging 四阶段
> **系列:** 2026-08-15 全项目深度审计 · 阶段 5（簇 C1，67 条）| **代表 finding:** F462 | **严重度上限:** P0（F340）| **涉及文件面:** src/shenbi/gates/（g0-g7、g_reconcile、cli）、scoring.py、pipeline/（chapter_loop、phase_runner、parallel_dispatch、audit_context_cache、trace/materialize）、新增 lint 对账工具

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

- **T1 · 死检查清剿（F450-F455、F458、F463-F470、F136、F466、F467、F468）**：逐条二选一——补写方（若该数据确需产生）或删除检查（若数据已废弃）。修复形状建议：优先删检查与数据面（死数据 + 死检查一起清，与 C37 死代码簇衔接但本 spec 只处理"读键无写方"面）；.gate-lock（F467）裁决后落地——当前全仓无写方即无互斥效果，与 C11 并发簇联动。
- **T2 · marker 协议单源（F121/F129/F131/F463）**：marker 文件命名族（`G4-<skill>-<test-type>.json`）收敛为单一模块常量，写方（评分路径）与读方（marker 强制检查）都从该常量取值；bug-hunt/clean 类型补写方。验收锚点：`shenbi-score --test-type bug-hunt` 不再 MARKER_MISSING exit 3。
- **T3 · rubric 适用性机制修复（F104/F757/F122/F128/F137）**：load_applicability 按真实 18 份 rubric 表格格式解析（或修订 18 份 rubric 至解析器可读格式，二选一后全量对账）；scope 区间解析改全区间展开（"3-7"→{3..7}）。
- **T4 · g_reconcile/评分读键对齐（F449/F710/F130/F462）**：GR.1/GR.2 状态词表与 '-scores' 后缀处理对齐唯一写方；G3.2 读键对齐 scoring 实际输出形状（final_score + 嵌套 dimensions）。
- **T5 · 管线触发器格式对账（F238/F303/F341/F342/F369/F370/F372/F373/F374/F375/F643/F891/F309/F312/F322/F364）**：每个触发器/解析器以 `novel-output/xinghuo-ranqiong` 真实产物为基准写对账断言（解析非空/触发可达）；审计级联 CORE/CASCADABLE 词表补 group-* 短名与 era/fanfic/highpoint 维度；resonance 解析器按技能自产格式实样对齐。
- **T6 · 写而不读数据裁决（F222/F225/F229/F469/F527/F640）**：逐字段裁决保留（补消费者）或删除；与 C37 联动。
- **T7 · 对账 lint 落地**：`tools/lint_key_reconciliation.py`——对每个 gate/管线读键做"写方存在性"静态断言（读键命名族 ∈ 写方产出命名族），接入 `just check` 与 ci.yml lint 面（与 C25 联动）。
- **T8 · 生产面修复验证**：F1103（revision_count/resonance_score 死字段）、F1107（BLOCKING 汇总抑制）、F1111（marker 空转/被覆写）、T105（context-decisions 断产静默落空）在修复后以 xinghuo-ranqiong 树复验。

## 批量清理（纯 M 成员）

- F136（gate_markers_verified 空转记 true）、F241（ProgressDoc 键空间对齐）、F353（triggers G3 失败不写 last_trigger_failure，stage 值族补 "g3"）、F370（"FAIL" 裸子串匹配过宽→精确词匹配）、F444（memory-distill L5 把 book_spine 当蒸馏产物校验→文件族改对）——随 T1/T5 批量处置，不逐条开修复项。

## 验收标准

1. `uv run python -m shenbi.score <rubric> <scores.json> --test-type bug-hunt`（tests/fixtures 真实样本）exit 0，不再 MARKER_MISSING（F463 断言）。
2. `uv run shenbi-validate G-reconcile <dir>` 对真实 `*-scores-subagent.json` 报告零 `status=?` 假 FAIL（F449/F710 断言）。
3. `uv run python tools/lint_key_reconciliation.py` exit 0，且对 gate/管线读键清单（本 spec T1-T5 涉及的 40+ 读键）全量断言写方存在。
4. 死检查清单复核：`git grep -n "G0.7\|GT.3\|\.gate-lock"` 确认删除或已接线，无恒 PASS 死分支残留。
5. `just check` 全绿；对 xinghuo-ranqiong 生产树重跑章节循环触发器单测（resonance/audit_drift/style_profile 解析非空断言，F372/F375/F643 复验）。

## 风险与回滚

- 风险：删除死检查可能移除"未来才接线"的占位门禁（如 .gate-lock 若 C11 需要锁标记文件）；T1 每条删除前核对 C11/C22 簇 spec 是否依赖同面。命名族收敛改动写方会破坏历史产物兼容——采用读方兼容双命名族过渡。
- 回滚：T1-T6 逐任务独立提交（`fix: ...`），对账 lint（T7）单独 PR，可独立 revert；lint 先 WARN 一个周期再升 FAIL。

## 簇成员清单（与 phase4-clustering.md §2 机械对照）

C1（67 条，代表 F462）：

F104 F121 F122 F128 F129 F130 F131 F136 F222 F225 F229 F238 F240 F241
F303 F309 F312 F322 F340 F341 F342 F349 F353 F364 F369 F370 F372 F373
F374 F375 F406 F419 F435 F444 F449 F450 F451 F452 F453 F454 F455 F458
F462 F463 F464 F465 F466 F467 F468 F469 F470 F511 F524 F527 F629 F639
F640 F643 F710 F726 F727 F757 F891 F1103 F1107 F1111 T105
