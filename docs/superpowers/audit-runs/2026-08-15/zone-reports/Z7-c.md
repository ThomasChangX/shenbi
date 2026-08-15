# Z7-c 段审查报告 — tests/tiers（场景定义 + deps/acceptance/g4-exemptions）

- 轮次: 2026-08-15 | 分区: Z7-c（只读） | 清单: docs/superpowers/audit-runs/2026-08-15/zones/Z7-c.files
- 规模: 445 文件 = 3 JSON 清单 + 418 t1-skill（70 目录含 _template）+ 18 t2-phase（9 phase × seed+rubric）+ 6 t3-pipeline（3 pipeline × seed+rubric）
- 处置方式: 机械全量核验（445/445，脚本 /tmp/z7c_audit.py）+ 语义核心提取全量（69 skill 族，脚本 /tmp/z7c_deep.py）+ 全文深读 18 文件
- 编号段: F751–F775（本报告使用 F751–F764）

## 机械核验总结果（脚本 /tmp/z7c_audit.py，完整输出 /tmp/z7c_out.txt）

| 检查 | 结果 |
|---|---|
| A. 清单↔磁盘双向 bijection | 445/445 完全一致，无多无漏 |
| B. t1 场景 schema（224 场景文件） | 32 文件无 `## Skill Under Test`（= 变体格式，见 F762）；39 bug-hunt 无 `## Planted Defect`（变体/routing 用内联植入表）；0 个 SUT 与目录名错配；**场景引用的 fixture 路径 0 断链**（43 个不同路径全部存在）；16 场景 Test Setup 对同一 fixture ≥3 次复用（F752）；全部 124 个 expected-output 可判定（bug-hunt 均有编号 findings 表；clean 均有零问题断言） |
| C. t2/t3 seed↔deps | drafting 缺 3 前置、genesis 缺 5、management 缺 4（F755）；无多余 skill；t3 前置 phase 全部有效；seed 引用 fixture 全部存在 |
| D. deps 闭包 | t2 9 相位双射 ✓；t3 3 管线双射 ✓；全部前置 skill 存在于 skills/ 且有 t1 目录 ✓；_out_of_pipeline 7 项全部有效且无矛盾 ✓；g4_checker 引用有效 ✓；_tool_hashes 99 条中 66 条漂移（63 哈希过期 + 3 文件已删除）（F756）；_calibration_hashes.combined 与磁盘一致 ✓ |
| E. acceptance.json | {t1:94,t2:94,t3:94} 与 thresholds.py T1/T2/T3_PASS=94 一致，与 AGENTS.md "≥94 tier 推进" 一致 ✓（90/100 见 F760） |
| F. g4-exemptions.json | schema={generative,bughunt,clean}，全空列表，无失效条目；G0.12 声明全 skill 有 dedicated+generic 覆盖，无需豁免 ✓ |
| G. rubric schema（82 份） | 权重和=100：81/82（唯一例外 _template 占位符 =15，合理）；维度编号连续 ✓；kill switch 可被 scoring.py 正则捕获（t2 "phase = 0"、t3 "pipeline = 0"）✓；18 份 applicability 表头与解析器不兼容（F757） |
| H. fixture 双向 | 场景→fixture 路径断链 0；fixture→场景孤儿 73/91，其中全仓库（tests/src/docs/skills/justfile）零引用的真孤儿 15（F761） |

---

## Findings

