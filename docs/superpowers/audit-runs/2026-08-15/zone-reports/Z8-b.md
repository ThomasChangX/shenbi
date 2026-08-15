# Z8-b 分区初审报告（2026-08-15 轮）

> 审查人：Z8-b 初审 agent（只读）
> 范围：`docs/superpowers/audit-runs/2026-08-15/zones/Z8-b.files` 全部 33 文件（26 个 SKILL.md + 6 个附属参考 md + 1 个 .gitkeep），skills/ 按字母序第 1/3 段。
> 方式：全部文件 deep-read；对照 `docs/framework/truth-files.yaml`、`docs/framework/decisions-schema.md`、`src/shenbi/pipeline/{dispatch_helper,chapter_loop,triggers,truth_io,audit_layer}.py`、`src/shenbi/gates/g4/generic.py`、`src/shenbi/contracts/schemas/novel.py`、`skills/using-shenbi/SKILL.md`、`skills/shenbi-genre-config/SKILL.md`、`skills/shenbi-volume-outlining/SKILL.md`、`tests/fixtures/`、`novel-output/` 交叉验证。
> 发现编号段：F834–F857（本报告实际使用 F834–F857 共 24 条）。
> 与 2026-08-14 轮衔接：本分区与 2026-08-14 轮 Z8-a/Z8-b/Z8-c 的分区方案不同（本轮按字母序 1/3），存在交叉。凡 2026-08-14 已入账且本轮**复检仍未修复**的发现，标注「复检 Fxxx（2026-08-14）」；本轮新发现标注「新」。
> 只读声明：除本段文件外未创建/修改/删除任何仓库文件；未 git add/commit；未运行 pytest / shenbi-dispatch / pipeline。

---

## 0. 总览

- deep-read 文件数：**33 / 33**（清单全覆盖）
- 未覆盖文件：**无**
- findings：**24**（P1 × 4，P2 × 11，M × 9）
- 其中复检未修复（2026-08-14 已入账）：F834（≈F904/F921/F950）、F835（≈F1009/F900/F957）、F836（≈F953）、F838（≈F909）、F841（≈F958/F1010）、F844（≈F1017）、F846（≈F1013）、F847（≈F962/F1017）、F848（≈F963）、F849（≈F916 扩展）；本轮新发现：F837、F839、F840、F842、F843、F845、F850、F851、F852、F853、F854、F855、F856、F857。
- 跨区观察（不入账，本区文件外）：`AGENTS.md` 声称 `skills/` 共 67 functional + 2 meta = 69，实测 `ls skills/ | wc -l` = **74**（含 15 个 DEPRECATED）；漂移属 AGENTS.md 属区，建议 Z1 复核。
- 本区 8 个 DEPRECATED skill（review-anti-ai / -character / -continuity / -dialogue / -foreshadowing / -memo-compliance / -motivation / -pacing）与 4 个 group-* 替代者的路由断裂是本区最大系统性问题（F834/F835）。

---

## 1. findings（F834–F857）

### F834 | using-shenbi 元技能触发映射路由到 8 个本区 DEPRECATED skill 且 4 个 group-* 替代者零触发行；DEPRECATED 正文仍自称"默认激活/每章必查" | deps | P1
- 证据：`skills/using-shenbi/SKILL.md:44`（"检查这章/审计/审查" → `shenbi-review-anti-ai (default)`）、`:45`（continuity）、`:46`（character）、`:47`（pacing）、`:48`（foreshadowing）、`:50`（dialogue）、`:51`（motivation）、`:63`（memo-compliance）、`:124`（"Default audits (always run): review-anti-ai, review-continuity, review-character, review-sensitivity, review-resonance"）、`:126`（"Phase 2 (review-pacing, review-foreshadowing), Phase 4b (review-world-rules, review-dialogue, review-motivation, …)"）；被引用 skill 均含 `<!-- DEPRECATED: Superseded by shenbi-review-group-* (2026-07-19). --> <!-- … Do not dispatch. -->`（`skills/shenbi-review-anti-ai/SKILL.md:16-17`、`shenbi-review-character/SKILL.md:19-20`、`shenbi-review-continuity/SKILL.md:24-25`、`shenbi-review-dialogue/SKILL.md:18-19`、`shenbi-review-foreshadowing/SKILL.md:18-19`、`shenbi-review-memo-compliance/SKILL.md:17-18`、`shenbi-review-motivation/SKILL.md:18-19`、`shenbi-review-pacing/SKILL.md:22-23`）；弃用正文仍自称活跃：`shenbi-review-anti-ai/SKILL.md:37`、`shenbi-review-character/SKILL.md:40`、`shenbi-review-continuity/SKILL.md:45`（均"这是默认激活的审计技能（每章必查）"）；运行时真实调度为 group-*（`src/shenbi/pipeline/chapter_loop.py:205-226` 步骤 9-14 dispatch `shenbi-review-group-{factual,character,craft,plan}`），而 chapter_loop 遗留死引用 `"anti-ai"`/`"dialogue"` 等（`:319` CASCADABLE_AUDITS、`:1817` 审计扫描清单）仍按旧维度名扫描。
- 根因：MERGE-2 分组迁移（2026-07-19）只改了 pipeline 调度与 SKILL.md 墓碑注释，未同步 using-shenbi 触发表 / chapter_loop 旧维度常量；deprecation 无 frontmatter 字段、无 lint enforcement。
- 验证命令+输出：`grep -n "review-anti-ai\|review-character\|review-continuity\|review-dialogue\|review-foreshadowing\|review-memo-compliance\|review-motivation\|review-pacing" skills/using-shenbi/SKILL.md` → 命中 :44-:63、:124、:126；`grep -rl "DEPRECATED: Superseded" skills/*/SKILL.md | wc -l` → 15。
- 建议方向：using-shenbi 触发表按替代者重写（"角色一致性"→ group-character 等）；deprecation 提升为 frontmatter 字段并被 lint 强制；清理 chapter_loop 旧维度常量。复检 F904/F921/F950（2026-08-14），未修复。

### F835 | 4 个 review-group-* 的 description 全部描述"做什么/怎么调度"，无 "Use when" 触发条件 | contract | P1
- 证据：`skills/shenbi-review-group-character/SKILL.md:3`（"Grouped audit for character integrity -- character consistency, dialogue, motivation, and POV in one call; dispatches as a parallel wave via parallel_dispatch.py"）、`shenbi-review-group-craft/SKILL.md:3`（同型）、`shenbi-review-group-factual/SKILL.md:3`（同型）、`shenbi-review-group-plan/SKILL.md:3`（同型）；AGENTS.md 显式契约："description: ONLY when-to-use trigger conditions … Never describes what the skill does"。
- 根因：MERGE-2 新技能按实现视角写 description，未按触发视角；description lint（g0 `_BEHAVIORAL_MARKERS` 前缀匹配）对 "Grouped audit …" 句式是盲区（2026-08-14 F957 已实测 lint 放行）。
- 验证命令+输出：读取四文件 frontmatter（本轮 deep-read 实录）；对照组同区 review-era/-fanfic/-highpoint 均为 "Use when …"。
- 建议方向：改写为触发式（"Use when a finished chapter needs X/Y/Z audits in a single pass"）；lint 增加"无 Use when 即 FAIL"与实现词黑名单。复检 F1009/F900/F957（2026-08-14；group-character/plan 彼轮 P1、craft/factual P2——本轮按 AGENTS.md 显式契约统一取 P1），未修复。

