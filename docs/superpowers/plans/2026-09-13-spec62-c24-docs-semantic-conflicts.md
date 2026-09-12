# Spec #62 · C24 文档语义矛盾批量修复 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 消除 C24 簇 45 条文档语义矛盾——每条裁决出唯一权威版本并同步所有出现处，INDEX/spec 体系自洽，评分刻度全仓统一。

**Architecture:** 纯文档改动零代码。裁决次序 = 代码/配置实值 > 最近设计决策 > 多数版本；裁决表内嵌本 plan（Task 1 产物）。七个 task：裁决表 → DOT/契约面 → 缺失件 → 术语刻度 → INDEX/spec 体系 → 配置注释 → 验收电池。执行为**单分支单 PR**（spec 风险节原提三 PR，deviation：SDD 串行纪律 + 每批 CI 成本，audit_loop 全量重审替代三 PR 的评审隔离，见 spec-deviations）。

**Tech Stack:** grep/Edits/`just check`（含 doc-links 551 测试）/`just lint-contracts`/`just generate`

## Global Constraints

- AGENTS.md：DOT 为权威过程定义；anti-rationalization 表为关键 skill 必件；conventional commits
- 零 `src/` 代码改动（唯一例外：无——F707 修 docstring 在 tests/，F1024 已归 #66）
- 归档 spec/plan 勘误 = 文内**追加**勘误注（#197/#178 先例），不重写裁决内容
- gittracked truth 实证对象（F949）不改 truth 文件本体，只修归档 spec 内的过期描述
- F1157（gitignored `.superpowers/`）local-only 修复不进 PR
- 契约相关文本（F841 group-* Contract YAML）改动后必须 `just lint-contracts` 绿 + `just generate` diff 为空
- 评分刻度权威 = /100（AGENTS.md 0-100 口径）

---

## Task 1 · 裁决表定稿（T1）

**Files:** Modify: 本 plan（裁决表节，随 PR 提交即为交付物）
**Interfaces:** Produces: 下述任务全部裁决依据（保留版本 + 修改位置清单）
**复杂度:** leaf · **test_kind:** characterization（docs）

裁决表（45/45；次序：代码实值 > 最近设计 > 多数版本）：

