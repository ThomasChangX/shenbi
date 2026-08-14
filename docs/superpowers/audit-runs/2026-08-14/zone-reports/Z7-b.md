# Z7 分区初审报告（Z7-b 段：tests/tiers/，445 文件）

> 审查人：Z7-b 初审 agent（只读）
> 范围：tests/tiers/ 全部 445 文件（acceptance.json、deps.json、g4-exemptions.json + t1-skill/ 418 + t2-phase/ 18 + t3-pipeline/ 6），清单 Z7-b.files 与磁盘树 **1:1 精确匹配**（445/445，无缺失/无多余/无重复）。
> 方式：全部 deep-read；`read` 全文精读 + `grep`/`python3 -c`/`pytest --collect-only`（只读）验证；未运行任何写入仓库的命令。
> 发现编号段：F750–F799（实际产出 16 条：F750–F765）。
> 只读声明：本报告写入前/后均未创建/修改/删除任何仓库文件（除本段文件 Z7-b.md）；未 git add/commit。

---

## 0. 总览

- deep-read 文件数：**445 / 445**（清单全部覆盖，per-file 报告见 §2）
- 未覆盖文件：**0**
- findings 数：**16**（P1 × 7，P2 × 6，M × 3）
- 低置信度文件：**无**（每文件全文精读；所有统计经 python 脚本复核，关键 claim 均给出验证命令+输出）
- 覆盖缺口（d1-06-coverage-gaps.txt）处置结论：该文件 **1448 行全部为 src/ 路径，tests/ 下 0 行**——覆盖缺口台账本身不覆盖本区；本区"真实缺口"是结构性缺口：69 个 T1 scaffold 中 8 个 rubric-only（无任何测试类型目录）、5 个 skill 无 scaffold、62 个 bug-hunt expected 中 58 个证据路径不可达、18 个 fixture 目录有效为空，逐一在 findings 与 per-file 中标注 `must-test` 语义（植错不可执行的测试面）。

### 本区已核实/修正的已知 finding

| 已知编号 | 本区核实结论 |
|---|---|
| F432（74 skill vs 69 scaffold） | **核实成立且更精确**：skills/ = 74，t1-skill scaffold = 69，缺 5 全为 group/lifecycle（foreshadowing-lifecycle + review-group-{character,craft,factual,plan}）→ 并入 F756 |
| T807（62/60 bug-hunt expected 引用不存在文件） | **核实成立且细分**：62 个 bug-hunt expected 中 **58 个**含"既未在 scenario 植入、也不存在于仓库"的证据路径（共 90 条）；clean 侧另有 2 个（review-arc-payoff、review-resonance）→ F750 |
| T808（scenario 植错前提与 fixture 不符） | **核实成立**：12 个 bug-hunt scenario 的植错断言（引号短语/词频/段落）在引用 fixture 中找不到（chapter-drafting 声称 然而×4/不过×3/与此同时×2 vs 实测 1/1/0；review-sensitivity 声称 sensitive_words.txt 含傻逼/白痴/脑残 vs 实测台独/藏独/法轮功；review-arc-payoff 声称 hook-007/老周/黑石饼/arc_beats vs fixture 零命中）→ F751 |
| F115（38/82 rubric 维度过滤 no-op） | **核实成立且给出精确分布**：82 份 rubric（70 T1 + 9 T2 + 3 T3）中 38 份 no-op = 18 份 per-dimension-row 表 + 8 份无 section + 12 份 T2/T3；其中 4 份（worldbuilding/faction-builder/location-builder/story-architecture）per-dim-row 表含显式 N/A 豁免但 parser 不读 → F755 |
| T806（19 空目录被引用） | **核实成立且量化**：18 个 fixture 目录有效为空（仅 .gitkeep），33 个 tiers 文件显式引用空目录路径、73 个文件含其路径模式 → F753 |
| T1105（scenario-pressure 免疫 G0.9） | **核实成立且扩展**：8 个压力场景 6 个含非 fixture 路径；另有 20 个 scenario-*.md 变体 16 个含非 fixture 路径，全部免疫 → F760 |
| T1106（压力场景计数 6） | **计数与实况不符**：当前树实为 **8 个** scenario-pressure.md（T11 报告"6 个"已陈旧）→ F760 备注 |
| T801/T802（chapter-N-draft 逐字节同/example 截断） | **核实成立**：chapter-8-example.md == chapter-9-example.md 逐字节相同；chapter-7-example.md 为 chapter-draft-example.md 截断；context-composing generative 声称"chapters 7-9 drafted for ending diversity" → F762 |
| F0-02（deps.json 缺 5 skill 登记） | **核实成立**：5 skill 不在任何 phase roster、不在 _out_of_pipeline → F756 |
| D1⑪（skip/xfail） | 本区无 pytest 测试文件（tests/tiers 在 norecursedirs），skip/xfail 全部位于 tests/unit、tests/integration；与本区相关者：test_scoring.py:520 对 deps.json 写测试的 read-only 守卫（环境依赖 skip，合理）→ 无 finding |
| g4-exemptions.json | 三键（generative/bughunt/clean）全空、G0.12 可读；空豁免与 G4 generic 回退自洽 → 无 finding（观察：豁免机制从未被使用） |

---

## 1. findings（F750–F765）

### F750 | 58/62 bug-hunt expected-output 的证据路径"既未植入也不存在"——植错测试无法按剧本执行 | error | P1
- 证据：`tests/tiers/t1-skill/<skill>/bug-hunt/expected/expected-output.md`（62 个中的 58 个）"Evidence location"列引用 `drafts/chapter-N.md`、`config/platform-rules/qidian-fatigue-list.json`、`import/canon/character.md`、`snapshots/chapter-030/manifest.json`、`truth/pending_hooks.md`、`world/factions/order-of-ash.md` 等 90 条路径；对照同技能 `bug-hunt/input/scenario.md` 的植错位置（引用 `tests/fixtures/xxx.md`）与 `tests/fixtures/`、仓库其他位置——全部不存在
- 根因：expected-output 描述的"证据位置"是虚拟项目路径，scenario 实际把证据放在 tests/fixtures/ 下（如 chapter-drafting：scenario 说 defect 在 `tests/fixtures/chapter-draft-example.md`，expected 说证据在 `drafts/chapter-7.md`）→ 证据位置断链
- 验证命令+输出：python 遍历 62 bug-hunt expected，提取反引号路径并 `os.path.exists` + 与 scenario 路径集合比对 → 58/62 含未植入且不存在的证据路径；clean 侧 review-arc-payoff（`truth/arc_payoff_trend.md`）、review-resonance（`truth/resonance_trend.md`）同病
- 影响：检查者/独立评分 agent 按 expected-output 找证据必然扑空；测试"发现植错"的判定无法落地；且 G5.1/G0.8 只查 scenario 不查 expected → 该断链无 gate 拦截
- 建议方向：expected-output 证据位置改为 scenario 实际植入的 tests/fixtures/ 路径；或把场景自包含（在 fixture 内建虚拟项目树）；加 lint 校验 expected-output 路径 ⊆ scenario 路径 ∪ tests/fixtures

### F751 | 12 个 bug-hunt scenario 的植错断言与 fixture 内容不符（T808 本区核实） | error | P1
- 证据：python 抽取 62 个 bug-hunt scenario "Planted Defect" 节的引号短语，逐个在 scenario 引用的 fixture 中检索 → 12 个技能的植错断言零命中：chapter-drafting（声称"然而×4/不过×3/与此同时×2"与"无 PRE_WRITE_CHECK" vs fixture 实测 然而×1/不过×1/与此同时×0、**含** PRE_WRITE_CHECK）、review-sensitivity（声称 sensitive_words.txt 含傻逼/白痴/脑残、第6章第9段含"你这个白痴" vs 实测文件 3 词=台独/藏独/法轮功、chapter-draft-example 无白痴）、review-continuity（"三天后"/"五天的恢复"均 0 命中）、review-arc-payoff（hook-007/黑石饼/arc_beats 全 0 命中）、review-era（点赞/给力 0 命中）、review-reader-pull（"那天的天气不错"0 命中）、review-resonance（"数字没错，一条都没错"0 命中）、chapter-pattern（决战 0 命中）、foreshadowing-track（玉佩秘密 0 命中）、review-long-span（"他不禁想起了那"0 命中）、review-world-rules（二十五岁 0 命中）、using-shenbi（"帮我看看角色/检查时间线/润色"0 命中）
- 根因：scenario 描述的"已植错"内容在引用 fixture 中并不存在——植错前提虚构；agent 按剧本无法复现
- 验证命令+输出：见上（python 遍历 + `txt.count` 复核，chapter-drafting：`然而=1 不过=1 与此同时=0 PRE_WRITE_CHECK=True`）
- 影响：bug-hunt 的"expected findings"（F750）与"planted defect"（本 finding）双重架空——测试既无法执行也无可验证答案；T1 层 62 个 bug-hunt 测试面整体失真
- 建议方向：按 fixture 实际内容重写植错断言，或重做 fixture 使其包含断言内容；新增 fixture↔scenario 断言一致性 lint（引号短语必须能在 fixture 中 grep 到）

### F752 | audit-report-example.md 单文件被 16 个不同审计技能的 bug-hunt/clean/generative scenario 当作"审计报告"证据 | error | P1
- 证据：19 个 tiers 文件引用 `tests/fixtures/audit-report-example.md`（16 个 bug-hunt scenario + drift-guidance clean + chapter-revision/intent-management generative）；该文件实际是**角色一致性审计报告**（H1="角色一致性审计报告"，内容为 BDI/OOC 表、催收员/林烽一致性 PASS）
- 根因：一 report 多用途——review-pacing 说"报告未 flag chapter 7 误分类"、review-era 说"未 flag 点赞/给力"、review-sensitivity 说"未 flag 白痴"……但该报告内容与 pacing/era/sensitivity 审计类型无关，报告里根本没有这些结论 → 16 个 scenario 的"报告漏检"前提全部建立在错误文件上
- 验证命令+输出：`head tests/fixtures/audit-report-example.md`（H2=角色一致性审计报告）；`grep -rl audit-report-example.md tests/tiers/` = 19
- 影响：与 F750/F751 叠加，bug-hunt 测试面三重失真；"expected non-findings"（如 review-character 声称报告是 character 审计）与文件实际类型部分吻合属巧合
- 建议方向：每审计类型建独立报告 fixture（或参数化模板），scenario 引用与报告内容对齐

### F753 | 18 个 fixture 目录有效为空却被 scenario 引用为存在的项目状态（T806 本区量化） | error | P1
- 证据：`tests/fixtures/` 下 18 个目录仅含 .gitkeep（skill-triggering-prompts/、samples/reference-texts/、truth/character_profiles/、config/platform-rules/、snapshots/chapter-030/、import/canon/、import/packaging/、world/factions/、world/locations/、story/volumes/、drafts/、chapters/、audits/、consolidation/volume-1/、source/、truth/source_material/、characters/supporting/、snapshots/pre-chapter-25/）；33 个 tiers 文件**显式**引用 `tests/fixtures/<空目录>`（另有 40 个引用其路径模式）；style-learning generative/clean 声称"5 篇参考文本约 3 万字"（samples/reference-texts/ 空）、using-shenbi 声称"10 个 trigger prompts"（skill-triggering-prompts/ 空，见 F761）、review-dialogue 声称"苏晴/老陈 voice profiles"（truth/character_profiles/ 空）
- 根因：G0.8/G0.9 只校验路径前缀存在性（目录本身存在 → PASS），不校验目录内容 → 空目录全部过 gate；generative 测试的 agent 读到空目录后无法执行任务
- 验证命令+输出：python 遍历 fixture 目录（排除 .gitkeep 后文件数=0）→ 18 个；grep 统计 tiers 引用
- 影响：T1 generative/clean 大量测试输入为空，测试前提（"项目已存在 X"）不可满足；与 T806 同根因，本区给出精确文件清单
- 建议方向：G0.8/G0.9 增加"目录引用必须非空"校验；为各空目录补真实 fixture 内容或从 scenario 移除引用

### F754 | 8 个 rubric-only scaffold：无任何测试类型目录，其中 6 个是 T2 prerequisite → T2 分层契约不可达 | error | P1
- 证据：`tests/tiers/t1-skill/` 下 8 个 skill 仅有 rubric.md（无 generative/clean/bug-hunt 目录）：anchor-curate、book-spine-init、escalation-review、foreshadowing-recall、memory-distill、score-arc、score-stratum、score-volume；`deps.json` 中 6 个是 T2 phase prerequisite：book-spine-init→genesis、foreshadowing-recall+score-arc→drafting、memory-distill+score-volume+score-stratum→management
- 根因：这些 skill 的 T1 测试从未建立（scaffold 半成品）；G5.1 对每个 prereq 要求 `*-generative-scores.json`/summary.json T1 分 → 无 scenario 则永无报告 → `G5.1:<skill>:no_report` FAIL
- 验证命令+输出：python 遍历 skill 目录（无 test-type 子目录）→ 8 个；deps.json prereqs ∩ rubric-only = 6 个
- 影响：genesis/drafting/management 三个 T2 phase 在现结构下 **G5.1 恒 FAIL**（除非人工伪造报告）；T2/T3 分层测试面从源头断链；与 F432 同根（但 F432 指无 scaffold 的 5 skill，本条指有 rubric 无场景的 8 skill，二者是不同缺口集）
- 建议方向：为 6 个 T2 prereq 补齐 generative scenario（至少）或将 rubric-only skill 移出 phase roster；或在 deps.json 显式标注"no-T1 豁免"