### F836 | memory-distill L4/L5 流程读取的 author_intent / book_spine / world/rules 均未声明 reads → L5 书脊滚动复核在 dispatch 契约下拿不到输入（盲写风险） | error | P1
- 证据：`skills/shenbi-memory-distill/SKILL.md:8-12`（reads 仅 chapter_summaries / volume_summaries / pending_hooks / character_matrix）；DOT `:78`（`"L5 spine review?" -> "Read author_intent + book_spine"`）、`:73`（L4 "Read L2 arcs + volume_summaries"——truth/arcs/arc-N.md 亦未入 reads）；`:164`（"world 铁律快照：从 world/rules.md 同步前5条"——world/rules.md 未入 reads）；铁律 4 `:89`（"复核只更新数据字段，不改声明本身"）与 updates `:18-20`（book_spine create_or_overwrite）组合：dispatcher 只注入 reads（`src/shenbi/pipeline/dispatch_helper.py:741-748` 输入注入仅 Input Files 列表），updates 目标不作为输入 → 无书脊原文的整写。
- 根因：分层记忆（L4/L5）能力加入时 frontmatter reads 未同步。
- 验证命令+输出：读 SKILL.md:8-12 vs :73/:78/:164；`grep -n "author_intent\|book_spine\|world/rules" skills/shenbi-memory-distill/SKILL.md` → 仅正文/DOT 命中，frontmatter 零命中。
- 建议方向：reads 补 `truth/author_intent.md`、`truth/book_spine.md`、`truth/arcs/arc-N.md`、`world/rules.md`；book_spine 更新语义见 2026-08-14 F954。复检 F953（2026-08-14），未修复。

### F837 | memory-distill DOT 的 L2/L4 分支标签在 ch36 同时为真（互斥分支图漏跑 L2） | error | P2 【新】
- 证据：`skills/shenbi-memory-distill/SKILL.md:66-68`：`"L2 arc distill?" -> "Read chapter_summaries…" [label="chapter%12==0"]` 与 `"L2 arc distill?" -> "L4 stratum distill?" [label="chapter%36==0"]`——ch36 同时满足两个出边标签（36%12==0 且 36%36==0），DOT 分支语义互斥，按标签走 L4 即跳过 L2；而触发规则表 `:46-49` 明确 ch36 应 L2+L4+L5 全部触发。
- 根因：DOT 把"是否进入 L2"画成单条件分支，未表达 ch36 的级联（L2→L4→L5）。
- 验证命令+输出：读 `:66-68` 边标签 + `:46-49` 表格对照（本轮 deep-read 实录）。
- 建议方向：DOT 改为顺序节点（L2 完成后判 `%36` 进入 L4），或在 L4 边标签上排除 `chapter%36==0 AND chapter%12==0` 的歧义。

### F838 | market-radar：唯一 writes 是 decisions.json 但正文零 decisions 指令，且单文件 dispatch 不注入 schema 注记 + 正文输出格式为 markdown 报告 → 按正文执行必然 JSON 校验失败 | error | P1 【复检 F909（2026-08-14 P2），本轮新增升级证据】
- 证据：`skills/shenbi-market-radar/SKILL.md:11-14`（writes 仅 `context/market-radar-decisions.json`，mode create_or_overwrite）；正文输出格式 `:70-90` 为 markdown「市场雷达报告」，全文无任何 decisions.json 内容/schema/P2.5 指令；`src/shenbi/pipeline/dispatch_helper.py:735-740`（schema 注记仅当 `len(output_paths) > 1` 注入——market-radar 单文件不注入）；`dispatch_helper.py:1126-1132`（.json 后缀走 `_validate_json_output`，不可恢复内容 `raise` → "Pipeline must stop"）；G4 路由 `src/shenbi/gates/g4/generic.py:332`（`"shenbi-market-radar": g4_decisions`）。
- 根因：decisions sidecar 契约（writes）与正文（markdown 报告）完全脱节；sub-agent 若按正文输出 markdown 且未写 `### FILE:` 块，`dispatch_helper.py:1172`（`content = parsed.get(rel_path, parsed.get("__stdout__", ""))`）会把整段 markdown 写入 .json → 校验崩溃；若写 markdown 进 FILE 块同样崩溃。
- 验证命令+输出：读 SKILL.md:11-14 vs :70-107；读 dispatch_helper.py:735-740、:1126-1132、:1172（本轮 deep-read 实录）。
- 建议方向：正文补「decisions 记录」节（selections targets=市场数据/趋势信号、adjustments=趋势例外，对齐 `docs/framework/decisions-schema.md:97` per-skill 表）；或将报告落盘为第二输出文件。复检 F909（2026-08-14），未修复；本轮证据支持由 P2 升 P1。

### F839 | review-arc-payoff dict-form reads 字段 volume_promise / arc_beats 不存在于真实 volume_map.md 结构；DOT 另引 resolved_this_arc / carried_forward 幻影字段 | error | P2 【新】
- 证据：`skills/shenbi-review-arc-payoff/SKILL.md:11-14`（`outline/volume_map.md` fields: [volume_promise, arc_beats]）；`:58-59` HARD-GATE（"含 volume_promise + arc_beats"）、`:91`（弧情感交付维度对照二者）；生产方 `skills/shenbi-volume-outlining/SKILL.md:129-134` EXACT 节标题 = `## 第N卷：{卷名}` / `### Key Results` / `### 卷内张力曲线` / `### 跨卷桥接` / `### 黄金三章约束` / `### 与 story_frame 的一致性`（无 promise/beats 节）；fixture `tests/fixtures/volume-map-xinghuo.md:9,53,62,71,80` 同结构零命中；DOT `:76-77`（"读 truth/pending_hooks.md (resolved_this_arc + carried_forward)"）、`:92-93`——`resolved_this_arc`/`carried_forward` 全仓仅本文件出现（grep 证实），pending_hooks 实际节为 活跃伏笔/hooks/伏笔统计/伏笔时间线（`tests/fixtures/truth-pending_hooks.md:12,20,73,81`）。
- 根因：arc-payoff 按设计稿字段名（volume_promise/arc_beats/resolved_this_arc/carried_forward）写契约，未对齐 volume-outlining / pending_hooks 的实际产出结构；字段过滤未命中 → 每次走 escape hatch（全文件 + WARN）。
- 验证命令+输出：`grep -rn "volume_promise\|arc_beats" skills/ tests/fixtures/ | grep -v review-arc-payoff` → 0 命中；`grep -n "^## \|^### " tests/fixtures/volume-map-xinghuo.md` → Key Results/张力曲线/桥接/黄金三章/story_frame 一致性。
- 建议方向：字段改为实际节名（Key Results / 卷内张力曲线 / 跨卷桥接），或 volume-outlining 输出补 volume_promise + arc_beats 节（需两端同步）；DOT 术语改为从 hooks YAML 状态推导的表述。

