> **Date:** 2026-08-14 | **Status:** Rejected (2026-08-30 · 总纲 #40 裁决 supersede → C20/C21/C22：R1/R1b/R2 分别由活跃 spec #58/#59/#60 按簇承接且证据全部存活于彼；R5 F1001 已由 C3 批次修复（5ce1a8e）；F907 已修；残留 F905 双重调度语义面补登 #59、F903 内部矛盾补登 #62；P2 成员条按总纲 §6 回写协议由 2026-08-16 新簇 merged 关账) | **Severity:** 🟠 P1 | **方法:** systematic-debugging 四阶段
> **系列:** 2026-08-14 全项目审查（补齐 spec 6/7） | **依赖:** contract-single-source | **范围:** skills/ 契约（Z8-a/b/c 全量）| **核心洞察:** Z8 契约漂移族（DEPRECATED 接线、reads/writes 未声明、字段漂移、双重调度）——contract-single-source 只覆盖 F0-02/F201/F218/F115/F0-01 代表 5 条，本 spec 补完其余 P1

# Z8 契约漂移补完（补齐 F）

## R1 · DEPRECATED skill 接线拆除（F904/F950/F1004, P1；F921, P2）
- 证据：F950 5 个（plant/continuity/dialogue/foreshadowing/reader-pull）+ F1004 7 个（recall/track/review-*）仍登记 deps.json/executor_config/audit_layer/chapter_loop/gates 接线；"Do not dispatch" 无 enforcement
- 修复：deps.json 调度相位/executor_config/审计矩阵/路由/测试全套件移除 deprecated；加 deprecation lint；**验收：全仓 0 引用 deprecated skill**

## R1b · description 触发条件性修复（F901/F1009, P1）
- 证据：foreshadowing-lifecycle/review-group-craft description 非触发式（F901）；review-group-character/plan description 描述实现（"in one call"/"dispatches via parallel_dispatch.py")且无 Use when（F1009）
- 修复：description 改为纯 when-to-use 触发条件（≤500 字符）；lint 校验 description 不含实现动词
- **验收：全 skill description 触发条件性合规**

## R2 · 契约 reads/writes 声明补全（F953/F1002/F1011/F1008/F951/F955/F956/F960/F961/F908, P1/P2）
- 证据：memory-distill L5 读 book_spine 未声明（F953）；state-settling 未声明 reads（character_matrix）与写（protagonist arc_log）（F1002）；book-spine-init 读 protagonist/world 未声明（F1011）；faction-builder 未声明写（F1008）
- 修复：按正文实际读/写补 frontmatter reads/writes/updates；sync_contracts 加 reads↔正文 lint；**验收：契约闭包 = 正文行为闭包**

## R3 · 双重调度与激活条件修复（F905/F906/F907, P1）
- 证据：review-sensitivity 固定步骤 14 + genre-circle 双重调度（F905）；genre-config 字段级 reads 全漂移 → blocking 空转（F906）；激活条件用存档数值维度（F907）
- 修复：去重调度（单一触发源）；genre-config 字段契约对齐（SKILL.md 规范 ↔ 真实 schema）；激活条件改运行时键；**验收：每审计技能每章恰一次派发**

## R4 · 内部契约矛盾修复（F903, P1；F1000/F1003/F1006/F1012/F1013/F1014/F1015/F1016/F1022 等, P2）
- 证据：foreshadowing-resolve CP 公式/阈值三处不一致自相矛盾（F903）；chapter-revision 模式词表三套（F1000）；state-settling 更新模式三处不一致（F1003）
- 修复：每技能内部单一权威数值/词表源；矛盾处裁决并同步；**验收：grep 无冲突词表残留**

## R5 · drift-guidance 契约落地或废弃（F1001, P1）
- 证据：契约声明写 truth/drift_guidance.md 但正文从未定义其内容；pipeline step output 指向该文件而真实项目无此文件；audit_drift.md append_dedup 与"合并重写权威版本"语义冲突
- 修复：定义 drift_guidance.md 内容契约（或从契约移除）；audit_drift 写语义统一；
- **验收：契约声明的每个文件都有正文定义与真实产物**