### F755 | F115 核实：38/82 rubric 维度过滤 no-op；4 份 per-dim-row rubric 的 N/A 豁免被 parser 静默吞掉 | error | P1
- 证据：70 份 T1 rubric 的 Dimension Applicability 表三种格式：44 scope-based（`| Dimension scope | Bug-hunt | Clean | Generative |`，parser 可读）、18 per-dimension-row（`| # | Dimension | Bug-hunt Standard | Clean Standard |`，parser 不读）、8 无该 section；9 份 T2 + 3 份 T3 rubric 全部无该 section → 38/82 no-op（与 F115 完全一致）；其中 4 份 per-dim-row 表含显式 N/A 豁免行：worldbuilding（dim4 Prose quality）、faction-builder（dim8 Prose quality）、location-builder（dim5 Prose format）、story-architecture（dim6 Prose quality）
- 根因：`scoring.py:load_applicability` 只认 header `cells[0]=="Dimension scope"`；per-dim-row 表 header 为 `| # | Dimension |...` → `applicability` 为空 → `filter_dimensions_by_test_type` 原样返回（no-op）；而 per-dim-row 表内明确写着"N/A — exempted ... scoring.py renormalizes weights"——renormalize 从未发生
- 验证命令+输出：python 用 scoring.py parser 解析 70 rubric → app=True 44 / app=False 26；`filter_dimensions_by_test_type(worldbuilding_rubric,'bug-hunt')` → dims 9→9（应 9→8）；仅 chapter-drafting（scope-based 且含 No 行）实际生效 10→7
- 影响：worldbuilding 等 4 技能 bug-hunt/clean 评分包含 rubric 自己声明 N/A 的 prose 维度 → 分数口径与 rubric 意图不符；38/82 无过滤则全部维度参与计分（若意图排除则错，若不排除则无害——但 rubric 文本表明作者意图排除）
- 建议方向：统一 applicability 表为 scope-based 格式（或 parser 兼容 per-dim-row）；对 4 份含 N/A 的 rubric 修复格式

### F756 | F0-02 核实：deps.json 缺 5 skill 登记（foreshadowing-lifecycle + review-group-*），契约 lint 无闭包检查 | error | P2
- 证据：`deps.json` 的 t2-phases(9 roster)/t3-pipelines(3)/_out_of_pipeline(7) 合计登记 69 skill；`skills/` 74 目录差 5 = foreshadowing-lifecycle、review-group-{character,craft,factual,plan}；`G0.15` 只查 `G4_CHECKER_SKILLS ⊆ known_skill_names()`，无 skills↔deps 双向闭包
- 根因：登记义务无 enforcement；5 skill 既无 T1 scaffold（F432）也未登记 out-of-pipeline → 无任何契约位置声明其存在
- 验证命令+输出：python `skills - (∪roster ∪oop)` = 5 个（与 F0-02 完全一致）；`grep -n G0.15 src/shenbi/gates/g0.py` 确认检查方向
- 影响：契约单信源破坏；pipeline 若调度这些 skill 无 gate 约束；G7.1b 反向覆盖以 74 为全集恒 FAIL（F432 第二面）
- 建议方向：deps.json 增加 skill 目录闭包校验（lint_repo_consistency 或 G0.16 扩展）

### F757 | genesis phase roster 与 rubric/seed 不一致：deps.json 列 11 个 prereq，rubric Phase 行与 seed 只执行 6 个 | error | P2
- 证据：`deps.json.t2-phases.genesis.prerequisites` = 11（含 story-architecture、volume-outlining、pacing-design、genre-config、book-spine-init）；`t2-phase/genesis/rubric.md` Phase 行 = "worldbuilding → power-system → faction-builder → location-builder → character-design → relationship-map"（6）；`t2-phase/genesis/input/seed.md` 指令同样只执行 6 个
- 根因：genesis roster 塞入了本应属于 architecture phase 的 4 个 skill（story-architecture/volume-outlining/pacing-design/genre-config 同时出现在 architecture roster）+ rubric-only 的 book-spine-init → 双重归属破坏 `phase_of()` 单 phase 契约（返回首个匹配=genesis）
- 验证命令+输出：python `phase_of(deps,'shenbi-genre-config')` → 'genesis'（实为 architecture 成员）；genesis∩architecture = 4 个
- 影响：G5.1 对 genesis 要求 11 个 T1 分（含 book-spine-init 无场景 → F754 恒 FAIL）；phase 边界模糊使 T2 报告口径漂移
- 建议方向：genesis roster 收敛为 6 个实际执行 skill；architecture 4 个成员从 genesis 移除；book-spine-init 补场景或移出

### F758 | deps.json _tool_hashes 陈旧：99 条中 63 条与当前文件哈希不符、3 条指向不存在文件，且无 gate 校验 | error | P2
- 证据：`deps.json._tool_hashes` 99 条（lock-tool-hashes.sh 生成，前缀 sha256:）；python 重算当前 src/shenbi 全部 .py → 63 条不匹配、3 条（summarize_round.py、contract.py、update_progress.py）文件不存在（已改名/删除）；`grep _tool_hashes src/` 显示无任何 gate 消费（G0.14 只校验 _calibration_hashes.combined，后者实测**匹配**）
- 根因：锁脚本在文件改名（summarize_round→?、contract→contracts/、update_progress→?）后未重跑；且该"锁"无消费方 = 死数据
- 验证命令+输出：python sha256 重算 → match=33/mismatch=63/missing=3；`grep -rn "_tool_hashes" src/` 仅注释与 schema
- 影响：声称的"工具哈希锁"实际不锁任何东西（G0.14 只锁 calibration）；若未来 gate 启用该锁将误报大量 FAIL
- 建议方向：重跑 lock-tool-hashes.sh 或删除该 section；若需真锁，在 G0 加校验并处理 CRLF 归一化（与 G0.14 对齐）

### F759 | 8 个 rubric-only skill 的 rubric 为模板化占位（通用维度/空 Standard 列），无 T1 测试价值 | error | P2
- 证据：anchor-curate、escalation-review 的 rubric Standard 列全空（`| 3 | Craft analysis quality | 50% | |`）；book-spine-init、foreshadowing-recall、memory-distill、score-arc、score-stratum、score-volume 为同一通用文案（"Core functionality 50% / Data contract compliance 20% / Error handling 15%"逐字相同）
- 根因：scaffold 只复制了模板骨架未填 skill 专属内容（anchor-curate 的"Slot mapping correctness"、score-volume 的"Route C goal attainment"为少数例外，但大多为空壳）
- 验证命令+输出：read 8 份 rubric（anchor-curate 12 行、book-spine-init 15 行等）；python 去重比较 → 5 份文本相同
- 影响：即使补了场景，通用维度也无法区分 skill 行为；评分信息量为零（与 F754 叠加 = 8 skill 完全无有效 T1 面）
- 建议方向：为 8 个 skill 编写 skill 专属维度（从 SKILL.md 的 outputs/contracts 提炼）或明确其 T1 测试豁免

### F760 | T1105 扩展：8 个压力场景 + 20 个变体场景免疫 G0.8/G0.9/G0.9c 纯度检查 | error | P2
- 证据：`g0_purity.py` 硬编码只扫 `scenario.md`（`for test_type in ("generative","bug-hunt","clean"): scenario = skill_dir/test_type/input/scenario.md`）；8 个 `scenario-pressure.md` 中 6 个含非 fixture 路径（import-analysis、snapshot-manage、state-settling、review-anti-ai、foreshadowing-track、review-memo-compliance），20 个 `scenario-*.md` 变体中 16 个含非 fixture 路径（characters/protagonist.md、truth/pending_hooks.md、plans/chapter-1-plan.md 等）
- 根因：G0.8/G0.9/G0.9c 的文件名白名单不含 pressure/variant 变体；这些文件按 tests/ARCHIVE-MIGRATED.md 是活跃 T1 输入却完全绕过 fixture 纯度契约
- 验证命令+输出：python 提取 28 个非 scenario.md 文件的 backtick 路径 → 6/8 压力 + 16/20 变体命中非 fixtures/ 路径；`git log` 确认 8 个压力场景同 commit（T1106 计"6"已陈旧）
- 影响：G0.9 声称的"all scenario input paths reference tests/fixtures/"被 20 个活跃文件绕过；且压力场景无 runner（T1106），只能手工构造项目 → 不可执行
- 建议方向：G0.9 扫描所有 `input/*.md`（含变体）；压力场景改为引用 tests/fixtures/ 或自包含；补 runner

### F761 | using-shenbi bug-hunt scenario 引用空目录 skill-triggering-prompts/，声称"10 个 trigger prompts" | error | P2
- 证据：`using-shenbi/bug-hunt/input/scenario.md`："Present 10 natural language requests from the existing trigger test prompts in `tests/fixtures/skill-triggering-prompts/`"；该目录仅 .gitkeep（0 文件）；scenario 的植错 Request 3/7/9 无载体文件
- 根因：trigger prompts 未迁移入库；10 个 routing-phase*.md 文件是自包含的替代载体，但 scenario.md 仍指向空目录
- 验证命令+输出：`ls tests/fixtures/skill-triggering-prompts/` → 仅 .gitkeep；grep scenario.md 确认引用
- 影响：主 scenario 无法执行；10 个 routing 变体与主 scenario 关系未声明（重复载体）
- 建议方向：将 10 个 routing-phase*.md 汇入 skill-triggering-prompts/ 或改主 scenario 引用 routing 文件

### F762 | context-composing generative scenario 的"ending diversity"输入无多样性（chapter-8==9 逐字节相同） | error | P2
- 证据：`shenbi-context-composing/generative/input/scenario.md` 声称"chapters 7-9 drafted ... recent chapter drafts for ending diversity check"；实测 `chapter-8-example.md == chapter-9-example.md`（md5 相同）、`chapter-7-example.md` 是 `chapter-draft-example.md` 的前 80 行截断（T802）
- 根因：ending diversity 检查的输入章节实际只有 1 个不同结尾 → "diversity"前提虚构；且 chapter-7/8/9-example 的 H1 自称"第1章"（T816 同源）
- 验证命令+输出：`diff chapter-8-example.md chapter-9-example.md` 空；`diff chapter-7-example.md chapter-draft-example.md` 仅 80 行截断
- 影响：context-composing 的 ending diversity 分支无真实输入可测；generative 输出质量依赖虚假前提
- 建议方向：用 multi-chapter-example/（5 个真实不同章节）或重建 7/8/9 不同结尾的 fixture

### F763 | acceptance.json 无 schema/版本字段，t3 阈值无 gate 消费 | doc drift | M
- 证据：`acceptance.json` = `{"t1":94,"t2":94,"t3":94}` 无 schema 版本；grep `acceptance` src/shenbi/gates/ → 仅 G3.2（读 t1）、G5.1（读 t2）；g6/g7 均不读 → **t3:94 是死配置**
- 根因：T3 通过判定（G6/G7）未接 acceptance.json 阈值（可能硬编码或缺失）
- 验证命令+输出：`grep -rn acceptance src/shenbi/gates/*.py` → 仅 g3/g5
- 影响：t3 阈值若调整 acceptance.json 无效；T3 判定阈值与声明不一致风险
- 建议方向：G6/G7 接 acceptance.json t3；或删除死配置并注明 T3 阈值来源

### F764 | T2/T3 rubric 无 Dimension Applicability section（12/12），kill switch 单条且 parser 可解析 | doc drift | M
- 证据：9 份 T2 + 3 份 T3 rubric 均无 `## Dimension Applicability`；kill switch 均为单条（"Any skill's output scores below its T1 score ... phase = 0"/"Any chapter fails sensitivity audit ... pipeline = 0"）；python load_rubric 确认 12/12 可解析（sumW=100，ks≥1）
- 根因：T2/T3 评分不按 test-type 过滤（无该维度），section 缺失无害但格式不统一；若未来以 --test-type 评分将 no-op
- 验证命令+输出：python load_rubric → 12/12 sumW=100、ks 解析成功
- 影响：无（现状无害）；格式一致性风险
- 建议方向：T2/T3 rubric 补 scope-based applicability 表（全部 Yes）保持解析器兼容

### F765 | audit phase "All 18 review-* skills" 措辞与全量 review 技能数（24）不符 | doc drift | M
- 证据：`t2-phase/audit/rubric.md` Phase 行与 seed "All 18 review-* skills"；deps audit roster 恰 18 个；skills/ 下 review-* 共 24（20 单体 + 4 group），review-arc-payoff（在 drafting roster）、review-resonance（在 drafting roster）不在 audit
- 根因："All 18" 指 roster 内 18 个，但"review-*"全量是 24 → 措辞易误解为全部 review 技能
- 验证命令+输出：python 统计 skills/review-* = 24；audit roster = 18
- 影响：审计覆盖声明与全量不符（若读者按字面理解会以为漏了 6 个）
- 建议方向：改为"18 个 audit roster review 技能（arc-payoff/resonance 在 drafting 阶段执行）"