| ID | 权威版本 | 修改位置 |
|---|---|---|
| F707 | 代码实值 78%（BRANCH_THRESHOLD_PCT） | tests/unit/test_coverage_thresholds.py:26-30 docstring 改述「floor 为 78%（历史 ≥80% 口径已由实值收敛取代）」 |
| F801 | 补 anti-rationalization 表 | skills/shenbi-anchor-curate/SKILL.md 新增节（§4.3 引用半已修） |
| F810 | 删除无关「缺陷证据格式」节；relationship_map→relationships.md | skills/shenbi-character-extraction/SKILL.md:236、:55、:19/:34/:172 对齐 |
| F813 | 补 anti-rationalization 表；escalation_check→run_escalation_check | skills/shenbi-escalation-review/SKILL.md:37（实 helper：orchestration/escalation_bridge.py:28） |
| F829 | DOT 补齐正文强制节点 | score-arc（audit_drift 追加节点）、genre-config（备份节点）、chapter-drafting（PRE_WRITE_CHECK 全列）三个 SKILL.md 的 DOT |
| F837 | 修 DOT 分支条件使 L2/L4 互斥（ch36 只走 L4，L2 条件加 `且非 %36`） | skills/shenbi-memory-distill/SKILL.md:69-71 |
| F841 | 删正文内嵌 Contract YAML（frontmatter 为唯一信源）；chapter_loop.py:1090-1168 → 符号化引用 | 4 个 group-* SKILL.md（group-plan:39,44-56 / group-character:46 / group-craft:41 / group-factual:45） |
| F847 | 空引用补指代对象 | review-continuity:118、review-dialogue:110、review-character:86、review-long-span:100「遵循  定义」→ 指向四要素格式正式定义处（review-* 契约节） |
| F848 | 示例数值与阈值对齐：+15.9% 等标「不满足 >0.20 的示例」或换满足例；窗口示例改「4 个 5 字串」 | skills/shenbi-review-long-span/ngram-methodology.md:14,56,62-64 |
| F850 | 输出模板枚举补 MUTUAL_SECRET（4 态，与 g4/relationship_map.py:47 一致） | skills/shenbi-relationship-map/SKILL.md:119 |
| F851 | B 线统一「中线」；默认值清单补 P3=16 | skills/shenbi-plot-thread-weaver/SKILL.md:59,:70,:144；:86 |
| F852 | DOT 改条件边「有变化→Update」 | skills/shenbi-intent-management/SKILL.md:42 |
| F853 | shenbi-reader-pull→shenbi-review-reader-pull | skills/shenbi-review-group-plan/SKILL.md:121 |
| F855 | 删 description 括注；DOT 扩写路径补 ≥3000 复核节点 | skills/shenbi-length-normalizing/SKILL.md:3-4,:49 |
| F856 | 蔗糖「唐代」、高足椅「唐宋普及」（多数史学口径） | skills/shenbi-review-era/era-reference.md:32-33 |
| F857 | 方法论指针改全路径 skills/shenbi-review-era/era-reference.md 消歧 | skills/shenbi-review-era/SKILL.md:81 |
| F874 | 同 F847 指代补全 | skills/shenbi-review-sensitivity/SKILL.md:74 |
| F876 | 「11 个」→「12 个」；合并双「## 铁律」节 | skills/shenbi-worldbuilding/SKILL.md:82；:62,:104 |
| F879 | 路径改 docs/superpowers/specs/archive/2026-06-08-shenbi-design.md | skills/using-shenbi/SKILL.md:116 |
| F883 | 步骤重编号；二输出模板择一（保留 :166 精确模板，:69 改指针） | skills/shenbi-volume-consolidation/SKILL.md:113-114,:69,:166 |
| F885 | 刻度统一 /100（约 20 处 X/10）；score-arc/stratum/volume description 中英分列 | 全 skills grep `[0-9]+/10` 清扫；三个 score-* SKILL.md:3 |
| F893 | 5 技能补 DOT：foreshadowing-lifecycle + 4 个 review-group-* | 5 个 SKILL.md 各新增 DOT 节 |
| F913 | goal-prompt 快照加「历史快照，现状以 AGENTS.md/INDEX 为准」注 + 修正 59 skill/60 T1/115 fixture 计数 | goal-prompt.md:3,71（skill 数以 tools/lint_registry_reconcile.py 权威计数为准） |
| F914 | 「7-gate (G0-G7)」→「8-gate (G0-G7)」 | CHANGELOG.md:18 |
| F915 | 占位符填实（repo owner GitHub 联系方式） | CODE_OF_CONDUCT.md:43 |
| F916 | ADR-0009 追加失效注（shim 已由 PR-22 0f68102f 删除） | docs/adr/0009-dispatcher-python-rewrite.md:12 后 |
| F918 | 删连续双水平线之一 | docs/getting-started/concepts.md:55,57 |
| F919 | 20 万（goal-prompt+concepts.md 2:1，outline-example 10 万为异值） | outline-example.md:7 + tests/fixtures/outline-example.md:7 → 200000 |
| F935 | INDEX 重排：#40→#63→#64→#6→#65→#62→#66 | docs/superpowers/specs/INDEX.md 执行队列 |
| F936 | 归档 spec 头部补 `# <N>` 编号标记（引用可解析） | docs/superpowers/specs/archive/ 各文件头部（引用到的编号处） |
| F938 | #19 副本重复条目改指针注「由 #22 主登记」 | archive/2026-08-14-decisions-chain-design.md:38,46 |
| F939 | 追加勘误注：头部分级 4+45+318+98=465，与 :8 467 差异源自 false-positive×1 口径 | archive/2026-08-14-full-project-audit-design.md |
| F941 | :34 F125 PR 归因加勘误注（正确为 PR-22，与 :19 F0-05 一致） | archive/2026-08-14-p2-batch-design.md |
| F942 | 追加「历史版本，以 v3 为准」注（T1-T11 → 实际 T1-T16） | archive/2026-08-13-full-project-audit-prompt-design.md:137,204 |
| F943 | §9 文件名加勘误注（实际 2026-08-14-*） | 同上文件 :272-274 |
| F946 | F1100 加勘误注（疑似误报：目标文件可解析于 plans/archive 且 :7 属实） | archive/2026-08-14-p2-batch-design.md:289 |
| F948 | MAX_DISPATCH_DETRIES→MAX_DISPATCH_RETRIES | archive/2026-08-01-output-side-waste-audit-design.md:38 |
| F949 | R1 实证描述加勘误注（现盘 1 行 9 列，以 truth 现盘为准） | archive/2026-08-14-truth-write-path-design.md:9 |
| F950 | 「23 份全部产自同一次」→「多数产自 2026-08-14 audit（20/23），余为 08-01/08-13」 | docs/superpowers/single-model-sdd-prompt.md:247 |
| F1028 | CODEOWNERS 收敛为单默认行 + 差异化段（或删冗余段） | .github/CODEOWNERS |
| F1029 | `弧段/卷级.高光` → `卷级.弧段高光`? 以其余 AC 记法「层级.维度」对齐实值核对后改 | benchmarks/anchors/AC-003.md calibrates 行 |
| F1156 | 12 skill 队列显式 void：INDEX #62 条目注记（本 spec 不承接温度调优，登记为 follow-up 待办或显式不做） | docs/superpowers/specs/INDEX.md #62 条目 + progress 注记 |
| F1157 | 本地删除过时 checklist（local-only，不进 PR） | .superpowers/sdd-archive-inference-control/progress.md:54-61 |
| T1307 | pydantic 注释改「g2 schemas 生产使用中」 | pyproject.toml:11 |
| T1505 | 归档 pipeline-never-completes R6 托付加勘误注（#16/#25 均未含 _shared.py 清理，待新 spec 承接或 void） | archive/2026-08-14-pipeline-never-completes-design.md R6 节 |

