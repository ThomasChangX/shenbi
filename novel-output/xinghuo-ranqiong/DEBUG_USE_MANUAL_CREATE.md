流水线产出文件全览：novel-output/xinghuo-ranqiong/
总计：1226 个文件，23.7 MB，56 章，生成时间约 40 小时

一、顶层配置文件（7 个）
文件	创建者	用途	时间
novel.json	pipeline-init	小说元数据	04:05
genre-config.json	shenbi-genre-config	类型配置	04:06
progress.json	shenbi-foundation-review	进度追踪	04:53
pipeline-state.json	phase_runner	流水线状态机	持续更新
truth-index.json	shenbi-style-learning	真相文件索引	04:52
truth-embeddings.db	shenbi-style-learning	向量嵌入	04:05
*.lockfile	phase_runner	状态锁	—
二、GENESIS 阶段（Genesis Phase）— 16 skills，约 49 分钟
#	Skill	输出文件	文件大小	门禁通过时间	耗时
1	shenbi-worldbuilding	world/rules.md (4.7KB), world/story_bible.md (37KB), genesis-context/world_rules.md (0.5KB)	42KB	04:05:19	—
2	shenbi-genre-config	genre-config.json (3.5KB)	3.5KB	04:06:25	1.1min
3	shenbi-character-design	characters/protagonist.md (16.6KB), characters/relationships.md (18.9KB), genesis-context/protagonist.md (0.8KB)	36KB	04:09:48	3.4min
4	shenbi-story-architecture	outline/story_frame.md (19.3KB)	19KB	04:11:47	2.0min
5	shenbi-faction-builder	world/factions.md (18.5KB), genesis-context/forces.md (0.8KB)	19KB	04:17:40	5.9min
6	shenbi-volume-outlining	outline/volume_map.md (10.4KB)	10KB	04:19:39	2.0min
7	shenbi-pacing-design	outline/rhythm_principles.md (8.3KB)	8.3KB	04:22:33	2.9min
8	shenbi-plot-thread-weaver	outline/thread_map.md (23.8KB), genesis-context/plot_lines.md (1.1KB)	25KB	04:27:35	5.0min
9	shenbi-foreshadowing-plant	truth/pending_hooks.md (9.9KB)	10KB	(持续更新)	—
10	shenbi-power-system	world/power_system.md (12.3KB)	12KB	04:34:05	6.5min
11	shenbi-location-builder	world/locations.md (32.4KB)	32KB	04:41:24	7.3min
12	shenbi-relationship-map	characters/relationships.md (18.9KB，更新)	19KB	04:48:41	7.3min
13	shenbi-book-spine-init	truth/book_spine.md (3.3KB)	3.3KB	04:49:36	0.9min
14	shenbi-style-learning	style/style_profile.md (6.6KB)	6.6KB	04:52:15	2.6min
15	shenbi-intent-management	truth/author_intent.md (5.3KB), truth/current_focus.md (20.3KB)	26KB	(稍后重运行)	—
16	shenbi-foundation-review	foundation/review_report.md (11.7KB)	12KB	04:53:55	1.7min
预生成种子文件（来自 outline-example.md，非 skill 产出）：genesis-context/ 下 9 个文件（three_act.md, deep_conflict.md, surface_conflict.md, personal_conflict.md 等），共 7.4KB，时间 04:01:57。

三、CHAPTER LOOP 阶段（56 章 × ~20 steps）— 约 40 小时
每章循环由以下 skills 重复执行，产出同类文件：