---

## 2. per-file 报告（445/445）
### tests/tiers/acceptance.json
- 处置: deep-read
- 声称检查的不变量: t1/t2/t3 阈值 = 94/94/94；G3.2 读 t1、G5.1 读 t2；t3 无消费 gate
- findings: ['F763']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: JSON 仅 3 键无 schema/版本

### tests/tiers/deps.json
- 处置: deep-read
- 声称检查的不变量: t2-phases(9)/t3-pipelines(3)/_tool_hashes(99)/_out_of_pipeline(7)/_calibration_hashes(1) 与目录、skills/ 对照
- findings: ['F756', 'F757', 'F758']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: _tool_hashes 63/99 陈旧+3 文件缺失；genesis roster 11 vs seed/rubric 6；5 skill 未登记

### tests/tiers/g4-exemptions.json
- 处置: deep-read
- 声称检查的不变量: generative/bughunt/clean 三键全空；G0.12 读取该文件，无 skill 被豁免
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 空豁免 = 全部走 generic 回退；G4_CHECKER_SKILLS=22 dedicated

### tests/tiers/t1-skill/_template/bug-hunt/expected/expected-output.md
- 处置: deep-read
- 声称检查的不变量: bug-hunt expected：植错/零错断言与 scenario 一致；证据路径存在
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/_template/bug-hunt/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/_template/clean/expected/expected-output.md
- 处置: deep-read
- 声称检查的不变量: clean expected：植错/零错断言与 scenario 一致；证据路径存在
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/_template/clean/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/_template/generative/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/_template/rubric.md
- 处置: deep-read
- 声称检查的不变量: 维度权重和=100；kill switch；Dimension Applicability 格式（F115/F755 分布）
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: scope-based 表 parser 可读

### tests/tiers/t1-skill/shenbi-anchor-curate/rubric.md
- 处置: deep-read
- 声称检查的不变量: 维度权重和=100；kill switch；Dimension Applicability 格式（F115/F755 分布）
- findings: ['F754', 'F755', 'F759']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 无 Dimension Applicability section；rubric-only scaffold（无任何测试类型目录）

### tests/tiers/t1-skill/shenbi-anti-detect/bug-hunt/expected/expected-output.md
- 处置: deep-read
- 声称检查的不变量: bug-hunt expected：植错/零错断言与 scenario 一致；证据路径存在
- findings: ['F750']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 证据路径未植入且不存在: ['drafts/chapter-7-antidetect.md']

### tests/tiers/t1-skill/shenbi-anti-detect/bug-hunt/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-anti-detect/clean/expected/expected-output.md
- 处置: deep-read
- 声称检查的不变量: clean expected：植错/零错断言与 scenario 一致；证据路径存在
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-anti-detect/clean/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-anti-detect/generative/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-anti-detect/rubric.md
- 处置: deep-read
- 声称检查的不变量: 维度权重和=100；kill switch；Dimension Applicability 格式（F115/F755 分布）
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: scope-based 表 parser 可读

### tests/tiers/t1-skill/shenbi-book-spine-init/rubric.md
- 处置: deep-read
- 声称检查的不变量: 维度权重和=100；kill switch；Dimension Applicability 格式（F115/F755 分布）
- findings: ['F754', 'F755', 'F759']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 无 Dimension Applicability section；rubric-only scaffold（无任何测试类型目录）

### tests/tiers/t1-skill/shenbi-canon-import/bug-hunt/expected/expected-output.md
- 处置: deep-read
- 声称检查的不变量: bug-hunt expected：植错/零错断言与 scenario 一致；证据路径存在
- findings: ['F750']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 证据路径未植入且不存在: ['import/canon/deviations.md', 'import/canon/relationship.md', 'import/canon/event.md']

### tests/tiers/t1-skill/shenbi-canon-import/bug-hunt/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: ['F753']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 引用空目录 tests/fixtures/import/canon/

### tests/tiers/t1-skill/shenbi-canon-import/clean/expected/expected-output.md
- 处置: deep-read
- 声称检查的不变量: clean expected：植错/零错断言与 scenario 一致；证据路径存在
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-canon-import/clean/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: ['F753']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 引用空目录 tests/fixtures/import/canon/

### tests/tiers/t1-skill/shenbi-canon-import/generative/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: ['F753']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 引用空目录 tests/fixtures/source/

### tests/tiers/t1-skill/shenbi-canon-import/rubric.md
- 处置: deep-read
- 声称检查的不变量: 维度权重和=100；kill switch；Dimension Applicability 格式（F115/F755 分布）
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: scope-based 表 parser 可读

### tests/tiers/t1-skill/shenbi-chapter-drafting/bug-hunt/expected/expected-output.md
- 处置: deep-read
- 声称检查的不变量: bug-hunt expected：植错/零错断言与 scenario 一致；证据路径存在
- findings: ['F750']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 证据路径未植入且不存在: ['drafts/chapter-7.md']

### tests/tiers/t1-skill/shenbi-chapter-drafting/bug-hunt/input/scenario-pressure.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: ['F760']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 压力场景（G0.9 免疫）

### tests/tiers/t1-skill/shenbi-chapter-drafting/bug-hunt/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: ['F751']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 植错断言在引用 fixture 缺失: ['与此同时']

### tests/tiers/t1-skill/shenbi-chapter-drafting/clean/expected/expected-output.md
- 处置: deep-read
- 声称检查的不变量: clean expected：植错/零错断言与 scenario 一致；证据路径存在
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-chapter-drafting/clean/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-chapter-drafting/generative/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-chapter-drafting/rubric.md
- 处置: deep-read
- 声称检查的不变量: 维度权重和=100；kill switch；Dimension Applicability 格式（F115/F755 分布）
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: scope-based 表 parser 可读

### tests/tiers/t1-skill/shenbi-chapter-pattern/bug-hunt/expected/expected-output.md
- 处置: deep-read
- 声称检查的不变量: bug-hunt expected：植错/零错断言与 scenario 一致；证据路径存在
- findings: ['F750']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 证据路径未植入且不存在: ['analysis/chapter-patterns.md']

### tests/tiers/t1-skill/shenbi-chapter-pattern/bug-hunt/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: ['F751']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 植错断言在引用 fixture 缺失: ['决战']

### tests/tiers/t1-skill/shenbi-chapter-pattern/clean/expected/expected-output.md
- 处置: deep-read
- 声称检查的不变量: clean expected：植错/零错断言与 scenario 一致；证据路径存在
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-chapter-pattern/clean/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-chapter-pattern/generative/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-chapter-pattern/rubric.md
- 处置: deep-read
- 声称检查的不变量: 维度权重和=100；kill switch；Dimension Applicability 格式（F115/F755 分布）
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: scope-based 表 parser 可读

### tests/tiers/t1-skill/shenbi-chapter-planning/bug-hunt/expected/expected-output.md
- 处置: deep-read
- 声称检查的不变量: bug-hunt expected：植错/零错断言与 scenario 一致；证据路径存在
- findings: ['F750']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 证据路径未植入且不存在: ['plans/chapter-7-plan.md']

### tests/tiers/t1-skill/shenbi-chapter-planning/bug-hunt/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-chapter-planning/clean/expected/expected-output.md
- 处置: deep-read
- 声称检查的不变量: clean expected：植错/零错断言与 scenario 一致；证据路径存在
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-chapter-planning/clean/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-chapter-planning/generative/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-chapter-planning/rubric.md
- 处置: deep-read
- 声称检查的不变量: 维度权重和=100；kill switch；Dimension Applicability 格式（F115/F755 分布）
- findings: ['F755']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: per-dim-row 格式 parser no-op（F115 计数内）

### tests/tiers/t1-skill/shenbi-chapter-revision/bug-hunt/expected/expected-output.md
- 处置: deep-read
- 声称检查的不变量: bug-hunt expected：植错/零错断言与 scenario 一致；证据路径存在
- findings: ['F750']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 证据路径未植入且不存在: ['drafts/chapter-12-revised.md']

### tests/tiers/t1-skill/shenbi-chapter-revision/bug-hunt/input/scenario-phase4b-revision-routing.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: ['F760']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 变体场景（G0.9 免疫）

### tests/tiers/t1-skill/shenbi-chapter-revision/bug-hunt/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-chapter-revision/clean/expected/expected-output.md
- 处置: deep-read
- 声称检查的不变量: clean expected：植错/零错断言与 scenario 一致；证据路径存在
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-chapter-revision/clean/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-chapter-revision/generative/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-chapter-revision/rubric.md
- 处置: deep-read
- 声称检查的不变量: 维度权重和=100；kill switch；Dimension Applicability 格式（F115/F755 分布）
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: scope-based 表 parser 可读

### tests/tiers/t1-skill/shenbi-character-design/bug-hunt/expected/expected-output.md
- 处置: deep-read
- 声称检查的不变量: bug-hunt expected：植错/零错断言与 scenario 一致；证据路径存在
- findings: ['F750']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 证据路径未植入且不存在: ['characters/protagonist.md', 'characters/mentor.md']

### tests/tiers/t1-skill/shenbi-character-design/bug-hunt/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-character-design/clean/expected/expected-output.md
- 处置: deep-read
- 声称检查的不变量: clean expected：植错/零错断言与 scenario 一致；证据路径存在
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-character-design/clean/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: ['F753']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 引用空目录 tests/fixtures/characters/supporting/

### tests/tiers/t1-skill/shenbi-character-design/generative/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-character-design/rubric.md
- 处置: deep-read
- 声称检查的不变量: 维度权重和=100；kill switch；Dimension Applicability 格式（F115/F755 分布）
- findings: ['F755']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: per-dim-row 格式 parser no-op（F115 计数内）

### tests/tiers/t1-skill/shenbi-character-extraction/bug-hunt/expected/expected-output.md
- 处置: deep-read
- 声称检查的不变量: bug-hunt expected：植错/零错断言与 scenario 一致；证据路径存在
- findings: ['F750']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 证据路径未植入且不存在: ['characters/protagonist.md', 'characters/relationships.md', 'characters/major/li-wei.md']

### tests/tiers/t1-skill/shenbi-character-extraction/bug-hunt/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-character-extraction/clean/expected/expected-output.md
- 处置: deep-read
- 声称检查的不变量: clean expected：植错/零错断言与 scenario 一致；证据路径存在
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-character-extraction/clean/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-character-extraction/generative/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-character-extraction/rubric.md
- 处置: deep-read
- 声称检查的不变量: 维度权重和=100；kill switch；Dimension Applicability 格式（F115/F755 分布）
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: scope-based 表 parser 可读

### tests/tiers/t1-skill/shenbi-context-composing/bug-hunt/expected/expected-output.md
- 处置: deep-read
- 声称检查的不变量: bug-hunt expected：植错/零错断言与 scenario 一致；证据路径存在
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-context-composing/bug-hunt/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-context-composing/clean/expected/expected-output.md
- 处置: deep-read
- 声称检查的不变量: clean expected：植错/零错断言与 scenario 一致；证据路径存在
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-context-composing/clean/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-context-composing/generative/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-context-composing/rubric.md
- 处置: deep-read
- 声称检查的不变量: 维度权重和=100；kill switch；Dimension Applicability 格式（F115/F755 分布）
- findings: ['F755']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: per-dim-row 格式 parser no-op（F115 计数内）

### tests/tiers/t1-skill/shenbi-drift-guidance/bug-hunt/expected/expected-output.md
- 处置: deep-read
- 声称检查的不变量: bug-hunt expected：植错/零错断言与 scenario 一致；证据路径存在
- findings: ['F750']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 证据路径未植入且不存在: ['audits/chapter-14-continuity.md', 'guidance/drift-chapter-14.md']

### tests/tiers/t1-skill/shenbi-drift-guidance/bug-hunt/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: ['F752']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-drift-guidance/clean/expected/expected-output.md
- 处置: deep-read
- 声称检查的不变量: clean expected：植错/零错断言与 scenario 一致；证据路径存在
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-drift-guidance/clean/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-drift-guidance/generative/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: ['F753']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 引用空目录 tests/fixtures/audits/

### tests/tiers/t1-skill/shenbi-drift-guidance/rubric.md
- 处置: deep-read
- 声称检查的不变量: 维度权重和=100；kill switch；Dimension Applicability 格式（F115/F755 分布）
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: scope-based 表 parser 可读

### tests/tiers/t1-skill/shenbi-escalation-review/rubric.md
- 处置: deep-read
- 声称检查的不变量: 维度权重和=100；kill switch；Dimension Applicability 格式（F115/F755 分布）
- findings: ['F754', 'F755', 'F759']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 无 Dimension Applicability section；rubric-only scaffold（无任何测试类型目录）

### tests/tiers/t1-skill/shenbi-faction-builder/bug-hunt/expected/expected-output.md
- 处置: deep-read
- 声称检查的不变量: bug-hunt expected：植错/零错断言与 scenario 一致；证据路径存在
- findings: ['F750']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 证据路径未植入且不存在: ['world/factions/order-of-ash.md']