### F840 | review-arc-payoff updates `key: chapter` 用于卷键文件（arc_payoff_trend 每行首列为 volume） | contract | P2 【新】
- 证据：`skills/shenbi-review-arc-payoff/SKILL.md:28-30`（`truth/arc_payoff_trend.md` mode append_dedup `key: chapter`）；`:150-155` 趋势行格式首列为 `| volume | … |`；`src/shenbi/pipeline/truth_io.py:201-220`（`_upsert_markdown_table_row` 实际取**首个单元格**做去重键，key_name 仅作默认参数）→ 当前功能上碰巧正确（首格=volume），但契约键名与数据语义不符。
- 根因：从 resonance（章键）复制契约时未改键名。
- 验证命令+输出：读 SKILL.md:28-30 vs :153；读 truth_io.py:201-220（本轮 deep-read 实录）。
- 建议方向：`key: chapter` → `key: volume`（audit_drift 的 chapter 键保留）。

### F841 | 4 个 group-* 正文内嵌 Contract YAML 与 frontmatter writes/updates 互换 + 陈旧代码行号引用 chapter_loop.py:1090-1168 | error | P2
- 证据：`shenbi-review-group-craft/SKILL.md:48-67`（正文块 `writes: []` + `updates: [三 audit 文件]` vs frontmatter `:20-29` `writes:` 三文件+mode）；`shenbi-review-group-character/SKILL.md:48-66`（同型，frontmatter `:15-24`）；`shenbi-review-group-factual/SKILL.md:47-65`（同型，frontmatter `:16-23`）；`shenbi-review-group-plan/SKILL.md:41-54`（同型，frontmatter `:12-17`）；四文件 Dispatch note 均写 "invoked at `chapter_loop.py:1090-1168`"（craft `:44`、character `:46`、factual `:45`、plan `:39`）——实测该行段是 step 推进/context 写入逻辑（`sed -n 1085,1100p` 与 `1160,1172p` 证实），并行审查波实际在别处（`grep -n "parallel_review_wave1_start" src/shenbi/pipeline/chapter_loop.py` → 2567；`grep -n "def dispatch_reviews_parallel" src/shenbi/pipeline/parallel_dispatch.py` → 150，2026-08-14 F958 已定位）。
- 根因：正文 Contract 块为 frontmatter 单源化迁移前的旧版残留；行号引用未随 chapter_loop 重构更新。
- 验证命令+输出：四文件正文块与 frontmatter 逐字对照（本轮 deep-read 实录）+ 上述 grep/sed 输出。
- 建议方向：删除正文 Contract YAML 块；行号引用改函数名。复检 F958/F1010（2026-08-14，覆盖 factual/character/plan；本轮补齐 craft），未修复。

### F842 | location-builder description 含功能子句（"building detailed place profiles with spatial layout and atmosphere"） | contract | P2 【新】
- 证据：`skills/shenbi-location-builder/SKILL.md:3-5`："Use when designing or expanding specific locations in a novel, **building detailed place profiles with spatial layout and atmosphere**, or resolving cross-location spatial consistency"——中间子句为纯功能描述（做什么），非触发条件；AGENTS.md："Never describes what the skill does"。
- 根因：触发句与能力卖点混写。
- 验证命令+输出：读 :3-5（本轮 deep-read 实录）；长度 179 字符合规。
- 建议方向：删除或改写中间子句为用户请求形态（"or when a place profile needs spatial/atmosphere design"）。

### F843 | review-highpoint 内部严重度矛盾：铁律 3「三段缺一 = error」 vs 检查执行 2「缺一段 = warning；缺两段 = error」 | error | P2 【新】
- 证据：`skills/shenbi-review-highpoint/SKILL.md:63`（"反转必须有三段式 — …三段缺一 = error"）vs `:85`（"缺一段 = warning；缺两段 = error"）。
- 根因：铁律与检查执行的阈值两处独立演进未同步。
- 验证命令+输出：读 :63 vs :85（本轮 deep-read 实录）。
- 建议方向：统一口径（建议 warning/error 双档写入铁律）。

### F844 | review-pacing 缺陷证据格式引用不存在的 skills/_shared/REVIEW_EVIDENCE.md；DOT 引用 pacingRules 而实际键为 pacing；maxConsecutiveQuest/maxGapQuest 为幻影键 | deps | P2
- 证据：`skills/shenbi-review-pacing/SKILL.md:94`（"遵循 `skills/_shared/REVIEW_EVIDENCE.md` 定义的四要素格式"）——`ls skills/_shared` → No such file or directory；`:53`（DOT "Read genre-config.json (pacingRules + chapterTypes)"）vs frontmatter `:10-13`（fields: [pacing, chapterTypes]——无 pacingRules）；`:79`（maxConsecutiveQuest / maxGapQuest）vs `skills/shenbi-genre-config/SKILL.md` pacing section 实际键 softRange/hardRange/minChaptersPerCycle/maxChaptersPerCycle（:82-87），chapterTypes 仅含每类型 maxConsecutive。
- 根因：DEPRECATED（`:22-23`，被 group-factual 取代）后停止维护，引用与键名双漂移。
- 验证命令+输出：`ls skills/_shared` → 不存在；读 genre-config SKILL.md:82-87（本轮 deep-read 实录）。
- 建议方向：随 F834 的 deprecation 清理一并处理（重定向到 group-factual 或修复引用）。复检 F1017（2026-08-14，REVIEW_EVIDENCE 部分），未修复；pacingRules/幻影键为本轮新增证据（并入 F1006 家族）。

### F845 | current_state.md 字段级 reads 的目标节名在真实产物中分裂：xinghuo-ranqiong 无「主角状态/当前世界局势/活跃线索」，test-validation/快照 fixture 有 | error | P2 【新（对 F911 的双向证据补强）】
- 证据：消费方 `skills/shenbi-review-continuity/SKILL.md:10-14`（fields: [主角状态, 当前世界局势, 活跃线索]）、`skills/shenbi-review-group-factual/SKILL.md:53`（正文 Contract 块同字段；frontmatter `:9` 为无字段整读——同文件两套粒度）；真实产物分裂：`novel-output/xinghuo-ranqiong/truth/current_state.md:15,26,42`（节名=系统演化阶段/参数当前位置/进行中的情节线/世界状态变化——零命中）vs `novel-output/test-validation/truth/current_state.md:7,10,13`（主角状态/当前世界局势/活跃线索——全命中）vs `tests/fixtures/truth-current_state.md:15,24`（进行中的情节线/角色当前位置——零命中）vs `tests/fixtures/snapshots/chapter-025/truth/current_state.md:13,20,27`（全命中）。
- 根因：current_state.md 无权威模板（state-settling 自由生成节名），字段级 reads 依赖的节名在不同代产物间漂移；escape hatch（未命中回全文件）使漂移静默化。
- 验证命令+输出：对四个文件 `grep -n "^## "`（本轮实测，输出见证据列）。
- 建议方向：state-settling 固定 EXACT 节标题（对齐 AGENTS.md 示例字段），或消费方 fields 改为结构无关的读取方式。复检 F911（2026-08-14，彼轮仅记录"不存在"侧），本轮补充"存在侧"证据。

