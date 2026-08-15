# Z8-c 分区初审报告（agent c）— skills/ 25 skill（33 文件）

- 日期：2026-08-14
- 范围：`docs/superpowers/audit-runs/2026-08-14/zones/Z8-c.files` 全部 33 文件（25 个 SKILL.md + 5 个目录内参考文档 + 3 个 .gitkeep；deep-read 33/33）
- 只读约束：仅执行 read / grep / python3 只读分析 / sed / ls；未创建/修改/删除任何仓库文件（本段文件除外）；未 git add/commit。
- 编号段：F1000–F1022（23 条；P1×6、P2×14、M×3）
- 与相邻区重叠说明：本区 7 个 skill 标有 `<!-- DEPRECATED: ... -->`（foreshadowing-recall / foreshadowing-track / review-character / review-memo-compliance / review-pacing / review-texture / review-world-rules），其框架侧接线（deps.json / audit_layer / chapter_loop / gates）属 Z1-Z4 范围，本报告仅从 skill 侧提供证据，phase 4 去重时注意与框架区 findings 合并。

## 0. 总体结论

**skills/ 本区 25 个 skill 的 SKILL.md 整体质量中等偏上**（frontmatter 自动生成节、DOT、铁律、Anti-Rationalization 表大多齐备），但存在三类横切问题：

1. **契约 ↔ 正文漂移（Z8 重点维度 3/4）**：多个 skill 的 frontmatter contract 与正文实际行为不一致——`drift-guidance` 契约声明写 `truth/drift_guidance.md` 但正文从未定义其内容且 pipeline step output 指向它（真实项目该文件不存在）；`book-spine-init` 正文使用 `characters/protagonist.md`+`world/rules.md` 但契约 reads 未声明（真实产物 book_spine.md 的 arc/世界铁律数据确实来自这两个文件）；`state-settling` 未声明写 `characters/protagonist.md`（arc_log）且未声明读 `character_matrix.md`（Write-Protection 规则要求保留角色定义区）；`faction-builder` 正文输出第二个文件 `world/faction-relations.md` 契约未声明。此类按决策表 P1/P2 分级（见 findings）。

2. **DEPRECATED 标记是装饰性的（Z8 重点维度 2/5 旁证）**：7 个 skill 标注 "Do not dispatch" 但全链接线未断——`tests/tiers/deps.json` 的 drafting/audit 阶段 prerequisites 仍 pin `shenbi-foreshadowing-track`、`shenbi-foreshadowing-recall` 及 9 个 deprecated review skill（而 chapter_loop 步骤表已换成 `shenbi-foreshadowing-lifecycle` + 4 个 `shenbi-review-group-*`）；`audit_layer.py` GENRE_ACTIVATION_MATRIX 仍映射 `worldRules→shenbi-review-world-rules`、`texture→shenbi-review-texture`（均已弃用）；g4/g5/ownership/write_safety/dispatch_helper 仍接线 track；T1 全套件 + T2 seed 仍运行 deprecated skills；`using-shenbi` 路由表仍指向 deprecated skill。→ F1004。

3. **激活条件与真实 genre-config schema 漂移**：真实 `genre-config.json` 的 `auditDimensions` 是 camelCase 布尔键（antiAi/character/motivation/pacing/continuity/foreshadowing/sensitivity/worldRules/dialogue/texture），而 5 个 skill 的激活条件仍引用**数字维度号**（维度 7/26/17/3/4/5/18/33），review-era 引用 `eraResearch`/`eraConstraints`（真实配置无此键）。→ F1006。

另有 5 处 skill 内部矛盾（阈值/范围/模式词表多套并存，见 F1000/F1012-F1015）与 3 处 M 级文案问题。

**合规点（正面验证）**：`compute_pattern.py`、`recall_overdue_hooks`、`drift_detection`、`review_resonance`/`calibration` CLI、`route_revision`/`verify_preservation` 等正文引用的确定性 helper 全部真实存在；`benchmarks/anchors/AC-001..006` 锚点存在且与 review-resonance/score-volume 的描述匹配；`g4_review_resonance` 校验的列名（维度/得分/满分/置信度/证据/裁判理由）与 SKILL.md 输出格式一致；`plans/chapter-N-plan.md` 的 "1. 当前任务" 字段与 chapter-revision/review-resonance 的字段级 reads 匹配；book_spine.md 真实产物与 book-spine-init 输出格式一致。

---

## 1. findings（F1000–F1022）

### F1000 | shenbi-chapter-revision 修订模式词表三处矛盾（SKILL.md 3 模式 vs revision-modes.md 6 模式 vs 顶部 DOT rewrite/rework） | error | P2
- 证据：`skills/shenbi-chapter-revision/SKILL.md:43-58`（顶部 DOT "rewrite/rework?" + "Generate REVISED_CONTENT"）、`:115-121`（重生路由"三种模式 spot-fix/regenerate/constrained-regenerate"）、`skills/shenbi-chapter-revision/revision-modes.md:3-12`（6 种模式 auto/spot-fix/polish/rewrite/rework/anti-detect）、`src/shenbi/skill_utils/revision_routing/route.py:29-31`（实现仅 SPOT_FIX/REGENERATE/CONSTRAINED_REGENERATE）
- 根因：实现（route.py）与 SKILL.md 重生路由一致（3 模式），但 revision-modes.md 的 6 模式表（polish/rework/anti-detect）从未被 auto 路由表路由到（revision-modes.md:14-38 只路由 spot-fix/rewrite），SKILL.md 顶部 DOT 又用 rewrite/rework 旧词——同文件内三套词表，agent 无法确定权威模式集。
- 验证命令+输出：`grep -n "MODE\|spot-fix\|regenerate\|constrained\|rewrite\|rework" src/shenbi/skill_utils/revision_routing/route.py` → `SPOT_FIX = "spot-fix" / REGENERATE = "regenerate" / CONSTRAINED_REGENERATE = "constrained-regenerate"`；`read` revision-modes.md:1-38 全文。
- 建议方向：以 route.py 为准统一词表；revision-modes.md 删除 polish/rework/anti-detect 死模式或标注 legacy；SKILL.md 顶部 DOT 改 regenerate/constrained-regenerate。

### F1001 | shenbi-drift-guidance 契约声明写 truth/drift_guidance.md 但正文从未定义其内容；pipeline step output 指向该文件而真实项目从未产生；audit_drift.md append_dedup 与"合并重写为权威版本"语义冲突 | error | P1
- 证据：`skills/shenbi-drift-guidance/SKILL.md:14-21`（contract writes: `truth/drift_guidance.md` create_or_overwrite；updates: `truth/audit_drift.md` append_dedup key: chapter）、`:40`/`:91`（正文唯一写目标为 `truth/audit_drift.md`）、`:42`（"合并重写为权威版本"——重写语义）、`src/shenbi/pipeline/chapter_loop.py:277-280`（`ChapterStep(2, "shenbi-drift-guidance", ..., output_path="truth/drift_guidance.md")`）、`ls novel-output/xinghuo-ranqiong/truth/`（13 个文件，无 drift_guidance.md；audit_drift.md 存在且头部注明"由 shenbi-review-resonance 追加，最终权威版本由 shenbi-drift-guidance 合并重写"）
- 根因：契约/pipeline 期望 `drift_guidance.md`，正文只写 `audit_drift.md`——声明输出从未被定义/产生；同时 append_dedup（追加）与正文的"合并重写权威版本"（覆盖）语义相反，按契约模式执行会导致无法完成滚动窗口合并。
- 验证命令+输出：`ls novel-output/xinghuo-ranqiong/truth/` → audit_drift.md …（无 drift_guidance.md）；`grep -n "drift_guidance" skills/shenbi-drift-guidance/SKILL.md` → 仅契约节/数据契约节出现；`sed -n '277,280p' src/shenbi/pipeline/chapter_loop.py` → output_path=truth/drift_guidance.md。
- 建议方向：契约 writes 改 `truth/audit_drift.md`（create_or_overwrite 语义=合并重写），删除 drift_guidance.md 声明并同步 chapter_loop output_path；或正文补充 drift_guidance.md 内容定义（二选一，单信源）。