### tests/tiers/t1-skill/shenbi-faction-builder/bug-hunt/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: ['F753']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 引用空目录 tests/fixtures/world/factions/

### tests/tiers/t1-skill/shenbi-faction-builder/clean/expected/expected-output.md
- 处置: deep-read
- 声称检查的不变量: clean expected：植错/零错断言与 scenario 一致；证据路径存在
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-faction-builder/clean/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-faction-builder/generative/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: ['F753']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 引用空目录 tests/fixtures/world/factions/

### tests/tiers/t1-skill/shenbi-faction-builder/rubric.md
- 处置: deep-read
- 声称检查的不变量: 维度权重和=100；kill switch；Dimension Applicability 格式（F115/F755 分布）
- findings: ['F755']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: per-dim-row 表含 1 个 N/A 豁免行，scoring.py load_applicability 不读该格式 → 豁免静默失效

### tests/tiers/t1-skill/shenbi-foreshadowing-plant/bug-hunt/expected/expected-output.md
- 处置: deep-read
- 声称检查的不变量: bug-hunt expected：植错/零错断言与 scenario 一致；证据路径存在
- findings: ['F750']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 证据路径未植入且不存在: ['truth/pending_hooks.md']

### tests/tiers/t1-skill/shenbi-foreshadowing-plant/bug-hunt/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-foreshadowing-plant/clean/expected/expected-output.md
- 处置: deep-read
- 声称检查的不变量: clean expected：植错/零错断言与 scenario 一致；证据路径存在
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-foreshadowing-plant/clean/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-foreshadowing-plant/generative/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-foreshadowing-plant/rubric.md
- 处置: deep-read
- 声称检查的不变量: 维度权重和=100；kill switch；Dimension Applicability 格式（F115/F755 分布）
- findings: ['F755']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: per-dim-row 格式 parser no-op（F115 计数内）

### tests/tiers/t1-skill/shenbi-foreshadowing-recall/rubric.md
- 处置: deep-read
- 声称检查的不变量: 维度权重和=100；kill switch；Dimension Applicability 格式（F115/F755 分布）
- findings: ['F754', 'F755', 'F759']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 无 Dimension Applicability section；rubric-only scaffold（无任何测试类型目录）

### tests/tiers/t1-skill/shenbi-foreshadowing-resolve/bug-hunt/expected/expected-output.md
- 处置: deep-read
- 声称检查的不变量: bug-hunt expected：植错/零错断言与 scenario 一致；证据路径存在
- findings: ['F750']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 证据路径未植入且不存在: ['truth/pending_hooks.md']

### tests/tiers/t1-skill/shenbi-foreshadowing-resolve/bug-hunt/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-foreshadowing-resolve/clean/expected/expected-output.md
- 处置: deep-read
- 声称检查的不变量: clean expected：植错/零错断言与 scenario 一致；证据路径存在
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-foreshadowing-resolve/clean/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-foreshadowing-resolve/generative/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-foreshadowing-resolve/rubric.md
- 处置: deep-read
- 声称检查的不变量: 维度权重和=100；kill switch；Dimension Applicability 格式（F115/F755 分布）
- findings: ['F755']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: per-dim-row 格式 parser no-op（F115 计数内）

### tests/tiers/t1-skill/shenbi-foreshadowing-track/bug-hunt/expected/expected-output.md
- 处置: deep-read
- 声称检查的不变量: bug-hunt expected：植错/零错断言与 scenario 一致；证据路径存在
- findings: ['F750']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 证据路径未植入且不存在: ['truth/pending_hooks.md']

### tests/tiers/t1-skill/shenbi-foreshadowing-track/bug-hunt/input/scenario-plant-track-resolve.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: ['F760']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 变体场景（G0.9 免疫）

### tests/tiers/t1-skill/shenbi-foreshadowing-track/bug-hunt/input/scenario-pressure.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: ['F760']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 压力场景（G0.9 免疫）

### tests/tiers/t1-skill/shenbi-foreshadowing-track/bug-hunt/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: ['F751']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 植错断言在引用 fixture 缺失: ['玉佩秘密']

### tests/tiers/t1-skill/shenbi-foreshadowing-track/clean/expected/expected-output.md
- 处置: deep-read
- 声称检查的不变量: clean expected：植错/零错断言与 scenario 一致；证据路径存在
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-foreshadowing-track/clean/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-foreshadowing-track/generative/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-foreshadowing-track/rubric.md
- 处置: deep-read
- 声称检查的不变量: 维度权重和=100；kill switch；Dimension Applicability 格式（F115/F755 分布）
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: scope-based 表 parser 可读

### tests/tiers/t1-skill/shenbi-foundation-review/bug-hunt/expected/expected-output.md
- 处置: deep-read
- 声称检查的不变量: bug-hunt expected：植错/零错断言与 scenario 一致；证据路径存在
- findings: ['F750']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 证据路径未植入且不存在: ['reviews/foundation-review.md']

### tests/tiers/t1-skill/shenbi-foundation-review/bug-hunt/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-foundation-review/clean/expected/expected-output.md
- 处置: deep-read
- 声称检查的不变量: clean expected：植错/零错断言与 scenario 一致；证据路径存在
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-foundation-review/clean/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-foundation-review/generative/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-foundation-review/rubric.md
- 处置: deep-read
- 声称检查的不变量: 维度权重和=100；kill switch；Dimension Applicability 格式（F115/F755 分布）
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: scope-based 表 parser 可读

### tests/tiers/t1-skill/shenbi-genre-config/bug-hunt/expected/expected-output.md
- 处置: deep-read
- 声称检查的不变量: bug-hunt expected：植错/零错断言与 scenario 一致；证据路径存在
- findings: ['F750']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 证据路径未植入且不存在: ['genre-config.json']

### tests/tiers/t1-skill/shenbi-genre-config/bug-hunt/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-genre-config/clean/expected/expected-output.md
- 处置: deep-read
- 声称检查的不变量: clean expected：植错/零错断言与 scenario 一致；证据路径存在
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-genre-config/clean/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-genre-config/generative/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-genre-config/rubric.md
- 处置: deep-read
- 声称检查的不变量: 维度权重和=100；kill switch；Dimension Applicability 格式（F115/F755 分布）
- findings: ['F755']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: per-dim-row 格式 parser no-op（F115 计数内）

### tests/tiers/t1-skill/shenbi-import-analysis/bug-hunt/expected/expected-output.md
- 处置: deep-read
- 声称检查的不变量: bug-hunt expected：植错/零错断言与 scenario 一致；证据路径存在
- findings: ['F750']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 证据路径未植入且不存在: ['import/analysis/02_characters.md', 'import/analysis/04_plot.md']

### tests/tiers/t1-skill/shenbi-import-analysis/bug-hunt/input/scenario-pressure.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: ['F760']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 压力场景（G0.9 免疫）

### tests/tiers/t1-skill/shenbi-import-analysis/bug-hunt/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: ['F753']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 引用空目录 tests/fixtures/chapters/

### tests/tiers/t1-skill/shenbi-import-analysis/clean/expected/expected-output.md
- 处置: deep-read
- 声称检查的不变量: clean expected：植错/零错断言与 scenario 一致；证据路径存在
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-import-analysis/clean/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: ['F753']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 引用空目录 tests/fixtures/chapters/

### tests/tiers/t1-skill/shenbi-import-analysis/generative/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: ['F753']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 引用空目录 tests/fixtures/chapters/

### tests/tiers/t1-skill/shenbi-import-analysis/rubric.md
- 处置: deep-read
- 声称检查的不变量: 维度权重和=100；kill switch；Dimension Applicability 格式（F115/F755 分布）
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: scope-based 表 parser 可读

### tests/tiers/t1-skill/shenbi-intent-management/bug-hunt/expected/expected-output.md
- 处置: deep-read
- 声称检查的不变量: bug-hunt expected：植错/零错断言与 scenario 一致；证据路径存在
- findings: ['F750']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 证据路径未植入且不存在: ['truth/current_focus.md']

### tests/tiers/t1-skill/shenbi-intent-management/bug-hunt/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-intent-management/clean/expected/expected-output.md
- 处置: deep-read
- 声称检查的不变量: clean expected：植错/零错断言与 scenario 一致；证据路径存在
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-intent-management/clean/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-intent-management/generative/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-intent-management/rubric.md
- 处置: deep-read
- 声称检查的不变量: 维度权重和=100；kill switch；Dimension Applicability 格式（F115/F755 分布）
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: scope-based 表 parser 可读

### tests/tiers/t1-skill/shenbi-length-normalizing/bug-hunt/expected/expected-output.md
- 处置: deep-read
- 声称检查的不变量: bug-hunt expected：植错/零错断言与 scenario 一致；证据路径存在
- findings: ['F750']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 证据路径未植入且不存在: ['drafts/chapter-7-normalized.md', 'reports/chapter-7-normalize-report.md']

### tests/tiers/t1-skill/shenbi-length-normalizing/bug-hunt/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-length-normalizing/clean/expected/expected-output.md
- 处置: deep-read
- 声称检查的不变量: clean expected：植错/零错断言与 scenario 一致；证据路径存在
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-length-normalizing/clean/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-length-normalizing/generative/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-length-normalizing/rubric.md
- 处置: deep-read
- 声称检查的不变量: 维度权重和=100；kill switch；Dimension Applicability 格式（F115/F755 分布）
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: scope-based 表 parser 可读

### tests/tiers/t1-skill/shenbi-location-builder/bug-hunt/expected/expected-output.md
- 处置: deep-read
- 声称检查的不变量: bug-hunt expected：植错/零错断言与 scenario 一致；证据路径存在
- findings: ['F750']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 证据路径未植入且不存在: ['world/locations/capital.md', 'world/locations/port-city.md']

### tests/tiers/t1-skill/shenbi-location-builder/bug-hunt/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-location-builder/clean/expected/expected-output.md
- 处置: deep-read
- 声称检查的不变量: clean expected：植错/零错断言与 scenario 一致；证据路径存在
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-location-builder/clean/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-location-builder/generative/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: ['F753']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 引用空目录 tests/fixtures/world/locations/

### tests/tiers/t1-skill/shenbi-location-builder/rubric.md
- 处置: deep-read
- 声称检查的不变量: 维度权重和=100；kill switch；Dimension Applicability 格式（F115/F755 分布）
- findings: ['F755']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: per-dim-row 表含 1 个 N/A 豁免行，scoring.py load_applicability 不读该格式 → 豁免静默失效

### tests/tiers/t1-skill/shenbi-market-radar/bug-hunt/expected/expected-output.md
- 处置: deep-read
- 声称检查的不变量: bug-hunt expected：植错/零错断言与 scenario 一致；证据路径存在
- findings: ['F750']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 证据路径未植入且不存在: ['reports/market-radar.md']

### tests/tiers/t1-skill/shenbi-market-radar/bug-hunt/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-market-radar/clean/expected/expected-output.md
- 处置: deep-read
- 声称检查的不变量: clean expected：植错/零错断言与 scenario 一致；证据路径存在
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-market-radar/clean/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-market-radar/generative/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-market-radar/rubric.md
- 处置: deep-read
- 声称检查的不变量: 维度权重和=100；kill switch；Dimension Applicability 格式（F115/F755 分布）
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: scope-based 表 parser 可读

### tests/tiers/t1-skill/shenbi-memory-distill/rubric.md
- 处置: deep-read
- 声称检查的不变量: 维度权重和=100；kill switch；Dimension Applicability 格式（F115/F755 分布）
- findings: ['F754', 'F755', 'F759']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 无 Dimension Applicability section；rubric-only scaffold（无任何测试类型目录）

### tests/tiers/t1-skill/shenbi-pacing-design/bug-hunt/expected/expected-output.md
- 处置: deep-read
- 声称检查的不变量: bug-hunt expected：植错/零错断言与 scenario 一致；证据路径存在
- findings: ['F750']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 证据路径未植入且不存在: ['story/pacing.md']

### tests/tiers/t1-skill/shenbi-pacing-design/bug-hunt/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-pacing-design/clean/expected/expected-output.md
- 处置: deep-read
- 声称检查的不变量: clean expected：植错/零错断言与 scenario 一致；证据路径存在
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-pacing-design/clean/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-pacing-design/generative/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-pacing-design/rubric.md
- 处置: deep-read
- 声称检查的不变量: 维度权重和=100；kill switch；Dimension Applicability 格式（F115/F755 分布）
- findings: ['F755']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: per-dim-row 格式 parser no-op（F115 计数内）

### tests/tiers/t1-skill/shenbi-plot-thread-weaver/bug-hunt/expected/expected-output.md
- 处置: deep-read
- 声称检查的不变量: bug-hunt expected：植错/零错断言与 scenario 一致；证据路径存在
- findings: ['F750']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 证据路径未植入且不存在: ['story/thread-map.md']

### tests/tiers/t1-skill/shenbi-plot-thread-weaver/bug-hunt/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-plot-thread-weaver/clean/expected/expected-output.md
- 处置: deep-read
- 声称检查的不变量: clean expected：植错/零错断言与 scenario 一致；证据路径存在
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-plot-thread-weaver/clean/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-plot-thread-weaver/generative/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-plot-thread-weaver/rubric.md
- 处置: deep-read
- 声称检查的不变量: 维度权重和=100；kill switch；Dimension Applicability 格式（F115/F755 分布）
- findings: ['F755']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: per-dim-row 格式 parser no-op（F115 计数内）