### F846 | pacing-design 多套 CONSTELLATION 阈值互相矛盾（15-25% / 15-30% PASS / <20% 警告 / 不合格 <10%>40%） | error | P2
- 证据：`skills/shenbi-pacing-design/SKILL.md:91`（三线比例典型 15-25%）、`:176`（"CONSTELLATION 低于 20% 或高于 30% 触发警告"）、`:187`（"PASS: … CONSTELLATION 15-30%"）、`:192`（标准卷 15-25%）、`:257`（自动检查表 15-30%，不合格 <10% 或 >40%）。
- 根因：三线阈值在 4 处独立演进未同步。
- 验证命令+输出：读 :91/:176/:187/:192/:257（本轮 deep-read 实录）。
- 建议方向：单一权威阈值表 + 其余处引用。复检 F1013（2026-08-14），未修复。

### F847 | 4 个 review skill 缺陷证据格式句空引用（"遵循  定义的四要素格式"双空格悬空） | error | M
- 证据：`skills/shenbi-review-character/SKILL.md:82`、`shenbi-review-continuity/SKILL.md:114`、`shenbi-review-dialogue/SKILL.md:106`、`shenbi-review-long-span/SKILL.md:100`（均为 `每条缺陷报告必须遵循  定义的四要素格式：`——引用主体被删空）；对照组完整内联版本：`shenbi-review-era/SKILL.md:145-154`、`shenbi-review-fanfic/SKILL.md:155-164` 等。
- 根因：模板迁移时引用名被删（应为某规范/skill 名）。
- 验证命令+输出：`grep -rn "遵循  定义的四要素格式" skills/` → 4 处（本轮实测）。
- 建议方向：直接内联四要素（同 era/fanfic 的完整写法）。复检 F962/F1017（2026-08-14，覆盖 continuity/dialogue/long-span/character），未修复。

### F848 | ngram-methodology.md 数值矛盾：示例 +15.9/+16.1/+17.9% 标注满足 ">0.20"；6 字窗口示例实为 4 个 5 字串 | error | M
- 证据：`skills/shenbi-review-long-span/ngram-methodology.md:56`（"连续 3 章同向漂移且每次 > 0.20 = warning"）vs `:60-64`（Ch11-13 = +15.9%/+16.1%/+17.9%，全部 <20%，却标 "← 连续 3 章同向 + > 20% = warning"）；`:17`（`"林轩看着他微微笑"`（8 字）的 6 字窗口应为 3 个：林轩看着他微/轩看着他微微/看着他微笑，示例给 4 个 5 字串）；SKILL.md `:138-141` 输出模板同用矛盾数字。
- 根因：示例按 15% 档写、阈值按 20% 写；窗口示例手写出错。
- 验证命令+输出：字符级复核（本轮实测）：len("林轩看着他微微笑")=8，6-gram 数 = 3。
- 建议方向：示例数字改 >20% 或阈值改 >15%；重算窗口示例。复检 F963（2026-08-14），未修复。

### F849 | review-fanfic 的 novel.json.fanfic.mode 无任何生产者，且 NovelConfig（extra: forbid）无 fanfic 字段 → au/ooc/cp 子模式实际不可配置 | error | M（升级证据已具备，保守取 M；建议 owner 复评 P2）【扩展 F916（2026-08-14）】
- 证据：`skills/shenbi-review-fanfic/SKILL.md:37`（"模式由 `shenbi-canon-import` 导入并声明"）、`:76`（"读取 `novel.json.fanfic.mode`"）vs `skills/shenbi-canon-import/SKILL.md` frontmatter writes 仅 `import/canon/*.md`（updates: []，不写 novel.json）；`src/shenbi/contracts/schemas/novel.py:16-28`（NovelConfig `extra: forbid`，字段表无 fanfic）；`grep -rn "fanfic\|sourceWork" src/shenbi/pipeline/seed_parser.py src/shenbi/contracts/` → 0 命中（DOT `:47` 引用的 sourceWork 同为幻影）；fanfic-modes.md `:139`（"若未声明 → 视为 canon"）→ 子模式缺失时静默回退最严格档。
- 根因：设计稿字段（fanfic.mode/sourceWork）从未落地到任何写方与 schema。
- 验证命令+输出：`grep -rn "fanfic" src/shenbi/pipeline/seed_parser.py src/shenbi/contracts/` → 无输出；读 canon-import frontmatter。
- 建议方向：NovelConfig 增 fanfic 子对象（或落 genre-config），canon-import 补 novel.json 更新声明。复检 F916（2026-08-14 仅记路径不一致），本轮补"无生产者 + schema 禁止"证据。

### F850 | relationship-map 输出模板信息边界枚举缺 MUTUAL_SECRET（维度表 4 态、汇总统计 4 态、模板仅 3 态） | error | M 【新】
- 证据：`skills/shenbi-relationship-map/SKILL.md:90-94`（4 态定义，含 MUTUAL_SECRET）、`:155`（汇总统计含 MUTUAL_SECRET: W 对）、`:118`（输出模板 `**信息边界**: [SYMMETRIC/ASYMMETRIC/ISOLATED]`——3 态）。
- 根因：枚举扩至 4 态时模板未同步。
- 验证命令+输出：读 :90-94 vs :118 vs :155（本轮 deep-read 实录）。
- 建议方向：模板枚举补 MUTUAL_SECRET。

### F851 | plot-thread-weaver 术语不一致：B 线一处称"主线"一处称"中线"；P3 max_gap=16 仅见于列校验规则，默认值清单缺 | error | M 【新】
- 证据：`skills/shenbi-plot-thread-weaver/SKILL.md:59`（"B 线（主线）必有窗口"）vs `:70`（分类表 "B 中线 | 卷内的主要支线"——A 才是核心长线）；`:86`（"默认值：P0 max_gap=2, P1 max_gap=4, P2 max_gap=8"——无 P3）vs `:152`（"max_gap 默认值：P0=2, P1=4, P2=8, P3=16"）。
- 根因：分级表与铁律各自演进。
- 验证命令+输出：读 :59/:70/:86/:152（本轮 deep-read 实录）。
- 建议方向：统一 B 线称"中线"；默认值清单补 P3=16。

### F852 | intent-management DOT 无条件 "Update author_intent.md"，正文为"若有变化则更新" | error | M 【新】
- 证据：`skills/shenbi-intent-management/SKILL.md:41-42`（DOT "Ask human: any changes…" → 无条件 "Update author_intent.md"）vs `:106`（步骤 3 "若有变化则更新"）。
- 根因：DOT 缺"无变化"旁路。
- 验证命令+输出：读 :41-42 vs :106（本轮 deep-read 实录）。
- 建议方向：DOT 增 no-change 分支直通 current_focus 环节。