### F1002 | shenbi-state-settling 未声明 reads（character_matrix.md）与未声明写（characters/protagonist.md arc_log），Write-Protection 规则在 dispatcher 过滤下无法成立 | error | P1
- 证据：`skills/shenbi-state-settling/SKILL.md:7-8`（contract reads 仅 `chapters/chapter-N.md`）、`:51-81`（"Truth File Update Mode Rules" + "character_matrix.md Write-Protection Rule"：`## 角色定义` 区为 human-authored，"MUST NEVER be overwritten"，只更新 per-chapter state 区——重写全文件需先读现状）、`:264-288`（"Character Matrix Update (NEW)" 第 2 步要求向 `characters/protagonist.md` frontmatter **追加 arc_log**——契约 updates 无此文件）、contract :9-29（updates 仅 6 个 truth 文件）
- 根因：contract reads 不含 character_matrix.md/protagonist.md → dispatcher 按 AGENTS.md 字段级过滤只传 chapter-N.md，agent 无法读到角色定义区来保留 → 按契约 create_or_overwrite 重写 character_matrix.md 必然丢"角色定义"区；`characters/protagonist.md` 的 arc_log 追加是未声明写，写越权审计（Z5）无法跟踪。
- 验证命令+输出：`read` SKILL.md:7-29,51-81,264-288；`head -30 novel-output/xinghuo-ranqiong/truth/character_matrix.md` → 有 `## 参数角色定位` 表（真实文件含 human-authored 定义区，重写需保留）。
- 建议方向：contract reads 增加 `truth/character_matrix.md`、`characters/protagonist.md`；updates 增加 `characters/protagonist.md`（append 语义）或把 arc_log 写入改为独立 truth 文件。

### F1003 | shenbi-state-settling 更新模式三处不一致：frontmatter append_dedup vs 更新规则表 replace vs Update Mode Rules 缺失 particle_ledger/subplot_board | error | P1
- 证据：`skills/shenbi-state-settling/SKILL.md:15-23`（contract：particle_ledger/subplot_board 均 append_dedup key: chapter）、`:53-73`（"Truth File Update Mode Rules (CRITICAL)" 只列 current_state/character_matrix（replace）与 resonance_trend/audit_drift/emotional_arcs/chapter_summaries（upsert_markdown_row）与 pending_hooks（upsert_yaml）——**particle_ledger/subplot_board 缺失**）、`:150-158`（更新规则表：资源→particle_ledger.md **replace**；线索→subplot_board.md **replace**）、`:68-73`（"Do NOT output the complete file content for cumulative files — doing so will cause data accumulation to fail"）、`:110`（铁律 4"增量更新—追加变更，不重写整个文件" vs replace-mode 定义"output the ENTIRE file content"）
- 根因：同一 skill 对 particle_ledger/subplot_board 给出 replace（表）/append_dedup（契约）/缺失（CRITICAL 节）三种语义；agent 按表输出全文件 → 按契约 append_dedup 写入时整文件成为单条 chapter 记录 → 数据累积失败（技能自身警告的正是该场景）。
- 验证命令+输出：`read` SKILL.md:15-29,53-73,110,150-158。
- 建议方向：统一为 append_dedup（与契约一致），更新规则表删除 replace 标注，Update Mode Rules 补 particle_ledger/subplot_board 行；铁律 4 措辞区分"replace-mode 全量重写"与"cumulative 增量"。

### F1004 | 7 个 DEPRECATED skill 全链接线未断："Do not dispatch" 无 enforcement；deps.json 前置契约与 pipeline 步骤表矛盾 | error | P1
- 证据：7 个 skill 文件头 `<!-- DEPRECATED: ... Do not dispatch. -->`（foreshadowing-recall:14-15、foreshadowing-track:18-19、review-character:19-20、review-memo-compliance:17-18、review-pacing:22-23、review-texture:17-18、review-world-rules:21-22）；`tests/tiers/deps.json` t2-phases.drafting.prerequisites 含 `shenbi-foreshadowing-track`、`shenbi-foreshadowing-recall`（而 pipeline chapter_loop.py:185-190 步骤 7 已改为 `shenbi-foreshadowing-lifecycle`，无 track/recall 步骤）；t2-phases.audit.prerequisites 仍列 18 个单独 review skill（含 review-character/dialogue/pacing/world-rules/memo-compliance/motivation/pov/texture 等 deprecated），**无** review-group-*；`src/shenbi/pipeline/audit_layer.py:46-55` GENRE_ACTIVATION_MATRIX `"worldRules": "shenbi-review-world-rules"`、`"texture": "shenbi-review-texture"`（均 deprecated）；`src/shenbi/pipeline/chapter_loop.py:3048`（`if step.skill == "shenbi-foreshadowing-recall"` 仍处理）；`src/shenbi/gates/g4/generic.py:290` + `src/shenbi/gates/shared.py:255`（foreshadowing-track G4）；`src/shenbi/gates/g5.py:243` + `src/shenbi/contracts/ownership.py:85` + `src/shenbi/pipeline/write_safety.py:29`（track 接线）；`skills/using-shenbi/SKILL.md:46-74`（路由表指向 review-character/pacing/world-rules/texture/memo-compliance/foreshadowing-track）；`tests/tiers/t1-skill/shenbi-review-memo-compliance/`（clean/bug-hunt/generative 全套件）；`tests/tiers/t2-phase/audit/input/seed.md:8-21`（T2 seed 仍运行 deprecated skills）
- 根因：deprecation 仅写在 SKILL.md 注释里，契约层（deps.json prerequisites）、门层（g4/g5/ownership）、调度层（audit_layer/chapter_loop）、测试层（T1/T2）、入口路由（using-shenbi）全部未同步 → 存在实际 dispatch deprecated skill 的路径（audit_layer 按 genre 键激活 review-world-rules/review-texture），且 deps.json 前置与 chapter_loop 步骤表自相矛盾。
- 验证命令+输出：`python3` 读 deps.json t2-phases.drafting/audit.prerequisites（输出见上）；`grep -rn "shenbi-review-world-rules\|shenbi-review-texture\|shenbi-foreshadowing-recall" src/` → audit_layer.py:46,49 / chapter_loop.py:3048；`ls tests/tiers/t1-skill/ | grep review-memo`。
- 建议方向：deps.json prerequisites 替换为 `shenbi-foreshadowing-lifecycle` + `shenbi-review-group-{factual,character,craft,plan}` + `shenbi-review-resonance` 等实际步骤；audit_layer 矩阵改映射 group-*；退役或标注 T1/T2 中 deprecated 套件；using-shenbi 路由改指向 group-*/lifecycle。

### F1005 | shenbi-review-resonance reads 字段 style_profile.md [11. 综合画像 / 6. 修辞模式] 与真实 style_profile.md 章节号不符（实际 8. 综合画像 / 5. 修辞模式） | error | P2
- 证据：`skills/shenbi-review-resonance/SKILL.md:15-18`（`file: style/style_profile.md, fields: ["11. 综合画像", "6. 修辞模式"]`）；`novel-output/xinghuo-ranqiong/style/style_profile.md:73`（`## 5. 修辞模式（推测）`）、`:85`（`## 6. 标点密度（推测，每千字）`）、`:121`（`## 8. 综合画像`，全文件仅 8 个编号节 + 风格学习汇总）
- 根因：字段名漂移 → 字段级 reads 过滤按声明字段找不到 → 恒走 escape hatch（全文件 + WARN），字段过滤对该 skill 死码；且 agent 若按"6. 修辞模式"定位会读到标点密度节。
- 验证命令+输出：`grep -n "^## " novel-output/xinghuo-ranqiong/style/style_profile.md` → 1..8 号节（修辞模式=5、标点密度=6、综合画像=8）。
- 建议方向：字段改为 `["8. 综合画像", "5. 修辞模式"]`（或按节名匹配）。

### F1006 | 激活条件与真实 genre-config schema 漂移：数字维度号 / eraResearch / eraConstraints 均不存在于真实 auditDimensions | error | P2
- 证据：`skills/shenbi-review-pacing/SKILL.md:45`（"auditDimensions 包含维度 7 或 26"）、`skills/shenbi-review-texture/SKILL.md:40`（"维度 17"）、`skills/shenbi-review-world-rules/SKILL.md:44`（"维度 3、4、5 或 18"）、`skills/shenbi-review-memo-compliance/SKILL.md:40` + `skills/shenbi-review-group-plan/SKILL.md:64`（"维度 33"）、`skills/shenbi-review-era/SKILL.md:37`（"eraResearch 为 truthy，或 eraConstraints 存在且非空"）；`novel-output/xinghuo-ranqiong/genre-config.json` → `auditDimensions` 键 = `['antiAi','character','motivation','pacing','continuity','foreshadowing','sensitivity','worldRules','dialogue','texture']`（布尔），`has eraResearch: False, has eraConstraints: False`；对照 `src/shenbi/pipeline/audit_layer.py:39-55`（真实激活按 camelCase 键）
- 根因：旧数字 auditDimensions schema 残留于 5 个 skill 的激活条件，与 genre-config 实际 schema（camelCase 布尔键）脱钩；其中 review-era 的 eraResearch/eraConstraints 键在真实配置中不存在 → 条件恒假/不可判定。
- 验证命令+输出：`python3` 解析 genre-config.json → 上述键列表 + eraResearch/eraConstraints False。
- 建议方向：激活条件统一改为引用 camelCase 键（如 `auditDimensions.worldRules == true`）；review-era 改由 audit_layer 的 `era` 键或显式约束文件触发。

