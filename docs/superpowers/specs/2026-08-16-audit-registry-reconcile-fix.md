> **Date:** 2026-08-16 | **Status:** Design (Revised 2026-09-12 · 两轮：①驳斥复核后修订——核心论点存活，C21/PR #204 与 spec #9/PR #66 已落地面移除，验收 2 不变量改 C21 禁注册语义；②-⑤设计审查轮 1-4 修复——T0 注册表提取/canonicalizer 前置、F1004 缺口改 14 活技能（59=45 live+14 DEPRECATED）、R5 定案（checker-having FAIL marker / checker-less 保留代码回退+WARN）、R4 删除性处置（含迁移器唯一测试消费者）、R2 参数化 patterns 不变量、5b registry backfill（G4_CHECKER_SKILLS+9 / index.md+5 / 触发表+7 或豁免）、F521/T208残/T209/T203/F759残 补归宿) | **Severity:** 🟠 P1（F432 生产相位假 FAIL / F1004 master.json 缺 14 活技能且路由 14 个 DEPRECATED）
> **系列:** 2026-08-15 全项目深度审计 · 阶段 5 修复 spec（簇 C22）| **代表 finding:** F231 | **簇规模:** 29 条 | **严重度上限:** P1
> **范围:** tests/tiers/deps.json、plugins/master.json、src/shenbi/gates/cli.py（SHORT_MAP）+ src/shenbi/gates/g5.py（G5_CHECKER_GLOBS）+ src/shenbi/gates/g4/generic.py（checkers）+ src/shenbi/gates/shared.py（G4_CHECKER_SKILLS）、docs/framework/truth-files.yaml、迁移表 CLASSIFICATION、tools/ 对账 lint 新增 | **证据等级:** 实验佐证（Z2-review-r2/r3 + Z4-review-r1 + T206-T209 + Z10）
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
- **F1004**（P1）：plugins/master.json 技能清单 59 条（45 live + 14 DEPRECATED），**缺 14 个活技能（含全部 score-* 与 group-review 家族）且路由 14 个 DEPRECATED**（Z10 复算逐字核实；2026-09-12 复算：「缺 15」系 74−59 粗算，live 缺口实为 14）
- **F231**（P2，代表）：deps.json 技能账目三方漂移：磁盘 74 vs 账目 69 vs AGENTS.md 69，5 个生产技能漏账且无对账防线（F905 同体）
- **F414/F445**（P2）：cli.py SHORT_MAP 缺 **11 个**新 checker skill → 简写调用静默降级为 generic（初审 9 个被 F445 修正）
- **F448**（P2）：四份注册表中的两份（G5_CHECKER_GLOBS、SHORT_MAP↔checkers）与"每个 checker 实际收到什么文件"均无漂移门禁
- **F756**（P2）：deps.json `_tool_hashes` 99 条中 66 条与磁盘不符（63 哈希过期 + 3 文件已删）
- **T207**（P2）：迁移表 CLASSIFICATION 自称 authoritative，与 frontmatter 漂移 18 格（2 kind + 16 IO，11 技能；**原审计快照**——2026-09-12 复核已扩至 29 格/19 技能，见上方恶化项），无对账 lint
- **T208**（P2）：存在性双向 closure 零门禁（G0.15 只查 G4_CHECKER_SKILLS 单向；deps/index.md/REGISTRY 三源无门禁）
- **T209**（P2）：词表死条目全量清单 + dag_key 与 normalize_to_glob 两个 canonicalizer 分歧（真实代码实测）；T203（自 #24 补登：dependency-dag.json 生成但零消费——唯一消费者是 CI idempotency git diff，随登记表对账裁决去留）
- 其余：F242（review-checklist-N.json 56 实例 resolves 全 False——词表唯一无 pattern 覆盖的参数化概念）、F521（OWNERSHIP 死条目）、F755（t2 seed 与 deps.json 前置闭包漂移，12 skill 未入 seed）、F758（8 skill 仅 rubric 无场景但 deps 声称 pass T1）、F759（5 个 skills/ 目录游离三层测试体系外）、F823（import/analysis/01_overview.md 概念与实际 01_parse.md 命名漂移）、F888（short/outline.md 与 short/package.md 孤儿概念）、F895（pipeline-written 节漏 progress.json/config-change-log.jsonl/gate-markers）、F1005（master.json 0.2.0 vs pyproject 0.1.0）、F1017（lint_repo_consistency 的 _G4_DECISIONS_SKILLS 硬编码快照）、F1022（migrate_contract_to_frontmatter.py 一次性迁移器 + 第三份契约快照残留）、F1106（truth/state_snapshot-pre-rev.md 不在词表——静默同义词）、F1151（根级 truth/ 模板与项目内 truth/ 语义同名冲突）、F1152（bridge_tracker.md 未登记词表且 write-only 无读者）、T206（worldbuilding.py 声称 Auto-generated 但无生成器、不在 CI diff 范围）

## 目标

单一对账 lint 收口五类登记表：**每张表 ↔ 磁盘现实 ↔ 其他表的双向闭包**，任何一边缺项/多项/过期即 FAIL——让 F432 类生产假 FAIL 在 PR 期被拦，而非运行期炸。

## 任务分解（设计审查轮 1-4 迭代修订 · 任务号连续化）

### T0 · 前置结构任务（设计审查 C1/I4——lint 可实施性的前提）
0a. **注册表提取**：`G5_CHECKER_GLOBS` 从 `gate_G5` 函数内提升为 g5.py 模块级常量；generic.py 提供模块级 `build_checkers()` 工厂（含 `register_score_checkers` 动态注册）并导出 declarative 的 `G4_DECISIONS_WIRED` frozenset（F1017 派生源——`make_composite_checker` 闭包不可内省，派生事实必须与构造同址声明）；gate 热路径改用提取物，行为等价测试钉住（同输入同 verdict）；**工厂保持 gate_G4 现有的 late-imports 惯例**（循环导入规避 + spawn 成本，见 cli.py T1604 记录）
0b. **T209 canonicalizer 裁决统一**（先于 R2）：`normalize_to_glob`（graph.py:20，patterns 优先）与 `dag_key`（graph.py:42，globs 优先）分歧实证（`truth/arcs/arc-N.md` 两函数产出不同键）——统一为单一 canonicalizer 或显式分工契约（各自消费面：sync_contracts 两处并用可分歧），lint_contract_graph 消费面回归钉

### T1 · 对账 lint 主体（一处实现，多表规则）
1. 新增 `tools/lint_registry_reconcile.py`（定案 M3：新文件——五规则一体 + 机器可读输出，与 lint_repo_consistency 的杂项职责分离；**接受 repo-root 参数**（lint_routing_faces 模式）使临时副本负样本注入可执行（验收 1 前提））：
   - **R1 技能闭包**（deps↔disk 面已由 `check_skill_deps_closure` 门禁为基线，扩展剩余面）：plugins/master.json ↔ 磁盘活技能集（master == 59 live ∧ master ∩ DEPRECATED = ∅，F1004）↔ SHORT_MAP ↔ G5_CHECKER_GLOBS ↔ generic.checkers（经 T0a 提取物读取）↔ t2 seed ↔ AGENTS.md 计数（**transitional 面**：验收 4 去数字化落地后此面移除，归 C23/#61 域）↔ using-shenbi 触发表反向（活技能漏提，F448）↔ **G4_CHECKER_SKILLS 双向 + docs/skills/index.md + contracts/registry.py `known_skill_names()`（三源存在闭包）**（T208 残余面：G0.15 现仅单向 ⊆disk）。**豁免语义**（C1 修订）：pipeline-internal-only 技能（设计上不应 agent 触发/入表者，如 score-* 若裁决为内部）经 `--allow-missing <list>` 显式豁免登记，豁免清单进 CI 严格模式
   - **每面不变量**（轮 3 补，方向显式化）：master.json `==` 磁盘活技能集 ∧ master ∩ DEPRECATED `=` ∅；SHORT_MAP `⊇` checker-having 技能（简写覆盖所有 checker）；G5_GLOBS `⊇` checker-having ∧ t2-prereq 技能（R5 面）；G4_CHECKER_SKILLS `==` checkers 全集（30）；docs/skills/index.md `⊇` 活技能集（存在闭包）；t2 seed `⊇` 各 phase prerequisites（字面 token 可解析）；AGENTS.md 计数 `=` R1 输出（transitional）；using-shenbi 触发表 `⊇` functional 活技能集 − 豁免清单（反向漏提面；两个 meta 技能 using-shenbi/shenbi-writing-skills 天然不入自身触发表，预豁免——docs/skills/index.md 面无此问题，两 meta 均在列）
   - **R2 词表闭包**（依赖 T0b）：truth-files.yaml ↔ 磁盘 truth 产物模式 ↔ 代码内 TRUTH_FILES/硬编码概念（F242/F895/F1106/F1152）；**不变量**（I2 修订 · 轮 5 措辞修正：yaml 共 5 个无 patterns 的参数化概念——yaml:70/71/94 三个经 `globs:` fallback 合法覆盖（graph.py:23-26 docstring 明示 bless per-dim 审计字面量），task 6 补 yaml:89/90 两个）：每个参数化概念必须 **glob 可解析（经对应 `patterns:` 条目或已声明 `globs:` 覆盖，二者居一）**（F242 复发防线；参数化定义：name 含 N/NNN/`<dim>`/SECTION 占位符的概念——全量恰 5 个即上列；verbatim glob 概念如 `genesis-context/*.md` 不属此类，豁免）；孤儿概念（零生产者零消费者）报 WARN（F888/F823；分工 M5：contract 级 producer/consumer 归 lint_contract_graph 的 ORPHAN_READ/DANGLING_WRITE，本 lint 只报 yaml 概念级，不双报）
   - **R3 哈希新鲜度门禁**（数据面已修——193/193 新鲜；本规则将 tests/lock-tool-hashes.sh 校验算法并入对账 lint，防再次单向过期；脚本自身保持 writer-only，**所有 src 改动落地后须终态重锁一次**——T0a/T1/R5 改 g5.py/generic.py/shared.py 均为 _tool_hashes 目标，中途校验红属预期非缺陷）（F756）
   - **R4 迁移表处置**（删除性处置为主方案；I1 修订）：删除一次性迁移器 `tools/migrate_contract_to_frontmatter.py` + CLASSIFICATION 表 + 第三份契约快照 + **其唯一外部消费者 `tests/unit/test_migrate_contract.py`**（repo grep 证实仅此四者有活代码引用；归档的 plan/audit-run 叙述与生成 site/search 索引按惯例豁免）——T207 的 29 格漂移随表消亡，无需持久对账规则；仅当删除被否决才退回「CLASSIFICATION ↔ frontmatter 对账 lint」分支方案
   - **R5 glob 有效性**（M2 定案）：G5_CHECKER_GLOBS 对**有专属 checker 的 prereq** 缺 glob → `mf.append` FAIL marker（错误消息 "missing G5_CHECKER_GLOBS entry"，非 exception——外围 `except Exception` 会把 raise 降级为 WARN，g5.py:334-342 已核实）；对**无专属 checker 的 prereq**（33 个 fallback-exposed 中 24 个）**保留代码回退 `["*.md"]` 作为安全网**走 generic generative 检查（generic.py:359-364 核实为正确行为非漂移），lint 报 WARN 提示可细化——R5 规则面 =「checker-having prereq 必须有具体 glob」而非「每个 prereq 必须有条目」
2. R1–R5 输出机器可读报告（表名/方向/条目三元组），供 CI 与人工共用

### T2 · 存量数据修正（lint 红转绿；分表分 commit）
3. master.json（I1 修订口径）：补 **14** 个缺失活技能（anchor-curate、book-spine-init、escalation-review、foreshadowing-lifecycle、memory-distill、review-arc-payoff、review-group-×4、review-resonance、score-×3）+ 删 14 个 DEPRECATED 路由 → 59 live；版本与 pyproject 单源化（F1005/T1306——pyproject 为源，保守方案只校验不生成）
4. t2 seed 补 15 个缺失技能步骤说明（F755）+ audit seed 清除 12 个 DEPRECATED 点名；rubric-only 技能登记真实 T1 状态（F758，M8 修正：**7 个**——排除 DEPRECATED 的 shenbi-foreshadowing-recall，死者登记 T1 状态与 C21 禁注册语义矛盾）
5. SHORT_MAP 补 11 个（F414/F445 清单：book-spine-init、chapter-revision、escalation-review、market-radar、memory-distill、review-arc-payoff、review-resonance、score-arc、score-stratum、score-volume、short-drafting）；G5_CHECKER_GLOBS 补 9 个 checker-having 且 t2-prereq 技能的 glob（2026-09-12 复算枚举：book-spine-init、chapter-revision、memory-distill、review-arc-payoff、review-resonance、score-arc、score-stratum、score-volume、short-drafting——**与 5b 的 +9 差 2**：本清单含 review-resonance/review-arc-payoff（t2 prereq 有 G5 暴露面），5b 含 escalation-review/market-radar（非 t2 prereq、无 G5 暴露，为其配 glob 属死条目））（F432 生产面；24 个 checker-less 保留代码回退安全网——R5 定案）
5b. **registry backfill**（C1 修订——R1 born-red 三面的 green-ing 任务，2026-09-12 复算缺口）：`G4_CHECKER_SKILLS`（gates/shared.py:409，21 条）补 9 个 checker-having（book-spine-init、chapter-revision、escalation-review、market-radar、memory-distill、score-arc、score-stratum、score-volume、short-drafting）；`docs/skills/index.md` 补 5 个 live（foreshadowing-lifecycle、review-group-×4——即 F759 残余半的归宿，同五个技能）；`using-shenbi` 触发表补 7 个 live（anchor-curate、book-spine-init、escalation-review、memory-distill、score-arc、score-stratum、score-volume）或经 `--allow-missing` 豁免（pipeline-internal 裁决）
5c. **验收 4 归属**（轮 3 补）：AGENTS.md:19 计数声称（"72 functional + 2 meta = 74"）去数字化（改非数字表述或指向 R1 输出；与 C23/#61 去数字化域分工一致；overview.md 经轮 4 核实无技能计数数字，仅阶段数——验证性 no-op）
6. truth-files.yaml：补 **两个**无 patterns 覆盖的参数化概念的 pattern/glob（轮 3 修正——F242「唯一」措辞有误）：`context/review-checklist-*.json` 与 `context/chapter-pattern-input-*.json`（yaml:89-90；patterns 节均无条目）、pipeline-written 三件（progress.json/config-change-log.jsonl/gate-markers/*）、bridge_tracker、state_snapshot-pre-rev；删 short/outline.md、short/package.md、import/analysis/01_overview.md 孤儿（F242/F895/F1152/F1106/F888/F823）
7. F1151：根级 truth/ 模板目录改名（如 `_templates/truth/`）消解同名冲突；消费者唯一文件为 `tests/unit/pipeline/test_bridge_tracker.py:10,19`（两处 template_path 引用；M6 核实非两个文件）；根级 `truth/character_matrix.md` 零代码消费者——随改名迁移或径直删除（二选一落定）
8. T206：worldbuilding.py（contracts/skills/worldbuilding.py:1）裁决——补真实生成器并进 CI diff，或删 "Auto-generated" 声称改手工维护注明
9. F1017：`_G4_DECISIONS_SKILLS` 硬编码快照（lint_repo_consistency.py:112）改从 T0a 导出的 `G4_DECISIONS_WIRED` 派生（快照现缺 genre-config，已具体错误）
10. F521：OWNERSHIP 死条目 foundation-review/genre-config.json 删除（ownership.py:78-80）
11. T203 裁决（I4 补登）：dependency-dag.json 生成零消费——停用生成器（从 justfile/CI 移除）或接入消费者，二选一落定

### T3 · CI 接线（I3 修订：双挂载明确化）
12. `tools/lint_registry_reconcile.py` 进 justfile `check` recipe + ci.yml lint step（与 lint_contracts 等并列一行）——双挂载即本 spec 的「同一入口」语义：单一脚本两处引用，两行重复记为 C25 debt（系统性清单一源化归 C25/#63，本 spec 不提前实施）；lint_routing_faces 的 CI 挂载不动（C21 follow-up ① 归 C25 T3 的分工不变）；红灯验证一次

### 批量清理（M 级成员）
- **F354**（M）：_verify_truth_integrity genesis_outputs 补 world/factions.md 与 foundation/review_report.md
- **F424**（M · 轮 4 修正措辞）：仅剩 `contracts/ownership.py:7` 的「完整 69 技能 OWNERSHIP 迁移」注释去数字化（shared.py/g_dispatch/g7 计数点已全部动态化 `len()`——原审计指向的硬编码形态已不存在）
- **T1306**（M）：master.json/pyproject 版本双源归 T2.4 一并收口

## 验收标准（真实数据可复验 · 设计审查轮 1 修订）

1. `uv run python tools/lint_registry_reconcile.py` 退出码 0 且报告 "0 violations"（violations 计 FAIL 级发现；WARN 级——checker-less 回退提示、R2 孤儿概念——不计入 violations 不阻退出码）；负样本注入在**临时副本**上变异（M4：不提交变异注册表，保持 G0.9 纯度与 revert 干净），五张表各一次 FAIL：master.json 加一个 DEPRECATED 路由（或删一个 live）/ SHORT_MAP 删一项 / G5_GLOBS 删一个 checker-having 技能的 glob / 词表删一个参数化概念的双覆盖（如 review-checklist 的 patterns+globs 同删——不变量已放宽为二者居一，单删 patterns 若有 globs 覆盖则合法不红）/ _tool_hashes 改一字节（红灯验证记录）
2. （C21 禁注册语义 · I1 修正）master.json == 59 live（45 现存 + 补 14）∧ master ∩ DEPRECATED = ∅（删 14）∧ 无 ghost；deps.json 维持 59 注册完备态；_tool_hashes 193/193 与磁盘一致（lock 脚本算法幂等复验）
3. F432 场景回归：G5 对 checker-having 技能缺 glob 输出 FAIL marker "missing G5_CHECKER_GLOBS entry"（单测断言 marker 而非 exception——外围 except Exception 会降级 raise 为 WARN）；checker-less prereq 保持显式 `*.md` 默认（G5 运行时静默如旧；WARN 由 R5 lint 在静态检查时发射，非 G5 运行时行为）
4. （M2 预承诺）计数类声称去数字化（C23 方向）：AGENTS.md/overview.md 的技能数计数改为非数字表述或指向 R1 输出——与 C23/#61 的去数字化域分工一致，在 PR 注明
5. （I3 明确化）双挂载：justfile `check` recipe 与 ci.yml lint step 各含 `tools/lint_registry_reconcile.py` 一行（单一脚本两处引用）；两行重复记为 C25 debt，系统性清单一源化归 C25/#63 不提前实施

## 风险与回滚

- **风险**：R1 闭包过严会拦正常 WIP（新技能先上磁盘后补表）——提供 `--allow-missing <list>` 显式豁免参数，CI 用严格模式
- **风险**：词表 R2 的"概念↔模式"匹配有歧义（参数化概念）——以 T209 的 canonicalizer 分歧裁决为前提，先统一 dag_key/normalize_to_glob 再上 R2
- **风险**：master.json 生成化动插件发布链路——保守方案为只校验不生成
- **风险**（修订新增）：master.json 删 14 个 DEPRECATED 路由可能破下游插件消费者——删除前 grep 全仓消费面（generate.py 只读 master.json；确认无其他消费者后按表 revert 粒度分 commit）
- **回滚**：lint 独立脚本可整体移除；存量数据修正分表分 commit（deps/master/词表/SHORT_MAP 各一），可按表 revert

## 簇成员清单（29 条，自查用 · 修订标注 2026-09-12）

F231 ✅closed（C21+#66 闭包门禁）, F242, F354, F414, F424 △仅剩 ownership.py:7 注释, F432, F445, F448, F521, F755（漂移扩至 15）, F756 △数据已修仅剩门禁, F758, F759 △注册半 done（T1 豁免面 codified）, F823, F888, F895, F905 ✅closed（同 F231）, F1004（新增 C21 违例维度：路由 14 DEPRECATED）, F1005, F1017（快照已具体错误）, F1022, F1106, F1151, F1152 △读者半 done, T206, T207（漂移 18→29 格）, T208 △deps 面 done（G0.15 单向/三源门禁仍缺）, T209, T1306（代表 F231；邻接提示：F232 属 C9 簇数值阈值面，不在本簇）
