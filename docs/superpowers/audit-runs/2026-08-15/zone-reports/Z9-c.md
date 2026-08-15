# Z9-c 分区初审报告（2026-08-15 轮）

- 范围：`zones/Z9-c.files` 全部 233 文件 = `docs/superpowers/plans/` 69（INDEX + archive 68）+ `docs/superpowers/audit-runs/2026-08-14/` 164（清单内）
- 审查者：Z9-c 初审 agent（只读；除本文件外未写任何仓库文件；未 git add/commit；未运行 pytest/dispatch/pipeline）
- 编号段：F967–F999（实际使用 F967–F975，共 9 条）
- 处置（DV1 裁量）：plans/ 69 机械全量 + 抽读 5；上轮语义文档 9 深读；机械归档（d1 11 + zones 19 + zone-reports 110 + thread-reports 15）批量完整性 + 计数对账
- 核验脚本：/tmp/z9c/check_plans.py、/tmp/z9c/check_refs2.py（及会话内联 python，均为只读）

## 0. 总体结论

两簇整体质量中上。plans/ 的 68 份归档 plan 无空文件/无截断、最新 5 份（2026-08-02/08-15）验收表引用路径 0 缺失；上轮审计产物（2026-08-14）的核心机械统计**基本诚实**：table-A(2738) ⊆ coverage-ledger(2908) 完全闭合（差值 170 = self-artifact 160 + 表 B audited 3 + cache-ignored 4 + generated-excluded 3）、G6 552 样本/228 ok、spotcheck 40/40、d1-06 1448 行、merged 35、P0×5/P1×118 均与台账实测一致。主要问题：**① INDEX 计数漂移族复发**（plans/INDEX 66/63 vs 磁盘 68，上轮 F1106 已立案未修）；**② 归档 plan 的 spec 引用批量路径漂移**（32 个引用指向迁移前路径，0 真死链）；**③ 上轮 final-report 多处统计未随晚到补录同步**（总数 781 vs 台账 786、verified 655 vs 660、线程 98 vs 103、spec 12 份 vs 20 份、活跃 14 vs 23）；**④ coverage-ledger 1008 行锚点指向不存在的 Z7.md/Z8.md**。

严重度分布：P2×4（F967/F968/F969/F970）+ M×5（F971–F975）。无 P0/P1。

---

## 1. Findings 清单

