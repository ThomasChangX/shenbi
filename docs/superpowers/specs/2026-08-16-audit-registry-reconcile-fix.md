> **Date:** 2026-08-16 | **Status:** Design (Revised 2026-09-12 · 驳斥复核后修订：核心论点存活；C21/PR #204 与 spec #9/PR #66 已落地面移除；验收 2 不变量改 C21 禁注册语义) | **Severity:** 🟠 P1（F432 生产相位假 FAIL / F1004 master.json 缺 15 且路由 14 个 DEPRECATED）
> **系列:** 2026-08-15 全项目深度审计 · 阶段 5 修复 spec（簇 C22）| **代表 finding:** F231 | **簇规模:** 29 条 | **严重度上限:** P1
> **范围:** tests/tiers/deps.json、plugins/master.json、src/shenbi/gates/cli.py（SHORT_MAP、G5_CHECKER_GLOBS）、docs/framework/truth-files.yaml、迁移表 CLASSIFICATION、tools/ 对账 lint 新增 | **证据等级:** 实验佐证（Z2-review-r2/r3 + Z4-review-r1 + T206-T209 + Z10）
> **与既有 spec 关系:** #9（contract-single-source）的 deps.json 补登（F0-02）并入本 spec 的对账门禁；#23 的登记类条目（F904/F950/F1004）由本 spec 机制化收口——两 spec 待协调者归档合并
> **phase4 §7 排序:** 第 9 位（改动小、拦截面大）

# C22 · 平行登记表对账门禁（registry-reconcile）

## 背景（根因 + 证据）

**根因**：五类登记表（deps.json、plugins/master.json、gates 注册表 SHORT_MAP/G5_CHECKER_GLOBS、truth-files.yaml、迁移表 CLASSIFICATION）各自与磁盘现实漂移，无 cross-registry 对账门禁——技能漏账、哈希过期、词表孤儿、glob 缺项各自单向累积，缺项在生产相位直接假 FAIL。

**2026-09-12 驳斥复核（REWRITE 依据，fresh-context 子 agent 全 29 条核验 + 协调者亲证）**：

- **核心论点仍成立**：五族登记表至今无跨表双向对账门禁。已落地的是两个局部/单向门禁——`check_skill_deps_closure`（lint_repo_consistency.py:239，spec #9/PR #66 建 + C21 改造，双向但**仅 deps↔disk 单面**）与 `lint_routing_faces.py`（C21，七面但**仅 DEPRECATED 零路由**单向禁令）。
- **已闭合（本 spec 移除对应存量工作）**：F231/F905（5 漏账已补 + 闭包门禁已有；deps=59=74−15 DEPRECATED 是 C21 禁注册语义下的完备态——15 个未注册技能全部带 DEPRECATED banner，含 foreshadowing-plant SKILL.md:29）；F756 数据面（_tool_hashes 193/193 新鲜，C21 重锁；**新鲜度门禁仍缺**）；F759 注册半（lifecycle + review-group-×4 已入 T2 前置，T1 豁免面 codified 于 shared.py:392+）；F1152 读者半（index.json:720-723 有 reader）；F424 仅剩 contracts/ownership.py:7 一处注释；T208 deps 面（已双向门禁）。
- **恶化项**：T207 迁移表漂移 18→29 格（2 kind + 27 IO，19 技能）；F1017 从「结构脆弱」变「具体错误」（`_G4_DECISIONS_SKILLS` 快照 7 条，实际 g4_decisions 接线 8 条——缺 shenbi-genre-config，generic.py:327）；F755 seed 漂移扩至 15 skill，且 audit seed（tests/tiers/t2-phase/audit/input/seed.md）仍点名 12 个 DEPRECATED 技能；F1004 新增 C21 违例维度（master.json 仍路由 14 个 DEPRECATED 技能，lint_routing_faces 七面不含 master.json，无任何 lint/test 引用它）。

代表证据：
- **F432**（P1）：G5.5 第三注册表 G5_CHECKER_GLOBS 漂移——缺项技能回退 `["*.md"]` 使专属 checker 扫全部 md 文件 → **生产相位假 FAIL**
- **F1004**（P1）：plugins/master.json 技能清单 59/74，**缺 15 技能（含全部 score-* 与 group-review 家族）**（Z10 复算逐字核实）
- **F231**（P2，代表）：deps.json 技能账目三方漂移：磁盘 74 vs 账目 69 vs AGENTS.md 69，5 个生产技能漏账且无对账防线（F905 同体）
- **F414/F445**（P2）：cli.py SHORT_MAP 缺 **11 个**新 checker skill → 简写调用静默降级为 generic（初审 9 个被 F445 修正）
- **F448**（P2）：四份注册表中的两份（G5_CHECKER_GLOBS、SHORT_MAP↔checkers）与"每个 checker 实际收到什么文件"均无漂移门禁
- **F756**（P2）：deps.json `_tool_hashes` 99 条中 66 条与磁盘不符（63 哈希过期 + 3 文件已删）
- **T207**（P2）：迁移表 CLASSIFICATION 自称 authoritative，与 frontmatter 漂移 18 格（2 kind + 16 IO，11 技能），无对账 lint
- **T208**（P2）：存在性双向 closure 零门禁（G0.15 只查 G4_CHECKER_SKILLS 单向；deps/index.md/REGISTRY 三源无门禁）
- **T209**（P2）：词表死条目全量清单 + dag_key 与 normalize_to_glob 两个 canonicalizer 分歧（真实代码实测）；T203（自 #24 补登：dependency-dag.json 生成但零消费——唯一消费者是 CI idempotency git diff，随登记表对账裁决去留）
- 其余：F242（review-checklist-N.json 56 实例 resolves 全 False——词表唯一无 pattern 覆盖的参数化概念）、F521（OWNERSHIP 死条目）、F755（t2 seed 与 deps.json 前置闭包漂移，12 skill 未入 seed）、F758（8 skill 仅 rubric 无场景但 deps 声称 pass T1）、F759（5 个 skills/ 目录游离三层测试体系外）、F823（import/analysis/01_overview.md 概念与实际 01_parse.md 命名漂移）、F888（short/outline.md 与 short/package.md 孤儿概念）、F895（pipeline-written 节漏 progress.json/config-change-log.jsonl/gate-markers）、F1005（master.json 0.2.0 vs pyproject 0.1.0）、F1017（lint_repo_consistency 的 _G4_DECISIONS_SKILLS 硬编码快照）、F1022（migrate_contract_to_frontmatter.py 一次性迁移器 + 第三份契约快照残留）、F1106（truth/state_snapshot-pre-rev.md 不在词表——静默同义词）、F1151（根级 truth/ 模板与项目内 truth/ 语义同名冲突）、F1152（bridge_tracker.md 未登记词表且 write-only 无读者）、T206（worldbuilding.py 声称 Auto-generated 但无生成器、不在 CI diff 范围）

## 目标

单一对账 lint 收口五类登记表：**每张表 ↔ 磁盘现实 ↔ 其他表的双向闭包**，任何一边缺项/多项/过期即 FAIL——让 F432 类生产假 FAIL 在 PR 期被拦，而非运行期炸。

## 任务分解

### T1 · 对账 lint 主体（一处实现，多表规则）
1. 新增 `scripts/lint_registry_reconcile.py`（或并入 lint_repo_consistency，避免又一个散点）：
   - **R1 技能闭包**（修订：deps↔disk 面已由 `check_skill_deps_closure` 门禁，以此为基线扩展剩余面）：plugins/master.json ↔ 磁盘活技能集（74 − DEPRECATED；含 master ∩ DEPRECATED = ∅ 禁路由，F1004）↔ SHORT_MAP ↔ G5_CHECKER_GLOBS ↔ generic.checkers ↔ t2 seed ↔ AGENTS.md 计数 ↔ using-shenbi 触发表反向（活技能漏提，F448；与 C21 T3 共用规则定义）
   - **R2 词表闭包**：truth-files.yaml ↔ 磁盘 truth 产物模式 ↔ 代码内 TRUTH_FILES/硬编码概念（F242/F895/F1106/F1152）；孤儿概念（零生产者零消费者）报 WARN（F888/F823）
   - **R3 哈希新鲜度门禁**（修订：数据面已修——193/193 新鲜；本规则只剩门禁化，将 lock-tool-hashes 校验并入对账 lint，防再次单向过期）（F756）
   - **R4 迁移表一致性**：CLASSIFICATION ↔ frontmatter（T207，现漂移 29 格）；一次性迁移器与第三份快照删除（F1022）
   - **R5 glob 有效性**：G5_CHECKER_GLOBS 缺项技能显式报错而非回退 `*.md`（F432 的生产面修复 + 门禁双管；g5.py:317 回退仍在，33 个 t2 prereq 暴露其中 9 个有专属 checker）
2. R1–R5 输出机器可读报告（表名/方向/条目三元组），供 CI 与人工共用

### T2 · 存量数据修正（lint 红转绿）
3. （修订：~~deps.json 补 5 个漏账技能、清 66 条过期哈希~~ 已由 C21 完成——deps=59 完备态、193 哈希新鲜；剩余：t2 seed 补 15 个缺失技能的步骤说明（F755）+ audit seed 清除 12 个 DEPRECATED 点名；8 个 rubric-only 技能登记真实 T1 状态（F758））
4. master.json（修订口径，按 C21 禁注册语义）：技能集改为磁盘活技能全集（74 − 15 DEPRECATED = 59），删除 14 个 DEPRECATED 路由；版本与 pyproject 单源化（F1005/T1306——pyproject 为源，master.json 生成或 CI 校验，保守方案只校验不生成）
5. SHORT_MAP 补 11 个（F414/F445 清单：book-spine-init、chapter-revision、escalation-review、market-radar、memory-distill、review-arc-payoff、review-resonance、score-arc、score-stratum、score-volume、short-drafting）；G5_CHECKER_GLOBS 补缺项并消灭 `*.md` 回退（F432）
6. truth-files.yaml：补 review-checklist-N.json 的 pattern/glob 解析（F242：`context/review-checklist-1.json` 实例 resolves=False——参数化概念需 pattern 级解析而非仅 verbatim 概念）、pipeline-written 三件（progress.json/config-change-log.jsonl/gate-markers/*）、bridge_tracker、state_snapshot-pre-rev；删 short/outline.md、short/package.md、import/analysis/01_overview.md 孤儿（F242/F895/F1152/F1106/F888/F823）
7. F1151：根级 truth/ 模板目录改名（如 `_templates/truth/`）消解同名冲突，2 个消费者同步
8. T206：worldbuilding.py（contracts/skills/worldbuilding.py:1）裁决——补真实生成器并进 CI diff，或删 "Auto-generated" 声称改手工维护注明
9. （修订新增）F1017：`_G4_DECISIONS_SKILLS` 硬编码快照改从 generic.checkers 的 g4_decisions 接线派生（快照已具体错误：缺 genre-config）

### T3 · CI 接线
9. lint 进 ci.yml 与 just check **同一入口**（吸取 C25 教训：不许 CI 与 justfile 双清单再漂移）；红灯验证一次

### 批量清理（M 级成员）
- **F354**（M）：_verify_truth_integrity genesis_outputs 补 world/factions.md 与 foundation/review_report.md
- **F424**（M）：shared.py/g_dispatch/g7 的 69 计数改单源（读 R1 的计数来源或去数字化）
- **T1306**（M）：master.json/pyproject 版本双源归 T2.4 一并收口

## 验收标准（真实数据可复验 · 修订 2026-09-12）

1. `uv run python scripts/lint_registry_reconcile.py`（或并入后的 just 入口）退出码 0 且报告"0 violations"；对五张表各注入一个负样本（删一个 deps.json 条目 / 改一个哈希字节 / 词表删一个 pattern / master.json 加一个 DEPRECATED 路由 / G5_GLOBS 删一项）各 FAIL 一次（红灯验证记录）
2. （修订：按 C21 禁注册语义）master.json 技能集 == 磁盘活技能集（74 − 15 DEPRECATED = 59）且 master.json ∩ DEPRECATED = ∅；deps.json 维持 59 注册完备态；_tool_hashes 193/193 与磁盘一致（lock 脚本算法幂等复验）
3. F432 场景回归：G5 对缺 glob 技能显式报 "missing G5_CHECKER_GLOBS entry" 而非扫 `*.md`（单测断言错误消息）
4. AGENTS.md/overview.md 计数类声称与 R1 输出一致（或按 C23 建议去数字化——二选一落定并在 PR 注明）
5. `just check` 与 ci.yml 同一命令驱动（无第二份清单；挂载模式沿用 C20/C21 先例——CI 清单一源化的系统性修复归 C25/#63，本 spec 不提前实施）

## 风险与回滚

- **风险**：R1 闭包过严会拦正常 WIP（新技能先上磁盘后补表）——提供 `--allow-missing <list>` 显式豁免参数，CI 用严格模式
- **风险**：词表 R2 的"概念↔模式"匹配有歧义（参数化概念）——以 T209 的 canonicalizer 分歧裁决为前提，先统一 dag_key/normalize_to_glob 再上 R2
- **风险**：master.json 生成化动插件发布链路——保守方案为只校验不生成
- **风险**（修订新增）：master.json 删 14 个 DEPRECATED 路由可能破下游插件消费者——删除前 grep 全仓消费面（generate.py 只读 master.json；确认无其他消费者后按表 revert 粒度分 commit）
- **回滚**：lint 独立脚本可整体移除；存量数据修正分表分 commit（deps/master/词表/SHORT_MAP 各一），可按表 revert

## 簇成员清单（29 条，自查用 · 修订标注 2026-09-12）

F231 ✅closed（C21+#66 闭包门禁）, F242, F354, F414, F424 △仅剩 ownership.py:7 注释, F432, F445, F448, F521, F755（漂移扩至 15）, F756 △数据已修仅剩门禁, F758, F759 △注册半 done（T1 豁免面 codified）, F823, F888, F895, F905 ✅closed（同 F231）, F1004（新增 C21 违例维度：路由 14 DEPRECATED）, F1005, F1017（快照已具体错误）, F1022, F1106, F1151, F1152 △读者半 done, T206, T207（漂移 18→29 格）, T208 △deps 面 done（G0.15 单向/三源门禁仍缺）, T209, T1306（代表 F231；邻接提示：F232 属 C9 簇数值阈值面，不在本簇）