### F853 | review-group-plan 引用错误技能名 `shenbi-reader-pull`（应为 shenbi-review-reader-pull） | deps | M 【新】
- 证据：`skills/shenbi-review-group-plan/SKILL.md:121`（"Distinction from `shenbi-reader-pull`"）vs `:122`（同行段 `shenbi-foreshadowing-lifecycle` 全名正确）；`ls skills/` 无 shenbi-reader-pull。
- 根因：手写省略 review- 前缀。
- 验证命令+输出：`grep -rn "shenbi-reader-pull" skills/` → 仅此 1 处（本轮实测）。
- 建议方向：改全名。

### F854 | shenbi-review-anti-ai/.gitkeep 0 字节冗余（目录已有 SKILL.md + checklist.md） | error | M 【新】
- 证据：`ls -la skills/shenbi-review-anti-ai/.gitkeep` → 0 bytes（本轮实测）。
- 根因：目录建立期占位遗留（2026-08-14 F968 已录另外 3 个 .gitkeep，本文件不在彼轮清单）。
- 建议方向：删除。

### F855 | length-normalizing description 括注功能（"(needs expansion)/(needs compression)"）；DOT 扩写路径无 ≥3000 复核节点 | error | M 【新】
- 证据：`skills/shenbi-length-normalizing/SKILL.md:3-4`（括注为"做什么"而非触发条件；对照组纯触发式写法见 review-continuity :3-4）；DOT `:50`（"Expand…" → 直达 "Output normalized chapter"，无压缩路径 `:51-53` 那样的底线复核分支）vs HARD-GATE `:38`（扩写必须 ≥3000）。
- 根因：触发句附带动作说明；DOT 扩写分支少画复核。
- 验证命令+输出：读 :3-4、:50-53 vs :38（本轮 deep-read 实录）。
- 建议方向：删括注或改触发形态；DOT 补 "Expanded ≥ 3000?" 复核节点。

### F856 | era-reference.md 两处历史年代存疑（蔗糖"汉代"；高足椅"汉末普及"） | error | M（置信度 medium）【新】
- 证据：`skills/shenbi-review-era/era-reference.md:32`（`| 蔗糖 | 汉代 | — |`——制糖术（印度熬糖法/沙糖）通说唐传入，汉代仅甘蔗浆/饴糖）、`:33`（`| 椅子（高足） | 汉末普及 | 商周 |`——高坐具（胡床）汉末传入，椅子普及通说唐宋；"汉末普及"偏早）。二行"高风险朝代"列分别为 —/商周，实际审计影响有限。
- 根因：参考表为手工速记，未过史料复核。
- 验证命令+输出：读 :25-39（本轮 deep-read 实录）；史实未做外部检索验证（标注：未验证，按通说判定 medium 置信）。
- 建议方向：蔗糖改"唐"、椅子改"唐宋普及（胡床汉末传入）"，或补"存疑待查"标注。

### F857 | review-era 双 era-reference.md 同名歧义：契约读项目根外部文件，方法论指针指向 skill 本地同名文件 | error | M 【新】
- 证据：`skills/shenbi-review-era/SKILL.md:11`（contract reads `era-reference.md`——词表 `docs/framework/truth-files.yaml:12` 定义为 author-supplied external read-only）、`:81`（"完整方法与各时代参考词表见 `era-reference.md`"——实际指向 `skills/shenbi-review-era/era-reference.md` 本地方法论文件，二者同名不同物）。
- 根因：skill 本地参考文件与项目输入文件取名相同。
- 验证命令+输出：`ls skills/shenbi-review-era/` → SKILL.md + era-reference.md；读 `:11` vs `:81`（本轮实测）。
- 建议方向：本地文件改名（如 era-methodology.md）或指针写相对路径。另注：激活键 eraResearch/eraConstraints 不存在于真实 genre-config（8 顶层字段：version/updated/fatigueWords/pacing/chapterTypes/auditDimensions/customRules/approval，`skills/shenbi-genre-config/SKILL.md:286`）→ 复检 F1006（2026-08-14 P2），未修复。

---

## 2. per-file 审查记录（33/33 全覆盖）

### skills/shenbi-intent-management/SKILL.md
- 处置: deep-read
- 声称检查的不变量: [description 纯触发；reads/writes 与词表一致；updates 含 mode；DOT 与正文一致；anti-rationalization 表；中文一致性；using-shenbi 引用（:92 存在 ✓）]
- findings: [F852]
- 验证命令: [Read 全文；frontmatter reads truth/author_intent.md + truth/audit_drift.md、updates truth/author_intent.md + truth/current_focus.md 均在 `docs/framework/truth-files.yaml:30-38` 词表内 ✓；description 136 字符 ✓]
- 置信度: high

### skills/shenbi-length-normalizing/SKILL.md
- 处置: deep-read
- 声称检查的不变量: [description 纯触发；novel.json 字段实存（target_word_count/genre/language = `src/shenbi/contracts/schemas/novel.py:18-22` ✓）；DOT 与 HARD-GATE 一致；merge_prose + no_op_behavior；anti-rationalization]
- findings: [F855]
- 验证命令: [Read 全文；`grep -rn "target_word_count" src/shenbi/contracts/schemas/novel.py` → :22 存在；g4 checker 存在（g4/generic.py:312 路由 ✓）]
- 置信度: high
- 备注: 确定性替换候选——字数阈值判定/底线复核可 Python 化（见 §4）。

