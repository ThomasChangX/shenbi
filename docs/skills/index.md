# 技能目录 / Skill Catalog

Shenbi 包含 67 个写作技能和 2 个元技能，按 9 个 T2 阶段组织。以下数据源自 `tests/tiers/deps.json`。

Shenbi includes 67 writing skills and 2 meta-skills, organized by 9 T2 phases. All groupings below are sourced from `tests/tiers/deps.json`.

---

## 创世 / Genesis

基础层：世界观、角色、故事架构和类型配置，在任何章节写作之前建立。

The foundation layer: worldbuilding, characters, story architecture, and genre configuration established before any chapters are written.

| Skill | Description |
|-------|-------------|
| shenbi-worldbuilding | Use when creating a new novel's world, building story bible, or designing setting rules, geography, and social structure |
| shenbi-power-system | Use when designing power systems, cultivation/level/ability systems, magic systems, technological capability ladders, or defining power ceilings and ability boundaries |
| shenbi-faction-builder | Use when designing factions, organizations, power groups, political entities, sects, guilds, corporations, or any collective actor within a novel's world |
| shenbi-location-builder | Use when designing or expanding specific locations in a novel, building detailed place profiles with spatial layout and atmosphere, or resolving cross-location spatial consistency |
| shenbi-character-design | Use when creating or refining character profiles, designing character arcs, voice profiles, or personality systems |
| shenbi-relationship-map | Use when modeling character relationships, building interest chains between characters, tracking faction affiliations, defining information boundaries, or designing how relationships evolve over the story |
| shenbi-story-architecture | Use when designing the overall story structure, creating story frame, volume map, or defining core conflicts and objectives |
| shenbi-volume-outlining | Use when designing a single volume's overall structure, planning a volume's per-chapter goals, building intra-volume tension curve, or designing cross-volume bridging |
| shenbi-genre-config | Use when configuring or updating genre rules, modifying fatigue word lists, calibrating pacing rules, defining chapter types, activating audit dimensions, or adding custom rules for a novel |
| shenbi-pacing-design | Use when designing pacing principles for the novel, planning the buildup→escalation→explosion→aftermath cycle, configuring scene type sequence, or calibrating the three-line ratio |
| shenbi-book-spine-init | Use when initializing the book spine at the end of the genesis layer, before entering the per-chapter writing loop |

## 架构 / Architecture

结构设计层：故事架构细化、分卷大纲、节奏、伏笔线协调。部分技能与创世阶段重叠。

Structural design layer: story architecture refinement, volume outlines, pacing, plot thread coordination. Some skills overlap with Genesis — this reflects their dual role in both initial creation and structural refinement.

| Skill | Description |
|-------|-------------|
| shenbi-story-architecture | Use when designing the overall story structure, creating story frame, volume map, or defining core conflicts and objectives |
| shenbi-volume-outlining | Use when designing a single volume's overall structure, planning a volume's per-chapter goals, building intra-volume tension curve, or designing cross-volume bridging |
| shenbi-pacing-design | Use when designing pacing principles for the novel, planning the buildup→escalation→explosion→aftermath cycle, configuring scene type sequence, or calibrating the three-line ratio |
| shenbi-plot-thread-weaver | Use when coordinating multiple plot threads across the novel, planning thread crossing points, managing A/B/C line priorities, or designing climax windows for subplots |
| shenbi-genre-config | Use when configuring or updating genre rules, modifying fatigue word lists, calibrating pacing rules, defining chapter types, activating audit dimensions, or adding custom rules for a novel |

## 规划 / Planning

逐章准备：章节计划、伏笔种植和上下文组装。

Per-chapter preparation: chapter plans, foreshadowing seeds, and context assembly before drafting.

| Skill | Description |
|-------|-------------|
| shenbi-chapter-planning | Use when planning the next chapter, generating chapter memo, or deciding what should happen in an upcoming chapter |
| shenbi-foreshadowing-plant | Use when a chapter memo's hook ledger contains OPEN items that need foreshadowing planted before drafting begins |
| shenbi-context-composing | Use when assembling context before drafting a chapter, collecting truth files, or preparing the writing context package |

## 起草 / Drafting

章节生成流水线：起草、状态更新、伏笔追踪、文风打磨、反检测、字数调整和评分。

Chapter generation pipeline: drafting, state updates, foreshadowing tracking, style polishing, anti-detect, length normalization, and scoring.

