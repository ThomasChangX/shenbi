# Zone Z8-a 审查报告（2026-08-15 轮）

- **范围**: `docs/superpowers/audit-runs/2026-08-15/zones/Z8-a.files`（skills/ 字母序前 1/3，33 个文件）
- **方法**: 逐文件语义深读 + 与 `docs/framework/truth-files.yaml`、`docs/framework/decisions-schema.md`、`skills/using-shenbi/SKILL.md`、真实 fixtures、`src/shenbi/` 辅助脚本交叉验证
- **findings 编号段**: F801–F823（23 条；清单文件无独立缺陷者不占号）
- **对照基线**: 2026-08-14 轮 findings（F900–F969 族）。本轮验证结论：**2026-08-14 设计文档（`docs/superpowers/specs/2026-08-14-z8-contract-drift-design.md`，状态 Design）中的 R1–R5 修复均未落地**——其列出的 Z8-a 侧 finding 在当前文件中全部复现，仅 F906（genre-config 字段级 reads 漂移）因 reads 改为非 dict 形式而失效、F911（chapter-planning 字段漂移）部分失效（字段已在真实 fixture 中存在）。

## findings 总表

| # | skill/文件 | 标题 | 严重度 |
|---|---|---|---|
| F801 | anchor-curate | 缺 anti-rationalization 表 + spec §4.3 引用仅存于归档 plan | P2 |
| F802 | anti-detect | 触发输入（anti-ai 审计报告）未入 reads；DOT 与铁律 3（sensitivity 复审）不一致；汇总模板无文件去向 | P2 |
| F803 | book-spine-init | reads 未声明 DOT/输出格式必需的 characters/protagonist.md 与 world/rules.md | P1 |
| F804 | 5 个 .gitkeep | 零字节占位文件在目录已有 SKILL.md 后冗余 | M |
| F805 | chapter-drafting | style_profile 字段号漂移（11/6/9 vs 实际 8/5，无对白占比）；novel.json 未入 reads；decisions sidecar 写声明无正文指令 | P2 |
| F806 | chapter-pattern | 熵评级阈值两处矛盾；13 模式词表与 genre-config chapterTypes 不匹配；Ⓣ 误用；kind:report vs outline 写 | P2 |
| F807 | chapter-planning | 黄金三章依赖 novel.json 未入 reads；plan-decisions.json 契约断链 | P2 |
| F808 | chapter-revision | 修订模式词表三处矛盾（3 模式 vs 6 模式 vs DOT rewrite/rework）；decisions sidecar 无正文指令 | P2 |
| F809 | character-design | IRON LAW 引用词表外文件 outline/chapter_outline.md、outline/three_act.md；expand 模式 characters/**/*.md 未声明 reads | P1 |
| F810 | character-extraction | 缺陷证据格式节与本 skill 职责无关；DOT "relationship_map" 命名漂移 | P2 |
| F811 | context-composing | 主产物 context/chapter-N-context.md 写未声明；近章结尾检查所需 chapter-(N-3..N-1).md 未入 reads（reads 中的 chapter-N.md 组装时尚不存在）；volume_summaries 字段漂移 | P1 |
| F812 | drift-guidance | 契约写 truth/drift_guidance.md 但正文零定义；audit_drift_archive.md 写未声明 | P1 |
| F813 | escalation-review | 缺 anti-rationalization 表；escalation_check 命名与实际 helper（run_escalation_check/check_escalation）漂移 | P2 |
| F814 | faction-builder | 正文输出词表已显式废弃的 world/faction-relations.md 且写未声明；append 语义 vs create_or_overwrite 模式错配 | P1 |
| F815 | foreshadowing-lifecycle | description 非触发式（违 AGENTS.md）；lifecycle-states.md/hook-types.md 相对引用落在他 skill 目录；Phase3 初始态 ACTIVE 与自身输出示例 PLANTED 矛盾；bridge_tracker.md 与 audits 输出写未声明 | P1 |
| F816 | foreshadowing-plant | DEPRECATED 但 using-shenbi 触发表与 deps.json 仍路由/注册本 skill（lifecycle 未进触发表） | P1 |
| F817 | foreshadowing-recall | DEPRECATED 仍注册于 deps.json；"last_reinformed" 拼写漂移 | P2 |
| F818 | foreshadowing-resolve | Chase Power 参数/阈值三套体系互相矛盾（auto-check constants vs 正文区间表 vs chase-power.md） | P1 |
| F819 | foreshadowing-track | DEPRECATED 仍注册；字段分工与 DOT 矛盾；foreshadowing_ledger.md 死引用 | P2 |
| F820 | lifecycle-states.md | 状态机缺 DORMANT/ACTIVE 态（lifecycle skill Phase 1–3 使用） | P2 |
| F821 | foundation-review | reads 缺 genre-config.json（tropeInventory 评分必需）与 truth/book_spine.md（前置验证必需）；重复"## 输出格式"节 | P1 |
| F822 | genre-config | 备份文件名两处不一致（.bak vs .bak.YYYYMMDD）；audit_drift 冲突检查依赖未声明 read | P2 |
| F823 | import-analysis | 词表概念 import/analysis/01_overview.md 与实际输出 01_parse.md 命名漂移（概念无生产者无消费者） | P2 |

---

## per-file 报告