### F1007 | 4 个 builder/planner skill 的"append 语义"正文与 frontmatter create_or_overwrite 模式冲突 | error | P2
- 证据：`skills/shenbi-faction-builder/SKILL.md:15-16`（contract updates world/factions.md create_or_overwrite）vs `:37`（"追加/扩展…append，不重写已有势力"）+ `:52`（DOT "Append to world/factions.md"）；`skills/shenbi-location-builder/SKILL.md:16-17` vs `:38`（"每个地点 append，不重写已有地点"）+ `:51`；`skills/shenbi-relationship-map/SKILL.md:15-18`（两个文件均 create_or_overwrite）vs `:108`（"追加到 characters/relationships.md"）+ `:127`（"追加到 truth/character_matrix.md"）+ `:63` 铁律 4（dedup/superseded 合并语义）；`skills/shenbi-volume-outlining/SKILL.md:14-15` vs `:122`（"追加到 outline/volume_map.md"）+ `:58`（DOT "Append to"）
- 根因：正文语义是"读现有 + 追加/合并"，契约模式是"create_or_overwrite"——模式名与正文语义冲突；relationship-map 对 truth/character_matrix.md（跨 skill 共享 truth）用 create_or_overwrite 尤其危险（若 agent 按模式名只输出新增小节即整文件覆盖）。
- 验证命令+输出：逐一 `grep -n "append\|create_or_overwrite\|追加"` 上述 4 文件。
- 建议方向：统一措辞——若为"读全部→重写全文件（含既有）"则在正文明示全量重写语义；若为纯追加则契约改用 append 语义；character_matrix.md 的写应改为"读+合并重写"并保留未涉及小节。

### F1008 | shenbi-faction-builder 正文输出 world/faction-relations.md（文件 2），契约仅声明 updates world/factions.md —— 未声明写 | error | P2
- 证据：`skills/shenbi-faction-builder/SKILL.md:179-193`（"文件 2: world/faction-relations.md（跨势力关系矩阵）" + 七列校验规则）、`:200`（汇总"更新文件: world/factions.md, world/faction-relations.md"）、contract :6-16（仅 world/factions.md）
- 根因：输出扩展未同步契约 → G2/G4 只校验 factions.md，faction-relations.md 的七列/枚举/对称性规则无门校验；写越权审计按声明 writes/updates 跟踪，该文件脱管。
- 验证命令+输出：`read` SKILL.md:6-16,179-213。
- 建议方向：契约 updates 增加 `world/faction-relations.md`（append 语义），并评估 G4 补充七列校验。

### F1009 | review-group-character / review-group-plan 的 description 描述实现而非纯触发条件（含 "in one call"、"dispatches via parallel_dispatch.py"），且无 "Use when" 触发条件 | error | P1
- 证据：`skills/shenbi-review-group-character/SKILL.md:3`（`description: Grouped audit for character integrity -- character consistency, dialogue, motivation, and POV in one call; dispatches as a parallel wave via parallel_dispatch.py`）、`skills/shenbi-review-group-plan/SKILL.md:3`（同型）；AGENTS.md"Skill Authoring"："description: ONLY when-to-use trigger conditions, ≤500 chars. Never describes what the skill does."；对照同区合规 description（如 review-character:3-4 "Use when a finished chapter needs character consistency audit…"）
- 根因：description 写成"做什么 + 怎么调度"的实现摘要（含 parallel_dispatch.py 实现细节），无触发条件 → 违反 AGENTS.md 显式契约；description 是 skill 触发/路由输入，缺触发条件使按触发语义的调度（skill-triggering-prompts / 路由）无法正确判定。
- 验证命令+输出：`read` 两个 SKILL.md:1-5。
- 建议方向：改写为触发条件（如 "Use when a finished chapter needs character integrity audits (OOC, dialogue, motivation, POV) before revision"），删除实现描述；parallel_dispatch 细节移到正文 Dispatch note。

### F1010 | review-group-character / review-group-plan 正文内嵌 "Contract" YAML 块与 frontmatter 契约 writes/updates 互换（writes: [] + updates: 4 文件 vs frontmatter writes: 4 文件 + updates: []） | error | P2
- 证据：`skills/shenbi-review-group-character/SKILL.md:50-66`（内嵌块 `writes: []`、`updates: [audits/chapter-N-character.md …]`）vs frontmatter :15-24（`writes: [4 文件]`、`updates: []`）；`skills/shenbi-review-group-plan/SKILL.md:43-54` 同型
- 根因：内嵌 Contract 块是旧版残留（当初 grouped 设计用 updates 语义），frontmatter 是权威；同一文件出现两份互相矛盾的契约声明，读者/工具无法判定。
- 验证命令+输出：`read` 两个文件 :15-24 与 :43-66。
- 建议方向：删除正文内嵌 Contract 块（frontmatter 为单信源）或同步为一致。

### F1011 | shenbi-book-spine-init 正文使用 characters/protagonist.md + world/rules.md 但契约 reads 未声明 | error | P1
- 证据：`skills/shenbi-book-spine-init/SKILL.md:7-10`（contract reads 仅 outline/story_frame.md、outline/volume_map.md、novel.json）；`:79-84`（输出格式主角弧"从 characters/protagonist.md 继承"）、`:90-92`（"世界铁律滚动快照（从 world/rules.md 同步前5条）"）、`:42-44`（DOT "Extract: protagonist arc from character files"）；`novel-output/xinghuo-ranqiong/truth/book_spine.md:24-29`（真实产物含 arc_type/arc_starting/arc_ending 数据 + 世界铁律规则一~五——来自 protagonist.md 与 world/rules.md，即实际执行读了未声明文件）
- 根因：contract reads 不全 → dispatcher 字段过滤下 agent 拿不到 protagonist.md/world/rules.md → 要么产出缺主角弧/铁律的不完整 book_spine，要么违规读未声明文件（真实产物证明实际走了后者）；契约单信源被架空。
- 验证命令+输出：`read` SKILL.md:7-15,79-92；`tail -30 novel-output/xinghuo-ranqiong/truth/book_spine.md`（主角弧+世界铁律节，数据与 protagonist.md/rules.md 同源）。
- 建议方向：contract reads 增加 `characters/protagonist.md`、`world/rules.md`。

### F1012 | shenbi-chapter-pattern 熵评级阈值内部矛盾 + 13 模式与 genre-config chapterTypes 词表不匹配 | error | P2
- 证据：`skills/shenbi-chapter-pattern/SKILL.md:106-109`（"熵 > 2.0 健康；1.5-2.0 轻度；< 1.5 严重单调"）vs `:328-336`（"H > 2.5 优秀；2.0 < H ≤ 2.5 健康；1.5 < H ≤ 2.0 轻度；1.0 < H ≤ 1.5 中度；H ≤ 1.0 严重"）——两套阈值并存；`:55`（"连续 N 章同模式 ≥ genre-config 中定义必须报警"）+ contract reads genre-config.json vs `novel-output/xinghuo-ranqiong/genre-config.json` `chapterTypes` = {战斗/对话/谋略/人物/世界观/过渡/高潮/反思}（8 类，maxConsecutive 2/3/1 等）而 SKILL.md 13 模式 = {引入/升级/转折/揭示/决战/沉淀/日常/训练/探索/阴谋/逃亡/回忆/总结} + 单调性表 {决战/转折/升级/日常/训练/其他}——词表不对应，genre-config 阈值无法映射到 13 模式
- 根因：熵阈值在流程节与评级表重复定义且不一致（<1.5 的判定二义）；genre-config.json 的 chapterTypes 词表与 skill 的 13 模式是两套分类，声明 reads 却无法实际消费其阈值。
- 验证命令+输出：`read` SKILL.md:104-118,328-347；`python3` 解析 genre-config.json chapterTypes 键。
- 建议方向：统一熵评级表（删流程节重复定义）；明确 genre-config chapterTypes 与 13 模式的映射或改用 skill 内默认阈值表。