- [ ] **Step 1:** 裁决表逐条 grep 现势确认（45/45 行号仍准，漂移则订正）
- [ ] **Step 2:** `uv run pytest tests/integration/test_doc_links.py -q` 基线（预期 551 passed，改动前锚点）
- [ ] **Step 3:** Commit `docs(plan): spec62 c24 adjudication table + task decomposition`

## Task 2 · DOT↔正文与契约面（T2 item 3：F829/F837/F841/F852/F855）

**Files:** Modify: skills/shenbi-{score-arc,genre-config,chapter-drafting,memory-distill,intent-management,length-normalizing}/SKILL.md + 4 个 review-group-*/SKILL.md
**Interfaces:** Consumes: 裁决表对应行 · **复杂度:** leaf · **test_kind:** regression_guard

- [ ] **Step 1:** 按 F841 删 4 个 group-* 内嵌 Contract YAML，行号引用符号化（`chapter_loop.py` 派发函数名）
- [ ] **Step 2:** F829 三 DOT 补节点、F837 互斥条件、F852 条件边、F855 复核节点 + description 括注删除
- [ ] **Step 3:** 验证：`just lint-contracts` 绿 + `just generate` diff 为空 + `uv run pytest tests/integration/test_doc_links.py -q` 551 passed
- [ ] **Step 4:** Commit `docs(skills): spec62 DOT-prose reconciliation + group-* contract yaml dedup (F829/F837/F841/F852/F855)` → audit-T2.md

## Task 3 · 缺失件补齐（T2 item 4：F801/F813/F874/F847/F893）

**Files:** Modify: skills/shenbi-{anchor-curate,escalation-review,review-sensitivity,review-continuity,review-dialogue,review-character,review-long-span,foreshadowing-lifecycle}/SKILL.md + 4 个 review-group-*/SKILL.md（DOT）
**复杂度:** leaf · **test_kind:** regression_guard

- [ ] **Step 1:** F801/F813 补 anti-rationalization 表（对齐既有 skill 的表式）
- [ ] **Step 2:** F847/F874 五处空引用补指代（指向四要素格式定义处）
- [ ] **Step 3:** F893 五技能补 DOT 流程图
- [ ] **Step 4:** 验证：`grep -l "flowchart\|graph TD\|graph LR" <五技能>/SKILL.md` 全命中；lint-contracts 绿
- [ ] **Step 5:** Commit `docs(skills): spec62 missing anti-rationalization tables + 5 DOTs + dangling refs (F801/F813/F847/F874/F893)` → audit-T3.md

## Task 4 · 术语/刻度/杂项（T2 items 5-6：F810/F848/F850/F851/F853/F856/F857/F876/F879/F883/F885）

**Files:** Modify: 上表对应 11 族文件（含 using-shenbi、worldbuilding、volume-consolidation、era-reference 等）
**复杂度:** leaf · **test_kind:** regression_guard

