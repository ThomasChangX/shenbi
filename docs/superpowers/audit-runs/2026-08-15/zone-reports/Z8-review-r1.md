# Z8 区三段初审独立复核报告（review-r1，2026-08-15 轮）

- **复核人**: Z8 独立复核 agent（fresh-context，只读）
- **复核对象**: Z8-a.md（F801–F823）、Z8-b.md（F834–F857）、Z8-c.md（F867–F885）
- **本轮角度**: (a) frontmatter 声明面（reads/writes/updates 全集）× truth-files.yaml 词表 × novel-output 磁盘产物三方对账；(b) SKILL.md 正文引用文件/字段/常量词表全仓幻影引用扫描
- **编号段**: F886–F895（10 条新 finding）
- **只读声明**: 除本文件外未创建/修改/删除任何仓库文件；未 git add/commit；未运行 pytest / shenbi-dispatch / pipeline。机械核验脚本仅写入 /tmp。

---

## 0. 复核方法与抽样

1. **清单完整性**: `find skills -type f`（100 文件）与 Z8-a/b/c 三清单并集 `comm -23` 差为空 → 文件级覆盖 100/100，无清单遗漏。
2. **findings 涉及 SKILL.md 全量重读核实**: 66 个技能目录被 findings 涉及（Z8-a 22、Z8-b 26、Z8-c 20，重叠 2）。其中 P0/P1 与结构性 P2 逐条读原文+读 src 侧执行链核实（见 §5 维持清单）。
3. **未涉及技能深读**: 8 个无 finding 技能目录全部深读（canon-import、power-system、sequel-writing、short-outline、short-packaging、snapshot-manage、story-architecture、world-extraction）+ escalation-review、location-builder、state-settling、memory-distill、market-radar 独立重读 = 独立深读 ≥13 文件，产出漏报 F887/F889/F890/F892。
4. **机械核验**: python 解析 74 个 SKILL.md frontmatter（0 解析错误）→ 388 条声明路径（reads 265 / writes 87 / updates 36）与 truth-files.yaml 70 concepts + 20 parametrics + 33 globs 全量 fnmatch/parametric 归一匹配；再与 `novel-output/xinghuo-ranqiong`（真实管道产物）磁盘路径反向对账。
5. **词表扫描**: description "Use when"、Anti-Rationalization 表、DOT digraph 三项 74 技能机械扫描；全部 SKILL.md 正文路径引用 vs 词表幻影扫描。

## 1. 三方对账统计（本轮角度核心产出）

| 对账方向 | 结果 |
|---|---|
| 声明路径 → 词表 | **388/388 全部命中**（concept/parametric/glob），0 个词表外声明 —— 路径级声明卫生良好（对初审结论的正向验证） |
| 词表 → 声明（无生产者概念） | 5 个：`plans/chapter-N-plan-decisions.json`（=F807②/T1-05 已立案）、`truth/state-settling-decisions.json`（=T1-05 已立案，2026-08-14 findings-ledger.md:503 确认存在）、`audits/chapter-N-<dim>.md`（假警报：具体维度文件由 group-*/review-* 经 glob 覆盖）、`short/outline.md` + `short/package.md`（**漏报 F888**）、`import/analysis/01_overview.md`（名称漂移 = F823 已立案，被 `import/analysis/*.md` glob 声明掩盖） |
| 词表 → 声明（无消费者概念） | `audits/volume-N-payoff.md`、`audits/arc-N-score.md`、`audits/volume-N-score.md`、`audits/stratum-N-score.md`、`audits/escalation-N-report.md`、`foundation/review_report.md`、`import/packaging/package.md`、`context/market-radar-decisions.json` 等 writes-only 概念（审计/评分产物由框架读取或仅人类消费，非缺陷）；**`genesis-context/*.md` 是唯一"产出了但全仓（skills+src）零消费"的实质内容目录**（漏报 F886） |
| 磁盘 → 词表（xinghuo-ranqiong 非 staging） | 未登记实产文件：`progress.json`、`config-change-log.jsonl`、`gate-markers/*`、`pipeline-state.json.lockfile`、`DEBUG_USE_MANUAL_CREATE.md`（Z11-a 已从磁盘侧立案 F1113 等；**yaml "pipeline-written files" 节侧的登记缺口无人认领** = F895）；`truth/state_snapshot-pre-rev.md` 由 `truth/*.md` glob 覆盖且 index.json:388 登记 ✓ |
| 声明 → 磁盘（声明了从不产出） | `snapshots/chapter-NNN/*`（sequel-writing reads + snapshot-manage writes）：磁盘 56+ 个快照全部为 D20 平文件 `snapshots/chapter-N-<ts>.md`，`chapter-NNN/` 目录数为 0（F890）；`truth/drift_guidance.md`（drift-guidance 写声明，磁盘不存在——与 F812 正文零定义互证） |