### F1013 | shenbi-pacing-design 内部矛盾：四拍范围 / CONSTELLATION 多套范围 / 场景类型 6-8 vs 恰好 8 / 单调性阈值统一 vs 分类型 | error | P2
- 证据：`skills/shenbi-pacing-design/SKILL.md:76-81`（四拍 铺垫 30-40/升级 30-40/爆发 10-20/余波 15-25）vs `:151-156`（铺垫 20-40/升级 30-45/爆发 10-20/余波 15-25）vs `:245`（跨卷补偿 铺垫 20-40/升级 30-45）；`:187`（PASS: CONSTELLATION 15-30%）vs `:176`（"低于 20% 或高于 30% 触发警告"）vs `:257`（不合格 <10% 或 >40%）vs `:193`（开卷 CONSTELLATION 30-40%）——至少 4 套范围；`:97`（"至少定义 6-8 种场景类型"）vs `:199`（"必须定义恰好 8 种"）；`:69`（铁律 3"不重复超 3 章"）vs `:203-210`（分类型阈值 战斗≤2/探索≤2/揭示≤1 等）vs `:231`（N > 3）
- 根因：数值约束在核心设计/输出格式/检查规则多处重复定义且互相矛盾，agent 无法确定权威范围；auto-check invariants 也无具体数值。
- 验证命令+输出：`read` SKILL.md:74-83,147-156,174-196,197-212,243-262。
- 建议方向：数值约束单信源化（以输出格式 + 检查规则表为准），删除核心设计的旧范围；场景类型统一为恰好 8；单调性阈值统一为分类型表。

### F1014 | shenbi-volume-outlining 内部矛盾：铺垫段占比 10-20% vs 15-25%；跨卷钩子 ≥1（铁律/核心设计）vs ≥3（输出/检查/汇总） | error | P2
- 证据：`skills/shenbi-volume-outlining/SKILL.md:100-103`（铺垫段 10-20%/上升 30-40%/爆发 20-30%/余波 15-25%）vs `:175-178`（铺垫 15-25%/上升 30-40%/爆发 20-30%/余波 15-25%）vs `:184-185`（检查规则 铺垫 15-25% 不合格 <10%/>35%）；`:66` 铁律 3（"至少 1 个实体钩子"）+ `:118`（"至少 1 个，理想 2-3 个"）vs `:202`（"至少 3 个实体钩子"）+ `:239`（钩子数 ≥3）+ `:272`（"要求 ≥ 3"）
- 根因：核心设计（≥1 钩子、铺垫 10-20%）与输出/检查规则（≥3 钩子、铺垫 15-25%）不一致 → 按铁律产出会被 G4 式自动检查判不合格。
- 验证命令+输出：`read` SKILL.md:97-119,167-242。
- 建议方向：统一为输出/检查规则的数值（≥3 钩子、铺垫 15-25%），同步铁律与核心设计措辞。

### F1015 | shenbi-foreshadowing-track 内部矛盾：字段分工（last_reinforced/subtlety 归 state-settling）vs DOT "Update last_reinforced / subtlety"；Cross-Volume Bridge Tracking 引用不存在文件 foreshadowing_ledger.md | error | P2
- 证据：`skills/shenbi-foreshadowing-track/SKILL.md:40`（"`last_reinforced`/`subtlety` 字段由 `shenbi-state-settling` 维护"）vs `:49`（DOT "Update last_reinforced / subtlety"）+ `:75`（"更新所有活跃伏笔的状态" + 输出样例含 last_reinforced）；`:156`（"After updating foreshadowing_ledger.md, also check truth/bridge_tracker.md"——`foreshadowing_ledger.md` 不存在于任何契约/truth 目录，应为旧文件名残留）
- 根因：字段归属声明（state-settling 维护 last_reinforced/subtlety）与本文档自身的 DOT/操作步骤冲突——同一字段两个写者；foreshadowing_ledger.md 是改名残留（现为 pending_hooks.md）。
- 验证命令+输出：`read` SKILL.md:40,46-56,154-164；`find . -name "foreshadowing_ledger.md" -not -path "./.venv/*"` → 无结果；`ls novel-output/xinghuo-ranqiong/truth/` → 无 foreshadowing_ledger.md。
- 建议方向：DOT 与操作步骤改为"本 skill 仅推进生命周期状态；last_reinforced/subtlety 由 state-settling 维护（或明示二者协作）"；foreshadowing_ledger.md 改 pending_hooks.md（注意本 skill 已弃用，修复或随退役处理）。

### F1016 | foreshadowing-track / foreshadowing-recall 的 dict-form reads 字段与真实 truth 文件结构不符（活跃伏笔/伏笔时间线/已完成章节 不存在） | error | P2
- 证据：`skills/shenbi-foreshadowing-track/SKILL.md:8-9`（`{file: truth/pending_hooks.md, fields: [活跃伏笔, 伏笔时间线]}`、`{file: truth/chapter_summaries.md, fields: [已完成章节]}`）；`novel-output/xinghuo-ranqiong/truth/pending_hooks.md:1-16`（frontmatter 为 title/project/version/last_updated/type/category/status/filled_by/last_chapter/track_chapter，无"活跃伏笔/伏笔时间线"节；正文为"## 第N章伏笔呈现"表）；`truth/chapter_summaries.md`（正文为"## 第N章：…"节 + 维度表，无"已完成章节"字段）
- 根因：字段名基于旧 YAML 结构假设，真实文件已演化为 markdown 表结构 → 字段过滤恒 miss → escape hatch 全文件 + WARN（字段级 reads 对该 skill 死码）。
- 验证命令+输出：`head -16` 两个 truth 文件确认无声明字段。
- 建议方向：按真实结构改字段（如 pending_hooks → 按节名/表格列）或改为整文件 reads；随弃用状态一并处理。

### F1017 | 缺陷证据格式引用缺失/死引用：review-character 空白引用；review-pacing 引用不存在的 skills/_shared/REVIEW_EVIDENCE.md | error | P2
- 证据：`skills/shenbi-review-character/SKILL.md:82`（"每条缺陷报告必须遵循  定义的四要素格式"——引用源空白）；`skills/shenbi-review-pacing/SKILL.md:94`（"遵循 `skills/_shared/REVIEW_EVIDENCE.md` 定义的四要素格式"）；`ls skills/_shared/` → 目录不存在；`grep -rln "REVIEW_EVIDENCE" skills/ src/` → 仅 shenbi-review-pacing/SKILL.md 自身
- 根因：四要素格式的"权威源"引用悬空（review-character 连文件名都没写）；pacing 引用的共享文件从未创建。
- 验证命令+输出：`ls skills/_shared/ 2>/dev/null` → 空；`grep -rln "REVIEW_EVIDENCE" .`（排除 .venv/.git）→ 仅 1 处。
- 建议方向：创建 skills/_shared/REVIEW_EVIDENCE.md 并让所有 review skill 统一引用，或删除引用改内联定义。

### F1018 | 多处 "spec §X.Y" 引用无命名文档，唯一可匹配文档为归档 plan（positive-quality-gates） | error | P2
- 证据：`skills/shenbi-review-resonance/SKILL.md:55,60,62,66,110,124,165,181`（"spec §5/§8.1/§8.2/§8.3/§9/§5.4/§5.6"）、`skills/shenbi-drift-guidance/SKILL.md:51,58,85`（"spec §8.3"）、`skills/shenbi-chapter-revision/SKILL.md:115-137`（"spec §5.2/§11.3-11.5"）、`skills/shenbi-foreshadowing-recall/SKILL.md:37`（"spec §3.6"）；`ls docs/superpowers/specs/`（当前 15 个 spec 无 resonance/drift/revision 主题）；`find docs -name "*.md" | xargs grep -l "共鸣评分\|review-resonance"` → 唯一设计文档为 `docs/superpowers/plans/archive/2026-06-22-positive-quality-gates.md`（归档 plan，非活跃 spec）
- 根因：skill 引用 "spec §X.Y" 但从不给出 spec 文件名；活跃 specs 目录无对应文档，唯一同主题文档是已归档 plan → 引用不可解析，读者无法核对权威定义。
- 验证命令+输出：`ls docs/superpowers/specs/`；`find docs -name "*.md" | xargs grep -l "共鸣评分"`（排除 audit-runs）→ 仅归档 plan + docs/skills/index.md + getting-started。
- 建议方向：将引用改为具名文档 + file:line，或在 specs/ 补对应设计 spec（positive-quality-gates 应迁移/复活为活跃 spec）。

### F1019 | shenbi-score-volume "从 book_spine.md (L5) 读 themes/master hooks" 行号引用过期 | M
- 证据：`skills/shenbi-score-volume/SKILL.md:86`（铁律 3"从 book_spine.md (L5) 读 themes/master hooks"）；`novel-output/xinghuo-ranqiong/truth/book_spine.md:1-5`（frontmatter：1 `---`、2 updated、3 total_chapters、4 status、5 `---`）——L5 是 frontmatter 结束符，themes 在 ~L17-21、master hooks 在 ~L31-42
- 根因：行号引用未随文件结构更新（L5 无意义）。
- 验证命令+输出：`head -25` book_spine.md 数行号。
- 建议方向：改为节名引用（"## 全书 themes / ## 主线钩子"）并删除行号。