**F751** | t1 bug-hunt/clean 模板场景的植入缺陷在所引 fixture 内容中不存在（内容级断链，测试空转） | error | **P0** | 证据（抽样，全部经 grep 落实）:
- `tests/tiers/t1-skill/shenbi-worldbuilding/bug-hunt/input/scenario.md:7-14,20` 声称 `tests/fixtures/chapter-plan-example.md` 含 hard rules/story bible/地理/暗流且 "Hard Rule 3 vs Hard Rule 7 矛盾"；实测该 fixture 是星火项目第 1 章备忘（`grep -c 'Hard Rule\|硬规则' = 0`）
- `tests/tiers/t1-skill/shenbi-chapter-planning/bug-hunt/input/scenario.md` 声称备忘"缺第 2/4/6 节"；实测 `tests/fixtures/chapter-plan-example.md:28,70,97` 第 2/4/6 节全部存在（8 节齐全）→ 诚实 agent 报零缺陷触发 false-negative kill switch 归零，或复述提示词伪通过
- `tests/tiers/t1-skill/shenbi-review-era/.../scenario.md` 声称 `tests/fixtures/novel-example.json` 声明 time_period=Ming Dynasty；实测该 JSON 无 time_period 字段（mode:"original"）。`shenbi-review-fanfic` 同文件声称 fanfic_mode:"Canon" — 同样不存在
- `tests/fixtures/chapter-draft-example.md`（18764B，星火第 1 章草稿，主角林烽）中 林墨/苏晴/老陈/小贩/给力/点赞/白痴/玉佩/Su Han/Mei Ling 计数全为 0 — review-{character,continuity,dialogue,motivation,pov,sensitivity,spinoff,texture,world-rules,era} 的具名缺陷不可发现；`shenbi-chapter-drafting` 声称 "然而4x/不过3x/与此同时2x"，实测三词合计 1 次
- `tests/fixtures/pending-hooks-example.md` 实为 hook-ch1-001..003（第 1 章 3 活跃伏笔），无 hook-001/hook-002/玉佩/CP=250/ABANDONED/第 5 章种植段 — foreshadowing-{plant,track,resolve} 的缺陷不可发现
- `tests/fixtures/audit-report-example.md` 是星火第 1 章审计报告（通过，1 warning），无 CC-F001/CH-F001/小贩/三天后/检查 8-10 跳过 — drift-guidance、review-{anti-ai,character,continuity,foreshadowing,highpoint,pacing,reader-pull,memo-compliance} 所述缺陷不可发现
- `skills/custom-scene-transition/SKILL.md`（writing-skills 缺陷定位）不存在于 skills/（74 目录无此项）
根因: 模板代场景采用"叙事性 Setup + 声称性缺陷定位"写法，fixture 只做了路径替换未做内容对齐；G0.9（g0_purity.py:26-40）只校验路径前缀纯度，不校验内容支撑；框架无缺陷注入机制（dispatcher 不物化产物）→ 测试要么恒失败要么奖励复述。验证: `python3 /tmp/z7c_audit.py`（B/B2 段）+ 上述 grep。建议: 以 scenario-* 变体格式（内联自包含，见 using-shenbi、review-character/phase2-character.md）为标准重写模板代场景，或为每个 bug-hunt 生成含缺陷的真实 fixture（G0.9 合规），并把"缺陷定位 fixture 内容包含缺陷描述关键词"加入 G0.9。

**F752** | 单一 fixture 被复用为多个不同产物角色，出现自引用比较 | error | **P1** | 证据: `shenbi-location-builder/bug-hunt/input/scenario.md` 缺陷表第一行定位为 "`tests/fixtures/chapter-plan-example.md` vs `tests/fixtures/chapter-plan-example.md`"（同一文件自我矛盾）；`shenbi-character-design/bug-hunt:8-11` 主角/反派/导师/关系矩阵 4 角色全指 `character-profile-example.md`（实为单角色档案）；`shenbi-snapshot-manage/bug-hunt` 的 11 个 truth 文件编号列表中 chapter-summaries-example.md 出现 4 次（1,3,11 位）、pending-hooks 3 次、author-intent 2 次；`shenbi-volume-outlining` 三卷角色全指 outline-example.md；worldbuilding/world-extraction/location-builder/faction-builder 的 Test Setup 4-5 个角色全指 chapter-plan-example.md。根因: 模板占位符批量替换未按角色映射真实 fixture。同 F751 根因，单列因其自引用证据独立成立。

**F753** | report-example.txt 角色滥用：874KB 公版小说《钢铁是怎样炼成的》（report-example.txt:1-5）被 9 个场景声称为各自的评审产物 | error | **P1** | 证据: 作为 import 源小说使用正确（t2/import/input/seed.md:3、t3/import-form、import-analysis generative）；但 drift-guidance（"drift guidance output at report-example.txt contains 3 drift items"）、intent-management（"3 warning-level items"）、foundation-review（"5 维评分 18/25…"）、market-radar（"Qidian 排行榜报告"）、length-normalizing（"missing consistency checklist"）、state-settling（"Su Han distrust entry"）、truth-sync（"Chen Wei weapon field"）、volume-consolidation（"H001-H005 hooks list"）、short-packaging（"blurb version 1"）均声称该文件是其技能输出 — 内容全部不存在。根因同 F751。建议: 为各评审技能生成真实输出 fixture 或改内联。