### tests/tiers/t1-skill/shenbi-power-system/bug-hunt/expected/expected-output.md
- 处置: deep-read
- 声称检查的不变量: bug-hunt expected：植错/零错断言与 scenario 一致；证据路径存在
- findings: ['F750']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 证据路径未植入且不存在: ['world/power-system.md']

### tests/tiers/t1-skill/shenbi-power-system/bug-hunt/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-power-system/clean/expected/expected-output.md
- 处置: deep-read
- 声称检查的不变量: clean expected：植错/零错断言与 scenario 一致；证据路径存在
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-power-system/clean/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-power-system/generative/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-power-system/rubric.md
- 处置: deep-read
- 声称检查的不变量: 维度权重和=100；kill switch；Dimension Applicability 格式（F115/F755 分布）
- findings: ['F755']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: per-dim-row 格式 parser no-op（F115 计数内）

### tests/tiers/t1-skill/shenbi-relationship-map/bug-hunt/expected/expected-output.md
- 处置: deep-read
- 声称检查的不变量: bug-hunt expected：植错/零错断言与 scenario 一致；证据路径存在
- findings: ['F750']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 证据路径未植入且不存在: ['characters/relationships.md']

### tests/tiers/t1-skill/shenbi-relationship-map/bug-hunt/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-relationship-map/clean/expected/expected-output.md
- 处置: deep-read
- 声称检查的不变量: clean expected：植错/零错断言与 scenario 一致；证据路径存在
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-relationship-map/clean/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-relationship-map/generative/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-relationship-map/rubric.md
- 处置: deep-read
- 声称检查的不变量: 维度权重和=100；kill switch；Dimension Applicability 格式（F115/F755 分布）
- findings: ['F755']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: per-dim-row 格式 parser no-op（F115 计数内）

### tests/tiers/t1-skill/shenbi-review-anti-ai/bug-hunt/expected/expected-output.md
- 处置: deep-read
- 声称检查的不变量: bug-hunt expected：植错/零错断言与 scenario 一致；证据路径存在
- findings: ['F750']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 证据路径未植入且不存在: ['audit/anti-ai-review-ch9.md']

### tests/tiers/t1-skill/shenbi-review-anti-ai/bug-hunt/input/scenario-pressure.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: ['F760']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 压力场景（G0.9 免疫）

### tests/tiers/t1-skill/shenbi-review-anti-ai/bug-hunt/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: ['F752']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-review-anti-ai/clean/expected/expected-output.md
- 处置: deep-read
- 声称检查的不变量: clean expected：植错/零错断言与 scenario 一致；证据路径存在
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-review-anti-ai/clean/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-review-anti-ai/generative/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-review-anti-ai/rubric.md
- 处置: deep-read
- 声称检查的不变量: 维度权重和=100；kill switch；Dimension Applicability 格式（F115/F755 分布）
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: scope-based 表 parser 可读

### tests/tiers/t1-skill/shenbi-review-arc-payoff/bug-hunt/expected/expected-output.md
- 处置: deep-read
- 声称检查的不变量: bug-hunt expected：植错/零错断言与 scenario 一致；证据路径存在
- findings: ['F750']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 证据路径未植入且不存在: ['truth/audit_drift.md']

### tests/tiers/t1-skill/shenbi-review-arc-payoff/bug-hunt/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: ['F751']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 植错断言在引用 fixture 缺失: ['那半块黑石饼老周临死前给的，原来竟是灵能催化剂，这件事林烽后来才知道']

### tests/tiers/t1-skill/shenbi-review-arc-payoff/clean/expected/expected-output.md
- 处置: deep-read
- 声称检查的不变量: clean expected：植错/零错断言与 scenario 一致；证据路径存在
- findings: ['F750']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 证据路径未植入且不存在: ['truth/arc_payoff_trend.md']

### tests/tiers/t1-skill/shenbi-review-arc-payoff/clean/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-review-arc-payoff/generative/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-review-arc-payoff/rubric.md
- 处置: deep-read
- 声称检查的不变量: 维度权重和=100；kill switch；Dimension Applicability 格式（F115/F755 分布）
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: scope-based 表 parser 可读

### tests/tiers/t1-skill/shenbi-review-character/bug-hunt/expected/expected-output.md
- 处置: deep-read
- 声称检查的不变量: bug-hunt expected：植错/零错断言与 scenario 一致；证据路径存在
- findings: ['F750']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 证据路径未植入且不存在: ['audit/character-review-ch8.md', 'drafts/chapter-8.md']

### tests/tiers/t1-skill/shenbi-review-character/bug-hunt/input/scenario-phase2-character.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: ['F760']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 变体场景（G0.9 免疫）

### tests/tiers/t1-skill/shenbi-review-character/bug-hunt/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: ['F752', 'F753']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 引用空目录 tests/fixtures/truth/character_profiles/

### tests/tiers/t1-skill/shenbi-review-character/clean/expected/expected-output.md
- 处置: deep-read
- 声称检查的不变量: clean expected：植错/零错断言与 scenario 一致；证据路径存在
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-review-character/clean/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: ['F753']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 引用空目录 tests/fixtures/truth/character_profiles/

### tests/tiers/t1-skill/shenbi-review-character/generative/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-review-character/rubric.md
- 处置: deep-read
- 声称检查的不变量: 维度权重和=100；kill switch；Dimension Applicability 格式（F115/F755 分布）
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: scope-based 表 parser 可读

### tests/tiers/t1-skill/shenbi-review-continuity/bug-hunt/expected/expected-output.md
- 处置: deep-read
- 声称检查的不变量: bug-hunt expected：植错/零错断言与 scenario 一致；证据路径存在
- findings: ['F750']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 证据路径未植入且不存在: ['drafts/chapter-2.md', 'drafts/chapter-3.md']

### tests/tiers/t1-skill/shenbi-review-continuity/bug-hunt/input/scenario-phase2-continuity.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: ['F760']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 变体场景（G0.9 免疫）

### tests/tiers/t1-skill/shenbi-review-continuity/bug-hunt/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: ['F751', 'F752']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 植错断言在引用 fixture 缺失: ['三天后', '五天的恢复']

### tests/tiers/t1-skill/shenbi-review-continuity/clean/expected/expected-output.md
- 处置: deep-read
- 声称检查的不变量: clean expected：植错/零错断言与 scenario 一致；证据路径存在
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-review-continuity/clean/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-review-continuity/generative/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-review-continuity/rubric.md
- 处置: deep-read
- 声称检查的不变量: 维度权重和=100；kill switch；Dimension Applicability 格式（F115/F755 分布）
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: scope-based 表 parser 可读

### tests/tiers/t1-skill/shenbi-review-dialogue/bug-hunt/expected/expected-output.md
- 处置: deep-read
- 声称检查的不变量: bug-hunt expected：植错/零错断言与 scenario 一致；证据路径存在
- findings: ['F750']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 证据路径未植入且不存在: ['drafts/chapter-5.md']

### tests/tiers/t1-skill/shenbi-review-dialogue/bug-hunt/input/scenario-phase4-dialogue.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: ['F760']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 变体场景（G0.9 免疫）

### tests/tiers/t1-skill/shenbi-review-dialogue/bug-hunt/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: ['F753']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 引用空目录 tests/fixtures/truth/character_profiles/

### tests/tiers/t1-skill/shenbi-review-dialogue/clean/expected/expected-output.md
- 处置: deep-read
- 声称检查的不变量: clean expected：植错/零错断言与 scenario 一致；证据路径存在
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-review-dialogue/clean/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: ['F753']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 引用空目录 tests/fixtures/truth/character_profiles/

### tests/tiers/t1-skill/shenbi-review-dialogue/generative/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-review-dialogue/rubric.md
- 处置: deep-read
- 声称检查的不变量: 维度权重和=100；kill switch；Dimension Applicability 格式（F115/F755 分布）
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: scope-based 表 parser 可读

### tests/tiers/t1-skill/shenbi-review-era/bug-hunt/expected/expected-output.md
- 处置: deep-read
- 声称检查的不变量: bug-hunt expected：植错/零错断言与 scenario 一致；证据路径存在
- findings: ['F750']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 证据路径未植入且不存在: ['novel.json', 'drafts/chapter-3.md']

### tests/tiers/t1-skill/shenbi-review-era/bug-hunt/input/scenario-phase4b-era.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: ['F760']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 变体场景（G0.9 免疫）

### tests/tiers/t1-skill/shenbi-review-era/bug-hunt/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: ['F751', 'F752']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 植错断言在引用 fixture 缺失: ['给力', '点赞']

### tests/tiers/t1-skill/shenbi-review-era/clean/expected/expected-output.md
- 处置: deep-read
- 声称检查的不变量: clean expected：植错/零错断言与 scenario 一致；证据路径存在
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-review-era/clean/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-review-era/generative/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-review-era/rubric.md
- 处置: deep-read
- 声称检查的不变量: 维度权重和=100；kill switch；Dimension Applicability 格式（F115/F755 分布）
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: scope-based 表 parser 可读

### tests/tiers/t1-skill/shenbi-review-fanfic/bug-hunt/expected/expected-output.md
- 处置: deep-read
- 声称检查的不变量: bug-hunt expected：植错/零错断言与 scenario 一致；证据路径存在
- findings: ['F750']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 证据路径未植入且不存在: ['novel.json', 'audit/fanfic-review-ch4.md']

### tests/tiers/t1-skill/shenbi-review-fanfic/bug-hunt/input/scenario-phase4b-fanfic.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: ['F760']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 变体场景（G0.9 免疫）

### tests/tiers/t1-skill/shenbi-review-fanfic/bug-hunt/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: ['F752']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-review-fanfic/clean/expected/expected-output.md
- 处置: deep-read
- 声称检查的不变量: clean expected：植错/零错断言与 scenario 一致；证据路径存在
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-review-fanfic/clean/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-review-fanfic/generative/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: ['F753']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 引用空目录 tests/fixtures/truth/source_material/

### tests/tiers/t1-skill/shenbi-review-fanfic/rubric.md
- 处置: deep-read
- 声称检查的不变量: 维度权重和=100；kill switch；Dimension Applicability 格式（F115/F755 分布）
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: scope-based 表 parser 可读

### tests/tiers/t1-skill/shenbi-review-foreshadowing/bug-hunt/expected/expected-output.md
- 处置: deep-read
- 声称检查的不变量: bug-hunt expected：植错/零错断言与 scenario 一致；证据路径存在
- findings: ['F750']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 证据路径未植入且不存在: ['drafts/chapter-4.md', 'audit/foreshadowing-review.md']

### tests/tiers/t1-skill/shenbi-review-foreshadowing/bug-hunt/input/scenario-lifecycle.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: ['F760']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 变体场景（G0.9 免疫）

### tests/tiers/t1-skill/shenbi-review-foreshadowing/bug-hunt/input/scenario-phase2-foreshadowing.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: ['F760']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 变体场景（G0.9 免疫）

### tests/tiers/t1-skill/shenbi-review-foreshadowing/bug-hunt/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: ['F752']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-review-foreshadowing/clean/expected/expected-output.md
- 处置: deep-read
- 声称检查的不变量: clean expected：植错/零错断言与 scenario 一致；证据路径存在
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-review-foreshadowing/clean/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-review-foreshadowing/generative/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-review-foreshadowing/rubric.md
- 处置: deep-read
- 声称检查的不变量: 维度权重和=100；kill switch；Dimension Applicability 格式（F115/F755 分布）
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: scope-based 表 parser 可读

### tests/tiers/t1-skill/shenbi-review-highpoint/bug-hunt/expected/expected-output.md
- 处置: deep-read
- 声称检查的不变量: bug-hunt expected：植错/零错断言与 scenario 一致；证据路径存在
- findings: ['F750']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 证据路径未植入且不存在: ['drafts/chapter-11.md']

### tests/tiers/t1-skill/shenbi-review-highpoint/bug-hunt/input/scenario-phase4b-highpoint.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: ['F760']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 变体场景（G0.9 免疫）

### tests/tiers/t1-skill/shenbi-review-highpoint/bug-hunt/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: ['F752']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-review-highpoint/clean/expected/expected-output.md
- 处置: deep-read
- 声称检查的不变量: clean expected：植错/零错断言与 scenario 一致；证据路径存在
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-review-highpoint/clean/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-review-highpoint/generative/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-review-highpoint/rubric.md
- 处置: deep-read
- 声称检查的不变量: 维度权重和=100；kill switch；Dimension Applicability 格式（F115/F755 分布）
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: scope-based 表 parser 可读

### tests/tiers/t1-skill/shenbi-review-long-span/bug-hunt/expected/expected-output.md
- 处置: deep-read
- 声称检查的不变量: bug-hunt expected：植错/零错断言与 scenario 一致；证据路径存在
- findings: ['F750']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 证据路径未植入且不存在: ['drafts/chapter-6.md', 'drafts/chapter-10.md', 'drafts/chapter-9.md']

### tests/tiers/t1-skill/shenbi-review-long-span/bug-hunt/input/scenario-phase4b-long-span.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: ['F760']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 变体场景（G0.9 免疫）