### F1020 | shenbi-chapter-pattern 熵计算输出模板 "第A-Ⓣ章" 全角符号误用 | M
- 证据：`skills/shenbi-chapter-pattern/SKILL.md:359`（`| 30章 | 第A-Ⓣ章 | X | 13 | ...`——`Ⓣ` 应为 `T`）
- 建议方向：改回半角 T（第A-T章）。

### F1021 | shenbi-book-spine-init HARD-GATE 语句重复 | M
- 证据：`skills/shenbi-book-spine-init/SKILL.md:34`（"（worldbuilding + character + story-architecture + volume-outlining）完成后、逐章循环开始前执行。（worldbuilding + character + story-architecture + volume-outlining）完成后、逐章循环开始前执行。"——同一分句重复两次）
- 建议方向：删除重复分句。

### F1022 | shenbi-state-settling/truth-files-reference.md 文件清单过期不完整（遗漏 9 个契约中 truth 文件）且"增量更新"原则与 replace-mode 冲突 | error | P2
- 证据：`skills/shenbi-state-settling/truth-files-reference.md:5-16`（列 10 个 truth 文件）——遗漏本区契约中存在的 `resonance_trend.md`、`arc_payoff_trend.md`、`volume_score_trend.md`、`volume_summaries.md`、`drift_guidance.md`、`book_spine.md`、`bridge_tracker.md`、`state_snapshot-pre-rev.md`、`foreshadowing_recall_result.md`（9 个，见各 skill contract 与 `ls novel-output/xinghuo-ranqiong/truth/`）；`:21`（"增量更新 — 只记录变化的部分，不重写整个文件"）vs SKILL.md replace-mode 定义（current_state/character_matrix 输出 ENTIRE file）
- 根因：参考文档未随 truth 文件集演进；"只追加不修改/增量更新"与 replace-mode 快照文件语义矛盾。
- 验证命令+输出：`ls novel-output/xinghuo-ranqiong/truth/`（13 文件 vs 参考列 10 文件）；`read` truth-files-reference.md 全文。
- 建议方向：补全清单并标注 replace/cumulative 两类模式；"增量更新"改为区分快照文件（全量重写）与累积文件（增量）。

---

## 2. per-file 报告（33/33）

### skills/shenbi-book-spine-init/SKILL.md
- 处置: deep-read（全文 101 行）
- 声称检查的不变量:
  - frontmatter name/description/kind/reads/writes 齐备；description 为纯触发条件 ≤500 字符 ✓
  - DOT 5 步与正文铁律一致（themes 从 novel.json、master hooks 从 volume_map、status pending_intent）✓
  - reads 声明覆盖正文所有数据源 ✗（characters/protagonist.md、world/rules.md 未声明）→ F1011
  - 输出格式与真实产物 book_spine.md 结构一致 ✓（核验 novel-output/xinghuo-ranqiong/truth/book_spine.md 的 frontmatter/核心冲突/themes/主角弧/master hooks/世界铁律六节）
  - 铁律 4"status: pending_intent 是合法初始态…由 memory-distill 合并"——真实产物 ch56 仍 pending_intent + total_chapters: 0（memory-distill 未滚动，属跨 skill 执行问题，本区只记录）
  - HARD-GATE 无重复 ✗ → F1021
- findings: [F1011, F1021]
- 验证命令: `read` 全文；`tail -30 novel-output/xinghuo-ranqiong/truth/book_spine.md`（结构比对）
- 置信度: high

### skills/shenbi-chapter-pattern/SKILL.md
- 处置: deep-read（全文 380 行）
- 声称检查的不变量:
  - description 触发条件 ✓；requires_independent_agent: true ✓
  - DOT 引用 compute_pattern.py 存在 ✓（src/shenbi/skill_utils/chapter_pattern/compute_pattern.py，JSON 输入输出 CLI 确认）
  - 熵计算示例数值正确 ✓（H=2.446 手算复核一致）
  - 熵评级阈值单一权威 ✗（流程节 vs 评级表两套）→ F1012
  - 13 模式与 genre-config chapterTypes 可映射 ✗（8 类 vs 13 类词表不对应）→ F1012
  - 单调性/分布/开篇收束表内部自洽 ✓
  - 输出模板无错字 ✗（"第A-Ⓣ章"）→ F1020
- findings: [F1012, F1020]
- 验证命令: `read` 全文；`python3` 解析 genre-config.json chapterTypes；`grep -n "argparse\|main" src/shenbi/skill_utils/chapter_pattern/compute_pattern.py`
- 置信度: high

### skills/shenbi-chapter-revision/.gitkeep
- 处置: deep-read（存在性 + 0 字节）
- 声称检查的不变量: 0 字节占位 ✓（wc -c = 0）
- findings: 无
- 验证命令: `wc -c skills/shenbi-chapter-revision/.gitkeep` → 0
- 置信度: high

### skills/shenbi-chapter-revision/SKILL.md
- 处置: deep-read（全文 153 行）
- 声称检查的不变量:
  - description 触发条件 ✓；contract reads/writes/updates（含 fields ["1. 当前任务","6. 章尾必须发生的改变","8. 不要做"] 与真实 plans/chapter-N-plan.md 节号一致 ✓）
  - DOT 引用 route_revision/verify_preservation 真实存在 ✓（src/shenbi/skill_utils/revision_routing/route.py:34、preserve_check.py:27）
  - 模式词表单一 ✗（3 模式 vs 6 模式 vs rewrite/rework 三套）→ F1000
  - 委派边界表（style-polishing/anti-detect/length-normalizing）与 revision-modes 路由表一致性——revision-modes 表只路由 spot-fix/rewrite 两值，polish/rework/anti-detect 死模式 ✓(异常归 F1000)
  - decisions.json 产出（chapter-N-revision-decisions.json）与 G4 composite checker 接线 ✓（g4/generic.py chapter-revision 复合 g4_decisions）
- findings: [F1000]
- 验证命令: `read` 全文 + revision-modes.md；`grep -n "def route_revision\|def verify_preservation" src/shenbi/skill_utils/revision_routing/`
- 置信度: high

### skills/shenbi-chapter-revision/revision-modes.md
- 处置: deep-read（全文 67 行）
- 声称检查的不变量:
  - 6 模式表与 SKILL.md 权威词表一致 ✗（polish/rewrite/rework/anti-detect 未在 auto 路由表出现，与 route.py 3 模式冲突）→ F1000
  - auto 路由表覆盖 18 个审计 skill 且与 phase 激活一致——表内 review-character/dialogue/motivation/pov/texture/world-rules/memo-compliance/foreshadowing/pacing 等 9 个已 DEPRECATED（superseded by group-*），路由目标过时 → F1004（证据补充）
  - PATCHES/REVISED_CONTENT 格式与 SKILL.md 一致 ✓；接受条件与 SKILL.md 一致 ✓
- findings: [F1000, F1004]
- 验证命令: `read` 全文；对照 7 个 deprecated SKILL.md 头注释
- 置信度: high

### skills/shenbi-drift-guidance/SKILL.md
- 处置: deep-read（全文 147 行）
- 声称检查的不变量:
  - description 触发条件 ✓；requires_independent_agent ✓
  - 契约 writes/updates 与正文行为一致 ✗（drift_guidance.md 声明但正文未定义；audit_drift.md append_dedup vs 合并重写）→ F1001
  - DOT/执行步骤引用的 `python -m shenbi.skill_utils.drift_detection` 存在 ✓（drift_detection/compute_drift.py main + argparse）
  - 单一写者声明（resonance/arc-payoff/score-arc 仅 append、本 skill 合并）与 review-resonance 输出格式"仅 append 本维度短板条目"一致 ✓；真实 audit_drift.md 头部注明该分工 ✓
  - 滚动窗口 12 章 + 归档逻辑自洽 ✓（正文描述）
  - 累积传导 ≤5 条与输出格式 X/5 一致 ✓
- findings: [F1001]
- 验证命令: `read` 全文；`ls src/shenbi/skill_utils/drift_detection/`；`ls novel-output/xinghuo-ranqiong/truth/ | grep -i drift`（仅 audit_drift.md）
- 置信度: high