**F754** | expected-output.md 的证据定位指向从未物化的轮次产物路径 | error | **P1** | 证据: `shenbi-worldbuilding/bug-hunt/expected/expected-output.md:7` 要求证据 "`world/rules.md`: hard rules section"；shenbi-story-architecture 期望证据 `story/okr.md`；shenbi-plot-thread-weaver 期望 `story/thread-map.md`；shenbi-chapter-revision 期望 `drafts/chapter-12-revised.md`。dispatcher 无 fixture→round-dir 物化逻辑（grep dispatcher/ 无 scenario/plant 机制），这些路径在评审时不存在 → "Evidence without file+line citation → detection dimension = 0" 的 kill switch 无法以真实证据满足。根因: 期望证据写的是假想产物树而非 fixture。建议: 期望证据定位统一指向 tests/fixtures 真实文件行号。

**F755** | t2 seed 与 deps.json 前置闭包漂移（12 skill 未入 seed） | deps | **P2** | 证据: deps.json:57-68 drafting 9 前置 vs `t2-phase/drafting/input/seed.md:5-11` 仅 6 步（缺 shenbi-foreshadowing-recall、shenbi-review-resonance、shenbi-score-arc）；deps.json:3-16 genesis 11 前置 vs seed 仅 6 步（缺 book-spine-init、genre-config、pacing-design、story-architecture、volume-outlining）；deps.json:105-116 management 9 前置 vs seed 5 步（缺 review-arc-payoff、memory-distill、score-volume、score-stratum）；t2 rubric 头部行同样缺（genesis rubric 头仅列 6 skill）。scoring.py:226-231 check_gate_markers 要求 deps 全部前置的 `G4-<skill>-generative.json` marker — seed 未运行的 skill 永远产不出 marker。t3/long-form seed 第 4/7 步同步缺失（drafting 6/9、management 5/9）。验证: 脚本 C 段输出。建议: seed/rubric 与 deps prerequisites 对齐或 deps 拆分 core/optional。