### tests/tiers/t1-skill/shenbi-review-long-span/bug-hunt/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: ['F751', 'F752']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 植错断言在引用 fixture 缺失: ['他不禁想起了那']

### tests/tiers/t1-skill/shenbi-review-long-span/clean/expected/expected-output.md
- 处置: deep-read
- 声称检查的不变量: clean expected：植错/零错断言与 scenario 一致；证据路径存在
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-review-long-span/clean/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-review-long-span/generative/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: ['F753']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 引用空目录 tests/fixtures/drafts/

### tests/tiers/t1-skill/shenbi-review-long-span/rubric.md
- 处置: deep-read
- 声称检查的不变量: 维度权重和=100；kill switch；Dimension Applicability 格式（F115/F755 分布）
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: scope-based 表 parser 可读

### tests/tiers/t1-skill/shenbi-review-memo-compliance/bug-hunt/expected/expected-output.md
- 处置: deep-read
- 声称检查的不变量: bug-hunt expected：植错/零错断言与 scenario 一致；证据路径存在
- findings: ['F750']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 证据路径未植入且不存在: ['audit/memo-compliance-ch7.md', 'plans/chapter-7-plan.md', 'drafts/chapter-7.md']

### tests/tiers/t1-skill/shenbi-review-memo-compliance/bug-hunt/input/scenario-phase4-memo.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: ['F760']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 变体场景（G0.9 免疫）

### tests/tiers/t1-skill/shenbi-review-memo-compliance/bug-hunt/input/scenario-pressure.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: ['F760']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 压力场景（G0.9 免疫）

### tests/tiers/t1-skill/shenbi-review-memo-compliance/bug-hunt/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: ['F752']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-review-memo-compliance/clean/expected/expected-output.md
- 处置: deep-read
- 声称检查的不变量: clean expected：植错/零错断言与 scenario 一致；证据路径存在
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-review-memo-compliance/clean/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-review-memo-compliance/generative/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-review-memo-compliance/rubric.md
- 处置: deep-read
- 声称检查的不变量: 维度权重和=100；kill switch；Dimension Applicability 格式（F115/F755 分布）
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: scope-based 表 parser 可读

### tests/tiers/t1-skill/shenbi-review-motivation/bug-hunt/expected/expected-output.md
- 处置: deep-read
- 声称检查的不变量: bug-hunt expected：植错/零错断言与 scenario 一致；证据路径存在
- findings: ['F750']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 证据路径未植入且不存在: ['drafts/chapter-8.md']

### tests/tiers/t1-skill/shenbi-review-motivation/bug-hunt/input/scenario-phase4b-motivation.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: ['F760']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 变体场景（G0.9 免疫）

### tests/tiers/t1-skill/shenbi-review-motivation/bug-hunt/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: ['F753']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 引用空目录 tests/fixtures/truth/character_profiles/

### tests/tiers/t1-skill/shenbi-review-motivation/clean/expected/expected-output.md
- 处置: deep-read
- 声称检查的不变量: clean expected：植错/零错断言与 scenario 一致；证据路径存在
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-review-motivation/clean/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: ['F753']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 引用空目录 tests/fixtures/truth/character_profiles/

### tests/tiers/t1-skill/shenbi-review-motivation/generative/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-review-motivation/rubric.md
- 处置: deep-read
- 声称检查的不变量: 维度权重和=100；kill switch；Dimension Applicability 格式（F115/F755 分布）
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: scope-based 表 parser 可读

### tests/tiers/t1-skill/shenbi-review-pacing/bug-hunt/expected/expected-output.md
- 处置: deep-read
- 声称检查的不变量: bug-hunt expected：植错/零错断言与 scenario 一致；证据路径存在
- findings: ['F750']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 证据路径未植入且不存在: ['drafts/chapter-7.md', 'audit/pacing-review.md']

### tests/tiers/t1-skill/shenbi-review-pacing/bug-hunt/input/scenario-phase2-pacing.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: ['F760']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 变体场景（G0.9 免疫）

### tests/tiers/t1-skill/shenbi-review-pacing/bug-hunt/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: ['F752']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-review-pacing/clean/expected/expected-output.md
- 处置: deep-read
- 声称检查的不变量: clean expected：植错/零错断言与 scenario 一致；证据路径存在
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-review-pacing/clean/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-review-pacing/generative/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-review-pacing/rubric.md
- 处置: deep-read
- 声称检查的不变量: 维度权重和=100；kill switch；Dimension Applicability 格式（F115/F755 分布）
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: scope-based 表 parser 可读

### tests/tiers/t1-skill/shenbi-review-pov/bug-hunt/expected/expected-output.md
- 处置: deep-read
- 声称检查的不变量: bug-hunt expected：植错/零错断言与 scenario 一致；证据路径存在
- findings: ['F750']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 证据路径未植入且不存在: ['truth/chapter_summaries.md', 'drafts/chapter-9.md']

### tests/tiers/t1-skill/shenbi-review-pov/bug-hunt/input/scenario-phase4b-pov.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: ['F760']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 变体场景（G0.9 免疫）

### tests/tiers/t1-skill/shenbi-review-pov/bug-hunt/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-review-pov/clean/expected/expected-output.md
- 处置: deep-read
- 声称检查的不变量: clean expected：植错/零错断言与 scenario 一致；证据路径存在
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-review-pov/clean/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-review-pov/generative/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-review-pov/rubric.md
- 处置: deep-read
- 声称检查的不变量: 维度权重和=100；kill switch；Dimension Applicability 格式（F115/F755 分布）
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: scope-based 表 parser 可读

### tests/tiers/t1-skill/shenbi-review-reader-pull/bug-hunt/expected/expected-output.md
- 处置: deep-read
- 声称检查的不变量: bug-hunt expected：植错/零错断言与 scenario 一致；证据路径存在
- findings: ['F750']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 证据路径未植入且不存在: ['drafts/chapter-10.md', 'audit/reader-pull-ch10.md']

### tests/tiers/t1-skill/shenbi-review-reader-pull/bug-hunt/input/scenario-phase4-reader-pull.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: ['F760']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 变体场景（G0.9 免疫）

### tests/tiers/t1-skill/shenbi-review-reader-pull/bug-hunt/input/scenario-pressure.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: ['F760']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 压力场景（G0.9 免疫）

### tests/tiers/t1-skill/shenbi-review-reader-pull/bug-hunt/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: ['F751', 'F752']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 植错断言在引用 fixture 缺失: ['那天的天气不错']

### tests/tiers/t1-skill/shenbi-review-reader-pull/clean/expected/expected-output.md
- 处置: deep-read
- 声称检查的不变量: clean expected：植错/零错断言与 scenario 一致；证据路径存在
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-review-reader-pull/clean/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-review-reader-pull/generative/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-review-reader-pull/rubric.md
- 处置: deep-read
- 声称检查的不变量: 维度权重和=100；kill switch；Dimension Applicability 格式（F115/F755 分布）
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: scope-based 表 parser 可读

### tests/tiers/t1-skill/shenbi-review-resonance/bug-hunt/expected/expected-output.md
- 处置: deep-read
- 声称检查的不变量: bug-hunt expected：植错/零错断言与 scenario 一致；证据路径存在
- findings: ['F750']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 证据路径未植入且不存在: ['truth/audit_drift.md']

### tests/tiers/t1-skill/shenbi-review-resonance/bug-hunt/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: ['F751']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 植错断言在引用 fixture 缺失: ['数字没错，一条都没错']

### tests/tiers/t1-skill/shenbi-review-resonance/clean/expected/expected-output.md
- 处置: deep-read
- 声称检查的不变量: clean expected：植错/零错断言与 scenario 一致；证据路径存在
- findings: ['F750']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 证据路径未植入且不存在: ['truth/resonance_trend.md']

### tests/tiers/t1-skill/shenbi-review-resonance/clean/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-review-resonance/generative/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-review-resonance/rubric.md
- 处置: deep-read
- 声称检查的不变量: 维度权重和=100；kill switch；Dimension Applicability 格式（F115/F755 分布）
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: scope-based 表 parser 可读

### tests/tiers/t1-skill/shenbi-review-sensitivity/bug-hunt/expected/expected-output.md
- 处置: deep-read
- 声称检查的不变量: bug-hunt expected：植错/零错断言与 scenario 一致；证据路径存在
- findings: ['F750']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 证据路径未植入且不存在: ['config/platform-rules/qidian-fatigue-list.json', 'drafts/chapter-6.md']

### tests/tiers/t1-skill/shenbi-review-sensitivity/bug-hunt/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: ['F751', 'F752']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 植错断言在引用 fixture 缺失: ['白痴']

### tests/tiers/t1-skill/shenbi-review-sensitivity/clean/expected/expected-output.md
- 处置: deep-read
- 声称检查的不变量: clean expected：植错/零错断言与 scenario 一致；证据路径存在
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-review-sensitivity/clean/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-review-sensitivity/generative/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: ['F753']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 引用空目录 tests/fixtures/config/platform-rules/

### tests/tiers/t1-skill/shenbi-review-sensitivity/rubric.md
- 处置: deep-read
- 声称检查的不变量: 维度权重和=100；kill switch；Dimension Applicability 格式（F115/F755 分布）
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: scope-based 表 parser 可读

### tests/tiers/t1-skill/shenbi-review-spinoff/bug-hunt/expected/expected-output.md
- 处置: deep-read
- 声称检查的不变量: bug-hunt expected：植错/零错断言与 scenario 一致；证据路径存在
- findings: ['F750']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 证据路径未植入且不存在: ['truth/parent_chapter_summaries.md', 'drafts/spinoff-chapter-3.md']

### tests/tiers/t1-skill/shenbi-review-spinoff/bug-hunt/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: ['F752']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-review-spinoff/clean/expected/expected-output.md
- 处置: deep-read
- 声称检查的不变量: clean expected：植错/零错断言与 scenario 一致；证据路径存在
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-review-spinoff/clean/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-review-spinoff/generative/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-review-spinoff/rubric.md
- 处置: deep-read
- 声称检查的不变量: 维度权重和=100；kill switch；Dimension Applicability 格式（F115/F755 分布）
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: scope-based 表 parser 可读

### tests/tiers/t1-skill/shenbi-review-texture/bug-hunt/expected/expected-output.md
- 处置: deep-read
- 声称检查的不变量: bug-hunt expected：植错/零错断言与 scenario 一致；证据路径存在
- findings: ['F750']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 证据路径未植入且不存在: ['drafts/chapter-7.md']

### tests/tiers/t1-skill/shenbi-review-texture/bug-hunt/input/scenario-phase4b-texture.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: ['F760']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 变体场景（G0.9 免疫）

### tests/tiers/t1-skill/shenbi-review-texture/bug-hunt/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: ['F752']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-review-texture/clean/expected/expected-output.md
- 处置: deep-read
- 声称检查的不变量: clean expected：植错/零错断言与 scenario 一致；证据路径存在
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-review-texture/clean/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-review-texture/generative/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-review-texture/rubric.md
- 处置: deep-read
- 声称检查的不变量: 维度权重和=100；kill switch；Dimension Applicability 格式（F115/F755 分布）
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: scope-based 表 parser 可读

### tests/tiers/t1-skill/shenbi-review-world-rules/bug-hunt/expected/expected-output.md
- 处置: deep-read
- 声称检查的不变量: bug-hunt expected：植错/零错断言与 scenario 一致；证据路径存在
- findings: ['F750']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 证据路径未植入且不存在: ['truth/character_profiles/lin-mo.md', 'drafts/chapter-5.md']

### tests/tiers/t1-skill/shenbi-review-world-rules/bug-hunt/input/scenario-phase4b-world-rules.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: ['F760']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 变体场景（G0.9 免疫）

### tests/tiers/t1-skill/shenbi-review-world-rules/bug-hunt/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: ['F751', 'F752']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 植错断言在引用 fixture 缺失: ['二十五岁']

### tests/tiers/t1-skill/shenbi-review-world-rules/clean/expected/expected-output.md
- 处置: deep-read
- 声称检查的不变量: clean expected：植错/零错断言与 scenario 一致；证据路径存在
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-review-world-rules/clean/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-review-world-rules/generative/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-review-world-rules/rubric.md
- 处置: deep-read
- 声称检查的不变量: 维度权重和=100；kill switch；Dimension Applicability 格式（F115/F755 分布）
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: scope-based 表 parser 可读

### tests/tiers/t1-skill/shenbi-score-arc/rubric.md
- 处置: deep-read
- 声称检查的不变量: 维度权重和=100；kill switch；Dimension Applicability 格式（F115/F755 分布）
- findings: ['F754', 'F755', 'F759']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 无 Dimension Applicability section；rubric-only scaffold（无任何测试类型目录）

### tests/tiers/t1-skill/shenbi-score-stratum/rubric.md
- 处置: deep-read
- 声称检查的不变量: 维度权重和=100；kill switch；Dimension Applicability 格式（F115/F755 分布）
- findings: ['F754', 'F755', 'F759']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 无 Dimension Applicability section；rubric-only scaffold（无任何测试类型目录）