## P2 清单（其余 34 条）
- **F1000（P2）** shenbi-chapter-revision 修订模式词表三处矛盾（SKILL.md 3 模式 vs revision-modes.md 6 模式 vs 顶部 DOT rewrite/rework）
- **F1005（P2）** shenbi-review-resonance reads 字段 style_profile.md [11. 综合画像 / 6. 修辞模式] 与真实 style_profile.md 章节号不符（实际 8. 综合画像 / 5. 修辞模式）
- **F1006（P2）** 激活条件与真实 genre-config schema 漂移：数字维度号 / eraResearch / eraConstraints 均不存在于真实 auditDimensions
- **F1007（P2）** 4 个 builder/planner skill 的"append 语义"正文与 frontmatter create_or_overwrite 模式冲突
- **F1008（P2）** shenbi-faction-builder 正文输出 world/faction-relations.md（文件 2），契约仅声明 updates world/factions.md —— 未声明写
- **F101（P2）** safe_write 写入后目标文件权限一律 0600，仓库 0644 工件已被改写
- **F1010（P2）** review-group-character / review-group-plan 正文内嵌 "Contract" YAML 块与 frontmatter 契约 writes/updates 互换（writes: [] + updates: 4 文件 vs frontmatter writes: 4 文件 + updates: []）
- **F1012（P2）** shenbi-chapter-pattern 熵评级阈值内部矛盾 + 13 模式与 genre-config chapterTypes 词表不匹配
- **F1013（P2）** shenbi-pacing-design 内部矛盾：四拍范围 / CONSTELLATION 多套范围 / 场景类型 6-8 vs 恰好 8 / 单调性阈值统一 vs 分类型
- **F1014（P2）** shenbi-volume-outlining 内部矛盾：铺垫段占比 10-20% vs 15-25%；跨卷钩子 ≥1（铁律/核心设计）vs ≥3（输出/检查/汇总）
- **F1015（P2）** shenbi-foreshadowing-track 内部矛盾：字段分工（last_reinforced/subtlety 归 state-settling）vs DOT "Update last_reinforced / subtlety"；Cross-Volume Bridge Tracking 引用不存在文件 foreshadowing_ledger.md
- **F1016（P2）** foreshadowing-track / foreshadowing-recall 的 dict-form reads 字段与真实 truth 文件结构不符（活跃伏笔/伏笔时间线/已完成章节 不存在）
- **F1017（P2）** 缺陷证据格式引用缺失/死引用：review-character 空白引用；review-pacing 引用不存在的 skills/_shared/REVIEW_EVIDENCE.md
- **F1018（P2）** 多处 "spec §X.Y" 引用无命名文档，唯一可匹配文档为归档 plan（positive-quality-gates）
- **F102（P2）** error_guidance 6 条 doc_url 全指向不存在的文档路径/锚点；2 条 action 指向不存在的脚本
- **F1022（P2）** shenbi-state-settling/truth-files-reference.md 文件清单过期不完整（遗漏 9 个契约中 truth 文件）且"增量更新"原则与 replace-mode 冲突
- **F103（P2）** exceptions.py 22 类中 17 类在 src/ 无 raise 站点；error_guidance/recovery 目录引用的全部 6 类均不会被真实错误命中
- **F104（P2）** scoring.py `--kill-switch` 无 scores.json 的死分支必然 REJECT，永远到不了 0 分
- **F105（P2）** phase_runner main() 不强制 --project-dir，缺失时把字符串 "None" 传给 G5；assert 守卫在 python -O 下失效
- **F106（P2）** scoring.py G3 gate 输出解析异常被 `except Exception: pass` 静默吞掉，无日志，评分继续
- **F107（P2）** G_TRANSITION/G_DISPATCH/G_RECONCILE 未接入 phase_runner 状态机，仅 CLI 手动入口 + 各自单测
- **F108（P2）** safe_write 两处并发缺陷：mkstemp 在锁获取后、try 块外 → mkstemp 失败锁泄漏；stale-takeover unlink 后 O_EXCL 竞态 FileExistsError 未捕获
- **F109（P2）** sync_contracts.verify_bijection 用 assert 做一致性守卫，python -O 下整函数失效
- **F900（P2）** 2 个 skill 的 description 违反"只写触发条件"（foreshadowing-lifecycle / review-group-craft）
- **F902（P2）** foreshadowing-lifecycle 引用不存在的参考文件 lifecycle-states.md / hook-types.md
- **F904（P2）** review-anti-ai / review-motivation / review-pov 的 DEPRECATED 标注未传导：仍注册于 index/deps/executor_config/using-shenbi，正文仍自称活跃
- **F907（P2）** review skill 激活条件使用存档 spec 的数值维度 ID（维度 15/9/19/11/17/32），与运行时 named-key 机制脱节
- **F908（P2）** character-design expand 模式读取 characters/**/*.md 未在 frontmatter 声明，且正文引用未注册文件 outline/chapter_outline.md、outline/three_act.md
- **F909（P2）** market-radar 声明写 context/market-radar-decisions.json 但正文输出格式无任何 decisions 指令，且 index 显示零消费者
- **F910（P2）** chapter-planning 实际产出未声明的 plans/chapter-N-plan-decisions.json（55 个中 38 个无效 JSON），index 无此条目
- **F911（P2）** chapter-planning 字段级 reads 漂移：主角状态/当前世界局势/活跃线索/已完成章节/伏笔统计 在真实 truth 文件中不存在
- **F912（P2）** sequel-writing 引用已废弃的 snapshots/chapter-NNN/ 目录概念（D20 已声明废弃，真实布局为平文件）
- **F913（P2）** truth-sync 铁律 3"增量更新不重写整个文件"与 frontmatter updates mode: create_or_overwrite 矛盾
- **F921（P2）** using-shenbi 未传导 MERGE-2：4 个 group auditor 完全缺席触发表，仍路由到已废弃 skill；docs/specs 路径已失效
- **F951（P2）** context-composing 写契约断链：主产物 context/chapter-N-context.md 无任何 skill 声明写，frontmatter 只声明 decisions.json；近章结尾检查所需 chapter-(N-3..N-1).md 未入 reads
- **F952（P2）** style_profile.md 字段级 reads 漂移：4 个消费 skill 引用旧节号（11. 综合画像 / 6. 修辞模式 / 9. 对白占比），style-learning 现输出仅 8 节且无对白占比 → 每次 dispatch 触发 field_filter_no_match WARN + 全量 escape hatch
- **F954（P2）** book_spine.md 双更新者 + updates 用 create_or_overwrite 模式错配（memory-distill 与 score-stratum 均整写同一 L5 声明文件，正文却声称"只更新数据字段"）
- **F955（P2）** snapshot-manage 回滚写面未声明：回滚覆盖项目文件（truth/ + chapters/ + world/ 等）但契约 writes 仅声明 snapshots/chapter-NNN/*
- **F956（P2）** foundation-review reads 缺 genre-config.json（评分程序 §六 tropeInventory 对照源）与 truth/book_spine.md（前置文件验证必需），且正文重复两个"## 输出格式"节
- **F957（P2）** review-group-factual description 违反触发条件性契约（描述"做什么/机制"而非"何时用"，lint 盲区放行）
- **F958（P2）** review-group-factual 正文 Contract YAML 与 frontmatter 矛盾（writes↔updates 互换），且正文引用陈旧代码行号 chapter_loop.py:1090-1168
- **F959（P2）** volume-consolidation 写模式与正文矛盾（volume_summaries.md create_or_overwrite vs "追加"）+ 重复"## 输出格式"节 + 执行步骤编号重复
- **F960（P2）** anti-detect 触发输入（anti-ai 审计报告）未入 reads，genre-config.json 声明读而正文零使用
- **F961（P2）** short-drafting 字数下限依赖 novel.json.target_word_count 但 novel.json 未入 reads

## M 清单（并入 M 批量 spec）
- **F1019（M）** shenbi-score-volume 铁律 3 "从 book_spine.md (L5) 读 themes/master hooks" 行号引用过期：L5 是 frontmatter 结束符，themes 实际在 ~L17-21、master hooks 在 ~L31-42
- **F1020（M）** shenbi-chapter-pattern 熵计算输出模板 "第A-Ⓣ章" 全角符号误用（Ⓣ 应为半角 T）
- **F1021（M）** shenbi-book-spine-init HARD-GATE 语句重复（"（worldbuilding + character + story-architecture + volume-outlining）完成后、逐章循环开始前执行。"同一分句重复两次）
- **F914（M）** review-highpoint DOT 引用 maxClimaxPerChapter，正文检查项实际用 climaxKeywords/prohibitedClimaxKeywords（DOT 与正文不一致）
- **F916（M）** review-fanfic 激活/读取字段路径不一致：novel.json.mode vs novel.json.fanfic.mode
- **F917（M）** short-packaging 书名候选类型"情绪"不在 Step 1 类型表（直白/隐喻/钩子/系列）
- **F918（M）** genre-config 备份文件名不一致：铁律 4 用 .bak，输出格式用 .bak.YYYYMMDD
- **F919（M）** review-sensitivity 缺陷证据格式句残缺（"遵循  定义的四要素格式"缺主语/引用）
- **F920（M）** sensitive-words.md 引用已废弃 review-anti-ai 协作，且引用 genre-config.json.genre（不存在，实为 novel.json.genre）
- **F923（M）** anchor-curate / escalation-review 缺少 anti-rationalization 表（其余 21 个 skill 均有）
- **F962（M）** 三个 review skill 的"缺陷证据格式"引用主体缺失（"遵循  定义的四要素格式"空白）
- **F963（M）** ngram-methodology.md 内部数值矛盾：示例 +15.9/+16.1/+17.9% 标注为满足 ">0.20" 阈值；6 字 n-gram 滑动窗口示例为 5 字窗口且串内容错误
- **F964（M）** spinoff-violations.md §7"所有违规统一为 error（无 warning）"与 SKILL.md 输出模板 WARNING 行矛盾；伏笔隔离要求 pending_hooks 每钩子有 scope 字段但种植模板无此字段
- **F965（M）** worldbuilding truth 文件数自相矛盾（"全部 11 个" vs 列出 12 个）+ 重复"## 铁律"节 + DOT "Read genre config" 对应文件未入 reads
- **F966（M）** description 含实现/执行注记（"runs in an independent agent"；score-stratum 中英混排）——description 纯度系统性瑕疵
- **F967（M）** style-learning 输出头"纯统计（零 LLM）"与正文"LLM 转散文"矛盾；style-polishing DOT "prohibitions" 未在 reads 字段声明
- **F968（M）** chapter-drafting 黄金三章规则依赖 novel.json.golden_opening_chapters 但 novel.json 未入 reads（anti-ai-reference.md 间接引用）；3 个 .gitkeep 零字节遗留
- **F969（M）** decisions.json 声明在 writes 但正文零指令（3 个 skill 均如此），dispatcher 只注入通用 schema 注记——decisions 内容契约悬空（Z11-01 无效 decisions 的 Z8 侧证据）