**F756** | deps.json `_tool_hashes` 99 条中 66 条与磁盘不符（63 哈希过期 + 3 文件已删除） | deps | **P2** | 证据: 脚本 D 段；已删除仍列于 deps.json:210,216,219（src/shenbi/summarize_round.py、contract.py、update_progress.py）；其余如 logging.py、scoring.py、全部 gates/g4/* 哈希漂移。注意 G0 只锁 _calibration_hashes（g0.py:71-127 G0.14，实测匹配 ✓），_tool_hashes 无任何运行时校验（仅 lock 脚本 tests/lock-tool-hashes.sh）→ 锁已名存实亡。建议: 运行 lock-tool-hashes.sh 重锁或将 _tool_hashes 纳入 G0 校验；清除已删除文件条目。

**F757** | Dimension Applicability 机制对 18 份 rubric 完全失效，4 份还宣称会发生权重重归一化 | error | **P2** | 证据: scoring.py:84-112 load_applicability 只识别 `| Dimension scope |` 表头；worldbuilding、faction-builder、location-builder、story-architecture、power-system、pacing-design、plot-thread-weaver、chapter-planning、character-design、context-composing、foreshadowing-{plant,resolve}、genre-config、relationship-map、short-{drafting,outline}、volume-outlining、writing-skills 共 18 份用 `| # | Dimension | Bug-hunt Standard | Clean Standard |` 旧表头 → 解析为空、不过滤。其中 worldbuilding/faction-builder/location-builder/story-architecture 的 N/A 行明文声称 "scoring.py renormalizes weights for remaining applicable dimensions" — 实际不会发生；且被豁免维度仍会被要求打分（validate_scores 拒绝缺失维度）。全仓库仅 shenbi-chapter-drafting 一份的 No 行带 dim 编号可被解析动作（`| Prose/narrative quality (dims 6,7,9) | No | No | Yes |`）。根因: 模板两代并存（_template 已是新表头，旧 rubric 未迁移）。建议: 统一迁移到 _template 新表头并在 scope 单元格标注 dim 编号。

**F758** | 8 个 skill 的 T1 仅有 rubric（无任何场景），其中 2 个连 kill switch/分档线都缺，而 deps 声称它们 "pass T1" | error | **P2** | 证据: shenbi-anchor-curate、book-spine-init、escalation-review、foreshadowing-recall、memory-distill、score-arc、score-stratum、score-volume 各仅 1 文件 rubric.md；anchor-curate 与 escalation-review 无 Kill Switch 节、无 90-100 分档线、无 applicability 节；deps.json:308-323 `_out_of_pipeline._note`: "These skills pass T1 but are not required by any T2 phase" — anchor-curate/escalation-review 无 T1 场景即无从"pass T1"。score-arc/stratum/volume/memory-distill/book-spine-init/foreshadowing-recall 由 T2 覆盖（drafting/management/genesis 前置），anchor-curate 与 escalation-review 则完全无场景层覆盖（tests/pipeline 中仅为 Python 单测对象）。建议: 补场景或显式声明"仅单测覆盖"。

**F759** | 5 个 skills/ 目录游离于三层测试体系外 | error | **P2** | 证据: skills/ 共 74 目录；t1-skill 覆盖 69；deps.json 无 shenbi-foreshadowing-lifecycle、shenbi-review-group-{character,craft,factual,plan}（t2/t3/_out_of_pipeline 均未列）→ 无 T1 场景、无 T2 前置、无豁免声明。附带: AGENTS.md 声称 "67 functional + 2 meta = 69 total"，磁盘 74（AGENTS.md 属他段，此处仅交叉备注）。建议: 入册 deps/_out_of_pipeline 或明确 meta 编排器豁免。

**F760** | 68 份 rubric 分档线 "75-89: PASS (acceptable)" 与 AGENTS.md "≥90 individual test pass" 冲突 | error | **P2** | 证据: 68 份 t1 rubric 逐字含 `90-100: PASS | 75-89: PASS (acceptable) | 60-74: CONDITIONAL | 0-59: FAIL`；scoring.py:201-208 classify() 同样把 ≥75 归 PASS_ACCEPTABLE（代码↔rubric 自洽）；thresholds.py:10 TEST_PASS=90 与 AGENTS.md ≥90 为更严契约。75-89 的结果会被标注 "PASS (acceptable)"，违背文档化通过线。建议: 统一术语（如 75-89 改称 CONDITIONAL-PASS）或在 AGENTS.md/阈值注明 acceptable band 语义。

**F761** | 15 个真孤儿 fixture，其中 4 个 world-* 正是 F751 场景本应使用的产物 | optimization | **P2** | 证据: 脚本 H 段；全仓库零引用: world-rules-example.md、world-story-bible-example.md、world-locations-example.md、world-power-system-example.md、truth-chapter_summaries.md、chapter-{2..10}-draft.md（9 个）、chapter-8-example.md。world-rules-example.md 是高质量《世界铁律》真实产物（规则一~六），恰是 worldbuilding/location/power-system 场景所需却从未接线。建议: 将 worldbuilding 族场景切换到 world-* fixture（配合 F751 修复）；评估 chapter-N-draft.md 是否留作长跨度备料。

**F762** | t1 场景 schema 双轨漂移：变体文件绕过 G0.9 纯度扫描 | error | **P2** | 证据: 模板代（英文标题 + fixture 引用）与变体代（中文自包含：测试目标/植入的 Bug/期望的审计输出/通过条件/失败条件，如 using-shenbi/bug-hunt/input/routing-phase2-character.md、shenbi-review-character/.../scenario-phase2-character.md）并存；G0.9（g0_purity.py:26-40,66+）只扫 `<test_type>/input/scenario.md`，30 个 scenario-*.md 与 10 个 routing-*.md 不被任何纯度/存在性检查覆盖（脚本 B 段: 32 文件无 SUT 块、39 无 Planted Defect 节 — 全为变体格式，属预期但框架未认知）。变体代质量显著更高（内联可判定），建议将其定为规范并对 input/ 下全部 .md 做 schema 登记。

**F763** | "11 truth files" 为虚构常数，与 fixture/技能契约不符 | error | **P2** | 证据: shenbi-snapshot-manage/bug-hunt/input/scenario.md 与 clean、t2/management/input/seed.md:5 均断言 11 个 truth 文件；skills/shenbi-snapshot-manage/SKILL.md:8,69,118 用 `truth/*.md` glob 不定数；tests/fixtures/truth/ 顶层仅 5 个 .md（+2 子目录）；snapshots/chapter-025/truth/ 实有 5 文件（bug-hunt 却断言快照 8/11、缺 ability_registry/faction_records/timeline — 该 3 文件全仓库不存在）。建议: 场景改为引用 fixtures/truth 实际清单。

**F764** | 零散不一致 | error | **M** | 证据: (a) shenbi-chapter-pattern expected-output 将 决战 译作 "action"（场景/期望术语不一致）；(b) shenbi-review-* 场景把单一 chapter-draft-example.md 说成"第 4~11 章"不同章节（一个文件多章节身份）；(c) _template/rubric.md 权重和=15（占位符所致，合理但机械检查需豁免标记）；(d) shenbi-genre-config bug-hunt 缺陷定位于不存在的 "modification log"，clean 声称存在 genre-config.json.bak（无此文件）。

---

## 簇条目（覆盖全部 445 文件）

### tests/tiers/{acceptance.json, deps.json, g4-exemptions.json}
- 处置: deep-read（机械核验 3 文件 + 全文读 3 文件）
- 声称检查的不变量: 阈值 94↔thresholds.py↔AGENTS.md；t2/t3 键↔磁盘双射；前置闭包↔skills/↔t1 目录；_out_of_pipeline 无矛盾；豁免清单有效性；哈希锁
- findings: F755 F756 F758(声明面) F759(声明面) + E/F 段通过项
- 验证命令: `python3 /tmp/z7c_audit.py` → A✓ t2/t3 双射✓ acceptance✓ exemptions✓ calibration-hash✓；_tool_hashes 66/99 漂移；deps 前置全存在✓
- 置信度: high

### tests/tiers/t1-skill/_template（6 文件: rubric + 3 场景 + 2 expected）
- 处置: deep-read（机械核验 6 + 全文读 4）
- 声称检查的不变量: 模板 schema 完整性（新代 applicability 表头 + kill switch 三型 + 分档线）
- findings: 无（模板本身健康；权重占位符 =15 属预期，见 F764c）
- 验证命令: 脚本 B/G 段 → 3 场景无 SUT 块（占位符所致，预期）
- 置信度: high

以下 69 个 t1-skill 簇，每簇机械核验其全部文件（schema/fixture 路径/expected 可判定性/rubric 权重），语义核心（Setup/缺陷表/期望表/applicability）经 /tmp/z7c_deep.py 全量提取审读；状态码: **BROKEN**=F751 类缺陷不可发现（已 grep 实证）、**ROLE**=F752 角色复用、**OK**=可判定（内联自包含）、**RUBRIC-ONLY**=F758。

| 簇（文件数） | 深读文件 | 机械核验 | 语义状态 |
|---|---|---|---|
| shenbi-anchor-curate (1) | rubric.md | 通过 | RUBRIC-ONLY（且缺 kill switch/分档线，F758） |
| shenbi-anti-detect (6) | bug-hunt scenario+expected, rubric, clean scenario | 通过；applicability 新表头 | BROKEN（声称的改写产物不存在于磁盘，F751/F754） |
| shenbi-book-spine-init (1) | rubric.md | 通过 | RUBRIC-ONLY（T2 genesis 覆盖） |
| shenbi-canon-import (6) | bug-hunt scenario+expected, rubric | 通过 | BROKEN（缺陷引 character-profile-example.md 单角色档案，F751） |
| shenbi-chapter-drafting (7, +pressure) | bug-hunt scenario+expected, scenario-pressure, rubric | 通过；唯一可动作的 No 行 rubric | BROKEN（转折词计数 4+3+2 vs 实测 1，F751）；pressure 变体自包含 OK |
| shenbi-chapter-pattern (6) | bug-hunt scenario+expected, rubric | 通过 | BROKEN-轻度（模式数据内联可判定，但 fixture 角色错位 + F764a 术语漂移） |
| shenbi-chapter-planning (6) | bug-hunt scenario+expected, clean scenario, rubric | 通过 | BROKEN（fixture 8 节齐全 vs 声称缺 3 节，F751 铁证）；clean ✓ 正确 |
| shenbi-chapter-revision (7, +phase4b) | bug-hunt scenario+expected, variant, rubric | 通过 | BROKEN（被审"修订稿"不存在；Frostbite/Frostveil 零命中）；variant 内联 OK |
| shenbi-character-design (6) | bug-hunt scenario, clean scenario, rubric | 通过 | ROLE+BROKEN（4 角色→1 单角色档案，F752） |
| shenbi-character-extraction (6) | bug-hunt scenario+expected, rubric | 通过 | BROKEN（"cynical sense of humor" 零命中） |
| shenbi-context-composing (6) | bug-hunt scenario, rubric | 通过（SUT 块在首行标题内，格式变体） | BROKEN（缺陷载体"组装结果"未物化） |
| shenbi-drift-guidance (6) | bug-hunt scenario+expected, rubric | 通过 | BROKEN（audit-report-example.md 无 CC-F001，F751） |
| shenbi-escalation-review (1) | rubric.md | 通过 | RUBRIC-ONLY（缺 kill switch/分档线，F758；全场景层无覆盖） |
| shenbi-faction-builder (6) | bug-hunt scenario, clean scenario, rubric | 通过；旧 applicability 表头+N/A 行 | ROLE+BROKEN（chapter-plan 当派系文件；"Order of Ash"不存在；F757） |
| shenbi-foreshadowing-plant (6) | bug-hunt scenario+expected, clean scenario, rubric | 通过 | BROKEN（pending-hooks 无第 5 章 12 操作段） |
| shenbi-foreshadowing-recall (1) | rubric.md | 通过 | RUBRIC-ONLY（T2 drafting 覆盖） |
| shenbi-foreshadowing-resolve (6) | bug-hunt scenario+expected, rubric | 通过 | BROKEN（hook-002 CP=250 不存在） |
| shenbi-foreshadowing-track (8, +plant-track-resolve/+pressure) | bug-hunt scenario+expected, 2 variants, rubric | 通过 | BROKEN（hook-001 玉佩 ABANDONED 不存在）；两 variant 内联 OK |
| shenbi-foundation-review (6) | bug-hunt scenario+expected, rubric | 通过 | BROKEN-轻度（评分内联可判定但声称载体 report-example.txt 是小说，F753） |
| shenbi-genre-config (6) | bug-hunt scenario, clean scenario, rubric | 通过 | BROKEN（"modification log"/.bak 不存在，F764d） |
| shenbi-import-analysis (7, +pressure) | bug-hunt scenario+expected, pressure, rubric | 通过（7 kill switch） | BROKEN（"coastal village/navy captain" 零命中）；pressure 变体 OK |
| shenbi-intent-management (6) | bug-hunt scenario, clean scenario, rubric | 通过 | BROKEN-轻度（P1 建议文本内联可判定，载体错位 F753） |
| shenbi-length-normalizing (6) | bug-hunt scenario+expected, rubric | 通过 | BROKEN（teahouse 场景/checklist 载体不存在） |
| shenbi-location-builder (6) | bug-hunt scenario+expected, clean scenario, rubric | 通过；旧表头+N/A | ROLE+BROKEN（自引用比较铁证，F752；F757） |
| shenbi-market-radar (6) | bug-hunt scenario+expected, rubric | 通过 | BROKEN（排行榜报告载体是小说，F753） |
| shenbi-memory-distill (1) | rubric.md | 通过 | RUBRIC-ONLY（T2 management 覆盖） |
| shenbi-pacing-design (6) | bug-hunt scenario+expected, rubric | 通过；旧表头 | BROKEN（Cycle 3 节奏环不存在于 chapter-plan）；F757 |
| shenbi-plot-thread-weaver (6) | bug-hunt scenario+expected, rubric | 通过；旧表头 | BROKEN（thread map/第 15 章条目不存在）；F757 |
| shenbi-power-system (6) | bug-hunt scenario+expected, rubric | 通过；旧表头 | BROKEN（"Spirit Sovereign" 层级不存在；孤儿 fixture world-power-system-example.md 本应用此，F761） |
| shenbi-relationship-map (6) | bug-hunt scenario+expected, rubric | 通过；旧表头 | BROKEN（单角色档案无关系条目） |
| shenbi-review-anti-ai (7, +pressure) | bug-hunt scenario+expected, pressure, rubric | 通过（7 kill switch） | BROKEN（审计载体是星火 ch1 通过报告，无检查 8-10 跳过）；pressure OK |
| shenbi-review-arc-payoff (6) | bug-hunt scenario+expected, rubric | 通过（6 kill switch） | **OK**（新代：旁白兑现引文内联，可判定，质量高） |
| shenbi-review-character (7, +phase2) | variant 全文, bug-hunt scenario, rubric | 通过（7 kill switch） | 主场景 BROKEN（小贩 BDI 缺席不存在）；variant scenario-phase2-character.md **OK**（优秀范本） |
| shenbi-review-continuity (7, +phase2) | bug-hunt scenario+expected, variant | 通过 | 主场景 BROKEN（三天后/五天恢复不存在）；variant OK |
| shenbi-review-dialogue (7, +phase4) | bug-hunt scenario, variant | 通过 | 主场景 BROKEN（苏晴/老陈 零命中）；variant OK |
| shenbi-review-era (7, +phase4b) | bug-hunt scenario, variant | 通过 | 主场景 BROKEN（novel-example.json 无 time_period，铁证）；variant OK |
| shenbi-review-fanfic (7, +phase4b) | bug-hunt scenario, variant | 通过 | 主场景 BROKEN（无 fanfic_mode 字段）；variant OK |
| shenbi-review-foreshadowing (8, +lifecycle/+phase2) | bug-hunt scenario, 2 variants, rubric | 通过 | 主场景 BROKEN（mysterious-key 不存在）；两 variant OK |
| shenbi-review-highpoint (7, +phase4b) | bug-hunt scenario, variant | 通过 | 主场景 BROKEN（载体是 ch1 通过报告）；variant OK |
| shenbi-review-long-span (7, +phase4b) | bug-hunt scenario, variant | 通过 | OK-轻度（n-gram 出现位置内联列出，可判定；载体声明仍错位） |
| shenbi-review-memo-compliance (8, +phase4/+pressure) | bug-hunt scenario, 2 variants | 通过 | OK-轻度（4 场景清单内联；audit 载体错位）；variants OK |
| shenbi-review-motivation (7, +phase4b) | bug-hunt scenario, variant | 通过 | 主场景 BROKEN（林墨背叛链不存在）；variant OK |
| shenbi-review-pacing (7, +phase2) | bug-hunt scenario, variant | 通过 | 主场景 BROKEN（QUEST/FIRE 误分类载体不存在）；variant OK |
| shenbi-review-pov (7, +phase4b) | bug-hunt scenario, variant | 通过 | 主场景 BROKEN（林墨/苏晴信息泄漏不存在）；variant OK |
| shenbi-review-reader-pull (8, +phase4/+pressure) | bug-hunt scenario, 2 variants | 通过 | 主场景 BROKEN（开篇钩子评估缺失载体不存在）；variants OK |
| shenbi-review-resonance (6) | bug-hunt scenario+expected, rubric | 通过（6 kill switch） | **OK**（新代：高潮段落引文内联，可判定，质量高） |
| shenbi-review-sensitivity (6) | bug-hunt scenario+expected, rubric | 通过 | BROKEN（白痴 一词零命中） |
| shenbi-review-spinoff (6) | bug-hunt scenario, rubric | 通过 | BROKEN（时间线泄漏载体不存在） |
| shenbi-review-texture (7, +phase4b) | bug-hunt scenario, variant | 通过 | 主场景 BROKEN（第 11 段清单式段落不存在）；variant OK |
| shenbi-review-world-rules (7, +phase4b) | bug-hunt scenario, variant | 通过 | 主场景 BROKEN（二十五岁/17 岁矛盾不存在）；variant OK |
| shenbi-score-arc (1) | rubric.md 全文 | 通过（权重 15+50+20+15=100） | RUBRIC-ONLY（T2 drafting 覆盖；有分档线、无 kill switch/applicability） |
| shenbi-score-stratum (1) | rubric.md | 通过 | RUBRIC-ONLY（T2 management 覆盖） |
| shenbi-score-volume (1) | rubric.md | 通过 | RUBRIC-ONLY（T2 management 覆盖） |
| shenbi-sequel-writing (6) | bug-hunt scenario+expected, rubric | 通过 | BROKEN（虚构校验和 a1b2c3d4…；T+30/120min 时间线无载体） |
| shenbi-short-drafting (6) | bug-hunt scenario+expected, rubric | 通过；旧表头 | BROKEN（时序/斗篷变色载体不存在）；F757 |
| shenbi-short-outline (6) | bug-hunt scenario+expected, rubric | 通过；旧表头 | BROKEN（40/30/30 比例声明载体不存在）；F757 |
| shenbi-short-packaging (6) | bug-hunt scenario+expected, rubric | 通过 | BROKEN（blurb/卖点载体是小说文本，F753） |
| shenbi-snapshot-manage (7, +pressure) | bug-hunt scenario+expected, rubric | 通过 | ROLE+BROKEN（11 文件清单重复条目 + 3 个不存在的文件名，F752/F763）；pressure OK |
| shenbi-state-settling (7, +pressure) | bug-hunt scenario+expected, rubric | 通过 | BROKEN（Su Han/Mei Ling 章节声明零命中；载体 F753）；pressure OK |
| shenbi-story-architecture (6) | bug-hunt scenario, clean scenario, rubric | 通过；旧表头+N/A | ROLE+BROKEN（chapter-plan 当 story frame/OKR）；F757 |
| shenbi-style-learning (6) | bug-hunt scenario+expected, rubric | 通过 | BROKEN（style-profile 无主观词、维度缺失声明不实） |
| shenbi-style-polishing (7, +phase2) | bug-hunt scenario, variant, rubric | 通过 | 主场景 BROKEN（润色产物不存在）；variant OK |
| shenbi-truth-sync (6) | bug-hunt scenario+expected, rubric | 通过 | BROKEN（Chen Wei 武器冲突载体是小说，F753） |
| shenbi-volume-consolidation (7, +phase3) | bug-hunt scenario, variant, rubric | 通过 | BROKEN（H001-H005 清单载体不存在；F753）；variant OK |
| shenbi-volume-outlining (6) | bug-hunt scenario+expected, rubric | 通过；旧表头 | ROLE+BROKEN（三卷→同一单卷 outline）；F757 |
| shenbi-world-extraction (6) | bug-hunt scenario+expected, rubric | 通过（7 kill switch） | ROLE+BROKEN（chapter-plan 5 连用为世界提取产物） |
| shenbi-worldbuilding (6) | 全部 5 个 md 深读 | 通过；旧表头+N/A | ROLE+BROKEN（Hard Rule 3/7 不存在，F751 头号证据；孤儿 world-* fixture 本应用此 F761） |
| shenbi-writing-skills (6) | bug-hunt scenario+expected, rubric | 通过；旧表头 | BROKEN（skills/custom-scene-transition 不存在） |
| using-shenbi (16, +10 routing) | routing-phase2-character 全文, clean scenario, bug-hunt scenario | 通过（8 kill switch） | **OK**（主场景 10 请求内联可判定；10 个 routing 变体自包含、通过/失败条件明确 — 全套最佳实践） |

### tests/tiers/t2-phase/<phase>（9 簇 × {input/seed.md, rubric.md}）
- 处置: deep-read（机械核验 18 文件；9 seed 全文读 + drafting/audit rubric 全文读，其余 rubric 核验权重与 kill switch）
- 声称检查的不变量: seed 步骤↔deps 前置闭包；seed/rubric 引用 fixture 存在；rubric 权重=100 + "phase = 0" kill switch 可解析
- findings: F755（genesis/drafting/management）、F763（management "11 truth files"）；audit seed "18 review skills" 与 deps 18 项一致 ✓
- 验证命令: `python3 /tmp/z7c_audit.py` → C 段: drafting 缺 3 / genesis 缺 5 / management 缺 4，其余 6 相位闭包一致；权重全 100 ✓
- 分簇: genesis BROKEN-closure / architecture ✓ / planning ✓ / drafting BROKEN-closure / audit ✓ / management BROKEN-closure / import ✓ / foundation ✓ / short-story ✓
- 置信度: high

### tests/tiers/t3-pipeline/<pipeline>（3 簇 × {input/seed.md, rubric.md}）
- 处置: deep-read（机械核验 6 文件；6 文件全部全文读）
- 声称检查的不变量: seed↔deps prerequisites；rubric 权重=100 + "pipeline = 0" kill switch；fixture 引用存在
- findings: F755（long-form 第 4/7 步与 deps drafting/management 同步缺 7 skill）；short-form/import-form 闭包一致 ✓；long-form seed:10 "all 18 review-* skills" 与 deps audit 18 项一致 ✓；权重 100 ✓
- 验证命令: 同上脚本 C/D 段
- 置信度: high

---

## 低置信度簇
- shenbi-review-anti-ai / shenbi-review-memo-compliance / shenbi-review-long-span（"OK-轻度/BROKEN"边界情形：关键数据部分内联，但审计载体声明与 fixture 错位 — 若评分 agent 允许仅凭内联数据判定则功能性尚存，判 BROKEN 依据载体契约）
- shenbi-chapter-pattern（模式分配内联完整，几乎可判 OK，因 fixture 角色错位 + 术语漂移保留 F764a）

## 未覆盖文件
无（445/445 经机械核验；簇条目覆盖全部 70 t1 目录 + 9 t2 + 3 t3 + 根 3 文件；文件数合计 3+418+18+6=445）。

## 统计摘要
- 机械核验: 445/445（A-H 八类检查）
- 语义提取审读: 69/69 skill 族核心内容 + 9/9 t2 + 3/3 t3
- 全文深读: 18 文件（worldbuilding 5、review-character variant、using-shenbi 2、t2 drafting/audit、t3 全 6、score-arc/_template rubric 等）
- findings: F751(P0)×1、P1×3（F752/F753/F754）、P2×9、M×1；正通过项: acceptance/exemptions/闭包双射/权重和/calibration-hash/fixture 路径零断链