### tests/tiers/t1-skill/shenbi-score-volume/rubric.md
- 处置: deep-read
- 声称检查的不变量: 维度权重和=100；kill switch；Dimension Applicability 格式（F115/F755 分布）
- findings: ['F754', 'F755', 'F759']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 无 Dimension Applicability section；rubric-only scaffold（无任何测试类型目录）

### tests/tiers/t1-skill/shenbi-sequel-writing/bug-hunt/expected/expected-output.md
- 处置: deep-read
- 声称检查的不变量: bug-hunt expected：植错/零错断言与 scenario 一致；证据路径存在
- findings: ['F750']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 证据路径未植入且不存在: ['reports/sequel-pre-writing.md', 'snapshots/chapter-030/manifest.json', 'chapters/chapter-25.md']

### tests/tiers/t1-skill/shenbi-sequel-writing/bug-hunt/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: ['F753']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 引用空目录 tests/fixtures/snapshots/chapter-030/

### tests/tiers/t1-skill/shenbi-sequel-writing/clean/expected/expected-output.md
- 处置: deep-read
- 声称检查的不变量: clean expected：植错/零错断言与 scenario 一致；证据路径存在
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-sequel-writing/clean/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: ['F753']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 引用空目录 tests/fixtures/snapshots/chapter-030/

### tests/tiers/t1-skill/shenbi-sequel-writing/generative/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-sequel-writing/rubric.md
- 处置: deep-read
- 声称检查的不变量: 维度权重和=100；kill switch；Dimension Applicability 格式（F115/F755 分布）
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: scope-based 表 parser 可读

### tests/tiers/t1-skill/shenbi-short-drafting/bug-hunt/expected/expected-output.md
- 处置: deep-read
- 声称检查的不变量: bug-hunt expected：植错/零错断言与 scenario 一致；证据路径存在
- findings: ['F750']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 证据路径未植入且不存在: ['chapters/chapter-4.md', 'reports/batch-summary.md', 'truth/chapter-2-state.md']

### tests/tiers/t1-skill/shenbi-short-drafting/bug-hunt/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-short-drafting/clean/expected/expected-output.md
- 处置: deep-read
- 声称检查的不变量: clean expected：植错/零错断言与 scenario 一致；证据路径存在
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-short-drafting/clean/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-short-drafting/generative/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-short-drafting/rubric.md
- 处置: deep-read
- 声称检查的不变量: 维度权重和=100；kill switch；Dimension Applicability 格式（F115/F755 分布）
- findings: ['F755']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: per-dim-row 格式 parser no-op（F115 计数内）

### tests/tiers/t1-skill/shenbi-short-outline/bug-hunt/expected/expected-output.md
- 处置: deep-read
- 声称检查的不变量: bug-hunt expected：植错/零错断言与 scenario 一致；证据路径存在
- findings: ['F750']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 证据路径未植入且不存在: ['outline/short_story_map.md']

### tests/tiers/t1-skill/shenbi-short-outline/bug-hunt/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-short-outline/clean/expected/expected-output.md
- 处置: deep-read
- 声称检查的不变量: clean expected：植错/零错断言与 scenario 一致；证据路径存在
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-short-outline/clean/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-short-outline/generative/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-short-outline/rubric.md
- 处置: deep-read
- 声称检查的不变量: 维度权重和=100；kill switch；Dimension Applicability 格式（F115/F755 分布）
- findings: ['F755']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: per-dim-row 格式 parser no-op（F115 计数内）

### tests/tiers/t1-skill/shenbi-short-packaging/bug-hunt/expected/expected-output.md
- 处置: deep-read
- 声称检查的不变量: bug-hunt expected：植错/零错断言与 scenario 一致；证据路径存在
- findings: ['F750']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 证据路径未植入且不存在: ['import/packaging/cover_prompt.md', 'import/packaging/selling_points.md', 'import/packaging/blurbs.md']

### tests/tiers/t1-skill/shenbi-short-packaging/bug-hunt/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: ['F753']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 引用空目录 tests/fixtures/import/packaging/

### tests/tiers/t1-skill/shenbi-short-packaging/clean/expected/expected-output.md
- 处置: deep-read
- 声称检查的不变量: clean expected：植错/零错断言与 scenario 一致；证据路径存在
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-short-packaging/clean/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: ['F753']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 引用空目录 tests/fixtures/import/packaging/

### tests/tiers/t1-skill/shenbi-short-packaging/generative/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: ['F753']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 引用空目录 tests/fixtures/chapters/

### tests/tiers/t1-skill/shenbi-short-packaging/rubric.md
- 处置: deep-read
- 声称检查的不变量: 维度权重和=100；kill switch；Dimension Applicability 格式（F115/F755 分布）
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: scope-based 表 parser 可读

### tests/tiers/t1-skill/shenbi-snapshot-manage/bug-hunt/expected/expected-output.md
- 处置: deep-read
- 声称检查的不变量: bug-hunt expected：植错/零错断言与 scenario 一致；证据路径存在
- findings: ['F750']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 证据路径未植入且不存在: ['timeline.md', 'faction_records.md', 'snapshots/pre-chapter-25/metadata.json']

### tests/tiers/t1-skill/shenbi-snapshot-manage/bug-hunt/input/scenario-pressure.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: ['F760']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 压力场景（G0.9 免疫）

### tests/tiers/t1-skill/shenbi-snapshot-manage/bug-hunt/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-snapshot-manage/clean/expected/expected-output.md
- 处置: deep-read
- 声称检查的不变量: clean expected：植错/零错断言与 scenario 一致；证据路径存在
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-snapshot-manage/clean/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: ['F753']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 引用空目录 tests/fixtures/snapshots/pre-chapter-25/

### tests/tiers/t1-skill/shenbi-snapshot-manage/generative/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: ['F753']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 引用空目录 tests/fixtures/drafts/

### tests/tiers/t1-skill/shenbi-snapshot-manage/rubric.md
- 处置: deep-read
- 声称检查的不变量: 维度权重和=100；kill switch；Dimension Applicability 格式（F115/F755 分布）
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: scope-based 表 parser 可读

### tests/tiers/t1-skill/shenbi-state-settling/bug-hunt/expected/expected-output.md
- 处置: deep-read
- 声称检查的不变量: bug-hunt expected：植错/零错断言与 scenario 一致；证据路径存在
- findings: ['F750']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 证据路径未植入且不存在: ['state/chapter-20-settling.md']

### tests/tiers/t1-skill/shenbi-state-settling/bug-hunt/input/scenario-pressure.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: ['F760']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 压力场景（G0.9 免疫）

### tests/tiers/t1-skill/shenbi-state-settling/bug-hunt/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-state-settling/clean/expected/expected-output.md
- 处置: deep-read
- 声称检查的不变量: clean expected：植错/零错断言与 scenario 一致；证据路径存在
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-state-settling/clean/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-state-settling/generative/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-state-settling/rubric.md
- 处置: deep-read
- 声称检查的不变量: 维度权重和=100；kill switch；Dimension Applicability 格式（F115/F755 分布）
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: scope-based 表 parser 可读

### tests/tiers/t1-skill/shenbi-story-architecture/bug-hunt/expected/expected-output.md
- 处置: deep-read
- 声称检查的不变量: bug-hunt expected：植错/零错断言与 scenario 一致；证据路径存在
- findings: ['F750']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 证据路径未植入且不存在: ['story/okr.md']

### tests/tiers/t1-skill/shenbi-story-architecture/bug-hunt/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-story-architecture/clean/expected/expected-output.md
- 处置: deep-read
- 声称检查的不变量: clean expected：植错/零错断言与 scenario 一致；证据路径存在
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-story-architecture/clean/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-story-architecture/generative/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-story-architecture/rubric.md
- 处置: deep-read
- 声称检查的不变量: 维度权重和=100；kill switch；Dimension Applicability 格式（F115/F755 分布）
- findings: ['F755']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: per-dim-row 表含 1 个 N/A 豁免行，scoring.py load_applicability 不读该格式 → 豁免静默失效

### tests/tiers/t1-skill/shenbi-style-learning/bug-hunt/expected/expected-output.md
- 处置: deep-read
- 声称检查的不变量: bug-hunt expected：植错/零错断言与 scenario 一致；证据路径存在
- findings: ['F750']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 证据路径未植入且不存在: ['config/style_profile.md']

### tests/tiers/t1-skill/shenbi-style-learning/bug-hunt/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: ['F753']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 引用空目录 tests/fixtures/samples/reference-texts/

### tests/tiers/t1-skill/shenbi-style-learning/clean/expected/expected-output.md
- 处置: deep-read
- 声称检查的不变量: clean expected：植错/零错断言与 scenario 一致；证据路径存在
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-style-learning/clean/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: ['F753']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 引用空目录 tests/fixtures/samples/reference-texts/

### tests/tiers/t1-skill/shenbi-style-learning/generative/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: ['F753']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 引用空目录 tests/fixtures/samples/reference-texts/

### tests/tiers/t1-skill/shenbi-style-learning/rubric.md
- 处置: deep-read
- 声称检查的不变量: 维度权重和=100；kill switch；Dimension Applicability 格式（F115/F755 分布）
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: scope-based 表 parser 可读

### tests/tiers/t1-skill/shenbi-style-polishing/bug-hunt/expected/expected-output.md
- 处置: deep-read
- 声称检查的不变量: bug-hunt expected：植错/零错断言与 scenario 一致；证据路径存在
- findings: ['F750']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 证据路径未植入且不存在: ['drafts/chapter-7-polished.md']

### tests/tiers/t1-skill/shenbi-style-polishing/bug-hunt/input/scenario-phase2-polishing.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: ['F760']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 变体场景（G0.9 免疫）

### tests/tiers/t1-skill/shenbi-style-polishing/bug-hunt/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-style-polishing/clean/expected/expected-output.md
- 处置: deep-read
- 声称检查的不变量: clean expected：植错/零错断言与 scenario 一致；证据路径存在
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-style-polishing/clean/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-style-polishing/generative/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-style-polishing/rubric.md
- 处置: deep-read
- 声称检查的不变量: 维度权重和=100；kill switch；Dimension Applicability 格式（F115/F755 分布）
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: scope-based 表 parser 可读

### tests/tiers/t1-skill/shenbi-truth-sync/bug-hunt/expected/expected-output.md
- 处置: deep-read
- 声称检查的不变量: bug-hunt expected：植错/零错断言与 scenario 一致；证据路径存在
- findings: ['F750']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 证据路径未植入且不存在: ['truth/character_profiles/chen-wei.md', 'sync/truth-sync-15-18.md']

### tests/tiers/t1-skill/shenbi-truth-sync/bug-hunt/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-truth-sync/clean/expected/expected-output.md
- 处置: deep-read
- 声称检查的不变量: clean expected：植错/零错断言与 scenario 一致；证据路径存在
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-truth-sync/clean/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-truth-sync/generative/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-truth-sync/rubric.md
- 处置: deep-read
- 声称检查的不变量: 维度权重和=100；kill switch；Dimension Applicability 格式（F115/F755 分布）
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: scope-based 表 parser 可读

### tests/tiers/t1-skill/shenbi-volume-consolidation/bug-hunt/expected/expected-output.md
- 处置: deep-read
- 声称检查的不变量: bug-hunt expected：植错/零错断言与 scenario 一致；证据路径存在
- findings: ['F750']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 证据路径未植入且不存在: ['truth/pending_hooks.md', 'consolidation/volume-1/report.md']

### tests/tiers/t1-skill/shenbi-volume-consolidation/bug-hunt/input/scenario-phase3-volume-consolidation.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: ['F760']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 变体场景（G0.9 免疫）

### tests/tiers/t1-skill/shenbi-volume-consolidation/bug-hunt/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: ['F753']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 引用空目录 tests/fixtures/consolidation/volume-1/

### tests/tiers/t1-skill/shenbi-volume-consolidation/clean/expected/expected-output.md
- 处置: deep-read
- 声称检查的不变量: clean expected：植错/零错断言与 scenario 一致；证据路径存在
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-volume-consolidation/clean/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-volume-consolidation/generative/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-volume-consolidation/rubric.md
- 处置: deep-read
- 声称检查的不变量: 维度权重和=100；kill switch；Dimension Applicability 格式（F115/F755 分布）
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: scope-based 表 parser 可读

### tests/tiers/t1-skill/shenbi-volume-outlining/bug-hunt/expected/expected-output.md
- 处置: deep-read
- 声称检查的不变量: bug-hunt expected：植错/零错断言与 scenario 一致；证据路径存在
- findings: ['F750']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 证据路径未植入且不存在: ['story/volumes/volume-2.md']

### tests/tiers/t1-skill/shenbi-volume-outlining/bug-hunt/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-volume-outlining/clean/expected/expected-output.md
- 处置: deep-read
- 声称检查的不变量: clean expected：植错/零错断言与 scenario 一致；证据路径存在
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-volume-outlining/clean/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-volume-outlining/generative/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: ['F753']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 引用空目录 tests/fixtures/story/volumes/

### tests/tiers/t1-skill/shenbi-volume-outlining/rubric.md
- 处置: deep-read
- 声称检查的不变量: 维度权重和=100；kill switch；Dimension Applicability 格式（F115/F755 分布）
- findings: ['F755']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: per-dim-row 格式 parser no-op（F115 计数内）