| ID | 标题 | 类别 | 严重度 | 证据 | 根因 | 验证 | 建议方向 |
|---|---|---|---|---|---|---|---|
| F967 | plans/INDEX.md 归档计数漂移（上轮 F1106 复发）：:4 声称"已归档 66"、:23 声称"63 个已完成的 plan"，磁盘 archive/ 实际 68 个（06 月 30 + 07 月 33 + 08 月 5） | error | P2 | docs/superpowers/plans/INDEX.md:4,23; plans/archive/ 目录 | 新 plan 归档（2026-08-15-pipeline-never-completes 等）后 INDEX 计数仅 +1（65→66）未对齐基线缺口；F0-04/F1106/F1115 计数漂移族第 4 实例。同仓 specs/INDEX.md 已改为"本页不追踪归档"（F0-04 的修复方向），plans/INDEX 未跟进 | `ls docs/superpowers/plans/archive \| wc -l` = 68；`grep -n "已归档\|个已完成" INDEX.md` → 66(:4)/63(:23)；上轮 Z9.md F1106 记录当时为 65/63 vs 67 | 修正计数，或仿照 specs/INDEX 改为不追踪归档计数（自动化/链接 archive 目录） |
| F968 | 归档 plan 的 spec 引用批量路径漂移：68 份 plan 中 34 个 distinct spec 引用有 32 个按原路径不存在（全部可在 `specs/archive/` 按 basename 找到，**0 真死链**）；含 `docs/specs/` → `docs/superpowers/specs/` 目录级前缀漂移（2026-06-08 两份 plan） | error | P2 | plans/archive/*.md `**Spec:**`/正文引用；例：2026-08-15-pipeline-never-completes.md:10 引用 `docs/superpowers/specs/2026-08-14-pipeline-never-completes-design.md`（实际在 specs/archive/）；2026-06-14 p-1.a/b/c/d 4 份引用 p-1-foundation-hygiene-design.md | specs 迁移/归档（移入 archive/）时未回写 plan 内引用；归档文档无人维护（上轮 T1001 行号再漂移、F1116 协议文档引用归档路径同族） | /tmp/z9c/check_refs2.py 全量输出：32 DRIFT + 2 OK-orig + 0 TRUE-DEAD；`find docs -name 2026-08-14-pipeline-never-completes-design.md` → specs/archive/ 命中 | 归档时批量 sed 重写引用，或引用改为"specs/ 按 basename 解析"约定；至少在 plans/INDEX 归档说明加"spec 已全部移入 specs/archive/"注记 |
| F969 | 上轮 final-report.md 统计未随晚到补录同步（内部自相矛盾）：§2 "总 findings: 781（655 verified + 90 specced）" vs §5 "findings-ledger（786）" vs 台账实测 786 行（660 verified + 90 specced + 35 merged + 1 FP）；§1 "T1-T15（15 条，98 findings）" vs 台账 T 前缀 103 条（progress 续 16 补录 T6-01~05 +5 后未回写）；§5 "12 份 spec…INDEX 登记 14 活跃" vs progress 续 30 补齐 8 份 spec、活跃 15→23（现 specs/INDEX.md:4 = 23 ✓） | error | P2 | docs/superpowers/audit-runs/2026-08-14/final-report.md:13,28,55-56; findings-ledger.md（786 数据行）; progress.md:102,176-180 | 晚到补录（T6 五条、F4A5、F1322、spec 补齐 8 份）后 final-report 仅部分更新（§5 的 786 是终值，§1/§2 是旧值）；progress 续 20 声称"final-report 同步 781→784"但磁盘仍为 781，说明该同步未落盘或被后续覆盖 | field-4/last-field 解析 786 行：verified=660/specced=90/merged=35/FP=1；`grep -c "^\| T" findings-ledger.md` 逻辑等价脚本 → 103；`grep -n "活跃 spec 数" specs/INDEX.md` → 23 | 归档前以台账为单一信源重生成 final-report 统计段；或加"统计快照时点"戳 |
| F970 | 上轮 coverage-ledger 1008 行报告锚点指向不存在的报告文件：908 行 → `zone-reports/Z7.md`、100 行 → `zone-reports/Z8.md`，实际仅有 Z7-a/b/c/d.md 与 Z8-a/b/c.md（拆分派发后未回写链接） | error | P2 | coverage-ledger.md（Z7/Z8 相关行）；zone-reports/ 目录清单 | Z7（908 文件）/Z8（100 文件）拆分为 4/3 个子段派发，coverage-ledger 的报告链接列仍指向拆分前的单文件路径 | python 遍历 coverage 行 → 锚点目标存在性：`{'zone-reports/Z8.md': 100, 'zone-reports/Z7.md': 908}` 缺失；其余 1900 行锚点全部存在 | 批量改写为 Z7-a~d/Z8-a~c；或归档时加 Z7→拆分的重定向说明 |
| F971 | final-report 覆盖率数值与归档工件不一致：:15 称"1448 真实未覆盖行（85.16% cov 版本）"，磁盘 d1/coverage.xml `line-rate="0.8728"`（87.28%），上轮 F514 自己也引用 0.8728 | error | M | final-report.md:15; d1/coverage.xml:2; findings-ledger.md:169 (F514) | 两次污染修复重生成后 final-report 未取终值（85.16% 为中间版本读数） | `head -c 300 d1/coverage.xml` → line-rate="0.8728"；`wc -l d1/d1-06-coverage-gaps.txt` = 1448 ✓（行数一致，比率不一致） | 统一为工件终值 87.28% 或注明口径（line vs pytest 汇总） |
| F972 | 上轮 findings-ledger 行格式缺陷：15 行仅 10 列（缺"建议方向"列，如 F514/F1300/F1322/F343/F344/F128-F133/F529/F642/F260/F269/F4A5）；F417 严重度列为占位 `—`；F627/F149/F160/F1205/F653 标题含未转义 `\|` 致固定索引 split 错位（progress.md:76 自认该脆弱性） | error | M | findings-ledger.md:169 (F514 10 列)、行 F417（严重度 '—'）、行 F627/F149/F653（field-4 非标准）；progress.md:75-76 | 补录行未按 11 列模板；管道符未转义。注：严重度合计经人工矫正后与声称一致（P0 5/P1 118/P2 496/M 166/F417 — = 786），无统计失真 | 11 列严格解析 → 15 行 MALFORMED；field-4 解析 → 6 行非标准严重度值 | 补录脚本加列数校验；管道符转义为 `\|` 或改 CSV |
| F973 | 上轮 zones 清单记账缺口：zones/*.files 并集 2755 vs table-A 2738，差 17 项（.superpowers/sdd* 12 + 运行时日志 2 + 3 项）未在任何文档归类（表 B 亦无对应说明）；Z7.files（908）vs Z7-a/b/c/d 之和（930）差 22 无说明 | error | M | zones/table-A-all-files.txt（2738 行）; zones/Z7*.files 计数（908 vs 314+445+119+52=930）; zones 并集 diff 输出 17 项 | Z7 拆分派发时子段清单含新增文件；sdd/运行时日志为表 B 磁盘产物但未入表 B 台账 | /tmp 对账脚本：`in zones but NOT in table-A: 17`（.superpowers/sdd/audit-T1..T7.md 等）；`tableA - cov: 0`（表 A 闭合无洞） | 拆分时同步更新 Z7.files 或注明子段清单为增量权威；17 项补入表 B 台账 |
| F974 | 归档 plan 完成状态未回填：68 份已归档（对应 PR 已合并）plan 中 63 份全部复选框未勾选（`- [ ]`）、2 份部分勾选（2026-06-11-test-framework 62 未勾/11 勾；2026-07-08-contract-consistency 114 未勾/15 勾）、3 份无复选框 | error | M | plans/archive/*.md（checkbox 扫描）；plan 模板声明 "Steps use checkbox syntax for tracking"（各 plan 头部） | 执行期跟踪未随归档回填，完成证据只存在于 PR/INDEX | python 全量扫描：all-unchecked 63 / mixed 2 / all-checked 0 / neither 3 | 归档时批量勾选或注明"完成状态见 PR"；避免读者误判 plan 未执行 |
| F975 | 本轮分区清单缺口：`zones/Z9-c.files` 漏登 `docs/superpowers/audit-runs/2026-08-14/d1/coverage.xml`（磁盘 2026-08-14 目录 165 文件 vs 清单 164；该文件已在本报告核验，非未覆盖） | error | M | zones/Z9-c.files（233 行，无 coverage.xml）; `find docs/superpowers/audit-runs/2026-08-14 -type f \| wc -l` = 165 | 分区清单生成时排除了该 XML（或按 *.md/.log/.files 过滤） | `comm -23` 磁盘 vs 清单 → 仅 d1/coverage.xml 一项 | 协调者将 coverage.xml 补入某分区或登记为表 B 类机械产物 |

---

## 2. 簇条目

### docs/superpowers/plans/（69 文件 = INDEX.md + archive/68）
- 处置: deep-read（机械核验 68 + INDEX 深读 + 抽读 5 份归档 plan）
- 声称检查的不变量:
  1. INDEX ↔ 磁盘双向闭合（活跃 0 + 归档计数）
  2. plan 头部 schema（de facto：Goal/Architecture/Tech Stack/Spec；Status/复杂度/test_kind 非该仓 plan 契约——0/68 有 Status 字段、3/68 提及 test_kind，plans/INDEX 与 specs/INDEX 均未要求这些字段，故不构成违反）
  3. spec 交叉引用有效（34 distinct 引用）
  4. 验收覆盖表真实性（引用的 tests/src 路径存在）
  5. 无空文件/截断
- findings: [F967, F968, F974]
- 验证命令+输出摘要:
  - `find docs/superpowers/plans -type f | wc -l` = 69；archive 按月 30/33/5 = 68
  - /tmp/z9c/check_plans.py：68 plan，empty=0、truncated=0；**Spec:** 字段 5/68（其余在正文引用）；34 distinct spec 引用 → 32 原路径缺失
  - /tmp/z9c/check_refs2.py：32 DRIFT（basename 全部命中 specs/archive/）+ 2 OK-orig + **0 TRUE-DEAD**
  - 验收路径存在性：68 plan 全量（tests/src 路径 regex）；32/68 含"缺失路径"但均为历史迁移前状态引用（归档语境正常，例：tests/phase-runner.py 已移入 src/）；**最新 5 份（2026-08-02×4 + 2026-08-15）0 缺失**——验收覆盖表现时真实
  - 抽读 5 份（06-08-phase1、06-15-p-1.e-02-pr-fraud、07-19-16-output-integrity、08-02-token-efficiency、08-15-pipeline-never-completes）：验收表均含可执行验证命令且引用真实文件；08-15 的验收覆盖表 13 行逐条映射 R1-R6/F340/F341/F304 → T1-T9，33 个引用路径全存在
- 置信度: high

### docs/superpowers/audit-runs/2026-08-14/ 语义文档（9 文件深读）
final-report.md / findings-ledger.md / coverage-ledger.md / meta-audit.md / progress.md / phase4-root-cause-clusters.md / phase4-spotcheck-report.md / g6-meta-audit-sample.txt / phase4-spotcheck-sample.txt
- 处置: deep-read（9 深读；findings-ledger 786 行逐字段机械解析；coverage-ledger 2908 行锚点全量核验）
- 声称检查的不变量:
  1. final-report 声称数字 ↔ ledger 实际行数（G5 机械统计诚实性）
  2. 台账 schema 一致（11 列）
  3. 表 A ⊆ coverage-ledger 双向闭合
  4. G6/spotcheck 声称数字 ↔ 样本文件行数
  5. 修复声称可提取（转本轮 T10）
- findings: [F969, F970, F971, F972]（+F973 关联 zones/）
- 验证命令+输出摘要（诚实性对账，**通过项**）:
  - 台账 786 数据行 = verified 660 + specced 90 + merged 35 + false-positive 1（§5 的"786" ✓；§2 的"781/655" ✗ 见 F969）
  - 严重度：P0=5（F324/F397/F364/F302/F1300 与 §2 清单一致 ✓）/ P1=118 ✓ / P2=496、M=166（含 6 行错位行人工矫正后 ✓，与 progress 续 22 裁定、续 30 闭合声明一致）；ID 零重复 ✓
  - 表 A：2738 行（table-A-all-files.txt）⊆ coverage-ledger 2908 唯一路径（tableA − cov = **0**）；差值 170 = self-artifact 160 + audited 表外 3 + cache 4 + generated 3 —— 完全闭合 ✓
  - G6：sample 文件 552 行 ✓；判定 228 ok / 0 样本级 fake / 2 finding 级（Z11 F1306/F1320，均入复查并由 Z11.review 落实修正）✓；final-report:14 "0 fake-deep-read（Z11 4 处子声称修正）" 为样本级口径，与 meta-audit 结论一致（措辞差异不立案）
  - spotcheck：样本 40 行 ✓、报告 40/40 证据充分+结论准确、3 对跨区重复合并建议已被 progress 续 15/续 22 G7 裁决落地（F269/F260 升 P2）✓
  - d1-06 = 1448 行 ✓；merged=35 ✓；FP=1（F325 撤销）✓；轮次历史 vs zone-reports 文件数：Z1 16 ✓、Z2 17 ✓、Z3 19+校准（review20=校准补复核，final-report 已注明）✓、Z4 16 ✓、Z5 6 ✓、Z6 17 ✓、thread-reports 15 ✓
- 置信度: high

### docs/superpowers/audit-runs/2026-08-14/d1/（清单内 11 + 清单外 1）
- 处置: 机械批量（11 非空/结尾完整 + d1-baseline.md 深读 + coverage.xml 头部核验）
- 声称检查的不变量: 文件非空、日志非截断（结尾有正常终止输出）、"12 项基线扫描" 计数
- findings: [F971（比率）, F975（清单漏登）]
- 验证命令+输出摘要: 12 文件全非空；final-report "d1/ 基线 12 项" ✓（11 清单内 + coverage.xml）；d1-01-just-check.log 以正常汇总结尾、d1-11-skip 系列与 skipxfail.txt 计数互相吻合；coverage.xml line-rate=0.8728（见 F971）
- 置信度: high

### docs/superpowers/audit-runs/2026-08-14/zones/（19 文件）
- 处置: 机械批量（计数对账 + 条目存在性抽验）
- 声称检查的不变量: .files 条目均存在于磁盘；Z8.files = Z8-a+b+c；table-A ⊆ zones 并集
- findings: [F973]
- 验证命令+输出摘要: 各 .files 行数 Z1:14 Z2:38 Z3:34 Z4:52 Z5:13 Z6:49 Z7:908 Z7-a:314 Z7-b:445 Z7-c:119 Z7-d:52 Z8:100 Z8-a:34 Z8-b:33 Z8-c:33 Z9:214 Z10:52 Z11:1281；并集 2755；Z8 拆分闭合 ✓（34+33+33=100）；Z7 拆分差 22（F973）；条目抽验（.superpowers/sdd/audit-T1.md 等）磁盘均存在
- 置信度: high

### docs/superpowers/audit-runs/2026-08-14/zone-reports/（110 文件）
- 处置: 机械批量（非空/结尾完整/围栏平衡）+ 深读 Z9.md + 抽读 Z11.review.md、Z2.review17.md、Z3.review3.md
- 声称检查的不变量: 110 份全部非空、无中途截断；上轮 Z9（同域）findings 可映射本轮
- findings: 无新增（围栏奇数 4 例均为表格/行文内联反引号误报：findings-ledger F271 行、Z11.review:21、Z2.review17:15/109/111、Z3.review3 各块，文件结尾均为完整结论段）
- 验证命令+输出摘要: python 完整性扫描 165 文件 EMPTY=0；UNCLOSED-FENCE 4 例逐一人工核判为误报；Z9.md 深读确认其 17 findings（P2×4+M×13）中 F1106 与本轮 F967 同域复发、F1116 与 F968 同族
- 置信度: high

### docs/superpowers/audit-runs/2026-08-14/thread-reports/（15 文件）
- 处置: 深读 T10.md（历史修复回归核验，本轮 T10 线程直接输入）+ 其余 14 机械批量 + 关键结论抽读（T5/T13/T15 与修复声称交叉）
- 声称检查的不变量: 15 份非空完整；T10 声称与台账 T1001/T1002 登记一致
- findings: 无
- 验证命令+输出摘要: 15 文件非空；T10.md 统计（19 声明：17 ✅/0 ❌/1 partial）与台账 T1001（P2）/T1002（M）登记一致 ✓；T5 明确 PR #40 finish_reason 保护仅 API 路径成立（T505）——本轮 F 修复回归核验时须沿用该口径
- 置信度: high

---

## 3. 上轮修复声称清单（本轮 T10 线程输入，22 条）

来源：thread-reports/T10.md（19 条）+ 台账/上轮自述（3 条）+ plans/INDEX（1 条）。

| # | 声称 | 出处 | 上轮核验 |
|---|---|---|---|
| 1 | TokenLedger 接线（PR #39 `d4b4e83`，spec §3.1 dead-wire 修复） | T10.md:14 | ✅ 存在（dispatch_helper.py:1333） |
| 2 | finish_reason=length 检测 + cap-raise（PR #40 `0be00bb`） | T10.md:15 | ✅ 存在（仅 API 路径；T505 注记 IDE/legacy 无保护） |
| 3 | truth_io upsert 调用方全覆盖（CN3 覆盖 bug 修复） | T10.md:16 | ✅ 存在（注意与 F397/F1104 的 append_dedup 路径区分） |
| 4 | torch-bump 处置 follow-up（PR #28 `1eb6e22`；torch 锁 2.13.0 + dependabot direct + embeddings-smoke） | T10.md:17 | ✅（INDEX:91 注记过期 → T1002） |
| 5 | cyclic-import 重构（PR #26 `4d228f7`，issue24） | T10.md:18 | ✅（`py/cyclic-import` 0 命中） |
| 6 | silent CWD fallback 移除（Task 15b，g4 resolve_input_path） | T10.md:19 | ✅ |
| 7 | G0.16 skill 契约验证 + P2.5 rationale 规则（AGENTS.md:70） | T10.md:20 | ✅ |
| 8 | 决策 JSON 恢复（`_validate_json_output` raw_decode + DecisionsDoc 校验） | T10.md:21 | ✅ |
| 9 | 文档行号漂移修复（sdd spec-deviations D1 spec 文本订正） | T10.md:22 | ⚠️ partial——订正值已再漂移 7-22 行（T1001） |
| 10 | PR #23 Issue 1：mkdocs 14 死链已修（`1933483`）+ pre-push --strict 拦截 | T10.md:28 | ✅ |
| 11 | PR #23 Issue 7：G0.11 fixture 漂移已修 + MIRROR_MAP 单一源 + pre-commit 钩子 | T10.md:29 | ✅（当时 sha256 一致） |
| 12 | PR #25 Gap B：pre-push pip-audit 锁 dev 组 | T10.md:30 | ✅ |
| 13 | PR #40 audit-T5：pro→flash 文档漂移订正 | T10.md:31 | ✅ |
| 14 | PR #40 audit-T6：RETRY_JITTER 加宽（2.0） | T10.md:32 | ✅ |
| 15 | PR #40 audit-T7：定价 fail-loud + ledger 守卫 | T10.md:33 | ✅ |
| 16 | PR #28：renovate.json 移除 + ci renovate step 移除 | T10.md:34 | ✅ |
| 17 | PR #40 audit-T3：drafting max_tokens 32768 | T10.md:35 | ✅ |
| 18 | PR #16/#17：字段级 reads（dict-form）落地 | T10.md:36 | ✅（注意本轮 F201/F836 指出该特性语义缺陷，非回归） |
| 19 | F508/F514：coverage.xml 污染重生成（d1-06 1448 行真实版，line-rate 0.8728） | findings-ledger.md:24,169 | ✅（磁盘工件佐证；但 final-report 85.16% 未同步 → F971） |
| 20 | F860：.hypothesis 17 个失败样本已修复 | findings-ledger.md:760 | 未独立核验（上轮清点确认） |
| 21 | 共享 coverage.xml 写竞争修复（独占 COVERAGE_FILE 运行） | final-report.md:66(§6.5) | 未独立核验（上轮自述） |
| 22 | PR #42：pipeline-never-completes（spec #6，R1-R6+F340/F341/F304）交付归档 | plans/INDEX.md:12; plans/archive/2026-08-15-pipeline-never-completes.md | 本轮未核验——**本轮 T10 重点**（上轮 P0×5 簇 1 的修复落地） |

## 4. 新旧 findings 重叠映射（同域不同 ID，供阶段 4 聚类）

本轮 ledger（418 行，P0×10/P1×64）与上轮 P0/P1 的重叠初判——**复发主因是上轮 spec 已产出未实施**（specs/INDEX 活跃 23 个中 #6-#16/#18-#25 均为上轮派生；簇 1 除外，PR #42 已交付待回归）：

| 上轮 ID(严重度) | 域 | 本轮 ID | 备注 |
|---|---|---|---|
| F397 (P0) | append_dedup no-op，chapter_summaries 2/56 | F1104 | 本轮自注"历史 finding 原样复现" |
| F1300 (P0) | 5 章正文被摘要覆写 | F1101 | 同域复发 |
| F302 (P0) | TokenLedger 少计 | F301/F302/F504/F505/F1115 | 分解为多点复发（by_chapter 坍缩/8 调用点/全仓不存在） |
| F364 (P0) | atexit 清 staging | F1108/F1109 | Z11 输出域关联 |
| F601 (P1) | drift >5.0 off-by-one | F602 | 逐字同域 |
| F602 (P1) | establish_baseline 零调用 | F604 | 逐字同域 |
| F608 (P2) | 引号桶恒 0 | F601 | 同域升 P1 |
| F606 (P2) | floor float 绕过 | F603 | 同域升 P1 |
| F507 (P1) | deleted 零拦截 | F502 | 同域复发 |
| F512 (P1) | 写审计主路径绕过 | F518 | 同域复发 |
| F218 家族 (P1) | 字段过滤部分匹配丢弃 | F201 | escape-hatch 契约同域 |
| F1205 (P2) | run_pipeline.sh auto-approve 过宽 | F002 | 同域升级 |
| Z11-01 (P1) | decisions.json 44/89 无效 | F1102 | 88/145（61%），恶化 |
| F1106 (M，本段域) | plans/INDEX 计数漂移 | **F967（本段）** | 65/63→66/63 vs 67→68，未修仅 +1 |
| F1116/T1001 (M/P2，本段域) | 归档引用断链/行号漂移 | **F968（本段）** | plan→spec 方向的同族扩展（32 处） |
| F0-04/F1115 (M) | specs/INDEX 计数漂移 | （已修复） | specs/INDEX 改为不追踪归档——修复方向验证了 F967 建议 |

非重叠佐证：上轮 F324（volume_map 中文解析）及簇 1 其余 4 根因未出现在本轮 P0/P1 清单——与 PR #42 交付声称一致（待 T10 独立回归）。

## 5. 覆盖统计

- 清单 233/233 全部核验：plans 69（机械 68 + INDEX 深读 + 抽读 5）+ 2026-08-14 164（深读 9 语义文档 + T10 深读 + 批量 155）
- 批量完整性：165 个磁盘文件（含清单外 coverage.xml）全非空、无真截断（4 例围栏奇数均为内联反引号误报）
- 未覆盖文件列表：**空**（清单内 233 全覆盖；清单外 d1/coverage.xml 已附带核验并立 F975 提请协调者）
- 机械核验脚本：/tmp/z9c/check_plans.py、/tmp/z9c/check_refs2.py；其余为会话内联只读 python/grep/find

## 6. 遗留说明

- 本段未运行任何写入型命令；唯一写入为本报告文件。
- F969 的"上轮统计过期"定性为诚实性瑕疵（过期非造假）：所有差异均可由 progress.md 的补录时间线解释，且台账本身自洽。
- 上轮 final-report §2 与台账的严重度合计（785）含 F417 占位行，正确口径为 786 行 = 5+118+496+166+1(F417 '—')。