| Skill | Description |
|-------|-------------|
| shenbi-chapter-drafting | Use when writing chapter content, generating chapter text, or drafting a new chapter after planning is complete |
| shenbi-state-settling | Use when updating truth files after a chapter is drafted, extracting state changes, or settling world state |
| shenbi-foreshadowing-track | Use when a chapter has been drafted and state-settled, and foreshadowing hooks need their lifecycle states evaluated and updated |
| shenbi-style-polishing | Use when a chapter has been drafted and audit-passed, and surface-level prose quality needs improvement without altering plot or character |
| shenbi-review-resonance | Use when a finished chapter needs a positive quality score on emotional landing, presence, prose craft, and reader reward — runs in an independent agent |
| shenbi-anti-detect | Use when anti-AI audit flags a chapter with critical/blocking-level detectability markers (structural tells, sentence-pattern regularity) that surface polishing cannot resolve — distinct from polishing, which handles only warning-level fatigue-word and rhythm issues |
| shenbi-length-normalizing | Use when a chapter falls below 3000 words (needs expansion) or exceeds 10000 words (needs compression) |
| shenbi-foreshadowing-recall | Use when checking for overdue foreshadowing hooks across a large chapter range, or after each chapter's state-settling to maintain the recall index |
| shenbi-score-arc | Use when scoring 弧段级评分 on goal attainment and anchor calibration |

## 审计 / Audit

起草后质量检查：18 个专项审核维度，覆盖角色、连贯性、对话、节奏、反 AI、伏笔、世界规则、敏感词等。

Post-drafting quality checks: 18 specialized audit dimensions covering character, continuity, dialogue, pacing, anti-AI, foreshadowing, world rules, sensitivity, and more.

| Skill | Description |
|-------|-------------|
| shenbi-review-character | Use when a finished chapter needs character consistency audit against profiles and arcs |
| shenbi-review-continuity | Use when a finished chapter needs an internal consistency audit against truth files |
| shenbi-review-dialogue | Use when a finished chapter needs a dialogue style consistency audit against character voice profiles |
| shenbi-review-pacing | Use when a finished chapter needs pacing audit against rhythm rules and chapter type sequence |
| shenbi-review-anti-ai | Use when a finished chapter needs an AI-pattern audit against fatigue words, structural tells, and genre-config prohibitions |
| shenbi-review-foreshadowing | Use when a finished chapter needs foreshadowing audit against hook ledger and cultivation rules |
| shenbi-review-world-rules | Use when a finished chapter needs a world-rules consistency audit against power system, setting, and numerical records |
| shenbi-review-sensitivity | Use when a finished chapter needs a sensitivity and platform-compliance audit against prohibited words and content boundaries |
| shenbi-review-memo-compliance | Use when a finished chapter needs an 8-section chapter memo compliance audit against `plans/chapter-N-plan.md` |
| shenbi-review-motivation | Use when a finished chapter needs a character motivation and behavior-chain plausibility audit |
| shenbi-review-pov | Use when a finished chapter needs a POV consistency and information boundary audit |
| shenbi-review-reader-pull | Use when a finished chapter needs a reader-pull audit (opening hook, chapter-end suspense, expectation management) |
| shenbi-review-highpoint | Use when a finished chapter needs a high-point audit (suppression-explosion, twist detection, climax keyword diversity, 爽点虚化) |
| shenbi-review-texture | Use when a finished chapter needs a writing texture audit (流水账 detection, paragraph breathing, author preaching, segment length extremes) |
| shenbi-review-long-span | Use when a finished chapter (≥3) needs a cross-chapter pattern repetition audit (6-char n-gram, word/image loops, paragraph length drift) |
| shenbi-review-era | Use when a finished chapter needs a historical era accuracy audit (period vocabulary, artifacts, locations) |
| shenbi-review-fanfic | Use when a finished chapter in fanfic mode needs a character fidelity and world consistency audit (4 modes: canon/au/ooc/cp) |
| shenbi-review-spinoff | Use when a finished chapter in a spinoff needs a main-story consistency audit (event conflict, future info leak, world rule consistency, hook isolation) |

## 基设 / Foundation

基础质量审查和章节修订：确保故事根基稳固，修复审计发现的问题。

Foundation quality review and chapter revision: ensuring the story bedrock is solid before large-scale writing, and fixing audit findings.

| Skill | Description |
|-------|-------------|
| shenbi-foundation-review | Use when reviewing the complete worldbuilding + character + story architecture foundation before writing begins, or when a human partner asks for a quality assessment of story fundamentals |
| shenbi-chapter-revision | Use when audit found issues in a chapter, fixing review feedback, or revising chapter content based on review results |
| shenbi-truth-sync | Use when restoring consistency between manually edited chapter content and truth files, re-extracting state from revised chapters, or bootstrapping truth files from existing novel content |
| shenbi-style-learning | Use when extracting a style fingerprint from existing chapters for style imitation, computing sentence/paragraph length statistics, or generating a statistical style profile |

## 管理 / Management

卷级和书级管理：快照、漂移引导、章节模式监控、卷总结、弧段结算审查、记忆蒸馏和分层评分。

Volume-level and novel-level management: snapshots, drift guidance, chapter pattern monitoring, volume consolidation, arc payoff review, memory distillation, and multi-level scoring.