- [ ] **Step 1:** 逐条按裁决表改（F885 先跑 `grep -rnE "[0-9]+/10" skills/` 全清单，豁免项入裁决表附理由）
- [ ] **Step 2:** 验证：`grep -rnE "[0-9]+/10(分| )?" skills/` 剩余命中 = 豁免清单；`shenbi-reader-pull` 0 命中；`MUTUAL_SECRET` 三处同构
- [ ] **Step 3:** Commit `docs(skills): spec62 terminology/scale/misc reconciliation (11 findings)` → audit-T4.md

## Task 5 · INDEX/spec 体系自洽（T3：F935/F936/F938/F939/F941/F942/F943/F946/F948/F949/F950/F913/F914/F915/F916/F918/F919/F707）

**Files:** Modify: docs/superpowers/specs/INDEX.md、specs/archive/ 9 件、docs/superpowers/single-model-sdd-prompt.md、goal-prompt.md、CHANGELOG.md、CODE_OF_CONDUCT.md、docs/adr/0009-*.md、docs/getting-started/concepts.md、outline-example.md + fixtures 副本、tests/unit/test_coverage_thresholds.py:26-30（docstring）
**复杂度:** leaf（全 docs + 一处 test docstring）· **test_kind:** regression_guard

- [ ] **Step 1:** F935 INDEX 重排（#62 条目移至 #66 前，预期序见裁决表）+ 「最后更新」行同步
- [ ] **Step 2:** F936 归档件头部补编号标记（限被引用编号）；F938/F939/F941/F942/F943/F946/F948/F949 归档件追加勘误注
- [ ] **Step 3:** F913/F914/F915/F916/F918/F919/F950/F707 顶层文档修正（F919 连带 fixtures 副本 :7）
- [ ] **Step 4:** 验证：`uv run pytest tests/unit/test_coverage_thresholds.py tests/integration/test_doc_links.py -q` 全绿；INDEX 序人工逐行核对粘贴
- [ ] **Step 5:** Commit `docs(index): spec62 index reorder + archive errata + top-level doc fixes (18 findings)` → audit-T5.md

## Task 6 · 配置注释与批量 M（T4：F1028/F1029/T1307/F1156/F1157/T1505）

**Files:** Modify: .github/CODEOWNERS、benchmarks/anchors/AC-003.md、pyproject.toml:11、docs/superpowers/specs/INDEX.md（F1156 注记）、archive/pipeline-never-compleces（T1505）；local-only：.superpowers/sdd-archive-inference-control/progress.md
**复杂度:** leaf · **test_kind:** regression_guard

- [ ] **Step 1:** 六条按裁决表改（F1157 本地删除过时 checklist，不 commit）
- [ ] **Step 2:** 验证：`uv lock --check`（pyproject 注释行改动不影响锁，仍必跑）；`just check`
- [ ] **Step 3:** Commit `chore(docs): spec62 config-comment cleanup (F1028/F1029/T1307/F1156/T1505)` → audit-T6.md

## Task 7 · 验收电池（spec 验收 5 条全跑）

**复杂度:** leaf · **test_kind:** characterization

- [ ] **Step 1:** 验收 1——抽样 10 条（F707/F837/F876/F885/F935/F936/F938/F948/F949/F950）git grep 单版本对照
- [ ] **Step 2:** 验收 2——INDEX 序逐行核对 + #6 引用逐命中可达编号标记
- [ ] **Step 3:** 验收 3——五技能 DOT grep 全命中
- [ ] **Step 4:** 验收 4——X/10 grep 与豁免清单对账
- [ ] **Step 5:** 验收 5——`just check` 全绿 + lint-contracts + generate diff 空
- [ ] **Step 6:** 输出粘贴 progress.md `## 验收证据` → audit-T7.md

## 验收覆盖表

| spec 验收 | task | 验证命令 |
|---|---|---|
| 1 抽样 10 条单版本 | T7 | git grep 对照裁决表 |
| 2 INDEX 机械自洽 | T5/T7 | 人工逐行核对（粘贴）+ #6 逐命中验证 |
| 3 五技能 DOT | T3/T7 | `grep -l "flowchart\|graph" <skill>/SKILL.md` |
| 4 刻度统一 | T4/T7 | `grep -rnE "[0-9]+/10" skills/` = 豁免清单 |
| 5 just check + doc-links 0 断链 + 契约同步 | T2/T7 | `just check`、`just lint-contracts`、`just generate` diff |