### tests/tiers/t1-skill/shenbi-world-extraction/bug-hunt/expected/expected-output.md
- 处置: deep-read
- 声称检查的不变量: bug-hunt expected：植错/零错断言与 scenario 一致；证据路径存在
- findings: ['F750']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 证据路径未植入且不存在: ['world/story_bible.md', 'world/rules.md']

### tests/tiers/t1-skill/shenbi-world-extraction/bug-hunt/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-world-extraction/clean/expected/expected-output.md
- 处置: deep-read
- 声称检查的不变量: clean expected：植错/零错断言与 scenario 一致；证据路径存在
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-world-extraction/clean/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-world-extraction/generative/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-world-extraction/rubric.md
- 处置: deep-read
- 声称检查的不变量: 维度权重和=100；kill switch；Dimension Applicability 格式（F115/F755 分布）
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: scope-based 表 parser 可读

### tests/tiers/t1-skill/shenbi-worldbuilding/bug-hunt/expected/expected-output.md
- 处置: deep-read
- 声称检查的不变量: bug-hunt expected：植错/零错断言与 scenario 一致；证据路径存在
- findings: ['F750']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 证据路径未植入且不存在: ['world/rules.md']

### tests/tiers/t1-skill/shenbi-worldbuilding/bug-hunt/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-worldbuilding/clean/expected/expected-output.md
- 处置: deep-read
- 声称检查的不变量: clean expected：植错/零错断言与 scenario 一致；证据路径存在
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-worldbuilding/clean/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-worldbuilding/generative/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-worldbuilding/rubric.md
- 处置: deep-read
- 声称检查的不变量: 维度权重和=100；kill switch；Dimension Applicability 格式（F115/F755 分布）
- findings: ['F755']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: per-dim-row 表含 1 个 N/A 豁免行，scoring.py load_applicability 不读该格式 → 豁免静默失效

### tests/tiers/t1-skill/shenbi-writing-skills/bug-hunt/expected/expected-output.md
- 处置: deep-read
- 声称检查的不变量: bug-hunt expected：植错/零错断言与 scenario 一致；证据路径存在
- findings: ['F750']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 证据路径未植入且不存在: ['skills/custom-scene-transition/SKILL.md']

### tests/tiers/t1-skill/shenbi-writing-skills/bug-hunt/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-writing-skills/clean/expected/expected-output.md
- 处置: deep-read
- 声称检查的不变量: clean expected：植错/零错断言与 scenario 一致；证据路径存在
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-writing-skills/clean/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-writing-skills/generative/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/shenbi-writing-skills/rubric.md
- 处置: deep-read
- 声称检查的不变量: 维度权重和=100；kill switch；Dimension Applicability 格式（F115/F755 分布）
- findings: ['F755']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: per-dim-row 格式 parser no-op（F115 计数内）

### tests/tiers/t1-skill/using-shenbi/bug-hunt/expected/expected-output.md
- 处置: deep-read
- 声称检查的不变量: bug-hunt expected：植错/零错断言与 scenario 一致；证据路径存在
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/using-shenbi/bug-hunt/input/routing-phase2-character.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/using-shenbi/bug-hunt/input/routing-phase2-continuity.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/using-shenbi/bug-hunt/input/routing-phase2-foreshadowing.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/using-shenbi/bug-hunt/input/routing-phase2-polishing.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/using-shenbi/bug-hunt/input/routing-phase3-foreshadowing.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/using-shenbi/bug-hunt/input/routing-phase3-intent.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/using-shenbi/bug-hunt/input/routing-phase3-snapshot.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/using-shenbi/bug-hunt/input/routing-phase3-truth-sync.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/using-shenbi/bug-hunt/input/routing-phase4-management.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/using-shenbi/bug-hunt/input/routing-phase4b-audit.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/using-shenbi/bug-hunt/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: ['F751', 'F753', 'F761']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: 引用空目录 tests/fixtures/skill-triggering-prompts/；植错断言在引用 fixture 缺失: ['帮我看看角色', '检查时间线', '润色']

### tests/tiers/t1-skill/using-shenbi/clean/expected/expected-output.md
- 处置: deep-read
- 声称检查的不变量: clean expected：植错/零错断言与 scenario 一致；证据路径存在
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/using-shenbi/clean/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/using-shenbi/generative/input/scenario.md
- 处置: deep-read
- 声称检查的不变量: scenario 引用的 fixture 存在；植错断言与 fixture 内容一致
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t1-skill/using-shenbi/rubric.md
- 处置: deep-read
- 声称检查的不变量: 维度权重和=100；kill switch；Dimension Applicability 格式（F115/F755 分布）
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: scope-based 表 parser 可读

### tests/tiers/t2-phase/architecture/input/seed.md
- 处置: deep-read
- 声称检查的不变量: seed 指令技能序列与 deps.json roster 一致；引用 fixture 存在
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t2-phase/architecture/rubric.md
- 处置: deep-read
- 声称检查的不变量: 维度权重和=100；kill switch 可解析；无 Dimension Applicability section（F764）
- findings: ['F764']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t2-phase/audit/input/seed.md
- 处置: deep-read
- 声称检查的不变量: seed 指令技能序列与 deps.json roster 一致；引用 fixture 存在
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t2-phase/audit/rubric.md
- 处置: deep-read
- 声称检查的不变量: 维度权重和=100；kill switch 可解析；无 Dimension Applicability section（F764）
- findings: ['F764']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t2-phase/drafting/input/seed.md
- 处置: deep-read
- 声称检查的不变量: seed 指令技能序列与 deps.json roster 一致；引用 fixture 存在
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t2-phase/drafting/rubric.md
- 处置: deep-read
- 声称检查的不变量: 维度权重和=100；kill switch 可解析；无 Dimension Applicability section（F764）
- findings: ['F764']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t2-phase/foundation/input/seed.md
- 处置: deep-read
- 声称检查的不变量: seed 指令技能序列与 deps.json roster 一致；引用 fixture 存在
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t2-phase/foundation/rubric.md
- 处置: deep-read
- 声称检查的不变量: 维度权重和=100；kill switch 可解析；无 Dimension Applicability section（F764）
- findings: ['F764']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t2-phase/genesis/input/seed.md
- 处置: deep-read
- 声称检查的不变量: seed 指令技能序列与 deps.json roster 一致；引用 fixture 存在
- findings: ['F757']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high
- 备注: seed 列 6 skill vs deps genesis roster 11

### tests/tiers/t2-phase/genesis/rubric.md
- 处置: deep-read
- 声称检查的不变量: 维度权重和=100；kill switch 可解析；无 Dimension Applicability section（F764）
- findings: ['F764']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t2-phase/import/input/seed.md
- 处置: deep-read
- 声称检查的不变量: seed 指令技能序列与 deps.json roster 一致；引用 fixture 存在
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t2-phase/import/rubric.md
- 处置: deep-read
- 声称检查的不变量: 维度权重和=100；kill switch 可解析；无 Dimension Applicability section（F764）
- findings: ['F764']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t2-phase/management/input/seed.md
- 处置: deep-read
- 声称检查的不变量: seed 指令技能序列与 deps.json roster 一致；引用 fixture 存在
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t2-phase/management/rubric.md
- 处置: deep-read
- 声称检查的不变量: 维度权重和=100；kill switch 可解析；无 Dimension Applicability section（F764）
- findings: ['F764']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t2-phase/planning/input/seed.md
- 处置: deep-read
- 声称检查的不变量: seed 指令技能序列与 deps.json roster 一致；引用 fixture 存在
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t2-phase/planning/rubric.md
- 处置: deep-read
- 声称检查的不变量: 维度权重和=100；kill switch 可解析；无 Dimension Applicability section（F764）
- findings: ['F764']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t2-phase/short-story/input/seed.md
- 处置: deep-read
- 声称检查的不变量: seed 指令技能序列与 deps.json roster 一致；引用 fixture 存在
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t2-phase/short-story/rubric.md
- 处置: deep-read
- 声称检查的不变量: 维度权重和=100；kill switch 可解析；无 Dimension Applicability section（F764）
- findings: ['F764']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t3-pipeline/import-form/input/seed.md
- 处置: deep-read
- 声称检查的不变量: seed 指令技能序列与 deps.json roster 一致；引用 fixture 存在
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t3-pipeline/import-form/rubric.md
- 处置: deep-read
- 声称检查的不变量: 维度权重和=100；kill switch 可解析；无 Dimension Applicability section（F764）
- findings: ['F764']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t3-pipeline/long-form/input/seed.md
- 处置: deep-read
- 声称检查的不变量: seed 指令技能序列与 deps.json roster 一致；引用 fixture 存在
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t3-pipeline/long-form/rubric.md
- 处置: deep-read
- 声称检查的不变量: 维度权重和=100；kill switch 可解析；无 Dimension Applicability section（F764）
- findings: ['F764']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t3-pipeline/short-form/input/seed.md
- 处置: deep-read
- 声称检查的不变量: seed 指令技能序列与 deps.json roster 一致；引用 fixture 存在
- findings: 无
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high

### tests/tiers/t3-pipeline/short-form/rubric.md
- 处置: deep-read
- 声称检查的不变量: 维度权重和=100；kill switch 可解析；无 Dimension Applicability section（F764）
- findings: ['F764']
- 验证命令: read 全文；grep/python 统计（见 findings 证据）
- 置信度: high


---

## 3. 返回摘要

### findings 清单摘要（16 条）

| 编号 | 严重度 | 一句话 |
|---|---|---|
| F750 | P1 | 58/62 bug-hunt + 2/62 clean expected-output 证据路径未植入且不存在（T807 细分核实） |
| F751 | P1 | 12 个 bug-hunt scenario 植错断言在引用 fixture 中缺失（T808 核实） |
| F752 | P1 | audit-report-example.md 单文件被 16 个不同审计技能 scenario 当作审计报告证据（实为角色一致性报告） |
| F753 | P1 | 18 个 fixture 目录有效为空却被 33 个 tiers 文件显式引用为项目状态（T806 量化） |
| F754 | P1 | 8 个 rubric-only scaffold（无测试目录），其中 6 个是 T2 prereq → genesis/drafting/management 的 G5.1 恒 FAIL |
| F755 | P1 | F115 核实：38/82 rubric 过滤 no-op；4 份 per-dim-row rubric 的 N/A 豁免被 parser 吞掉 |
| F756 | P2 | F0-02 核实：deps.json 缺 5 skill 登记，契约 lint 无闭包检查 |
| F757 | P2 | genesis roster（11）与 rubric/seed（6）不一致，4 skill 双重归属破坏 phase_of 契约 |
| F758 | P2 | deps.json _tool_hashes 陈旧（63/99 不符 + 3 缺失），且无 gate 校验（死数据） |
| F759 | P2 | 8 个 rubric-only rubric 为模板化占位（通用维度/空 Standard 列） |
| F760 | P2 | T1105 扩展：8 压力场景 6 个 + 20 变体 16 个含非 fixture 路径，全部免疫 G0.9 |
| F761 | P2 | using-shenbi bug-hunt 引用空目录 skill-triggering-prompts/，声称 10 prompts 实为 0 |
| F762 | P2 | context-composing "ending diversity" 输入无多样性（ch8==ch9 逐字节相同，T802 核实） |
| F763 | M | acceptance.json 无 schema；t3 阈值无 gate 消费（死配置） |
| F764 | M | T2/T3 rubric 12/12 无 Dimension Applicability section（现状无害，格式不统一） |
| F765 | M | audit phase "All 18 review-*" 措辞与全量 24 个 review 技能不符 |

### 覆盖统计

- 清单文件：**445**；deep-read：**445/445**；未覆盖：**0**
- 结构分布：3 JSON（acceptance/deps/g4-exemptions）+ 70 T1 rubric（含 _template）+ 9 T2 rubric + 3 T3 rubric + 124 expected-output（62 bug-hunt + 62 clean）+ 224 scenario/变体/压力输入 + 12 seed = 445
- rubric 格式分布：44 scope-based（parser 可读）/ 18 per-dimension-row（no-op）/ 8 无 section；12 份 T2/T3 无 section → 38/82 no-op（F115 精确核实）
- T1 scaffold：69 个目录（74 skill 缺 5）；其中 61 个含 generative/clean/bug-hunt 完整三型、8 个 rubric-only
- 已知 finding 核实：F432 ✓、T807 ✓（58/62 细分）、T808 ✓（12 例）、F115 ✓（38/82）、F0-02 ✓、T806 ✓（18 空目录）、T1105 ✓（扩展至变体）、T801/T802 ✓、D1⑪ ✓（本区无 skip/xfail）

### 低置信度文件列表

**无。** 全部 445 文件均全文精读，且所有聚合性断言（rubric 解析、fixture 存在性、证据路径断链、植错短语缺失）均由 python 脚本复核并给出输出；代表性文件（chapter-drafting、review-sensitivity、review-continuity、review-arc-payoff、worldbuilding、context-composing、using-shenbi、t2/t3 全部 rubric+seed、3 个 JSON）均 read 全文精读。

### 未覆盖文件列表

**空（0 文件）。** 清单 Z7-b.files 的 445 个文件每个都有 §2 对应条目。