**正向验证（初审未做、本轮补做的系统性结论）**: 路径级三方对账基本干净；Z8 区真正的系统性缺陷集中在**字段级**（style 11/6/9、volume_promise/arc_beats、current_state 节名分裂——初审已捕获）、**未声明 reads**（初审已捕获 F803/F811/F821/F836，本轮补 F889）、**孤儿概念/孤儿产物**（本轮新捕 F886/F888/F895）三个层面。

## 2. 漏报（F886–F895）

### F886 | genesis-context/*.md 写后全仓零消费：种子实质内容在管道 genesis 阶段断流 | error | P1
- 证据: `src/shenbi/pipeline/cli.py:459-462`（"Persist each genesis-context section as its own prompt fragment" 写 9 个文件）；`src/shenbi/pipeline/seed_parser.py:148-160`（Protagonist/World Rules/Forces/Plot Lines/Chapter Outline/Three-Act/Core Conflict 三层 → 仅存入 genesis_context）；`src/shenbi/pipeline/genesis.py:302-306`（genesis 派发 prompt 仅 "Execute {skill}. Project dir: {dir}"，无种子内容）；`grep -rn "genesis-context" skills/ src/ --include=*.py --include=*.md` → 除 cli.py/seed_parser.py 写入侧外 0 命中（无 skill reads、无框架回读）；磁盘 `novel-output/xinghuo-ranqiong/genesis-context/` 9 文件实存；`novel-output/xinghuo-ranqiong/novel.json` 仅 title/genre/era/core_concept/target_word_count/ending_direction
- 根因: wave1 设计（archive/2026-07-02-novel-pipeline-wave1-foundation.md:1456 注释 "Write genesis context for later skill dispatch"）只落了"写"半边，"later skill dispatch" 消费侧从未接线；wordbuilding/character-design/story-architecture 等 genesis 技能 reads 只有 novel.json，dispatcher 只注入 reads
- 验证: `grep -rn "genesis-context" skills/` → 空（exit 1）；`grep -rn "genesis.context" src/shenbi/ --include="*.py" | grep -v "cli.py\|seed_parser"` → 空（exit 1）；`head -30 novel-output/xinghuo-ranqiong/novel.json` → 无 protagonist/world_rules/plot_lines 等节
- 影响链: 正常路径（`just pipeline-init <seed>` → genesis 17 步）下，作者种子的 World Rules/Protagonist/Forces/Plot Lines/Chapter Outline/Three-Act/三层 Core Conflict 对全部 genesis 技能不可见——genesis 仅凭 core_concept 一句话自行发挥。同时使 F809（character-design 引用 `outline/chapter_outline.md`/`outline/three_act.md`）的修复方向更正：这两个 basename 的真实文件在 `genesis-context/` 下，但同样无人读——F809 的 IRON LAW 无论改指哪条路径都是死输入
- 建议方向: genesis 步骤派发 prompt 注入对应 genesis-context 片段（worldbuilding←world_rules+forces；character-design←protagonist；story-architecture←three_act+plot_lines+chapter_outline），或让相关 skill 声明 `reads: genesis-context/<key>.md`（词表已注册该概念，producer: pipeline）