3.1 章节规划
Skill: shenbi-chapter-planning
产出	plans/chapter-N-plan.md + plans/chapter-N-plan-decisions.json（56对）
暂存	staging/plans/chapter-N-plan.md + staging/plans/chapter-N-plan-decisions.json（111个文件）
总大小	784KB（plans）+ 1.2MB（staging）= ~2MB
平均耗时	~2-5 min/chapter（plan→draft 间隔）
3.2 章节起草
Skill: shenbi-chapter-drafting
产出	chapters/chapter-N.md + chapters/chapter-N-decisions.json（56对）
总大小	1.7MB
字数统计	总计 510,442 字，平均 9,115 字/章
最大章	Ch47: 18,363 字 (46.7KB)
最小章	Ch55: 101 字 (0.1KB)（生成中断）
平均耗时	~8-15 min/chapter（实测 DeepSeek 生成时间）
3.3 章节修订
Skill: shenbi-chapter-revision
产出	chapters/chapter-N-revision-decisions.json（34章触发修订）
触发率	60.7%（34/56 章需要修订）
总大小	~110KB
平均耗时	~3-5 min/次
3.4 审计审查（13 种审计 × 55-56 章）
#	审计类型	Skill	覆盖	篇幅范围
1	anti-ai	shenbi-audit-anti-ai	56章	1-3KB
2	character	shenbi-audit-character	56章	1-3KB
3	continuity	shenbi-audit-continuity	56章	1-3KB
4	dialogue	shenbi-audit-dialogue	55章	1-3KB
5	foreshadowing	shenbi-audit-foreshadowing	56章	1-3KB
6	memo-compliance	shenbi-audit-memo-compliance	56章	1-3KB
7	motivation	shenbi-audit-motivation	55章	1-3KB
8	pacing	shenbi-audit-pacing	56章	1-3KB
9	pov	shenbi-audit-pov	56章	1-3KB
10	resonance	shenbi-audit-resonance	55章	1-3KB
11	review-summary	shenbi-audit-review-summary	55章	2-5KB
12	sensitivity	shenbi-audit-sensitivity	55章	1-3KB
13	world-rules	shenbi-audit-world-rules	55章	1-3KB
合计	722 个审计文件			6.2MB
3.5 共鸣审查
Skill: shenbi-review-resonance
产出	context/review-checklist-N.json（56个）
总大小	~270KB
重试	大量重试记录（retry_feedback 中 30+ 次）
3.6 状态沉淀
Skill: shenbi-state-settling
产出	更新 truth/current_state.md、truth/chapter_summaries.md、truth/character_matrix.md、truth/emotional_arcs.md、truth/particle_ledger.md、truth/subplot_board.md
暂存	staging/truth/ 下 8 个文件（截至 Ch56 的中间态）
总大小	truth: 80KB + staging/truth: ~45KB
平均耗时	~3-8 min（第35章曾超时 900s）
3.7 其他 chapter-loop skills
Skill	产出	数量	总大小
shenbi-foreshadowing-track	更新 truth/pending_hooks.md	持续	9.9KB
shenbi-context-compression	context/chapter-N-context.md	13个	~125KB
shenbi-audit-drift	truth/audit_drift.md	1个	0.8KB
shenbi-snapshot	snapshots/chapter-NNN-YYYYMMDDTHHMMSS.md	52个	12.9MB
shenbi-style-learning-update	更新 style/style_profile.md	持续	6.6KB
3.8 门禁标记
产出	文件	数量
G4 门禁标记	gate-markers/G4-shenbi-*-generative.json	21个（每个 skill 一个）
总大小	11KB
四、汇总表格
按目录分类
目录	文件数	总大小	创建者
audits/	722	6.2MB	shenbi-audit-* (13种审计)
chapters/	145	1.7MB	shenbi-chapter-drafting, shenbi-chapter-revision
snapshots/	52	12.9MB	shenbi-snapshot
staging/	119	1.2MB	shenbi-chapter-planning, shenbi-state-settling
plans/	56	0.8MB	shenbi-chapter-planning
context/	69	0.5MB	shenbi-context-compression, shenbi-review-resonance
truth/	13	0.1MB	shenbi-state-settling 等（持续更新）
world/	5	0.1MB	shenbi-worldbuilding, shenbi-faction-builder, shenbi-power-system, shenbi-location-builder
outline/	4	0.06MB	shenbi-story-architecture, shenbi-volume-outlining, shenbi-pacing-design, shenbi-plot-thread-weaver
characters/	2	0.04MB	shenbi-character-design, shenbi-relationship-map
genesis-context/	9	0.01MB	outline-example.md 种子（非skill产出）
style/	1	0.01MB	shenbi-style-learning
foundation/	1	0.01MB	shenbi-foundation-review
gate-markers/	21	0.01MB	phase_runner (G4验证)
顶层 json	6	0.15MB	pipeline-init + 各skill
耗时汇总
阶段	Skills	耗时
Genesis	16 skills	~49 分钟
Chapter Loop	56章 × ~20 steps	~40 小时
总计		~41 小时
平均每章		~43 分钟
最快章	Chapter 13	~10 分钟
最慢章	Chapter 24	~87 分钟
重试统计
retry_feedback 记录: 54 条（涉及 drafting、planning、state-settling、review-resonance）
soft_fail_trackers: transition（过渡不足）、fatigue（疲劳）
修订触发: 34/56 章（60.7%）
Chapter 35 超时: state-settling 超过 900s → escalation checkpoint → 重试成功



1.  identify similar
2.  character不全
3.  /Users/xiaotiac/Documents/GitHub/shenbi/novel-output/xinghuo-ranqiong/outline/volume_map.md 信息很好，但是生成没有充分利用
4.  /Users/xiaotiac/Documents/GitHub/shenbi/novel-output/xinghuo-ranqiong/plans 12章开始结构发生变化，后续plan情节出现巨大脱节和问题
5.