### skills/shenbi-location-builder/SKILL.md
- 处置: deep-read
- 声称检查的不变量: [description 纯触发；reads 5 文件均在词表；updates world/locations.md + mode；6 节 EXACT 标题自洽；anti-rationalization]
- findings: [F842]
- 验证命令: [Read 全文；reads novel.json/world/*.md/outline/story_frame.md 对照 truth-files.yaml:10,14-16,23 ✓；g4_location_builder 存在（g4/generic.py:313）✓；mode create_or_overwrite 与正文"追加"（:96,38）机械语义一致（dispatcher 整文件写，`dispatch_helper.py:1070-1081` 证实 append_dedup 不走 generic 路径）——不另立 finding]
- 置信度: high

### skills/shenbi-market-radar/SKILL.md
- 处置: deep-read
- 声称检查的不变量: [description 纯触发（"Use when researching…" ✓）；decisions sidecar 声明 vs 正文（F838）；writes 在词表（context/market-radar-decisions.json = truth-files.yaml:57 ✓）；anti-rationalization]
- findings: [F838]
- 验证命令: [Read 全文；读 dispatch_helper.py:735-740（单文件无 schema 注记）+ :1126-1132（json 校验 raise）+ :1172（__stdout__ 回退写入）；g4 路由 `"shenbi-market-radar": g4_decisions`（g4/generic.py:332）]
- 置信度: high

### skills/shenbi-memory-distill/SKILL.md
- 处置: deep-read
- 声称检查的不变量: [description 纯触发（12/36 章间隔 ✓）；reads 覆盖流程所需（F836 违反）；writes truth/arcs/arc-N.md + book_strata.md 在词表（:48,47 ✓）；DOT 分支正确性（F837）；anti-rationalization]
- findings: [F836, F837]
- 验证命令: [Read 全文；`grep -n "author_intent\|book_spine\|world/rules" skills/shenbi-memory-distill/SKILL.md` → 仅正文命中；pipeline 触发实存（triggers.py:9-22 L2/L4/L5）但密度触发未实现（`grep -n "density\|密度" src/shenbi/pipeline/triggers.py` → 0；SKILL.md:60 自述"Wave 3 实现前为声明性文档"——自披露，置信 low，不立 finding）]
- 置信度: high

### skills/shenbi-pacing-design/SKILL.md
- 处置: deep-read
- 声称检查的不变量: [description 纯触发 ✓；reads 4 文件在词表 ✓；auto-check invariants（beat sum 100 / 8 场景类型 / 无 3 连同型）与正文计数规则一致 ✓；阈值一致性（F846 违反）；anti-rationalization ✓]
- findings: [F846]
- 验证命令: [Read 全文；g4_pacing_design 存在（g4/generic.py:314）✓；本文件 AUTO-CHECK 段有实内容（73 个 skill 中少数有值）]
- 置信度: high

### skills/shenbi-plot-thread-weaver/SKILL.md
- 处置: deep-read
- 声称检查的不变量: [description 纯触发 ✓；reads 4 文件在词表 ✓；updates outline/thread_map.md ✓；8 列总览表自洽 ✓；状态枚举 4 值一致 ✓；anti-rationalization ✓]
- findings: [F851]
- 验证命令: [Read 全文；g4_plot_thread_weaver 存在（g4/generic.py:315）✓]
- 置信度: high
- 备注: 确定性替换候选——约束检查表 max_gap 实际值计算纯数值（见 §4）。

### skills/shenbi-power-system/SKILL.md
- 处置: deep-read
- 声称检查的不变量: [description 纯触发 ✓；reads 4 文件在词表 ✓；updates world/power_system.md + mode ✓；DOT 与正文一致 ✓；anti-rationalization ✓]
- findings: 无
- 验证命令: [Read 全文；g4_power_system 存在（g4/generic.py:316）✓；本区质量最好的 skill 之一]
- 置信度: high

### skills/shenbi-relationship-map/SKILL.md
- 处置: deep-read
- 声称检查的不变量: [description 纯触发 ✓；reads 含 glob characters/**/*.md（词表 globs:127 ✓）；updates 双文件 + mode ✓；信息边界枚举一致性（F850）；anti-rationalization ✓]
- findings: [F850]
- 验证命令: [Read 全文；g4_relationship_map 存在（g4/generic.py:317）✓]
- 置信度: high

### skills/shenbi-review-anti-ai/.gitkeep
- 处置: deep-read（结构验证）
- 声称检查的不变量: [占位文件必要性]
- findings: [F854]
- 验证命令: [`ls -la skills/shenbi-review-anti-ai/.gitkeep` → 0 bytes]
- 置信度: high

### skills/shenbi-review-anti-ai/SKILL.md
- 处置: deep-read
- 声称检查的不变量: [description 纯触发 ✓（124 字符）；DEPRECATED 与 using-shenbi/管道一致性（F834）；writes audits/chapter-N-anti-ai.md 在词表参数化（truth-files.yaml:62）✓；checklist.md 引用存在 ✓；anti-rationalization ✓]
- findings: [F834]
- 验证命令: [Read 全文；`grep -n "anti-ai" src/shenbi/pipeline/chapter_loop.py` → :319（CASCADABLE 死引用）、:397、:1817（扫描清单死引用——group-craft 实际写 chapter-N-anti-ai.md，扫描仍有效但常量语境为旧维度）；运行时真实写者=group-craft（frontmatter :20-24）]
- 置信度: high

### skills/shenbi-review-anti-ai/checklist.md
- 处置: deep-read
- 声称检查的不变量: [10 项检查与 SKILL.md 检查执行清单 1-10 逐项一致 ✓；评分规则与铁律 4/5 一致 ✓；与 review-texture 职责分界与 SKILL.md:39 一致 ✓]
- findings: 无
- 验证命令: [Read 全文，与 SKILL.md:65-77 逐项对照]
- 置信度: high
- 备注: 全部 10 项为 regex/计数型确定性检查——本区最强确定性替换候选（见 §4）；Phase 1 note（:69）职责分界声明清晰。

### skills/shenbi-review-arc-payoff/SKILL.md
- 处置: deep-read
- 声称检查的不变量: [description 触发式但含 "— runs in an independent agent" 实现注记（复检 F966（2026-08-14 M），未修复）；dict-reads 字段实存性（F839 违反）；updates 键语义（F840）；writes audits/volume-N-payoff.md 在词表（:63）✓；5 维权重 25/25/20/15/15=100 与 DOT/表格一致 ✓；门逻辑 §6.4 二元一致 ✓；趋势行格式与 drift CLI 契约一致（compute_drift.py:272-280 parse_trend("overall") ✓）；anti-rationalization 7 行（本区最丰富）✓]
- findings: [F839, F840]
- 验证命令: [Read 全文；`grep -rn "volume_promise\|arc_beats" skills/ tests/fixtures/ | grep -v review-arc-payoff` → 0；`grep -n "^## \|^### " tests/fixtures/volume-map-xinghuo.md` → 实际节名；truth_io.py:201-220 首格去重实测]
- 置信度: high