### skills/shenbi-faction-builder/SKILL.md
- 处置: deep-read（全文 225 行）
- 声称检查的不变量:
  - description 触发条件 ✓
  - 契约 updates 覆盖全部输出文件 ✗（faction-relations.md 未声明）→ F1008
  - append 语义与 create_or_overwrite 一致 ✗ → F1007
  - 节标题校验（7 节）与 G4 checker 接线 ✓（g4/generic.py "shenbi-faction-builder": g4_faction_builder）
  - 可自动检查规则（锚点≥2 且存在于 characters/*.md、矛盾≥3、预测=4、关系≥2、对称性）——确定性校验候选 ✓（见候选清单）
  - "利益驱动"散文 200-400 字与"内部矛盾≥3"数值规则内部无冲突 ✓
- findings: [F1007, F1008]
- 验证命令: `read` 全文；`grep -n "faction-builder" src/shenbi/gates/g4/generic.py`
- 置信度: high

### skills/shenbi-foreshadowing-recall/SKILL.md
- 处置: deep-read（全文 82 行）
- 声称检查的不变量:
  - DEPRECATED 标记存在 ✓（:14-15），但接线未断 → F1004（deps.json drafting prerequisites + chapter_loop:3048 处理分支）
  - 引用的 recall_overdue_hooks 真实存在 ✓（src/shenbi/skill_utils/foreshadowing_recall/recall.py:31）
  - MVP 声明"确定性全量扫描 + max_distance 阈值过滤"——整个 skill 可确定性替代（高 payoff 候选）✓
  - reads truth/pending_hooks.md 存在 ✓（真实文件确认）
- findings: [F1004]
- 验证命令: `grep -n "def recall_overdue_hooks" src/shenbi/skill_utils/foreshadowing_recall/recall.py`；`grep -n "foreshadowing-recall" tests/tiers/deps.json src/shenbi/pipeline/chapter_loop.py`（python3 提取 prerequisites）
- 置信度: high

### skills/shenbi-foreshadowing-track/SKILL.md
- 处置: deep-read（全文 164 行）
- 声称检查的不变量:
  - DEPRECATED 标记 ✓（:18-19），接线未断 → F1004（deps.json drafting/audit prerequisites、g4/g5/ownership/write_safety/dispatch_helper）
  - 字段分工（last_reinforced/subtlety 归 state-settling）与自身 DOT 冲突 ✗ → F1015
  - reads 字段（活跃伏笔/伏笔时间线/已完成章节）与真实 truth 结构不符 ✗ → F1016
  - lifecycle-states.md 状态机与本 skill 规则一致 ✓（core_hook 禁 ABANDON 双处一致；EXPIRE 仅 TRIGGERED 出发 vs "超过 max_distance 标记 EXPIRED" 的跨状态表述不一致——并入 F1015 备注）
  - Cross-Volume Bridge Tracking 引用的 foreshadowing_ledger.md 不存在 ✗ → F1015
- findings: [F1004, F1015, F1016]
- 验证命令: `read` 全文；`head -16 novel-output/xinghuo-ranqiong/truth/pending_hooks.md`；`find . -name "foreshadowing_ledger.md"`
- 置信度: high

### skills/shenbi-foreshadowing-track/lifecycle-states.md
- 处置: deep-read（全文 43 行）
- 声称检查的不变量:
  - 状态机图与操作表一致 ✓（PLANTED/RELEVANT/TRIGGERED/RESOLVED/ARCHIVED/ABANDONED/EXPIRED 全转换有定义）
  - 与 SKILL.md 铁律（core_hook 禁 ABANDON）一致 ✓
  - EXPIRE 仅从 TRIGGERED 转换 vs SKILL.md"超过 max_distance 的伏笔标记为 EXPIRED"（未限状态）——不一致，归 F1015
  - DEFER"重置 max_distance 倒计时"语义自洽 ✓
- findings: [F1015]
- 验证命令: `read` 全文
- 置信度: high

### skills/shenbi-import-analysis/SKILL.md
- 处置: deep-read（全文 196 行）
- 声称检查的不变量:
  - description 触发条件 ✓；contract reads import/source/*.txt + writes import/analysis/*.md ✓
  - 8 通道串并混合 DOT 与并行策略自洽 ✓（Pass 6 只依赖 Pass 1；Pass 7 依赖 4+5+6——DOT 中 5→7、6→7 与策略"4-6 全部完成"一致）
  - 铁律 4"Pass 6 调用 shenbi-style-learning（纯统计），不调用语言模型"——风格学习确定性委派 ✓
  - 零猜测/输出可追溯铁律与"未确认"标记一致 ✓
- findings: 无
- 验证命令: `read` 全文；`ls src/shenbi/skill_utils/style_learning/`（存在）
- 置信度: high

### skills/shenbi-location-builder/SKILL.md
- 处置: deep-read（全文 193 行）
- 声称检查的不变量:
  - description 触发条件 ✓
  - append 语义 vs create_or_overwrite ✗ → F1007
  - 节标题校验（6 节）与 G4 checker 接线 ✓（g4/generic.py location_builder）
  - 可自动检查规则（感官细节≥5/功能事件≥3/主导感官五选一/距离+单位/时间光色≥2 时段）自洽 ✓（确定性校验候选）
  - 职责边界（worldbuilding 创建初始 3-5 地点、本 skill 追加）与 DOT 一致 ✓
- findings: [F1007]
- 验证命令: `read` 全文；`grep -n "location-builder" src/shenbi/gates/g4/generic.py`
- 置信度: high

### skills/shenbi-pacing-design/SKILL.md
- 处置: deep-read（全文 296 行）
- 声称检查的不变量:
  - description 触发条件 ✓；auto-check invariants 列出 6 项（beat sum/constellation range/eight scene types/four beats/no three consecutive/three lines）✓（但无具体数值 → 与正文多套数值矛盾，归 F1013）
  - 数值约束单信源 ✗（四拍范围 3 套、CONSTELLATION 4 套、场景类型 6-8 vs 8、单调性阈值统一 vs 分类型）→ F1013
  - 职责边界（story-architecture 建骨架、本 skill 细化/创建）与 DOT 一致 ✓
  - 与 chapter-pattern 的委派（单调性检测可自动检测）一致 ✓
- findings: [F1013]
- 验证命令: `read` 全文
- 置信度: high

### skills/shenbi-relationship-map/SKILL.md
- 处置: deep-read（全文 171 行）
- 声称检查的不变量:
  - description 触发条件 ✓
  - append 语义 vs create_or_overwrite（含 character_matrix.md 全量重写风险）✗ → F1007
  - 铁律 4 去重/superseded 语义与契约模式冲突（同 F1007）；"character.md 中仅保留关系摘要指针"隐含对 character 档案的未声明维护（备注，未单列 finding）
  - 信息边界四状态（SYMMETRIC/ASYMMETRIC/ISOLATED/MUTUAL_SECRET）自洽 ✓；去重/对称性为确定性候选 ✓
- findings: [F1007]
- 验证命令: `read` 全文
- 置信度: high

### skills/shenbi-review-character/SKILL.md
- 处置: deep-read（全文 136 行）
- 声称检查的不变量:
  - DEPRECATED 标记 ✓（:19-20）；接线未断 → F1004
  - description 触发条件 ✓（对照 group-character 的违规 description）
  - DOT/检查执行 6 维度与 ooc-dimensions.md 一致 ✓
  - 缺陷证据格式引用完整 ✗（空白引用）→ F1017
  - reads/writes 与契约一致 ✓（audits/chapter-N-character.md）
- findings: [F1004, F1017]
- 验证命令: `read` 全文 + ooc-dimensions.md
- 置信度: high

### skills/shenbi-review-character/ooc-dimensions.md
- 处置: deep-read（全文 34 行）
- 声称检查的不变量: BDI 框架 + 5 检测维度与 SKILL.md 检查执行一一对应 ✓；引用 truth/emotional_arcs.md（契约已声明）✓
- findings: 无
- 验证命令: `read` 全文
- 置信度: high

### skills/shenbi-review-era/SKILL.md
- 处置: deep-read（全文 154 行）
- 声称检查的不变量:
  - description 触发条件 ✓；requires_independent_agent ✓
  - 激活条件（eraResearch/eraConstraints）与真实 genre-config 不符 ✗ → F1006
  - reads era-reference.md 解析（skill 目录内相对路径）✓
  - 铁律 5 exempt 逻辑与正文判定一致 ✓
  - era-reference.md 引用的 world/rules.md、world/locations.md 未在契约 reads 声明（架空审计需查）→ F1006（备注）
- findings: [F1006]
- 验证命令: `read` 全文；`python3` 检查 genre-config eraResearch/eraConstraints（False）
- 置信度: high

### skills/shenbi-review-era/era-reference.md
- 处置: deep-read（全文 109 行）
- 声称检查的不变量:
  - 判定方法与 SKILL.md 检查执行一致 ✓（词汇/器物/地点/制度）
  - 高风险元素时间表（咖啡明末/辣椒明末/内阁明/军机处清/紫禁城明）与 SKILL.md 示例一致 ✓
  - 架空类型审计要点与 SKILL.md 铁律 4 一致 ✓
  - 扩展建议（western-medieval.md 等）为可选项 ✓
- findings: 无
- 验证命令: `read` 全文
- 置信度: high

### skills/shenbi-review-group-character/SKILL.md
- 处置: deep-read（全文 314 行）
- 声称检查的不变量:
  - description 纯触发条件 ✗（描述实现 + parallel_dispatch.py）→ F1009
  - 内嵌 Contract 块与 frontmatter 一致 ✗（writes/updates 互换）→ F1010
  - 四维度各自 supersedes 声明与 7 个 deprecated skill 对应 ✓（character/dialogue/motivation/pov）
  - Dispatch note 引用的 chapter_loop.py:1090-1168 与 parallel_dispatch.py——核验 chapter_loop.py:199-212（group-character 为步骤 10）存在；parallel_dispatch.py 存在 ✓
  - 四维度输出文件与契约 writes 一致 ✓（character/dialogue/motivation/pov 四个 audits 文件）
- findings: [F1009, F1010]
- 验证命令: `read` 全文；`sed -n '199,212p' src/shenbi/pipeline/chapter_loop.py`
- 置信度: high

### skills/shenbi-review-group-plan/SKILL.md
- 处置: deep-read（全文 194 行）
- 声称检查的不变量:
  - description 纯触发条件 ✗ → F1009
  - 内嵌 Contract 块与 frontmatter 一致 ✗ → F1010
  - 维度 1 激活条件"auditDimensions 包括 dimension 33"与真实 schema 不符 ✗ → F1006
  - 两维度 supersedes 声明与 deprecated memo-compliance/foreshadowing 对应 ✓
  - 输出文件与契约 writes 一致 ✓（memo-compliance/foreshadowing 两个 audits 文件）
- findings: [F1009, F1010, F1006]
- 验证命令: `read` 全文
- 置信度: high

### skills/shenbi-review-memo-compliance/SKILL.md
- 处置: deep-read（全文 150 行）
- 声称检查的不变量:
  - DEPRECATED 标记 ✓（:17-18）；接线未断 → F1004（deps.json audit prerequisites、T1 全套件、T2 seed、using-shenbi 路由）
  - 激活条件"维度 33"与真实 schema 不符 ✗ → F1006
  - 备忘 8 段引用（第 1/3/6/7/8 段）与真实 plans/chapter-N-plan.md 节号一致 ✓（chapter-56-plan.md "## 1. 当前任务" 等确认）
- findings: [F1004, F1006]
- 验证命令: `read` 全文；`head -30 novel-output/xinghuo-ranqiong/plans/chapter-56-plan.md`
- 置信度: high

### skills/shenbi-review-pacing/SKILL.md
- 处置: deep-read（全文 134 行）
- 声称检查的不变量:
  - DEPRECATED 标记 ✓（:22-23）；接线未断 → F1004（deps.json audit prerequisites、T2 seed）
  - 激活条件"维度 7 或 26"与真实 schema 不符 ✗ → F1006
  - 缺陷证据格式引用 skills/_shared/REVIEW_EVIDENCE.md 不存在 ✗ → F1017
  - reads 字段（genre-config pacing/chapterTypes、chapter_summaries 已完成章节）——chapterTypes 真实存在 ✓；"已完成章节"字段不存在（同 F1016 模式，deprecated skill 未单列）
- findings: [F1004, F1006, F1017]
- 验证命令: `read` 全文；`ls skills/_shared/`（不存在）
- 置信度: high

### skills/shenbi-review-resonance/SKILL.md
- 处置: deep-read（全文 232 行）
- 声称检查的不变量:
  - description 触发条件 + "runs in an independent agent"（实现细节尾注，M 级备注，未单列）
  - 硬门/HARD-GATE（缺完成稿不评分、独立 agent）与 requires_independent_agent ✓
  - 铁律 3"先确定性"引用的 review_resonance/calibration CLI 参数与实现一致 ✓（routing.py --overall/--threshold/--confidence/--prior-revisions/--floor；calibration --reported/--high-confidence/--threshold）
  - reads 字段 style_profile.md [11/6] 与真实章节号不符 ✗ → F1005
  - 校准门阈值表（高潮≥75/推进≥65/过渡≥50 + 子地板）与 §5.4 分流表自洽 ✓
  - Route A 锚点 AC-001/002/004/005 存在且主题匹配 ✓（benchmarks/anchors/ 11 个锚点，AC-001 诡秘·小丑消化、AC-004 炮火·燃烧的原野、AC-005 炮火·我炮多）
  - Route C 硬二元触发"重生路由（§5.2 revision_routing）"——revision_routing 存在 ✓
  - 输出格式列名（裸"证据"）与 g4_review_resonance 校验列一致 ✓（review_resonance.py _DETAIL_COLS）
  - "spec §5.x/§8.x/§9"引用无命名文档 ✗ → F1018
- findings: [F1005, F1018]
- 验证命令: `read` 全文；`grep -n "add_argument" src/shenbi/skill_utils/review_resonance/routing.py src/shenbi/skill_utils/calibration/confidence.py`；`head -6 benchmarks/anchors/AC-00{1..6}.md`
- 置信度: high

### skills/shenbi-review-texture/SKILL.md
- 处置: deep-read（全文 167 行）
- 声称检查的不变量:
  - DEPRECATED 标记 ✓（:17-18）；接线未断 → F1004（deps.json audit prerequisites、audit_layer "texture" 键）
  - 激活条件"维度 17"与真实 schema 不符 ✗ → F1006
  - 段长阈值内部自洽（>500 warning / >800 error；<20 连续 3 段碎片化；极差 >20x）✓
  - 与 pacing/anti-ai 的区别声明一致 ✓
- findings: [F1004, F1006]
- 验证命令: `read` 全文
- 置信度: high

### skills/shenbi-review-world-rules/SKILL.md
- 处置: deep-read（全文 157 行）
- 声称检查的不变量:
  - DEPRECATED 标记 ✓（:21-22）；接线未断 → F1004（deps.json audit prerequisites、audit_layer "worldRules" 键）
  - 激活条件"维度 3、4、5 或 18"与真实 schema 不符 ✗ → F1006
  - reads 6 文件（world/rules、power_system、locations、story_bible、chapter_summaries、current_state）均真实存在 ✓
  - 检查执行 4 维度与铁律对应 ✓
- findings: [F1004, F1006]
- 验证命令: `read` 全文；`ls novel-output/xinghuo-ranqiong/world/`
- 置信度: high

### skills/shenbi-score-volume/SKILL.md
- 处置: deep-read（全文 124 行）
- 声称检查的不变量:
  - description 触发条件（"Use when scoring 卷级评分…"）✓
  - auto-check constants/formula/computed fields（PASS_THRESHOLD 90、权重 0.4/0.6、TIER 94）自洽 ✓
  - 铁律 3"book_spine.md (L5)"行号过期 ✗ → F1019
  - Route A 锚点 AC-003/AC-006 存在且主题匹配（规模管理/群像调度）✓
  - 契约 reads（volume_summaries/volume_map/book_spine/benchmarks-anchors）——volume_summaries.md 在 ch56 项目未产生（卷边界产物，设计内）；volume_score_trend.md append_dedup key "chapter"（卷级文件按 chapter 键，命名不一致，M 级备注并入 F1019）
  - G4 checker 接线 ✓（g4/generic.py score_volume）
- findings: [F1019]
- 验证命令: `read` 全文；`head -6 benchmarks/anchors/AC-003.md benchmarks/anchors/AC-006.md`；`ls novel-output/xinghuo-ranqiong/truth/volume_summaries.md`（不存在）
- 置信度: high

### skills/shenbi-short-outline/SKILL.md
- 处置: deep-read（全文 206 行）
- 声称检查的不变量:
  - description 触发条件 ✓；contract reads/writes 一致 ✓
  - 三步流程（生成→复核→修订）DOT 与正文一致 ✓
  - 三幕占比（20/60/20）与 30 章范围自洽 ✓；章节数 ≤30 铁律与短篇特征一致 ✓
  - 下游任务（short-drafting）存在 ✓（skills/shenbi-short-drafting）
- findings: 无
- 验证命令: `read` 全文
- 置信度: high

### skills/shenbi-state-settling/.gitkeep
- 处置: deep-read（存在性 + 0 字节）
- 声称检查的不变量: 0 字节占位 ✓（wc -c = 0）
- findings: 无
- 验证命令: `wc -c`
- 置信度: high

### skills/shenbi-state-settling/SKILL.md
- 处置: deep-read（全文 288 行）
- 声称检查的不变量:
  - description 触发条件 ✓
  - 更新模式三处一致 ✗（frontmatter append_dedup vs 更新规则表 replace vs CRITICAL 节缺失）→ F1003
  - reads/updates 覆盖全部操作对象 ✗（character_matrix.md 未读、protagonist.md 未声明写）→ F1002
  - 铁律 4"增量更新—不重写整个文件"与 replace-mode 定义冲突 → F1003
  - pending_hooks 字段分工与真实文件 filled_by 注释一致 ✓（真实 pending_hooks.md 注明 state-settling 只更新 last_reinforced/subtlety、track 管生命周期）
  - 9 类变化提取模板与 truth-files-reference 9 类一致 ✓
  - 跨文件一致性验证表（current_state vs character_matrix 等字段）——确定性候选 ✓
- findings: [F1002, F1003]
- 验证命令: `read` 全文；`head -16 novel-output/xinghuo-ranqiong/truth/pending_hooks.md`（filled_by/分工注释确认）
- 置信度: high

### skills/shenbi-state-settling/truth-files-reference.md
- 处置: deep-read（全文 35 行）
- 声称检查的不变量:
  - 文件清单覆盖全部 truth 文件 ✗（遗漏 9 个）→ F1022
  - 更新原则与 replace/cumulative 两类模式区分 ✗（"只追加不修改/增量更新"与快照重写冲突）→ F1022
  - 9 类事实变化与 SKILL.md 一致 ✓
- findings: [F1022]
- 验证命令: `read` 全文；`ls novel-output/xinghuo-ranqiong/truth/`
- 置信度: high

### skills/shenbi-volume-outlining/SKILL.md
- 处置: deep-read（全文 294 行）
- 声称检查的不变量:
  - description 触发条件 ✓；auto-check invariants（entity hooks/kr count/tension sum）✓
  - 铺垫段占比/跨卷钩子数内部一致 ✗ → F1014
  - append 语义 vs create_or_overwrite ✗ → F1007
  - KR 数量 3-5、节点角色枚举、张力四段 100% 等可自动检查规则自洽 ✓（除 F1014 冲突项）
  - 职责边界（volume_map 骨架由 story-architecture 创建；缺失则报错）与正文一致 ✓
  - G4 checker 接线 ✓（g4/generic.py volume_outlining）
- findings: [F1007, F1014]
- 验证命令: `read` 全文；`grep -n "volume-outlining" src/shenbi/gates/g4/generic.py`
- 置信度: high

### skills/shenbi-writing-skills/.gitkeep
- 处置: deep-read（存在性 + 0 字节）
- 声称检查的不变量: 0 字节占位 ✓（wc -c = 0）
- findings: 无
- 验证命令: `wc -c`
- 置信度: high

### skills/shenbi-writing-skills/SKILL.md
- 处置: deep-read（全文 140 行）
- 声称检查的不变量:
  - meta: true 无 contract（meta skill，deps.json `_out_of_pipeline.t1_only_meta` 含 shenbi-writing-skills ✓）
  - description 触发条件（"Use when creating or modifying any shenbi skill"）✓
  - 自身遵循其 frontmatter 规则（name 小写 kebab / description 触发式 / ≤500 字符）✓
  - 消歧括号例外说明（description 可含边界消歧）与 AGENTS.md 一致 ✓
  - DOT/铁律/反理性化/红旗检查表元素齐备 ✓
- findings: 无
- 验证命令: `read` 全文；`python3` 读 deps.json _out_of_pipeline.t1_only_meta
- 置信度: high

---

## 3. 确定性替换候选清单（交 T14 评估）

按"是否存在可被 Python 确定性替代的环节"逐 skill 判定（高=可消除整次 dispatch；中=替代 LLM 内部子步骤；低=仅校验层）：

| # | skill | 候选环节 | payoff 评估 | 已有确定性先例 |
|---|-------|---------|------------|--------------|
| C1 | shenbi-foreshadowing-recall | **整个 skill**：recall_overdue_hooks 纯数值比较（max_distance/沉默章数），MVP 自述"确定性全量扫描"；LLM 包装仅格式化输出 | **高**——消除每次 recall dispatch（chapter_loop 现有分支可直接调 helper） | skill_utils/foreshadowing_recall/recall.py |
| C2 | shenbi-book-spine-init | 字段复制：story_frame.md frontmatter 三冲突、novel.json themes、volume_map 跨卷钩子、world/rules.md 前 5 条、frontmatter 元数据（updated/total_chapters/status）——全部"声明值继承"，无需 LLM 判断 | **中-高**——大部分写入是确定性复制；仅 arc_starting/arc_turning 需定位字段 | 输出格式模板本身即字段映射 |
| C3 | shenbi-chapter-pattern | 分类后的熵/分布/连续/转移矩阵计算（已由 compute_pattern.py 承接）；分类本身可用 13 模式模板 + chapter_summaries 关键词半自动 | **中**——分析层已确定性；分类层可部分替代 | skill_utils/chapter_pattern/compute_pattern.py |
| C4 | shenbi-state-settling | 跨文件一致性验证表（current_state vs character_matrix vs particle_ledger 等字段比对）；pending_hooks last_reinforced 更新（文本出现判定可 NLP 化） | **中**——一致性验证纯比对；9 类提取仍 LLM | write_truth_file 去重/合并已确定性 |
| C5 | shenbi-faction-builder / shenbi-location-builder | 计数/枚举/节标题/对称性检查（锚点≥2、矛盾≥3、预测=4、感官≥5、事件≥3、关系对称、七列非空）——SKILL.md 自述"可被 G4 检查器自动拒绝/可自动检测" | **中**——校验层已 G4；设计层 LLM | g4/faction_builder.py、g4/location_builder.py |
| C6 | shenbi-relationship-map | 关系对去重/superseded 合并（(A,B,type) 键）、信息边界对称性 | **中**——去重合并纯数据操作 | 无（需新建） |
| C7 | shenbi-pacing-design / shenbi-volume-outlining | 全部"可自动检查规则"：beat sum=100、四拍范围、KR 3-5、节点角色枚举、钩子≥3、8 场景类型、张力 100% | **中**——校验层（auto-check invariants 已声明）；设计层 LLM | g4/pacing_design.py、g4/volume_outlining.py |
| C8 | shenbi-drift-guidance | drift_detection 计算（逐章 3 点平滑/均值-2σ/卷级趋势）已 Python；12 章滚动窗口合并+归档是纯文件操作 | **中**——计算层已确定性；传导指导合成需 LLM | skill_utils/drift_detection/ |
| C9 | shenbi-score-volume | final_score 公式（0.6×route_c + 0.4×route_a）、硬二元门、PASS_THRESHOLD=90 判定 | **中**——评分公式层已确定性（auto-check constants）；锚点定位需 LLM | g4/score_volume.py |
| C10 | shenbi-review-resonance | 校准门阈值/置信度降级/§5.4 三路分流（--overall/--threshold/--floor 等）已 Python；resonance_trend 行格式化 | **低-中**——辅助层已确定性；4 维评分需 LLM | skill_utils/review_resonance/routing.py、calibration/ |
| C11 | shenbi-import-analysis | Pass 1 解析（章节切分/字数统计）、汇总关键统计、Pass 6 风格（已委派 style-learning 纯统计） | **中**——解析/统计层确定性；识别类 Pass 需 LLM | skill_utils/style_learning/ |
| C12 | shenbi-foreshadowing-track（已弃用） | 培育间隔/超期/密度预算数值检查（current_chapter - last_reinforced > cultivation_interval 等） | **中**（若随弃用退役则取消） | 无 |

**总体判断**：C1 为最高 payoff（整次 dispatch 可消除）；C2 次之（创世层高频单次调用，大部分写入为声明值复制）；其余为"已确定性/校验层"的固化与补全。

## 4. 覆盖统计

- deep-read 文件数：**33 / 33**（25 个 SKILL.md + 5 个目录内参考文档 + 3 个 .gitkeep）
- 未覆盖文件：**0**
- findings：**23**（P1 × 6、P2 × 14、M × 3）
  - P1：F1001（drift-guidance 契约/正文/pipeline 三向矛盾）、F1002（state-settling 未声明 reads/writes）、F1003（state-settling 更新模式三处矛盾）、F1004（deprecated skill 全链接线未断）、F1009（group-* description 违规）、F1011（book-spine-init reads 漂移）
  - P2：F1000/F1005/F1006/F1007/F1008/F1010/F1012/F1013/F1014/F1015/F1016/F1017/F1018/F1022
  - M：F1019/F1020/F1021
- 低置信度文件：无（全部 high；未运行任何写命令，全部断言基于 read/grep/只读 python 输出）

## 5. 未覆盖文件列表

（空）