### skills/shenbi-anchor-curate/SKILL.md
- 处置: deep-read
- 声称检查的不变量: [description 触发条件性、reads/writes 词表一致性（import/source/*.txt、benchmarks/anchors/AC-NNN.md）、DOT 与正文一致、参照文件 AC-001.md 存在、有决策分支的 skill 应有 anti-rationalization 表]
- findings:
  - **F801** | anchor-curate 缺 anti-rationalization 表且 spec 引用悬空 | error | P2 | 证据: `skills/shenbi-anchor-curate/SKILL.md:1-55`（全文无 Anti-Rationalization 节；line 48 引用 "spec §4.3 的 9 类"） | 根因: 与 review 类 skill 共用的模板未回填；"spec §4.3" 实际定义在归档 plan `docs/superpowers/plans/archive/2026-06-28-hierarchical-system-wave3-scoring.md:16`（"§4.3 锚点库（9 类槽位）"），正文未命名文档 | 验证: `grep -c "Anti-Rationalization" skills/shenbi-anchor-curate/SKILL.md` → 0；`grep -rn "4.3 锚点\|锚点库" docs/superpowers/plans/archive/2026-06-28-hierarchical-system-wave3-scoring.md` → 命中 line 16 | 方向: 补 anti-rationalization 表（工艺分析 vs 原文复制、模糊区间等借口）；spec 引用改为命名文档路径。注: 2026-08-14 轮 F923（M）未修。
- 验证命令: 见上；另 `ls benchmarks/anchors/` → AC-001.md…AC-005.md 存在（SKILL.md:54 引用 AC-001.md 有效）；`head -8 benchmarks/anchors/AC-001.md` → frontmatter 含 id/category/source_work/source_ref/calibrates，与输出格式描述一致。
- 置信度: high

### skills/shenbi-anti-detect/SKILL.md
- 处置: deep-read
- 声称检查的不变量: [description 触发条件性、updates merge_prose 与输出模板一致、DOT 与铁律一致、reads 声明覆盖正文实际依赖]
- findings:
  - **F802** | anti-detect 触发输入未入 reads + DOT 漏 sensitivity 复审 + 汇总模板无写目标 | error | P2 | 证据: `skills/shenbi-anti-detect/SKILL.md:8-11`（reads 仅 chapters/chapter-N.md + genre-config.json）；`:3-6`（description 说 "anti-AI audit flags a chapter" 即触发输入为审计报告，但 audits/chapter-N-anti-ai.md 未入 reads）；`:44-49`（DOT "Re-run anti-AI audit" 单边循环）vs `:57`（铁律 3 "anti-ai + sensitivity 两个审计必须重新通过"）；`:81`（Anti-Rat 表 "3 次后未通过 = 回退"——DOT 无该分支）；`:104-146`（"## 反检测改写汇总" 模板未声明写入目标，且 `src/shenbi/gates/shared.py:110-114` strip 列表只含 润色说明/改写报告/归一化报告，无此标题——若追加进章节文件将计入正文字数）| 根因: 2026-08-14 F960 只修了一半（genre-config 入了 reads 但正文依旧零使用，审计报告仍缺） | 验证: `grep -n "audit" skills/shenbi-anti-detect/SKILL.md | head` → 无 audits/ 路径；`sed -n '108,116p' src/shenbi/gates/shared.py` → strip 标签列表无"反检测改写汇总" | 方向: reads 补 audits/chapter-N-anti-ai.md（触发输入）；DOT 补 sensitivity 复审与 3 次上限/回退分支；汇总模板明确去向（human 消息）或并入 strip 列表。
- 验证命令: `grep -rn "genre-config" skills/shenbi-anti-detect/SKILL.md` → 仅 frontmatter + AUTO-GENERATED 两处，正文 0 使用（token 浪费面）。
- 置信度: high

### skills/shenbi-book-spine-init/SKILL.md
- 处置: deep-read
- 声称检查的不变量: [reads 覆盖 DOT/输出格式全部输入、truth/book_spine.md 词表一致、输出格式字段与生产者契约一致]
- findings:
  - **F803** | book-spine-init reads 未声明 protagonist/world/rules 输入 | error | P1 | 证据: `skills/shenbi-book-spine-init/SKILL.md:7-14`（reads 仅 story_frame/volume_map/novel.json）；`:45`（DOT "Extract: protagonist arc from character files"）；`:79-84`（输出格式 "主角弧…从 characters/protagonist.md 继承"）；`:90-92`（"世界铁律滚动快照（从 world/rules.md 同步前5条）"）——dispatcher 字段过滤策略下未声明 reads 拿不到文件内容，书脊的主角弧/世界铁律两节无法填充 | 根因: 2026-08-14 F1011（P2）未修 | 验证: `grep -n "protagonist\|rules.md" skills/shenbi-book-spine-init/SKILL.md` → 正文 4 处引用，frontmatter 0 声明 | 方向: reads 补 `file: characters/protagonist.md, fields: [arc_type, arc_starting, arc_turning, arc_ending]` 与 `file: world/rules.md`。
  - 附注（M，未占号）: `:34` HARD-GATE 语句重复（"（worldbuilding + …）完成后、逐章循环开始前执行。"出现两次，2026-08-14 F1021 未修）；`:80` arc_type 合法值列 GROWTH/REDEMPTION/FALL，character-design（`:67`）定义四值含 FLAT——示例漏值。
- 验证命令: `grep -n "characters/\|world/rules" skills/shenbi-book-spine-init/SKILL.md`；`grep -n "arc_type" skills/shenbi-character-design/SKILL.md` → "GROWTH | FALL | FLAT | REDEMPTION"。
- 置信度: high

### skills/shenbi-canon-import/SKILL.md
- 处置: deep-read
- 声称检查的不变量: [description 触发条件性、reads source_canon/* 与 writes import/canon/*.md 词表一致、DOT 5-SECTION 流程与正文一致、anti-rationalization 表存在]
- findings: 无（description 为触发式；词表 `source_canon/*`、`import/canon/*.md` 均在 truth-files.yaml globs；DOT 10 步与 5 SECTION + 模式过滤正文一致；有 Anti-Rationalization 表 `:204-211`；using-shenbi `:80` "原作导入" 路由一致）
- 验证命令: `grep -n "source_canon\|import/canon" docs/framework/truth-files.yaml` → `:89-90, :141-142` 均有登记；`grep -n "canon-import" skills/using-shenbi/SKILL.md` → `:80`。
- 置信度: high

### skills/shenbi-chapter-drafting/.gitkeep
- 处置: deep-read（占位文件核验）
- 声称检查的不变量: [占位文件不掩盖实际内容]
- findings:
  - **F804**（合并，覆盖清单中全部 5 个 .gitkeep: chapter-drafting/chapter-planning/chapter-revision/character-design/context-composing）| 目录已有 SKILL.md 后 .gitkeep 冗余 | error | M | 证据: `wc -c skills/shenbi-chapter-drafting/.gitkeep skills/shenbi-chapter-planning/.gitkeep skills/shenbi-chapter-revision/.gitkeep skills/shenbi-character-design/.gitkeep skills/shenbi-context-composing/.gitkeep` → 全部 0 字节，且各目录均有 SKILL.md | 根因: 建目录占位后未清理（2026-08-14 F968 提到 3 个，本轮实为 5 个） | 验证: `ls -la skills/shenbi-chapter-drafting/` 等 → .gitkeep 0 字节 | 方向: 删除 5 个 .gitkeep。
- 验证命令: `file skills/*/.gitkeep` → empty。
- 置信度: high

### skills/shenbi-chapter-drafting/SKILL.md
- 处置: deep-read
- 声称检查的不变量: [plan 字段级 reads 与 chapter-planning 输出段标题一致、style/genre 字段与生产者实况一致、DOT 与铁律一致、decisions sidecar 声明与 P2.5 规则描述]
- findings:
  - **F805** | chapter-drafting 三项字段/声明漂移 | error | P2 | 证据: ① `skills/shenbi-chapter-drafting/SKILL.md:16-20`（style_profile 字段声明 "11. 综合画像 / 6. 修辞模式 / 9. 对白占比"）vs 实际生产者 `skills/shenbi-style-learning/SKILL.md:172-243` 输出仅 8 节（"5. 修辞模式"、"8. 综合画像"，无"对白占比"）→ 每次 dispatch 触发 field_filter_no_match WARN + 全量 escape hatch（token 浪费）。② `:86` 铁律 6 引用 anti-ai-reference.md，其 `:46` "N = novel.json.golden_opening_chapters" 依赖 novel.json，但 frontmatter reads 无 novel.json（2026-08-14 F952/F968 未修）。③ `:30-31` writes 声明 chapters/chapter-N-decisions.json，正文（50-160 行）零 decisions.json 指令——schema 引用（shenbi-decisions-v1）与 P2.5 规则均未描述（F969 未修） | 验证: `grep -n "^## " skills/shenbi-style-learning/SKILL.md | grep 综合画像` → `## 8. 综合画像`；`grep -c "decisions" skills/shenbi-chapter-drafting/SKILL.md` → 仅 frontmatter/AUTO-GENERATED 4 处，正文 0 | 方向: 字段改 8. 综合画像 / 5. 修辞模式（或让 style-learning 增补对白占比节）；reads 补 novel.json [golden_opening_chapters]；正文补 decisions sidecar 输出指令（selections=plan beats/foreshadowing，adjustments=pacing deviations/opening，参照 docs/framework/decisions-schema.md:98）。
  - 通过项: plan 字段 "1. 当前任务 / 3. 该兑现的 / 暂不掀的 / 6. 章尾必须发生的改变 / 8. 不要做" 与 chapter-planning 段标题（`skills/shenbi-chapter-planning/SKILL.md:144-151`）逐字一致 ✓；genre-config 字段 fatigueWords/pacing/chapterTypes 均在 genre-config 字段规范表（`skills/shenbi-genre-config/SKILL.md:270-284`）✓；`src/shenbi/gates/shared.py:120-121` META strip 引用真实存在 ✓；`docs/framework/chapter-file-format.md` 存在 ✓。
- 验证命令: 见上；另 `grep -n "转折词" skills/shenbi-chapter-drafting/SKILL.md skills/shenbi-chapter-drafting/anti-ai-reference.md` → 两处 1/3000 + 六词列表一致 ✓。
- 置信度: high

### skills/shenbi-chapter-drafting/anti-ai-reference.md
- 处置: deep-read
- 声称检查的不变量: [与 chapter-drafting 铁律数值一致、引用键存在]
- findings: 无（转折词 1/3000 与六词列表、了字 ≥6 句警告、标记词 ≤1/章 与 SKILL.md 铁律 5/DOT 一致；novel.json.golden_opening_chapters 引用问题归入 F805②）
- 验证命令: `grep -n "3000\|然而" skills/shenbi-chapter-drafting/anti-ai-reference.md skills/shenbi-chapter-drafting/SKILL.md` → 两文件数值/词表一致；`grep -n "golden_opening_chapters" src/shenbi/contracts/schemas/novel.py` → `:25` 存在（但类型为 `str = ""`，与 seed_parser.py:131 写入 int 3 类型不一致——框架侧问题，记录供 Z 系 src 段参考）。
- 置信度: high

### skills/shenbi-chapter-pattern/SKILL.md
- 处置: deep-read
- 声称检查的不变量: [requires_independent_agent 与产出性质一致、DOT 与 compute_pattern.py 分工一致、阈值内部一致、kind 与 writes 匹配]
- findings:
  - **F806** | chapter-pattern 熵阈值内部矛盾 + 词表/格式四项缺陷 | error | P2 | 证据: ① `skills/shenbi-chapter-pattern/SKILL.md:106-109`（"熵 > 2.0 健康；1.5-2.0 轻度单调；< 1.5 严重单调"）vs `:328-336` 熵评级阈值表（"2.0<H≤2.5 健康；1.5<H≤2.0 轻度；1.0<H≤1.5 中度；H≤1.0 严重"）——同一 skill 两套阈值，"< 1.5 严重" 与 "1.0-1.5 中度" 矛盾（2026-08-14 F1012 未修）。② 铁律 3 `:56` "连续 N 章同模式 ≥ genre-config 中定义必须报警"，但本 skill 13 模式（引入/升级/转折…）与 genre-config chapterTypes 词表（battle/dialogue 等 6-10 类，`skills/shenbi-genre-config/SKILL.md:92-95,281`）不匹配，无法对应。③ `:359` "第A-Ⓣ章" 全角圈号误用（F1020 未修）。④ frontmatter `kind: report` 但 writes 是 outline/chapter_patterns.md（truth-files.yaml:27 kind: outline；OutputKind 语义见 `src/shenbi/contracts/models.py:40-42` "report = emits a persisted report"） | 验证: `grep -n "严重单调\|中度单调" skills/shenbi-chapter-pattern/SKILL.md` → 两套定义；`grep -n "chapterTypes" skills/shenbi-genre-config/SKILL.md` → battle/dialogue 词表 | 方向: 裁决单一阈值表（建议保留五档表并同步 106-109）；13 模式与 chapterTypes 建立映射或声明两词表用途差异；修 Ⓣ；kind 改 artifact 或将报告写入 audits/。
  - 通过项: DOT（`:41-47`）与 compute_pattern.py 分工（LLM 分类 + 脚本统计）描述一致，`src/shenbi/skill_utils/chapter_pattern/compute_pattern.py` 存在 ✓；熵示例计算 2.446 复算无误 ✓。
- 验证命令: `ls src/shenbi/skill_utils/chapter_pattern/compute_pattern.py`；熵示例手算：0.3·log₂0.3+2·0.2·log₂0.2+3·0.1·log₂0.1 = -2.447 ✓。
- 置信度: high

### skills/shenbi-chapter-planning/.gitkeep
- 处置: deep-read（占位文件核验）——见 **F804**（合并）
- findings: [F804]
- 验证命令: `wc -c skills/shenbi-chapter-planning/.gitkeep` → 0
- 置信度: high

### skills/shenbi-chapter-planning/SKILL.md
- 处置: deep-read
- 声称检查的不变量: [8 段式输出与消费方（drafting/revision/context-composing）字段级 reads 一致、truth 字段与真实 fixture 一致、auto-check invariants 与可自动检查规则一致、decisions 契约链]
- findings:
  - **F807** | chapter-planning 两项契约断链 | error | P2 | 证据: ① `skills/shenbi-chapter-planning/SKILL.md:113-119`（黄金三章纪律 "N = novel.json.golden_opening_chapters"）但 frontmatter reads（`:7-23`）无 novel.json。② `docs/framework/decisions-schema.md:99`（per-skill 表含 chapter-planning）与 `docs/framework/truth-files.yaml:56`（plans/chapter-N-plan-decisions.json 已注册）均声明本 skill 产 plan-decisions sidecar，但 frontmatter writes（`:24-27`）只有 plans/chapter-N-plan.md，正文亦零 decisions 指令——schema 文档、词表、skill 契约三方不一致（2026-08-14 F910 未修，方向相反：仍未声明） | 验证: `grep -n "novel.json" skills/shenbi-chapter-planning/SKILL.md` → 正文 `:115` 引用，frontmatter 0 声明；`grep -n "chapter-planning" docs/framework/decisions-schema.md` → `:99` | 方向: reads 补 novel.json [golden_opening_chapters]；要么 writes 补 plan-decisions.json + 正文 P2.5 指令，要么从 schema/词表移除该 sidecar。
  - 通过项（重要修复验证）: 字段级 reads 全部命中真实 fixture——`tests/fixtures/snapshots/chapter-025/truth/current_state.md:13,20,27`（主角状态/当前世界局势/活跃线索）、`truth/pending_hooks.md:12,73`（活跃伏笔/伏笔统计）、`truth/chapter_summaries.md:15`（已完成章节）✓（2026-08-14 F911 对本 skill 已失效）；auto-check invariants（defer silence/hook ops/typed change ch3）与 `:261-271` 计数规则一致 ✓；8 段标题与 chapter-drafting/revision/context-composing 声明字段逐字一致 ✓。
- 验证命令: `grep -n "^## " tests/fixtures/snapshots/chapter-025/truth/current_state.md tests/fixtures/snapshots/chapter-025/truth/pending_hooks.md`；`grep -n "## 已完成章节" tests/fixtures/snapshots/chapter-025/truth/chapter_summaries.md` → `:15`。
- 置信度: high

### skills/shenbi-chapter-revision/.gitkeep
- 处置: deep-read（占位文件核验）——见 **F804**（合并）
- findings: [F804]
- 验证命令: `wc -c skills/shenbi-chapter-revision/.gitkeep` → 0
- 置信度: high

### skills/shenbi-chapter-revision/SKILL.md
- 处置: deep-read
- 声称检查的不变量: [修订模式词表单一权威、updates merge_prose 与输出一致、decisions sidecar 契约、重生路由 helper 存在性]
- findings:
  - **F808** | chapter-revision 模式词表三处矛盾（未修） | error | P2 | 证据: `skills/shenbi-chapter-revision/SKILL.md:44-58`（顶部 DOT: spot-fix vs rewrite/rework 两分支）；`:115-121`（"支持三种模式：spot-fix / regenerate / constrained-regenerate"——与 `src/shenbi/skill_utils/revision_routing/route.py:30-31` 的 REGENERATE/CONSTRAINED_REGENERATE 一致）；vs `skills/shenbi-chapter-revision/revision-modes.md:3-12`（6 模式：auto/spot-fix/polish/rewrite/rework/anti-detect，无 regenerate）。同一 skill 目录三套词表，SKILL.md `:71` 还让执行者"参考 revision-modes.md 获取完整的模式说明"——但该文件不含主路由的实际模式（2026-08-14 F1000 未修）。附: `:30-31` writes chapters/chapter-N-revision-decisions.json 正文零指令（F969 未修）；`:9` reads `audits/chapter-N-*.md` 为 parametric+glob 混合形式（词表登记的是 `audits/chapter-N-<dim>.md` parametric 与 `audits/chapter-*.md` glob）；`:10` `audits/chapter-N-resonance.md` 是 `:9` glob 的子集（冗余声明） | 验证: `grep -n "regenerate" skills/shenbi-chapter-revision/revision-modes.md` → 0 命中；`grep -n "REGENERATE\|CONSTRAINED" src/shenbi/skill_utils/revision_routing/route.py` → `:30-31` | 方向: revision-modes.md 并入 regenerate/constrained-regenerate 并标注 route.py 为单一权威；正文补 decisions sidecar 指令；reads 规范为词表形式。
  - 通过项: `truth/state_snapshot-pre-rev.md` 写声明与五步闭环 `:131` 一致，且登记于 `docs/framework/truth-files.index.json:388` ✓；verify_preservation/route_revision helper 存在（`src/shenbi/skill_utils/revision_routing/preserve_check.py`、`route.py`）✓。
- 验证命令: `grep -rn "revision_routing\|verify_preservation" src/shenbi --include="*.py" -l` → 4 文件命中。
- 置信度: high

### skills/shenbi-chapter-revision/revision-modes.md
- 处置: deep-read
- 声称检查的不变量: [auto 路由表与 18 审计 skill 名单一致、接受条件与 SKILL.md 一致]
- findings: [F808]（本文件为矛盾三方之一：6 模式表缺 regenerate/constrained-regenerate；其余内部自洽——18 审计路由行与 using-shenbi 审计名单（`skills/using-shenbi/SKILL.md:124-128`）对应，PATCHES/接受条件与 SKILL.md `:62-67,92-100` 一致）
- 验证命令: `grep -c "shenbi-review-" skills/shenbi-chapter-revision/revision-modes.md` → 18 行路由。
- 置信度: high

### skills/shenbi-character-design/.gitkeep
- 处置: deep-read（占位文件核验）——见 **F804**（合并）
- findings: [F804]
- 验证命令: `wc -c skills/shenbi-character-design/.gitkeep` → 0
- 置信度: high

### skills/shenbi-character-design/SKILL.md
- 处置: deep-read
- 声称检查的不变量: [reads 覆盖正文全部输入、正文引用文件在词表内、writes 词表一致、expand 模式契约]
- findings:
  - **F809** | character-design 引用词表外文件 + expand 模式 reads 未声明 | error | P1 | 证据: `skills/shenbi-character-design/SKILL.md:40-41`（"No character explicitly named in `outline/chapter_outline.md` or `outline/three_act.md` may be omitted"）、`:101-102`、`:196-199`（IRON LAW 完整性检查基于这两个文件）——两文件均不在 `docs/framework/truth-files.yaml` concepts（outline/ 词表只有 story_frame/volume_map/rhythm_principles/thread_map/chapter_patterns/short_story_map），也不在本 skill reads；实际生产者是 story-architecture（story_frame.md）与 volume-outlining（volume_map.md），判断为陈旧命名残留 → IRON LAW 永远无法按字面执行。另 `:222-241` expand 模式 DOT "Read all existing characters/**/*.md" 但 frontmatter reads（`:7-9`）仅 world/story_bible.md + world/rules.md——dispatcher 过滤策略下 expand 模式拿不到已有角色卡，去重检查（铁律 2）必然空转（2026-08-14 F908 未修） | 验证: `grep -n "chapter_outline\|three_act" docs/framework/truth-files.yaml` → 0 命中；`grep -n "characters/" skills/shenbi-character-design/SKILL.md` → 正文 expand 节引用，frontmatter reads 0 声明 | 方向: chapter_outline.md→volume_map.md、three_act.md→story_frame.md 全局替换（或入词表）；reads 补 characters/**/*.md（expand 模式）。
- 验证命令: 见上；`grep -rn "chapter_outline" skills/ --include="SKILL.md" | wc -l` → 仅本 skill 引用。
- 置信度: high

### skills/shenbi-character-extraction/SKILL.md
- 处置: deep-read
- 声称检查的不变量: [reads 与 import-analysis 实际输出文件名一致、DOT 命名与词表一致、正文节与职责一致]
- findings:
  - **F810** | character-extraction 模板残留与命名漂移 | error | P2 | 证据: `skills/shenbi-character-extraction/SKILL.md:236-245`（"缺陷证据格式…引用 SKILL.md 中的精确规则名…BLOCKING|CRITICAL|MINOR"）——本 skill 是提取技能非审计技能，该四要素缺陷报告格式属 review 族模板（对照 foreshadowing-track/lifecycle 同款节），与"反向提取角色档案"职责无关，误导执行者产出审计格式。`:55` DOT "Cross-check with relationship_map for consistency"——`relationship_map` 是另一 skill 名（shenbi-relationship-map），实际交叉对象是本 skill 自写的 characters/relationships.md（`:172`），命名漂移且该交叉检查目标不在 reads | 验证: `grep -n "缺陷证据格式" skills/ -r` → 同时出现在 review 族与 track/lifecycle/extraction | 方向: 删除或改写缺陷证据格式节为"证据格式"（evidence 字段已在前向档案模板 `:141-145`）；DOT 节点改为 "Cross-check relationships.md internal consistency"。
  - 通过项: reads import/analysis/02_characters.md + 04_plot.md 与 import-analysis Pass 2/4 输出（`skills/shenbi-import-analysis/SKILL.md:73,84`）一致 ✓；writes 与 character-design 相同词表 ✓；与 using-shenbi `:78` 路由一致 ✓。
- 验证命令: `grep -n "02_characters\|04_plot" skills/shenbi-import-analysis/SKILL.md` → `:73,84`。
- 置信度: medium（"缺陷证据格式"节是否为有意共享模板不确定，判 P2）

### skills/shenbi-context-composing/.gitkeep
- 处置: deep-read（占位文件核验）——见 **F804**（合并）
- findings: [F804]
- 验证命令: `wc -c skills/shenbi-context-composing/.gitkeep` → 0
- 置信度: high

### skills/shenbi-context-composing/SKILL.md
- 处置: deep-read
- 声称检查的不变量: [writes 覆盖正文声明的主产物、reads 覆盖近章结尾检查输入、L2/L4/L5 字段与生产者实况一致、9 节输出与 auto-check 一致]
- findings:
  - **F811** | context-composing 写/读契约断链（未修，升 P1） | error | P1 | 证据: ① `skills/shenbi-context-composing/SKILL.md:116`（pipeline 模式 "输出: 策展后的上下文包覆写到 `context/chapter-N-context.md`"）但 frontmatter writes（`:46-49`）仅 context/chapter-N-context-decisions.json——主产物写路径未声明，G2 审计面与实际产出不符。② `:123-125`（铁律 2/4：近章结尾检查必须读 `chapters/chapter-(N-3).md` 到 `chapter-(N-1).md`）但 reads 只声明 `chapters/chapter-N.md`（`:45`）——上下文组装发生在第 N 章起草前，chapter-N.md 尚不存在（死声明），而实际需要的 N-1..N-3 反而拿不到；G4 invariant "no 3 consecutive endings"（`:59`）所需输入不在契约内。③ `:24-28` volume_summaries 字段声明 [卷目标达成/核心事件/跨卷钩子]，实际 L3 生产者 volume-consolidation 输出节为 叙事弧线/关键事件/角色成长/未兑现伏笔（带入下卷）/卷入尾声状态（`skills/shenbi-volume-consolidation/SKILL.md:77-100`）——三个声明字段零命中 → field_filter escape hatch + WARN（token 浪费）。2026-08-14 F951（P2）未修且证据增强 | 验证: `grep -n "卷目标达成\|核心事件\|跨卷钩子" skills/shenbi-volume-consolidation/SKILL.md` → 0 命中；`grep -n "chapter-(N-3)" skills/shenbi-context-composing/SKILL.md` → `:123,125` 正文需要 vs `:45` reads 无 | 方向: writes 补 context/chapter-N-context.md（或明确 pipeline 为唯一写者并删正文覆写声明）；reads 改 chapters/chapter-*-context 邻近章（glob 或 N-1/N-2/N-3）；volume_summaries 字段改为 关键事件/未兑现伏笔。
  - 通过项: book_spine 字段（核心冲突三层/主线钩子/世界铁律快照）与 book-spine-init 输出节（`:70,86,90`）匹配 ✓；book_strata 字段与 memory-distill（`:121,141,144` 未解决悬置/本弧主题推进/跨弧伏笔账）匹配 ✓；arc 字段与 memory-distill L2 模板（`:107,110,121` 弧内事件链/弧内伏笔兑现推进/未解决悬置）匹配 ✓；plan 字段 1/3/7/8 与 chapter-planning 段标题一致 ✓；pending_hooks 字段与 fixture（活跃伏笔 `:12`/伏笔统计 `:73`）匹配 ✓。
- 验证命令: `grep -n "^## " skills/shenbi-memory-distill/SKILL.md | sed -n '1,20p'`；`grep -n "弧内事件链\|未解决悬置" skills/shenbi-memory-distill/SKILL.md`。
- 置信度: high

### skills/shenbi-drift-guidance/SKILL.md
- 处置: deep-read
- 声称检查的不变量: [契约写文件均有正文定义、updates 模式与单一写者语义一致、drift_detection helper 存在、reads 覆盖三条 trend 输入]
- findings:
  - **F812** | drift-guidance 契约写 truth/drift_guidance.md 正文零定义（未修，升 P1） | error | P1 | 证据: `skills/shenbi-drift-guidance/SKILL.md:14-16`（writes: truth/drift_guidance.md, mode: create_or_overwrite）vs 全文正文（`:38-147`）只写 truth/audit_drift.md（`:40,54,86,91` 等），`grep -c "drift_guidance" ` 正文 0 次定义其内容/格式——执行者对契约产物无任何内容规范；该文件在 truth-files.yaml:39 有登记但无正文契约（2026-08-14 F1001/R5 未修）。附: `:67` 铁律 6 要求把超 12 章条目归档到 `truth/audit_drift_archive.md`，该写未在契约声明（updates 只有 audit_drift.md append_dedup）；`:19-20` append_dedup(key: chapter) 与 `:42` "合并重写为权威版本" 语义张力未消解 | 验证: `grep -n "drift_guidance" skills/shenbi-drift-guidance/SKILL.md` → 仅 frontmatter + AUTO-GENERATED 3 处，正文 0；`grep -n "audit_drift_archive" docs/framework/truth-files.yaml` → 0 | 方向: 按 R5 裁决——定义 drift_guidance.md 内容契约（如下一章写作指导快照）或从 writes 移除；补 audit_drift_archive.md 写声明。
  - 通过项: `python -m shenbi.skill_utils.drift_detection` 模块存在（`src/shenbi/skill_utils/drift_detection/`）✓；reads 三条 trend（resonance/volume_score/arc_payoff）正文均有使用（`:49,85,139`）✓。
- 验证命令: `find src/shenbi/skill_utils -name "*drift*"` → drift_detection/ 目录存在。
- 置信度: high

### skills/shenbi-escalation-review/SKILL.md
- 处置: deep-read
- 声称检查的不变量: [description 触发条件性、触发 helper 名称真实存在、writes 词表一致]
- findings:
  - **F813** | escalation-review 缺 anti-rationalization 表 + helper 名漂移 | error | P2 | 证据: `skills/shenbi-escalation-review/SKILL.md` 全文无 Anti-Rationalization 节（本 skill 有"给 2-3 个决策选项"分支，其余 21+ skill 均有表，2026-08-14 F923 未修）；`:34` "仅在 escalation_check 返回非空信号时触发"——实际 helper 为 `run_escalation_check`（`src/shenbi/orchestration/escalation_bridge.py:28`）/`check_escalation`（`src/shenbi/skill_utils/escalation/check.py`），无名为 `escalation_check` 的函数 | 验证: `grep -c "Anti-Rationalization" skills/shenbi-escalation-review/SKILL.md` → 0；`grep -rn "def escalation_check" src/` → 0 命中；`grep -n "def run_escalation_check" src/shenbi/orchestration/escalation_bridge.py` → `:28` | 方向: 补表（"分数够了不用人审"/"自动选选项"类借口）；引用改为 check_escalation 全名。附注（M）: frontmatter `requires_independent_agent: true` 与铁律 1 "只读不评——不产生评分" 张力（该 flag 语义为评分/审核独立性，spec §8.1）。
- 验证命令: 见上。
- 置信度: high

### skills/shenbi-faction-builder/SKILL.md
- 处置: deep-read
- 声称检查的不变量: [writes/updates 与正文输出文件一致且在词表内、append 语义与 mode 一致、锚点角色交叉检查输入已声明]
- findings:
  - **F814** | faction-builder 写词表已废弃文件 faction-relations.md（未修，升 P1） | error | P1 | 证据: `skills/shenbi-faction-builder/SKILL.md:179-193`（"文件 2: world/faction-relations.md"完整输出格式+列校验）与 `:200`（汇总"更新文件: world/factions.md, world/faction-relations.md"）——但 frontmatter writes:[] / updates 仅 world/factions.md（`:13-16`），且 `docs/framework/truth-files.yaml:160` 注释明确 "world/faction-relations.md (legacy deps.json) has no producer -> dropped"：词表显式废弃的文件被本 skill 继续生产 = 静默同义词再创造（词表头注 "Adding a genuinely new file = ONE edit here; 防止 silent synonym creation"）。另 `:37` "负责后续追加/扩展（append，不重写已有势力）" + DOT `:52` "Append to world/factions.md" vs updates mode `create_or_overwrite`——全量覆写与 append 语义错配（2026-08-14 F1008/F1007 未修） | 验证: `grep -n "faction-relations" docs/framework/truth-files.yaml` → 仅 `:160` dropped 注释；`grep -n "faction-relations" skills/shenbi-faction-builder/SKILL.md` → `:179,181,184(隐含),193,200,213` | 方向: faction-relations 矩阵并入 world/factions.md（跨势力动态节已有同构表 `:142-149`）或走词表 PR 登记新概念；mode 改 append 语义或在正文说明整文件重写含既有势力。
- 验证命令: 见上。
- 置信度: high

### skills/shenbi-foreshadowing-lifecycle/SKILL.md
- 处置: deep-read
- 声称检查的不变量: [description 触发条件性、参考文件引用可达、状态词表与 lifecycle-states.md 一致、bridge_tracker 与审计报告写声明]
- findings:
  - **F815** | foreshadowing-lifecycle description 违反触发条件性契约（未修）等五项 | error | P1 | 证据: ① `skills/shenbi-foreshadowing-lifecycle/SKILL.md:3` description = "Combined foreshadowing lifecycle -- recall dormant hooks, track active hooks..., and plant new hooks from plan in a single call."——纯功能描述（"做什么"），无 "Use when"，违反 AGENTS.md "description ONLY when-to-use trigger conditions"（2026-08-14 F901/R1b 未修）。② `:59`（"see `lifecycle-states.md`"）与 `:103`（"Full ... lookup table in `hook-types.md`"）相对引用——两文件实际位于 `skills/shenbi-foreshadowing-track/lifecycle-states.md` 与 `skills/shenbi-foreshadowing-plant/hook-types.md`，本 skill 目录（仅 SKILL.md）不可达（F902 半修：文件存在但位置错）。③ `:79` Phase 3 "Set initial `lifecycle_state` to ACTIVE" vs 自身输出示例 `:154` "| hook-004 | (new) | — | PLANTED |" 且 fixture 真实字段为 `state: PLANTED`（`tests/fixtures/truth-pending_hooks.md:24`）——初始态与字段名（lifecycle_state vs state）双漂移。④ `:120-126` Cross-Volume Bridge Tracking 读写 `truth/bridge_tracker.md` 未在契约声明（writes:[] / updates 仅 pending_hooks.md，`:11-15`）。⑤ 输出格式 `:135` "### FILE: audits/chapter-N-foreshadowing.md" 审计报告写未声明 | 验证: `ls skills/shenbi-foreshadowing-lifecycle/` → 仅 SKILL.md；`grep -n "state:" tests/fixtures/truth-pending_hooks.md` → `:24 state: PLANTED` | 方向: description 改 "Use when a chapter is drafted and settled and hook recall/track/plant operations are needed in one pass"；参考文件改跨目录真实路径；初始态统一 PLANTED、字段名统一 state；契约补 bridge_tracker.md 与审计报告写。
- 验证命令: 见上；另 `grep -rn "foreshadowing-lifecycle" skills/using-shenbi/SKILL.md` → 0（触发表无本 skill，见 F816）。
- 置信度: high

### skills/shenbi-foreshadowing-plant/SKILL.md
- 处置: deep-read
- 声称检查的不变量: [DEPRECATED 标注存在、字段落 reads 与 fixture 一致、hook-types.md 同目录可达、不被路由/接线引用]
- findings:
  - **F816** | DEPRECATED 伏笔 skill 仍被 using-shenbi 路由与 deps.json 注册（未修） | error | P1 | 证据: `skills/shenbi-foreshadowing-plant/SKILL.md:29-30`（"# DEPRECATED: Superseded by shenbi-foreshadowing-lifecycle (2026-07-19). ... Do not dispatch."）vs `skills/using-shenbi/SKILL.md:73`（"伏笔" / "埋线" / "hook" → shenbi-foreshadowing-plant——用户正常路径说出触发词即被路由到废弃技能）+ `tests/tiers/deps.json:47`（仍注册 shenbi-foreshadowing-plant；track `:61`、recall `:66` 同）+ `skills/using-shenbi/SKILL.md:96` 兜底行仍指向 "design spec Section 8"（归档文档）| 根因: 2026-08-14 R1（"验收：全仓 0 引用 deprecated skill"）未执行，且替代者 lifecycle 未加入触发表（`grep foreshadowing-lifecycle using-shenbi` = 0） | 验证: `grep -n "foreshadowing-plant\|foreshadowing-track\|foreshadowing-recall" tests/tiers/deps.json` → `:47,61,66` | 方向: using-shenbi 触发表三行改指 shenbi-foreshadowing-lifecycle；deps.json/executor_config 移除三个 deprecated 条目；加 deprecation lint。
  - 通过项: 本文件自身 pending_hooks 字段（活跃伏笔/伏笔统计/伏笔时间线）与 fixture `:12,73,81` 全命中 ✓；hook-types.md 同目录存在且词表一致 ✓；contract 形式合规。
- 验证命令: 见上。
- 置信度: high

### skills/shenbi-foreshadowing-plant/hook-types.md
- 处置: deep-read
- 声称检查的不变量: [类型/维度/曲线/微妙度词表与 plant/lifecycle 正文一致]
- findings: 无（GENUINE/SMOKESCREEN/SIDE_SHADOW、THEMATIC/CHARACTER/SYMBOLIC/STRUCTURAL、FLAT/RISING/EXPONENTIAL 与 plant DOT `:59-62` 及 lifecycle Phase 3 完全一致；微妙度分级与 plant 策略区间兼容）
- 验证命令: `grep -n "GENUINE\|SMOKESCREEN" skills/shenbi-foreshadowing-plant/SKILL.md skills/shenbi-foreshadowing-plant/hook-types.md` → 词表一致。
- 置信度: high

### skills/shenbi-foreshadowing-recall/SKILL.md
- 处置: deep-read
- 声称检查的不变量: [DEPRECATED 标注、helper 名存在、写目标词表]
- findings:
  - **F817** | foreshadowing-recall 仍注册于 deps.json + 字段拼写漂移 | error | P2 | 证据: `skills/shenbi-foreshadowing-recall/SKILL.md:14-15`（DEPRECATED, do not dispatch）vs `tests/tiers/deps.json:66` 仍注册；`:58` 铁律 3 "标注 last_reinformed/max_distance/沉默章数"——`last_reinforced` 误拼为 `last_reinformed`（DOT `:48` 与全仓其余处均为 last_reinforced） | 验证: `grep -n "foreshadowing-recall" tests/tiers/deps.json` → `:66`；`grep -rn "last_reinformed" skills/ src/` → 仅本文件 1 处 | 方向: deps.json 移除；拼写修正（若保留参考价值）。
  - 附注: recall_overdue_hooks helper 存在（`src/shenbi/skill_utils/foreshadowing_recall/`，2026-08-01 spec §1.2 列为先例）✓。
- 验证命令: `ls src/shenbi/skill_utils/foreshadowing_recall/` → recall.py 存在。
- 置信度: high

### skills/shenbi-foreshadowing-resolve/SKILL.md
- 处置: deep-read
- 声称检查的不变量: [CP 公式/参数/阈值内部单一权威、auto-check constants 与正文一致、铁律 5 公式展示要求与输出模板一致]
- findings:
  - **F818** | foreshadowing-resolve Chase Power 三套参数/阈值体系矛盾（未修） | error | P1 | 证据: 三套并存——① auto-check constants `skills/shenbi-foreshadowing-resolve/SKILL.md:24`（GREEN_MAX: 50, RED_NOW: 100, FORCE_NEXT_CHAPTER: 200）；② 正文区间表 `:124`（"GREEN < 20, YELLOW 20-50, ORANGE 50-100, RED ≥ 100"）且参数表 `:80-82`（hook_power core=10/main=5/side=2；escalation_factor 按 PAYOFF 类型 FULL=1.0/PARTIAL=0.7/TWIST=0.8/FLAT=0.3）；③ 权威参考 `skills/shenbi-foreshadowing-resolve/chase-power.md:13-24`（hook_power core=2.0/普通=1.0/支线=0.5；escalation_factor 按曲线 FLAT=1.0/RISING=1.5/EXPONENTIAL=2.0；等级 GREEN<50/YELLOW 50-100/ORANGE 100-200/RED>200）。交叉矛盾：constants GREEN_MAX=50 vs 正文表 GREEN<20；正文示例 `:85` "hook-001: CP = 10 × 8 × 1.0 = 80 (RED 区)" 按正文自己的区间表（RED≥100）应为 ORANGE，按 constants（RED_NOW=100）也应非 RED；TWIST 语义反转（正文 factor 0.8 < FULL 1.0 vs chase-power 释放 120% > FULL 100%）。DOT `:56` 指定 "Evaluate resolution quality (chase-power.md)" 为权威但参数体系与 SKILL.md 完全不同——执行者无论跟随哪套都会被另两套判无效（2026-08-14 F903 P1 未修）。附: `:200` 表尾行 "| 核心伏笔兑现质量 | core_hook ≥ PARTIAL_PAYOFF | FLAT_PAYOFF" 缺闭合竖线且与下一节间无空行（M） | 验证: 见上引用；`grep -n "GREEN\|RED" skills/shenbi-foreshadowing-resolve/chase-power.md` → `:21-24` | 方向: 裁决单一参数体系（建议以 auto-check constants + chase-power.md 对齐为 GREEN≤50/RED≥100/FORCE 200），hook_power 与 factor 取值二选一后全文同步（含示例 80 的区间标注）。
- 验证命令: 见上。
- 置信度: high

### skills/shenbi-foreshadowing-resolve/chase-power.md
- 处置: deep-read
- 声称检查的不变量: [与 SKILL.md CP 体系一致]
- findings: [F818]（本文件为三套矛盾体系之一：hook_power 2.0/1.0/0.5 + 曲线 factor + GREEN<50/RED>200，与 SKILL.md 正文/constants 均不同）
- 验证命令: `sed -n '9,25p' skills/shenbi-foreshadowing-resolve/chase-power.md`。
- 置信度: high

### skills/shenbi-foreshadowing-track/SKILL.md
- 处置: deep-read
- 声称检查的不变量: [DEPRECATED 标注、字段分工声明与 DOT 一致、引用文件存在]
- findings:
  - **F819** | foreshadowing-track 三项残留缺陷（未修，skill 已 DEPRECATED 降影响） | error | P2 | 证据: `skills/shenbi-foreshadowing-track/SKILL.md:18-19`（DEPRECATED）但 ① `:40` 字段分工声明 "last_reinforced/subtlety 由 shenbi-state-settling 维护" vs DOT `:49` "Update last_reinforced / subtlety" 自相矛盾（2026-08-14 F1015 未修）；② `:156` "After updating foreshadowing_ledger.md"——全仓无 foreshadowing_ledger.md（真实文件为 truth/pending_hooks.md，词表/`grep -rn foreshadowing_ledger src docs/framework` = 0）；③ `tests/tiers/deps.json:61` 仍注册。附: 契约 writes truth/bridge_tracker.md 是全仓唯一显式声明该文件者，但 lifecycle（现行技能）同样操作它却未声明（见 F815④） | 验证: `grep -rn "foreshadowing_ledger" src/ docs/framework/` → 0 | 方向: 修正字段分工/DOT 矛盾与死引用（若保留参考），或整文件标注仅存档并从 deps.json 移除。
- 验证命令: 见上；`grep -n "bridge_tracker" docs/framework/truth-files.yaml` → 0（仅 glob truth/*.md 覆盖）。
- 置信度: high

### skills/shenbi-foreshadowing-track/lifecycle-states.md
- 处置: deep-read
- 声称检查的不变量: [状态机覆盖现行消费方（lifecycle）使用的全部状态]
- findings:
  - **F820** | lifecycle-states.md 状态机缺 DORMANT/ACTIVE 态 | error | P2 | 证据: `skills/shenbi-foreshadowing-track/lifecycle-states.md:5-17`（DOT 状态机仅有 PLANTED/RELEVANT/TRIGGERED/RESOLVED/ARCHIVED/EXPIRED/ABANDONED）vs 现行消费者 `skills/shenbi-foreshadowing-lifecycle/SKILL.md:43-45`（Phase 1 处理 "lifecycle state is DORMANT ... Update state from DORMANT to ACTIVE"）、`:54`（"For each ACTIVE hook"）、`:79`（初始态 ACTIVE）——DORMANT/ACTIVE 两态及其转换在权威状态机中不存在；该文件被 lifecycle `:59` 引用为转换规则来源 | 根因: lifecycle 合并 recall 时引入的新状态词表未回写状态机 | 验证: `grep -n "DORMANT\|ACTIVE" skills/shenbi-foreshadowing-track/lifecycle-states.md` → 0 | 方向: 状态机补 DORMANT→ACTIVE（及 ACTIVE 与 PLANTED/RELEVANT 的关系或统一词表）。
- 验证命令: 见上。
- 置信度: high

### skills/shenbi-foundation-review/SKILL.md
- 处置: deep-read
- 声称检查的不变量: [reads 覆盖前置验证清单与评分程序输入、六维分值加总=100、DOT 与评分表一致、无重复节]
- findings:
  - **F821** | foundation-review reads 缺 genre-config.json 与 book_spine.md（未修，升 P1） | error | P1 | 证据: `skills/shenbi-foundation-review/SKILL.md:40-51`（前置文件验证清单含 `genre-config.json`、`truth/book_spine.md`）+ `:217`（评分程序 "读取 `genre-config.json` 的 `tropeInventory`"——第六维 5 分项的强制输入）vs frontmatter reads（`:9-14`：world/*.md, characters/**/*.md, outline/*.md, truth/current_state.md, truth/chapter_summaries.md）——genre-config.json 与 truth/book_spine.md 均未声明：dispatcher 过滤策略下第六维 tropeInventory 对照与前置验证无法执行（正常路径功能缺陷）。附: `:95` 与 `:125` 两个 "## 输出格式" 节重复（2026-08-14 F956 未修） | 验证: `grep -n "genre-config\|book_spine" skills/shenbi-foundation-review/SKILL.md` → 正文 `:50,51,213,217` 引用，frontmatter reads 0 声明 | 方向: reads 补 genre-config.json [tropeInventory] 与 truth/book_spine.md；合并重复输出格式节。
  - 通过项: 六维 25+20+20+15+10+10=100 ✓ 且与 DOT `:62-67`、scoring-rubric.md、再平衡说明（`:54`）一致；铁律 "核心冲突<15 自动不通过" 与评分工作表 `:164,234` 一致 ✓；foundation/review_report.md 在词表 ✓。
- 验证命令: 见上。
- 置信度: high

### skills/shenbi-foundation-review/scoring-rubric.md
- 处置: deep-read
- 声称检查的不变量: [分档与 SKILL.md 六维满分/门槛一致]
- findings: 无（25/20/20/15/10/10 分档与 SKILL.md 评分工作表一致；核心冲突 15 门槛一致。M 级格式：`:48-49` "## 维度 6" 前缺空行，未占号）
- 验证命令: `grep -n "^## \|(25分)\|(20分)\|(15分)\|(10分)" skills/shenbi-foundation-review/scoring-rubric.md`。
- 置信度: high

### skills/shenbi-genre-config/SKILL.md
- 处置: deep-read
- 声称检查的不变量: [字段规范与消费方（drafting/plant/chapter-pattern）声明字段一致、备份流程一致、铁律与计数规则一致、audit_drift 对比输入已声明]
- findings:
  - **F822** | genre-config 备份名两处不一致 + audit_drift 对比输入未声明 | error | P2 | 证据: ① `skills/shenbi-genre-config/SKILL.md:67`（铁律 4 "cp genre-config.json genre-config.json.bak"）vs `:183,214`（修改流程/输出格式 ".bak.YYYYMMDD"）——回滚指南指向的备份名两套（2026-08-14 F918 未修）。② 铁律 2 `:65`（"修改后必须与已有 audit_drift 对比"）+ 冲突检查 `:242,257`（"不与 audit_drift 中已确认纠偏矛盾"）但 reads（`:8-10`）无 truth/audit_drift.md——对比检查无输入来源 | 验证: `grep -n "audit_drift" skills/shenbi-genre-config/SKILL.md` → 正文 4 处，frontmatter 0；`grep -n "\.bak" skills/shenbi-genre-config/SKILL.md` → `:67` .bak vs `:183,214` .bak.YYYYMMDD | 方向: 统一备份名（建议 .bak.YYYYMMDD）；reads 补 truth/audit_drift.md。
  - 通过项: chapterTypes/auditDimensions/customRules/fatigueWords/pacing 字段规范表 `:270-284` 与 chapter-drafting（fatigueWords/pacing/chapterTypes）、plant（chapterTypes/customRules）字段级 reads 全部命中 ✓；auto-check invariants 与计数规则表 `:288-300` 一致 ✓；approval 必填（8 顶层字段）与铁律 6 一致 ✓。
- 验证命令: 见上。
- 置信度: high

### skills/shenbi-import-analysis/SKILL.md
- 处置: deep-read
- 声称检查的不变量: [8 通道输出文件名与词表概念及下游 reads 一致、DOT 与并行策略一致、下游调用 skill 存在]
- findings:
  - **F823** | import-analysis Pass 1 输出名与词表概念漂移 | error | P2 | 证据: `skills/shenbi-import-analysis/SKILL.md:66`（Pass 1 输出 `import/analysis/01_parse.md`）vs `docs/framework/truth-files.yaml:85`（词表概念 `{name: import/analysis/01_overview.md, kind: import}`）——`grep -rn "01_overview" src skills tests docs/framework` 仅词表自身 1 处：概念无生产者、无消费者，属 D1 同义词漂移残留；实际文件名 01_parse.md 仅被 glob `import/analysis/*.md` 覆盖 | 验证: `grep -rn "01_overview" --include="*.md" --include="*.py" src skills docs/framework tests | grep -v audit-runs` → 仅 truth-files.yaml:85 | 方向: 词表概念改名 01_parse.md（一次编辑）或删除该概念行。
  - 通过项: Pass 2/4 输出（02_characters.md/04_plot.md）与 character-extraction reads 一致 ✓；Pass 6 调用 shenbi-style-learning ✓；DOT 串并结构与铁律 1/并行策略节一致 ✓；汇总下游调用 4 项 skill 均存在 ✓。
- 验证命令: 见上。
- 置信度: high

---

## 确定性替换候选初筛（rubric #8，判据对齐 docs/superpowers/specs/2026-08-01-deterministic-skill-replacement-audit-design.md §2）

| # | skill | 环节 | 理由（输入输出皆结构化、无创造性判断） |
|---|---|---|---|
| C1 | chapter-drafting | 转折词密度计数与 1/3000 阈值判定 + AI 标记词 ≤1/词/章计数（POST_WRITE_SELF_CHECK 前两项） | 纯计数+阈值比较；词表封闭（6 词 + 9 标记词）；compute_stats.py 已有同型先例 |
| C2 | chapter-drafting / chapter-revision | 接受条件三项 ≤ 比较（blocking/critical/ai_tell 不增） | 结构化计数对比，改写前后两份审计数字即可判定 |
| C3 | drift-guidance | 滚动窗口 12 章归档（读取 audit_drift.md → 超龄条目移 audit_drift_archive.md） | 纯文件操作+键值比较（truth_io.py write_truth_file 先例） |
| C4 | drift-guidance | 累积传导 ≤5 条排序截断 | 阈值+排序，输入是本 skill 自产结构化条目 |
| C5 | foreshadowing-resolve | CP 计算（hook_power × time_since_plant × escalation_factor）与区间判定 | 纯数值计算；铁律 5 本就要求公式入输出；Python 化可同时消除 F818 三套参数矛盾的执行面 |
| C6 | foreshadowing-lifecycle | Phase 1 Recall 的超期判定（last_reinforced/max_distance/cultivation_interval 数值比较） | SKILL 自述 "final verdict is determined by pure numeric comparison"；recall.py（skill_utils/foreshadowing_recall/）已存在 |
| C7 | foreshadowing-plant（经 lifecycle） | hook ID 生成 + pending_hooks upsert + 密度预算 8 上限计数 | hook_planting.py 先例（ID 唯一性 + append_dedup key: hook_id） |
| C8 | genre-config | 备份（cp → .bak.YYYYMMDD）+ 输出 JSON 字段规范 12 项自动校验 | 纯文件操作 + schema 校验（decisions_validator.py 同型） |
| C9 | chapter-pattern | 开篇/收束/情感基调连续重复检测（N=3/3/4）与转移矩阵合规检查 | 分类结果为封闭词表标签，连续段比较 100% 确定（compute_pattern.py 已覆盖熵/分布，此为剩余面） |
| C10 | book-spine-init | 书脊骨架生成（frontmatter + 从 story_frame/novel.json/protagonist/volume_map 的 frontmatter 字段填充模板） | 固定模板填充，全部输入输出结构化；LLM 仅需覆核（且当前 reads 缺失即 F803，Python 化顺带修复） |
| C11 | import-analysis Pass 1 | 章节切分 + 字数统计 + 章节摘要列表骨架 | 纯统计/解析（compute_stats 先例；切分可规则化） |
| C12 | escalation-review | 触发信号读取与升级上下文数据装配（trend 行解析 + 报告骨架） | 输入 trend/audit 均结构化；escalation_bridge.py 已做解析，报告模板填充可确定性 |

## 低置信度文件
- skills/shenbi-character-extraction/SKILL.md（F810，medium）：「缺陷证据格式」节可能是有意的全技能统一模板，判 P2 存疑。
- skills/shenbi-book-spine-init/SKILL.md（F803 主判定 high，但 arc_type 漏 FLAT 为 M 级附注，影响面小）。

## 未覆盖文件
（无——清单 33/33 全覆盖）