### F887 | GENESIS_STEPS 仍派发 DEPRECATED 的 shenbi-foreshadowing-plant；另有 3 处正文把 track/plant 当现行链路引用 | error | P1
- 证据: `src/shenbi/pipeline/genesis.py:69-71`（`GenesisStep(9, "shenbi-foreshadowing-plant", mode="genesis", output_path="truth/pending_hooks.md")`）vs `skills/shenbi-foreshadowing-plant/SKILL.md:29-30`（"DEPRECATED: Superseded by shenbi-foreshadowing-lifecycle (2026-07-19) … Do not dispatch"）；对照 `src/shenbi/pipeline/chapter_loop.py:124-126`（"Deprecated skills removed: foreshadowing-plant, foreshadowing-track, foreshadowing-recall … Merged: 3 foreshadowing skills → shenbi-foreshadowing-lifecycle (MERGE-1)"——chapter_loop 已清理、genesis.py 漏改）；另 `skills/shenbi-state-settling/SKILL.md:162-163`（"foreshadowing-track：唯一推进 hook 生命周期状态的 skill … foreshadowing-plant：追加新 hook"——两者均 DEPRECATED，现行者 lifecycle 未提及）、`skills/shenbi-sequel-writing/SKILL.md:39`（字段所有权归 "state-settling/foreshadowing-track/memory-distill 等"）、`:120`（续写链路 "调用 shenbi-foreshadowing-plant（若需要）"）
- 根因: MERGE-1（2026-07-19）弃用清理只扫了 chapter_loop/deps.json/using-shenbi 的部分表面；genesis 步骤表与 3 个 skill 正文的链路引用未纳入 "全仓 0 引用 deprecated skill" 的验收范围（2026-08-14 R1 同样未覆盖）。磁盘佐证：`novel-output/xinghuo-ranqiong/gate-markers/` 存在 `G4-shenbi-foreshadowing-track-generative.json`（弃用技能真实跑过）
- 验证: `grep -n "foreshadowing-plant" src/shenbi/pipeline/genesis.py` → `:70`；`grep -rn "foreshadowing-plant\|foreshadowing-track" skills/shenbi-sequel-writing/SKILL.md skills/shenbi-state-settling/SKILL.md` → sequel:39/:120、settling:162-163；全 24 份 2026-08-15 zone 报告 grep "genesis.py" + plant → 0 命中（三段初审与他区均未捕获）
- 建议方向: genesis.py 步骤 9 改派 shenbi-foreshadowing-lifecycle（mode=genesis）或其拆分入口；state-settling:160-165 与 sequel-writing:39/:120 的分工/链路引用改指 lifecycle；将 "DEPRECATED 技能全仓 0 派发/0 引用" 做成 lint（覆盖 genesis 步骤表、SKILL 正文、deps.json、using-shenbi）
- 严重度注: 该证据同时加重 F816/F873（不只是交互路由残留，管道自身在每次 init 的正常路径派发 Do-not-dispatch 技能）；因弃用技能本体完整可执行、产出结构合规，维持 P1 不升 P0