### skills/shenbi-review-character/SKILL.md
- 处置: deep-read
- 声称检查的不变量: [description 纯触发 ✓；DEPRECATED 与 using-shenbi:46 一致性（F834）；reads 含 characters/major/*.md glob ✓；writes audits/chapter-N-character.md ✓；缺陷证据格式完整性（F847）；anti-rationalization ✓]
- findings: [F834, F847]
- 验证命令: [Read 全文；using-shenbi:46/:124 引用实测]
- 置信度: high

### skills/shenbi-review-character/ooc-dimensions.md
- 处置: deep-read
- 声称检查的不变量: [BDI 框架与 SKILL.md 检查执行 1-6 一致 ✓；引用 truth/emotional_arcs.md 与 frontmatter reads ✓；voice_profile/catchphrases 与 character 档案字段约定一致 ✓]
- findings: 无
- 验证命令: [Read 全文，与 SKILL.md:69-77 逐项对照]
- 置信度: high

### skills/shenbi-review-continuity/SKILL.md
- 处置: deep-read
- 声称检查的不变量: [description 纯触发 ✓；DEPRECATED 一致性（F834）；dict-reads 字段实存性（F845）；reads world/rules.md ✓；writes audits/chapter-N-continuity.md ✓；缺陷证据格式（F847）；anti-rationalization ✓]
- findings: [F834, F845, F847]
- 验证命令: [Read 全文；四个 current_state.md 实物 `grep -n "^## "` 对照]
- 置信度: high

### skills/shenbi-review-dialogue/SKILL.md
- 处置: deep-read
- 声称检查的不变量: [description 纯触发 ✓；DEPRECATED 一致性（F834）；激活条件"维度 16"数值 ID 与运行时 named-key 机制脱节（复检 F907（2026-08-14 P2），未修复）；reads 4 文件 ✓；缺陷证据格式（F847）；anti-rationalization ✓]
- findings: [F834, F847]
- 验证命令: [Read 全文；`grep -rn "auditDimensions" src/shenbi/pipeline/audit_layer.py` → :36-54 camelCase 键]
- 置信度: high

### skills/shenbi-review-era/SKILL.md
- 处置: deep-read
- 声称检查的不变量: [description 纯触发 ✓；未 DEPRECATED（活跃）✓；reads era-reference.md 与词表 external 条目一致 ✓；era-reference.md 指针无歧义（F857）；激活键 eraResearch/eraConstraints 幻影（复检 F1006，未修复，并入 F857 备注）；缺陷证据格式完整 ✓；anti-rationalization ✓]
- findings: [F857]
- 验证命令: [Read 全文；genre-config 8 顶层字段对照（shenbi-genre-config/SKILL.md:286）]
- 置信度: high

### skills/shenbi-review-era/era-reference.md
- 处置: deep-read
- 声称检查的不变量: [判定方法与 SKILL.md 检查执行 1-5 一致 ✓；表内容历史准确性（F856 部分存疑）；扩展建议路径合法 ✓]
- findings: [F856]
- 验证命令: [Read 全文；史实部分未做外部检索（标注未验证）]
- 置信度: medium（仅 F856 相关）

### skills/shenbi-review-fanfic/SKILL.md
- 处置: deep-read
- 声称检查的不变量: [description 纯触发（含模式括注，可接受）✓；激活 novel.json.mode="fanfic"（mode 字段在 NovelConfig ✓）vs 子模式 fanfic.mode（F849）；reads source_canon/* 在词表 ✓；writes audits/chapter-N-fanfic.md ✓；cp 与 Chase Power CP 语义消歧声明（:37）✓；缺陷证据格式完整 ✓；anti-rationalization ✓]
- findings: [F849]
- 验证命令: [Read 全文；`grep -rn "fanfic\|sourceWork" src/shenbi/` → 仅 audit_layer.py:51 激活映射，无 schema/生产者]
- 置信度: high（fanfic 模式无真实运行产物——子模式行为路径 low，已在 §5 声明）

### skills/shenbi-review-fanfic/fanfic-modes.md
- 处置: deep-read
- 声称检查的不变量: [4 模式严格度表与 SKILL.md 铁律/检查执行一致 ✓；判定流程与 SKILL.md:75-77 一致 ✓；协作边界（§8）与 character/world-rules 分工清晰 ✓]
- findings: 无
- 验证命令: [Read 全文，与 SKILL.md 逐项对照]
- 置信度: high

### skills/shenbi-review-foreshadowing/SKILL.md
- 处置: deep-read
- 声称检查的不变量: [description 纯触发 ✓；DEPRECATED 一致性（F834）；空账本不自动 PASS 指令（:43）✓；reads 含 subplot_board ✓；大规模召回引用 shenbi-foreshadowing-recall 技能实存 ✓；缺陷证据格式完整（:137-144）✓；anti-rationalization ✓]
- findings: [F834]
- 验证命令: [Read 全文；`ls skills/shenbi-foreshadowing-recall/` → 存在；激活条件"维度 6 或 24"数值 ID 复检 F907 未修复（并入 F834 备注）]
- 置信度: high

### skills/shenbi-review-foreshadowing/hook-lifecycle.md
- 处置: deep-read
- 声称检查的不变量: [5 状态机与 SKILL.md 检查执行一致 ✓；培育/密度规则与铁律 2/5 一致 ✓；Phase 2/3 分层引用 skills/shenbi-foreshadowing-track/lifecycle-states.md 存在性——track 已 DEPRECATED 且目录内无 lifecycle-states.md（`ls skills/shenbi-foreshadowing-track/` → 仅 SKILL.md）→ 死引用，M 级（并入 F834 deprecation 清理家族，不另立编号）]
- findings: 无（死引用随 F834 一并处置）
- 验证命令: [`ls skills/shenbi-foreshadowing-track/` → SKILL.md only]
- 置信度: high

### skills/shenbi-review-group-character/SKILL.md
- 处置: deep-read
- 声称检查的不变量: [description 触发式（F835 违反）；frontmatter writes 4 audit 文件在词表 ✓；正文 Contract 块一致性（F841）；povMode 字段幻影（复检 F231（2026-08-14 P2），未修复——frontmatter :14 为整读，正文块 :59 的 fields 不生效）；四维度与被取代 skill 内容等价 ✓；anti-rationalization ✓]
- findings: [F835, F841]
- 验证命令: [Read 全文；`grep -rn "povMode" src/shenbi/ skills/shenbi-genre-config/` → 0 命中]
- 置信度: high

### skills/shenbi-review-group-craft/SKILL.md
- 处置: deep-read
- 声称检查的不变量: [description 触发式（F835 违反）；writes 3 audit 文件 ✓；正文 Contract 块一致性（F841——craft 为本轮补齐）；段长双档阈值（500 warning/800 error）与导语 ">500/<20" 自洽 ✓；维度 3 十项检查与 review-anti-ai/checklist.md 逐项一致 ✓；dimension 17/32 数值激活 ID 复检 F907 未修复；anti-rationalization ✓]
- findings: [F835, F841]
- 验证命令: [Read 全文；与 checklist.md 逐项对照]
- 置信度: high

### skills/shenbi-review-group-factual/SKILL.md
- 处置: deep-read
- 声称检查的不变量: [description 触发式（F835 违反）；reads 8 文件在词表 ✓；writes 3 audit 文件 ✓；正文 Contract 块 + 陈旧行号（F841）；body 块 fields [主角状态…] 与 frontmatter 整读粒度不一（并入 F845）；三维内容与被取代 skill 等价 ✓；anti-rationalization ✓]
- findings: [F835, F841, F845]
- 验证命令: [Read 全文；并行波真实位置 grep（chapter_loop.py:2567 / parallel_dispatch.py:150）]
- 置信度: high

### skills/shenbi-review-group-plan/SKILL.md
- 处置: deep-read
- 声称检查的不变量: [description 触发式（F835 违反）；writes 2 audit 文件 ✓；正文 Contract 块（F841）；错误技能名（F853）；维度 1 备忘 8 段检查与 review-memo-compliance 等价 ✓；维度 2 与 lifecycle 边界声明 ✓；anti-rationalization ✓]
- findings: [F835, F841, F853]
- 验证命令: [Read 全文；`grep -rn "shenbi-reader-pull" skills/` → 1 处]
- 置信度: high

### skills/shenbi-review-highpoint/SKILL.md
- 处置: deep-read
- 声称检查的不变量: [description 纯触发（括注为审计范围，可接受）✓；reads 3 文件 ✓；writes audits/chapter-N-highpoint.md ✓；DOT 与正文键一致性（DOT maxClimaxPerChapter vs 正文 climaxKeywords/prohibitedClimaxKeywords——复检 F914（2026-08-14 M），未修复；climaxKeywords 系列键不存在于真实 genre-config——复检 F906/F1006 家族，未修复）；反转三段式口径（F843）；缺陷证据格式完整 ✓；anti-rationalization ✓]
- findings: [F843]
- 验证命令: [Read 全文；:46 vs :88 对照]
- 置信度: high

### skills/shenbi-review-long-span/SKILL.md
- 处置: deep-read
- 声称检查的不变量: [description 纯触发（≥3 章条件）✓；reads chapters/chapter-N.md + chapters/*.md 冗余但合法 ✓；边界触发 ch%24==0 与 audit_layer.py:74 一致 ✓；阈值与 methodology 一致（除 F848 示例矛盾）；缺陷证据格式（F847）；anti-rationalization ✓]
- findings: [F847]
- 验证命令: [Read 全文；audit_layer.py BOUNDARY_TRIGGERS 对照]
- 置信度: high
- 备注: 确定性替换候选（n-gram/意象/段长统计，见 §4）。

### skills/shenbi-review-long-span/ngram-methodology.md
- 处置: deep-read
- 声称检查的不变量: [算法/阈值与 SKILL.md 一致（除 F848）；误报过滤规则完备 ✓；自带 Python 实现可用 ✓]
- findings: [F848]
- 验证命令: [Read 全文；字符级窗口复核 len=8 → 3 个 6-gram]
- 置信度: high

### skills/shenbi-review-memo-compliance/SKILL.md
- 处置: deep-read
- 声称检查的不变量: [description 纯触发 ✓；DEPRECATED 一致性（F834）；reads 3 文件 ✓；writes audits/chapter-N-memo-compliance.md ✓；8 段备忘检查与 chapter-planning 备忘结构对齐 ✓；缺陷证据格式完整 ✓；anti-rationalization ✓；激活"维度 33"数值 ID 复检 F907 未修复（并入 F834 备注）]
- findings: [F834]
- 验证命令: [Read 全文]
- 置信度: high

### skills/shenbi-review-motivation/SKILL.md
- 处置: deep-read
- 声称检查的不变量: [description 纯触发 ✓；DEPRECATED 一致性（F834）；reads 4 文件 ✓；writes audits/chapter-N-motivation.md ✓；与 review-character 分界声明（:43）✓；:103 "与 review-character 协作"引用同为 DEPRECATED 技能（并入 F834）；激活"维度 11"数值 ID 复检 F907 未修复；缺陷证据格式完整 ✓；anti-rationalization ✓]
- findings: [F834]
- 验证命令: [Read 全文]
- 置信度: high

### skills/shenbi-review-pacing/SKILL.md
- 处置: deep-read
- 声称检查的不变量: [description 纯触发 ✓；DEPRECATED 一致性（F834）；dict-reads 字段 pacing/chapterTypes 在 genre-config 实存 ✓、已完成章节在 fixture 实存 ✓；与 highpoint/texture 分界声明（:46-47）清晰 ✓；缺陷证据格式引用（F844）；anti-rationalization ✓]
- findings: [F834, F844]
- 验证命令: [Read 全文；`ls skills/_shared` → 不存在]
- 置信度: high

---

## 3. 与 2026-08-14 轮的衔接对照（复检结论）

| 本轮 ID | 2026-08-14 对应 | 复检结论 |
|---|---|---|
| F834 | F904 / F921 / F950 | 未修复（using-shenbi :44-:63/:124/:126 仍路由 8 个 DEPRECATED；group-* 仍零触发行） |
| F835 | F1009（P1）/ F900、F957（P2） | 未修复（4 个 group-* description 原样） |
| F836 | F953（P1） | 未修复（reads 仍缺 author_intent/book_spine/arcs/world-rules） |
| F838 | F909（P2） | 未修复；本轮新增"单文件无 schema 注记 + 正文 markdown → JSON 校验崩溃"升级证据 |
| F839 | （未入账；F826/T809 为 scenario 侧） | 新发现（字段级） |
| F841 | F958 / F1010 | 未修复；本轮补齐 craft 正文块 |
| F844 | F1017（REVIEW_EVIDENCE 部分） | 未修复；新增 pacingRules/幻影键证据 |
| F845 | F911（单侧证据） | 未修复；补"存在侧"产物证据（分裂） |
| F846 | F1013 | 未修复 |
| F847 | F962 / F1017（character 部分） | 未修复 |
| F848 | F963 | 未修复 |
| F849 | F916（M） | 未修复；新增无生产者 + extra:forbid 证据 |
| — | F966（arc-payoff description 实现注记） | 未修复（记入 arc-payoff per-file） |
| — | F907（数值维度 ID）/ F1006（eraResearch 等） | 未修复（记入 dialogue/memo-compliance/motivation/foreshadowing/highpoint/craft/era per-file 备注） |
| — | F231（povMode 幻影） | 未修复（记入 group-character per-file） |
| — | F968（.gitkeep 家族） | 本轮新增第 4 处（review-anti-ai，F854） |

---

## 4. 确定性替换候选清单（rubric 第 8 项）

1. **shenbi-review-anti-ai / group-craft 维度 3**（强候选，P1 级 token 收益）：checklist.md 全部 10 项为 regex/计数（CV、句式正则、破折号 includes、转折词密度、标记词计数、疲劳词、元叙事、术语、套话、禁忌词）——SKILL.md 自述"确定性检查（零 LLM 成本）先跑"，但现由 LLM 执行；Python 化后 LLM 仅处理修复建议。
2. **shenbi-review-long-span**（中候选，P2 级）：6 字 n-gram 重复率/意象计数/句式开端/段长漂移全部为确定性统计，ngram-methodology.md:112-120 已附现成 Python 实现；LLM 保留"读起来是否重复"判定。
3. **shenbi-length-normalizing**（弱候选）：触发判定（<3000/>10000）与双底线复核（≥3000 且 ≥25%）纯数值；扩写/压缩正文为 LLM 核心。
4. **shenbi-plot-thread-weaver**（弱候选）：约束检查表（max_gap 实际值 vs 规定值逐章比对）纯数值，可由 Python 从章节推进表预计算后交 LLM 判定。
5. **shenbi-memory-distill**（弱候选）：触发判定（chapter%12/36、卷边界）已在 triggers.py 确定；L2 结构字段（hook 兑现表/角色态）聚合可确定化，~800 字事件链留 LLM。
6. **shenbi-pacing-design**（边缘）：卷节奏分配表"四拍和=100"等校验已是 G4 auto-check；生成侧仍 LLM。
7. 否决：market-radar（web 研究）、power-system/location-builder/relationship-map/fanfic/era/highpoint/motivation/memo-compliance（语义审计核心）、intent-management（人类口述整理）、arc-payoff（锚点评分）。

---

## 5. 低置信度文件列表

- `skills/shenbi-review-era/era-reference.md` — F856 历史年代判定基于通说，未做外部史料检索验证（medium）。
- `skills/shenbi-review-fanfic/SKILL.md` — fanfic 子模式（au/ooc/cp）无真实运行产物可对照（F849 的行为影响为推导）。
- `skills/shenbi-memory-distill/SKILL.md` — "密度驱动触发"是否已到实现波次无法从仓内确证（SKILL.md 自述声明性文档；triggers.py 无密度逻辑），未立 finding。

## 6. 未覆盖文件列表

**空**（33/33 全覆盖）。