| Skill | Description |
|-------|-------------|
| shenbi-snapshot-manage | Use when creating chapter completion snapshots, viewing snapshot history, rolling back to a previous snapshot, or recovering novel state after a misstep |
| shenbi-drift-guidance | Use when a chapter has completed all audits and results need to be conveyed to the next chapter's writing context |
| shenbi-intent-management | Use when your human partner wants to set or update their creative intent, or before chapter-planning when current focus may have changed |
| shenbi-chapter-pattern | Use when classifying chapters by structural pattern, detecting pattern monotony across the novel, monitoring chapter type distribution, or preventing repetitive chapter structures |
| shenbi-volume-consolidation | Use when a volume has been completed and needs summarization for context management in subsequent writing |
| shenbi-review-arc-payoff | Use when at a volume/arc boundary to gate advancement on arc emotional delivery, foreshadowing payoff quality, thread resolution, expectation-debt settlement, and character arc — runs in an independent agent |
| shenbi-memory-distill | Use when distilling chapter summaries into arc syntheses (every 12 chapters), stratum syntheses (every 36 chapters), or rolling book spine review at volume or stratum boundaries |
| shenbi-score-volume | Use when scoring 卷级评分 on goal attainment and anchor calibration |
| shenbi-score-stratum | Use when scoring 大弧/书级健康评分 on goal attainment and anchor calibration |

## 导入 / Import

稿件导入：分析已有小说、提取角色/世界数据、导入同人原作设定。

Manuscript ingestion: analyzing existing novels, extracting character/world data, and importing canon for fanfic.

| Skill | Description |
|-------|-------------|
| shenbi-import-analysis | Use when ingesting an existing novel manuscript for analysis, parsing source chapters into structured data, or building the 8-pass reverse-engineering pipeline before downstream extraction |
| shenbi-character-extraction | Use when reverse-extracting character profiles from existing chapters, building character cards from an analyzed manuscript, or generating speech-style fingerprints from sample dialogue |
| shenbi-world-extraction | Use when reverse-extracting worldbuilding files from existing chapters, building story_bible/rules/locations/factions/power_system from an analyzed manuscript, or reconstructing a novel's setting from text |
| shenbi-canon-import | Use when importing source material for fanfic writing, extracting canon from existing works, or generating reference files for AU/OOC/CP fanfic modes (AU=Alternate Universe 架空设定, OOC=Out of Character 性格偏离, CP=Couple/Pairing 角色配对) |

## 短篇 / Short Story

短篇小说流水线（<30 章）：快速大纲、批量起草和出版打包。

Short novel pipeline (<30 chapters): fast outlining, batch drafting, and publication packaging.

| Skill | Description |
|-------|-------------|
| shenbi-short-outline | Use when outlining a short novel with fewer than 30 chapters, condensing the outline process for shorter works, or generating a fast outline for short-story publication |
| shenbi-short-drafting | Use when batch-generating all chapters of a short story at once, drafting the complete short novel in one go, or running generate → review → revise on a full manuscript |
| shenbi-short-packaging | Use when preparing a short story for publication, generating sales materials, writing the book blurb and selling points, or producing cover image prompts |

---

## 管道外技能 / Out-of-Pipeline Skills

这些技能通过 T1 验证但不属于任何 T2 阶段。它们是辅助工具、元/设置工具或单一用途的起草辅助。

These skills pass T1 validation but are not required by any T2 phase. They serve as auxiliary tools, meta/setup utilities, or single-purpose drafting helpers.

### 辅助 / Auxiliary

| Skill | Description |
|-------|-------------|
| shenbi-market-radar | Use when researching current platform trends, analyzing leaderboard data, evaluating genre opportunities, or seeking competitive positioning advice for a new novel |
| shenbi-sequel-writing | Use when continuing a paused novel from a breakpoint snapshot, resuming writing after a break, reconstructing context for sequel chapters, or picking up an abandoned draft |
| shenbi-anchor-curate | Use when generating a new scoring anchor from a reference work passage, or curating the existing anchor library |
| shenbi-escalation-review | Use when an escalation signal has been triggered and human review is required |

### 元技能 / Meta

| Skill | Description |
|-------|-------------|
| shenbi-writing-skills | Use when creating or modifying any shenbi skill — guides the design, testing, and iteration of new novel-writing skills |
| using-shenbi | Use when starting any conversation — establishes skill discovery and trigger rules for the shenbi novel writing skill system |

### 起草辅助 / Drafting Helper

| Skill | Description |
|-------|-------------|
| shenbi-foreshadowing-resolve | Use when foreshadowing hooks reach TRIGGERED state and need resolution, or when a volume ends and requires foreshadowing inventory |

---

!!! note "Cross-phase skills"
    Some skills appear in multiple phases (e.g., `genre-config` in both Genesis and Architecture). This reflects `tests/tiers/deps.json`, not an error. Total unique skills: **69** (67 writing + 2 meta).