### F888 | truth-files.yaml 孤儿概念 short/outline.md 与 short/package.md（零生产者、零消费者、零引用） | error | P2
- 证据: `docs/framework/truth-files.yaml:91-92`（`short/outline.md`、`short/package.md`，kind: short）；实际写方：`skills/shenbi-short-outline/SKILL.md:11`（writes outline/short_story_map.md）、`skills/shenbi-short-packaging/SKILL.md:13-14`（writes import/packaging/*）
- 根因: 短篇技能早期设计的输出名（short/outline、short/package）落地时改为复用 outline/ 与 import/packaging/ 词表位，旧概念行未删——词表头注自述 "Adding a genuinely new file = ONE edit here; 防止 silent synonym creation"，此为反向的 "removing a dead concept = ZERO edits" 违例
- 验证: `grep -rn "short/outline\|short/package" skills/ src/` → 0 命中（exit 1）；`grep -n "short/outline\|short/package" docs/superpowers/audit-runs/2026-08-15/zone-reports/Z8-*.md` → 0 命中（三段初审均未捕获）
- 建议方向: 删除两行概念（或若短篇体系规划仍需 short/ 目录，则在技能侧落地后再注册）

### F889 | sequel-writing Step 2 风格指纹上下文所需 style/style_profile.md 未声明 reads | error | P2
- 证据: `skills/shenbi-sequel-writing/SKILL.md:8-12`（reads: snapshots/chapter-NNN/*、truth/*.md、outline/volume_map.md、outline/thread_map.md——无 style/）vs `:84`（6 类上下文表 "风格指纹 | style/style_profile.md（若存在）"）、`:148-152`（续写前报告"风格指纹回顾：句长均值/TTR/主导修辞"）
- 根因: 与 F803/F821/F836 同族——正文新增输入未回填 frontmatter；dispatcher 只注入声明 reads（dispatch_helper.py:600-660 raw_inputs 仅来自 contract reads），style_profile 在 truth/*.md glob 之外，注入不可达
- 验证: `grep -n "style_profile" skills/shenbi-sequel-writing/SKILL.md` → 仅 :84/:148-152 正文命中，frontmatter 0；Z8-c sequel-writing per-file 记录 "findings: 无"（漏报）
- 建议方向: reads 补 `style/style_profile.md`（fields: [11. 综合画像, 6. 修辞模式]，对齐 F867 修复后的真实产物编号）

### F890 | 快照双体系未对账：声明面 snapshots/chapter-NNN/*（sequel 读 / snapshot-manage 写）vs 磁盘面 D20 平文件 | error | P2
- 证据: 声明侧 `skills/shenbi-sequel-writing/SKILL.md:9`（reads snapshots/chapter-NNN/*）、`skills/shenbi-snapshot-manage/SKILL.md:16-19`（writes snapshots/chapter-NNN/* + manifest.json）、`docs/framework/truth-files.yaml:75-77`（2026-08-15 注释宣布 chapter-NNN/manifest.json 为真实契约写）；磁盘侧 `find novel-output/xinghuo-ranqiong/snapshots -type d -name "chapter-*"` → 0 个 chapter-NNN 目录，实存 56+ 个平文件 `snapshots/chapter-5-20260715T232231.md` 式 + 1 个 manifest.json（D20 `snapshots/chapter-NNN-*.md` 概念，producer: pipeline）
- 根因: 契约于 2026-08-15 刚改向目录式快照（spec #6 R3），但管道真实写者（chapter_loop._snapshot_chapter_files 平文件）未迁移，snapshot-manage 从未运行（无任何 chapter-NNN/ 目录产物）——过渡期"声明了从不产出的路径"：sequel-writing Step 1 首选断点（:68 "最近的 snapshots/chapter-NNN/（最完整）"）在现存项目上永远落空，退化为候选 2
- 验证: `find novel-output -type d -name "chapter-0*" | wc -l` → 0；`ls novel-output/xinghuo-ranqiong/snapshots/ | head -3` → chapter-5-20260715T232231.md 等平文件
- 建议方向: 过渡期 sequel-writing Step 1 增加 D20 平文件候选（`snapshots/chapter-N-<ts>.md` 按时间戳取最新），或管道迁移到目录式后再收紧契约；两套 glob（`snapshots/chapter-*/*` 与 `snapshots/chapter-*-*.md`）在 yaml:137-138 并存需注明淘汰时间表

### F891 | SharedAuditContext 缓存 4 字段中 2 个经幻影路径/键错位 100% 失效 | error | P2（跨区 Z7）
- 证据: `src/shenbi/pipeline/audit_context_cache.py:53`（`world_rules_file = project_dir / "truth" / "world_rules.md"`——词表/磁盘/12 个技能声明的真实路径是 `world/rules.md`，`truth/world_rules.md` 全仓不存在 → ctx.world_rules 恒为空）；`src/shenbi/pipeline/dispatch_helper.py:616-622`（注入键 `_input_key(project_dir/"truth"/"world_rules.md")` = "truth/world_rules.md"、`_input_key(project_dir/"truth"/"style_profile.md")` = "truth/style_profile.md"）vs 磁盘读取侧键 `_input_key` 返回项目相对路径（:515-521）即 "world/rules.md"、"style/style_profile.md"——两个键永不相等，注入分支永不命中（character_matrix/pending_hooks 两字段键恰好同名，正常生效）
- 根因: spec §6.1 C1 统一键格式时，缓存注入侧照抄了错误的 truth/ 前缀；配套测试 `tests/pipeline/test_audit_context_cache.py:57-69` 在测试体内重实现了同一错误键（"Simulate the injection logic"），自证通过——正是 Z7-b F728 指出的模拟自证问题放大：测试连路径错误也一起祝福了
- 验证: `grep -rn "truth/world_rules.md" src/ tests/` → 仅 audit_context_cache.py:53、dispatch_helper.py:617、test_audit_context_cache.py:57/68/69 五处（互相引用，无外部存在）；`grep -n "world/rules" docs/framework/truth-files.yaml` → `:15`
- 影响链: world_rules（5000 字预算）与 style_profile（2000 字预算）两路"审计省钱缓存"完全死代码，每个并行审计波照旧整文件读盘（token/IO 浪费）；功能不受损（回退为磁盘读），故 P2
- 建议方向: audit_context_cache.py:53 改 `world/rules.md`；dispatch_helper.py:616-622 两个注入键改为与真实 reads 键一致（"world/rules.md"、"style/style_profile.md"）；测试改为调 `_build_skill_prompt(..., shared_context=ctx)` 断言真实 prompt

### F892 | escalation-review reads 仅覆盖自家触发 helper 六类信号源中的两类 | error | P2
- 证据: `skills/shenbi-escalation-review/SKILL.md:8-10`（reads 仅 truth/resonance_trend.md + audits/chapter-N-sensitivity.md）vs `src/shenbi/skill_utils/escalation/check.py:54-60`（`check_escalation(resonance_scores, sensitivity_blocking, volume_objective_met, regeneration_attempts, arc_score, stratum_axis_drift, ...)`——卷目标未达/重写次数/弧分/大弧轴漂移四类信号无对应输入：truth/volume_score_trend.md、audits/arc-N-score.md 等均未声明）
- 根因: F813 只抓了 helper 名漂移与 anti-rat 表缺失，未对触发源做 reads 覆盖对账；升级报告（"升级上下文：触发条件的完整数据"）在卷/弧/重写类触发下无数据可汇总
- 验证: `sed -n '54,60p' src/shenbi/skill_utils/escalation/check.py` → 参数清单；`grep -n "volume\|arc\|regeneration" skills/shenbi-escalation-review/SKILL.md` → 0 命中
- 建议方向: reads 补 truth/volume_score_trend.md、truth/arc_payoff_trend.md（或 audits/arc-N-score.md）并在输出格式中为每类触发源设上下文小节

### F893 | 5 个现行技能缺 DOT 流程图（含 4 个现行主力审计技能 group-*） | error | P2
- 证据: 机械扫描 `grep -c "digraph"` → 无 DOT：shenbi-review-group-character、shenbi-review-group-craft、shenbi-review-group-factual、shenbi-review-group-plan、shenbi-foreshadowing-lifecycle；AGENTS.md 显式约定 "Critical skills include DOT flowcharts for authoritative process definition"
- 根因: MERGE-2 分组技能与 MERGE-1 lifecycle 合并产出时未按技能编写规范补权威流程图；三段初审的 DOT 不变量均为"DOT 与正文一致"（存在性默认成立），从未对缺失本身立案（F835/F841/F815 都绕过了这一点）
- 验证: `for f in skills/*/SKILL.md; do grep -L "digraph" "$f"; done` → 恰好上述 5 文件（using-shenbi 自身有 digraph，不在列）
- 建议方向: 为 4 个 group-* 补"分派→并行波→三/四维审计→汇总"DOT（与 parallel_dispatch 真实行为对齐），lifecycle 补 Phase1-3 状态机 DOT；顺带 foreshadowing-recall 亦无 Anti-Rationalization 表（DEPRECATED，随清理家族处理）

### F894 | 跨段重复立案与同缺陷异处置：F874 复制 F847 缺陷家族第 5 例；11 个 .gitkeep 三段仅 6 立案 5 放行 | process | M
- 证据: `grep -rn "遵循  定义的四要素格式" skills/` → 5 文件：review-continuity:114、review-long-span:100、review-dialogue:106、review-character:82（Z8-b F847 列 4 个）+ **review-sensitivity:74（Z8-c 又以 F874 单独立案，未引 F847，双空格悬空同源同缺陷）**；`.gitkeep` 全仓 11 个 0 字节（chapter-drafting/planning/revision/character-design/context-composing=F804 五个、review-anti-ai=F854 一个；state-settling/story-architecture/worldbuilding/writing-skills/using-shenbi 五个在 Z8-c per-file 记录中处置 "findings: 无——空占位文件"）
- 根因: 三分段按文件切责任区，同族缺陷跨段重复发现时无去账机制；.gitkeep 处置标准段间不一
- 验证: 见上述 grep 输出；`find skills -name ".gitkeep" | wc -l` → 11
- 建议方向: 终审合账时 F874 并入 F847（计 5 文件一处修）；.gitkeep 家族按 F804 统一处置（11 个全删或全留）

### F895 | truth-files.yaml "pipeline-written files" 节登记不全：progress.json / config-change-log.jsonl / gate-markers/* 实产未注册 | error | P2（跨区，归属未定）
- 证据: `docs/framework/truth-files.yaml:78-84`（pipeline 产物登记了 snapshots/manifest.json、truth-index.json、pipeline-state.json、genesis-context/*.md、truth-embeddings.db、context/review-checklist-N.json）vs 磁盘+框架实产：`novel-output/xinghuo-ranqiong/progress.json`（g1.py:259 等框架读取）、`config-change-log.jsonl`（config_coherence.py 等写入）、`gate-markers/G4-*.json`（G4 门禁写）、`pipeline-state.json.lockfile`——四者均不在词表
- 根因: 词表只登记了部分 pipeline 产物；Z11-a 从磁盘侧审了这些文件的内容质量（F1113 progress.json 空壳等），但 yaml 侧登记缺口未入账
- 验证: `grep -n "config-change-log\|progress.json\|gate-markers\|lockfile" docs/framework/truth-files.yaml` → 0 命中；`grep -rn "progress.json" src/shenbi/gates/g1.py` → :259
- 建议方向: yaml 补登四类（gate-markers/ 可作目录概念）；或明确声明"框架内部运转文件不入词表"的边界规则并写入 yaml 头注（当前无此规则，词表自述是全量 schema source）

## 3. 误报（1 条，均为事实性错误）

### M1 | Z8-b review-foreshadowing/hook-lifecycle.md per-file 记录声称 track 目录无 lifecycle-states.md（"死引用"）——文件实存
- Z8-b 原文（Z8-b.md:331）: "引用 skills/shenbi-foreshadowing-track/lifecycle-states.md 存在性——track 已 DEPRECATED 且目录内无 lifecycle-states.md（`ls skills/shenbi-foreshadowing-track/` → 仅 SKILL.md）→ 死引用，M 级（并入 F834）"
- 复核: `ls -la skills/shenbi-foreshadowing-track/` → **SKILL.md + lifecycle-states.md（1882 字节，Jun 11）**。hook-lifecycle.md:5/:29 的跨目录引用 `skills/shenbi-foreshadowing-track/lifecycle-states.md` 是**可达的**，非死引用（真正的可达性问题在 lifecycle SKILL.md:59 的裸相对引用，即 F815②，Z8-a 判定正确）
- 影响: 该 M 级附注会导致清理时误删/误改 hook-lifecycle.md:5/:29 的正确绝对路径；未占编号，不影响 findings 计数
- 根因推测: Z8-b 用了错误的 ls 目标或缓存了 F834 "track 已弃用" 的印象

## 4. 覆盖空洞

1. **三方机械对账在初审中缺位**: 三段各自做了"单技能 reads vs 正文"抽查，但从未做过 74×388 声明路径 × 词表 × 磁盘的系统对账。本轮补做后：路径级干净（正向结论）、并新捕 F886/F888/F890/F895 四条。后续轮建议将对账脚本固化（本报告 /tmp/extract_frontmatter.py + /tmp/reconcile.py 思路可复现）。
2. **genesis 派发链路无区认领**: genesis.py 的 17 步技能表既属 src（Z3 区，Z3 审了 genesis.py 的 token 记账/测试覆盖但未对步骤表做弃用扫描）又直接决定 skills 的执行面（Z8 区）。F887 即从此缝隙漏出。建议终审将 "GENESIS_STEPS × DEPRECATED 集合" 交叉检查列为显式项。
3. **执行链下游验证只到 dispatch_helper 半程**: Z8-b/Z8-c 大量引用 dispatch_helper.py 行为做证据（如 F838/F868，均经本轮核实为真），但缓存注入层（audit_context_cache + _INJECT_FROM_CACHE）无人审——F891 即在该层。属 Z7 区盲区。
4. **字段级 reads 的"生产者实况"核验不均衡**: style_profile（F867 ✓）、volume_map（F839 ✓）、current_state（F845 ✓）被核；但 `truth/audit_drift.md`（6 写者各自的行格式/节结构无权威模板）与 `truth/pending_hooks.md`（4 写者字段分工仅在 state-settling:160-165 一处有声明，lifecycle/resolve 的分工单方面自述）未做同样的多写者一致性对账——audit_drift 至少有 drift-guidance(reset 12 章)、review-resonance(append_dedup chapter)、score-arc(append_dedup) 三种写语义并存，疑似同族问题，未验证行格式互溶性，列为终审建议项。
5. **AGENTS.md 计数漂移（Z8-b 跨区观察）复核属实**: `ls skills/ | wc -l` = 74，DEPRECATED 15，meta 2 → 活跃 functional 57 + meta 2；AGENTS.md 声称 67 functional + 2 meta = 69。功能技能数漂移 15（72 实际 vs 67 声称），归 Z1 处置。

## 5. 严重度异议与维持

| Finding | 初审判级 | 复核结论 | 关键验证 |
|---|---|---|---|
| F868 volume-consolidation 覆写丢卷摘要 | P0 | **维持 P0** | 全链核实：reads 无 volume_summaries（:7-10）+ mode create_or_overwrite（:12-13）+ 正文三处"追加到"（:72/:114/:169）+ `_check_content_size_guard` 仅护 chapters/（dispatch_helper.py:940-975，`if path.parent.name != "chapters": return False`）+ 字面路径整文件写（:1163-1180）+ triggers.py:232-234 经通用派发无 write_truth_file 上位调用。第二卷整合 = 旧卷摘要必然丢失，且磁盘尚无该文件（第一卷未触发），属潜伏正常路径数据丢失 |
| F838 market-radar | P1（自 P2 升） | **维持 P1** | 单输出无 schema 注记（`if len(output_paths) > 1` dispatch_helper.py:734）+ 正文纯 markdown 报告 + `.json` 走 `_validate_json_output` raise（:1126-1132）+ `__stdout__` 回退写入（:1172）——按正文执行必崩 |
| F836/F803/F811/F821 未声明 reads 族 | P1 | **维持 P1×4** | input 注入仅来自 contract reads（:600-660 raw_inputs 构造核实）；各正文必需输入逐行在场 |
| F814 faction-relations | P1 | **维持 P1** | yaml:160 "no producer -> dropped" + 正文 :179/:200/:213 完整生产已废弃文件 |
| F867 style-learning 模板漂移 | P1 | **维持 P1** | fixture 11 节（6/9/11）vs 模板 8 节（5/8）+ compute_stats.py:330-358 输出键无 dialogue_ratio/per-chapter（"纯统计零 LLM"声明对 §9/§10 不成立）+ 4 个下游声明 11/6/9 |
| F816/F873 DEPRECATED 路由残留 | P1 | **维持 P1，证据增强** | 本轮新增 genesis.py:70 管道自身派发（F887）；"Do not dispatch 契约被静默违反"字面更贴近 P0，但弃用技能可执行、无数据损坏，维持 P1（与 Z8-c 边界备注一致） |
| F869 state-settling 模式矛盾 | P1 | **维持 P1**（边界） | frontmatter append_dedup vs 正文 replace 三处清单互斥，G0.16 校验面与执行面必有一侧失真；按"不确定取更高"保 P1 |
| F870 契约外写 protagonist.md | P1 | **维持 P1** | index.json writers=[character-design, character-extraction] 核实；dispatcher 只写声明路径 → arc_log 静默丢弃或越权写 |
| F849 fanfic 子模式无生产者 | M（建议复评 P2） | **支持升 P2** | NovelConfig extra:forbid + 无任何写方；子模式静默回退 canon 最严格档，属"正常路径功能错误"的边界——激活顶层 mode=fanfic 可达时子模式全不可用，P2 合理 |
| F845 current_state 节名分裂 | P2 | **维持 P2** | xinghuo :15/:26/:42 vs test-validation :7/:10/:13 节名实测分裂；escape hatch 使其静默化 |
| F874 | P2 | **并入 F847**（F894） | 同一缺陷家族第 5 例 |
| F804/F854 .gitkeep | M | **维持 M，家族扩为 11 个**（F894） | |
| 其余抽检（F805/F806/F807/F809/F812/F813/F815/F818/F822/F823/F835/F837/F839/F840/F841/F842/F843/F846/F847/F875/F876/F877/F879/F880/F881/F884/F885/F850/F851/F853） | — | **全部核实成立**（行号/内容逐一比对通过；F809 根因由 F886 补正） | |

## 6. 结论

- 三段初审质量总体**高**：抽核 40+ 条 findings 中仅 1 条事实性误报（M1）、1 条重复立案（F894），行号级证据几乎全部精确。
- 本轮角度（三方对账+幻影扫描）净增 **10 条**：P1×2（F886 种子断流、F887 genesis 派发弃用技能）、P2×7、M×1。
- 系统性图谱：Z8 区缺陷密度最高的三个面 = ①弃用迁移未完成的全仓清理（F816/F834/F873/F887 + state-settling/sequel 正文残留）；②"frontmatter 单源化"迁移半途（正文 Contract 块、行号引用、模式词表、decisions sidecar 零正文指令——F805③/F807②/F838/F841/F881 五条同根）；③多写者 truth 文件无权威字段/格式模板（F845/F869/audit_drift 疑似项）。
