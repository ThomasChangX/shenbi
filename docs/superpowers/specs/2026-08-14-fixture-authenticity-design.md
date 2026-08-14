> **Date:** 2026-08-14 | **Status:** Design | **Severity:** 🟠 P1 | **方法:** systematic-debugging 四阶段
> **系列:** 2026-08-14 全项目审查（补齐 spec 1/7） | **依赖:** 无 | **范围:** tests/fixtures + tests/tiers + calibration/ | **核心洞察:** fixtures 56% 为手写/伪造（G0.9 "真实输出"声称不符），scenario 与 fixture 大面积断链，测试质量洞（空转/植错前提/伪造基准）使 T1/T2 门禁建立在假基准上

# Fixture 真实性与测试质量（补齐 A）

## 症状
- G0.9 声称 "fixtures 全是真实输出/上游副本" 与磁盘实际不符：49/88 非 .gitkeep 文件为手写/伪造（T801/T8 统计）
- bug-hunt 测试三重失真：证据不可达（F750）、植错不存在（F751/F804）、报告文件类型错配（F752）
- 伪造基准进门禁：G0.14 锁 27 个手写锚点（F807）、lint_contract_fields 用自述 mock 做基准（F811）、G6.12 用 3 词敏感词表空转（F821）
- 空目录被 scenario 引用为存在状态（F753/F814），快照伪造（F806）污染续写 agent

## R1 · fixtures 真实性审计与 G0.9 声称对齐（T801/T802/T803/T804/T805, P1）
- 证据：chapter-2..10-draft.md 9 文件 = chapter-draft-example 截断 + 仅 H1 不同（T801）；chapter-7/8/9-example 逐字节相同（T802）；snapshots/chapter-025 占位 checksum + 第1章数据改标第25章（T803/T806）；calibration 27 锚点手写（T804/T807）；lint 基准自述非真实（T805/F811）
- 修复：逐文件标注 provenance（真实输出/上游副本/构造样本）并移出 fixtures 或改 G0.9 声称；伪造快照/锚点重建或降级为显式合成样本
- **验收：fixtures 100% 可溯源；G0.9 声称与磁盘一致**

## R2 · scenario↔fixture 断链修复（T806/T807/T808/T809, P1；F750/F751/F752/F753/F814/F815/F819, P1）
- 证据：19 空目录被 20+ scenario 引用（T806/F753/F814）；62 bug-hunt expected 中 60 引用不存在证据路径（T807/F750）；12 scenario 植错断言与 fixture 不符（T808/F751/F804）；audit-report-example 单文件被 16 技能当审计报告（F752）；import-analysis 链断（F815）；snapshot bug-hunt 前提不符（F819）；chapter-7/8/9-example 逐字节相同（F801）；chapter-draft-example 被 127 处 scenario 引用为矛盾章号（F802）；review-resonance 内嵌自创 lore 当被评估成稿（F803）
- 修复：scenario 引用的每个路径加入 fixture 存在性校验（G0.8/G0.9 扩展）；expected-output 证据路径统一指向真实 fixture；断链 scenario 修文案或补 fixture
- **验收：全量 scenario 引用闭包扫描 0 断链；G0.9 门禁校验引用存在性**

## R3 · 测试质量洞修复（F700/F701/F702/F703, P1）
- 证据：test_chapter_loop step_index=16 越界恒真空转（F700）；test_parallel_steps 只断言 call_count 不验证并发（F701）；test_g_reconcile docstring 自述绕开 GR.2 bug（F702）；test_scoring 直接覆写 tracked deps.json 并发 flaky（F703）
- 修复：F700 改真实 step 表；F701 断言并发交错（barrier）；F702 删规避注释并补生产命名回归；F703 用 tmp_path 隔离
- **验收：上述测试在真实路径下断言真实行为；pytest -n auto 稳定**

## R4 · 伪造基准进门禁处置（F807/F811, P1；F808/F809/F810, P2）
- 证据：G0.14 锁手写锚点哈希（F807）；lint_contract_fields EXAMPLE_FIXTURES 为自述 mock（F811）；锚点 schema 违反（F808）/README 过期（F809）/零单文件引用（F810）；8 个 rubric-only scaffold 中 6 个是 T2 prereq → G5.1 恒 FAIL（F754）；38/82 rubric 维度过滤 no-op + 4 份 N/A 豁免被 parser 吞（F755）
- 修复：锚点重建为真实 prose excerpt 或显式合成标注；lint 基准改真实产物；G0.14 锁值重算
- **验收：G0.14 锁定的基准可溯源；lint 基准非自述 mock**

## P2 清单（家族扩展，随 R1-R4 修复）
- **F756（P2）** F0-02 核实：deps.json 缺 5 skill 登记（foreshadowing-lifecycle + review-group-*），契约 lint 无闭包检查
- **F757（P2）** genesis phase roster 与 rubric/seed 不一致：deps.json 列 11 个 prereq，rubric Phase 行与 seed 只执行 6 个
- **F758（P2）** deps.json _tool_hashes 陈旧：99 条中 63 条与当前文件哈希不符、3 条指向不存在文件，且无 gate 校验
- **F759（P2）** 8 个 rubric-only skill 的 rubric 为模板化占位（通用维度/空 Standard 列），无 T1 测试价值
- **F760（P2）** T1105 扩展：8 个压力场景 + 20 个变体场景免疫 G0.8/G0.9/G0.9c 纯度检查
- **F761（P2）** using-shenbi bug-hunt scenario 引用空目录 skill-triggering-prompts/，声称"10 个 trigger prompts"
- **F762（P2）** context-composing generative scenario 的"ending diversity"输入无多样性（chapter-8==9 逐字节相同）
- **F805（P2）** **review-sensitivity scenario 声称 novel-example.json 指定 `target_platform: "qidian"`**——JSON 无此字段（键：title/genre/language/status/core_concept/themes/target_word_count/ending_direction/mode）
- **F808（P2）** **calibration 锚点 schema 违反之二**：arc-payoff 的 期待债务结算(3)/线索收束(3)/角色弧推进(3) 共 9 个锚点正文为**评论/概述体**（"本卷净偿还了读者期待…"）而非 README schema 要求的 prose excerpt（"the actual text under evaluation"）；伏笔兑现质量 3 个为叙述+评论混合体
- **F810（P2）** **calibration 锚点零单文件引用**：27 个锚点全部仅目录级/glob 引用（`calibration/resonance/`、`calibration/arc-payoff/`、`**/*.md`），无任何单文件路径引用；9 个 low 锚点无单文件引用
- **F812（P2）** **弧系列 fixture 章节范围互相矛盾**：arc-example `chapter_range: 1-12`、volume-summary-example `1-15`、book-strata-example `1-36`、book-spine `total_chapters: 15`——同为"第一大弧/第一卷"，章节数 12/15/36 三方冲突
- **F813（P2）** **21 个零特定引用死 fixture**（全库活代码无引用）：chapter-2..10-draft（9，兼伪造 F800）、chapter-8-example、market-data-example.md、multi-chapter-example.md、parent-canon-example.md、truth-chapter_summaries/emotional_arcs/particle_ledger/character_matrix（4）、world-rules/locations/power-system/story-bible-example（4）。（T8 的 T812 计 28 个含 calibration 9 个 low 锚点——本区按"无任何特定引用"口径为 21；arc/book-spine/book-strata 仅归档 plan + lint 硬编码引用，另计 F811）
- **F816（P2）** **truth-* 与伪造快照双份逐字节重复**：truth-chapter_summaries/character_matrix/emotional_arcs/pending_hooks 与 snapshots/chapter-025/truth/ 对应文件 4 对逐字节相同（同一第1章数据两处存放，其中一处是伪造快照的一部分）
- **F820（P2）** **genre-config-example.json 与真实输出结构漂移**：chapterTypes 键英文（battle/dialogue/exposition/transition/climax/politics）vs 真实（novel-output/xinghuo-ranqiong）中文（战斗/对话/谋略/人物/世界观/过渡）；示例多 tropeInventory 键；approval.reviewer 示例 human-partner vs 真实 pipeline-autonomous——示例非真实输出副本
- **F821（P2）** **sensitive_words.txt 仅 3 词**（台独/藏独/法轮功），G6.12 全文章节敏感扫描近乎空转；scenario 声称的敏感词（傻逼/白痴/脑残）与文件不符（并入 F804 影响面）
- **F822（P2）** **stop_words_zh.txt 格式违反自身 spec 且零消费者**：spec 要求"每行一个停用词"，文件为单行 47 词逗号分隔；src/tests/scripts 零引用（chapter_loop/volume_align 用硬编码停用词集）
- **F824（P2）** **market-data-example.md 自述"真实收集数据"但全库零引用（死 fixture）**；数据（月票 52,358 等）不可核验
- **F826（P2）** **review-arc-payoff bug-hunt scenario 引用 fixture 中不存在的内容**：声称 outline-example.md "lists arc_beats"（outline 无 arc_beats）、truth-pending_hooks "mark hook-007 as resolved_this_arc"（实际只有 hook-ch1-001..003 全 PLANTED）、"hook-007 老周留下的半块黑石饼"（老周/黑石仅存在于手写锚点+scenario 闭环）→ 剧本与 fixture 断链
- **F850（P2）** tests/skill-behavior + skill-triggering 全部 33 个 .md 是 tiers 场景的精确重复副本（38 对 diff IDENTICAL），非执行、无同步机制 → 双源漂移隐患
- **F851（P2）** phase3-plant-track-resolve 内部算术自相矛盾（CP 债务 18 vs 12，公式支持 12）
- **F852（P2）** revision-mode-routing 测试期望混合策略与 shenbi-chapter-revision SKILL.md"混合→rewrite"契约冲突
- **F855（P2）** using-shenbi 触发映射对"伏笔"类请求存在路由歧义（plant vs review/track）
- **F856（P2）** test_word_count_md_always_non_negative 空转（策略字母表不含 CJK 字符 → word_count_md 恒 0）
- **F857（P2）** test_excluding_all_decline_indices_suppresses_finding 空转（升序序列永不产生递减）
- **F861（P2）** property 测试对 11 个 src 模块的增量覆盖缺口（空转/伪属性同根）
- **T810（P2）** **stop_words_zh.txt 格式违反自身 spec 且零消费者**：spec 规定"每行一个停用词"，文件为单行逗号分隔；chapter_loop.py/volume_align.py 各有硬编码停用词集，G6.7 文档声称的停用词过滤在 g6.py 中不存在（G6.7 是伏笔生命周期检查）
- **T811（P2）** **sensitive_words.txt 仅 3 词**，G6.12 全文章节敏感扫描近乎空转；且 scenario 声称的敏感词与文件不符（并入 T808 影响面）
- **T812（P2）** **28 个零引用死 fixture**：chapter-2..10-draft（9，并入 T801）、truth-emotional_arcs.md、truth-particle_ledger.md、market-data-example.md、multi-chapter-example.md、parent-canon-example.md、world-rules/locations/power-system/story-bible-example.md（4）、snapshots/chapter-025/manifest.md（并入 T803）、calibration 9 个 low 锚点（目录级引用外无单文件引用）
- **T813（P2）** **truth fixture 命名断裂**：16 个 scenario 引用 `tests/fixtures/truth/`（空目录），仅 3 个引用实际存在的 `truth-*.md`（破折号形式）；`truth/` 下只有 character_profiles/、source_material/ 两个空子目录
- **T815（P2）** **G0.14 双重实现漂移**：lock-tool-hashes.sh（无 CRLF 规范化、无 sort by relative path）vs g0.py check_calibration_integrity（有 CRLF 规范化、有 sort）vs test_g0_calibration_hash.py _compute_combined（镜像 gate）——Windows CRLF checkout 下重新 lock 会产生与 gate 不一致的哈希 → G0.14 假 FAIL
- **T816（P2）** **chapter-draft-example.md 身份漂移**：同一文件被 139 处 scenario 引用为 chapter 5/6/7/8/10/15…（互相矛盾），audit-report-example.md 自述"第1章"；文件自身 H1 在第1章与第2章之间漂移（ch2-draft 标题"第2章"vs example 标题"毕业即失业与穿越即负债"）

## M 清单（并入 M 批量 spec）
- **F763（M）** acceptance.json 无 schema/版本字段，t3 阈值无 gate 消费
- **F764（M）** T2/T3 rubric 无 Dimension Applicability section（12/12），kill switch 单条且 parser 可解析
- **F765（M）** audit phase "All 18 review-* skills" 措辞与全量 review 技能数（24）不符
- **F809（M）** **calibration README 过期自相矛盾**："No anchors are authored yet … contains only this README and `.gitkeep`"、"G0.14 locks the empty-set hash"——实际 27 个锚点存在且哈希被锁定
- **F817（M）** **chapter-draft-example 字数自述矛盾**：POST_WRITE_SELF_CHECK "~3100字"、chapter-summaries-example "~3100" vs audit-report-example "5403字" vs style-profile 第1章 "5444字"；audit 引文行号（行59）与正文实际行号（行68）偏移
- **F818（M）** **同 hook-ch1-001 内容双版本漂移**：pending-hooks-example "强制劳役或**灵能剥离**" vs truth-pending_hooks "强制劳役或**灵能僭越罪**"（同一钩子的罚则表述不一致）
- **F823（M）** **market-data/qidian-urban-fantasy-2026-06.md 声称真实榜单数据（弱证据）**：作品/作者为真实知名网文（我在东京当阴阳师/夜之命名术/诡秘之主 等），但阅读量/月票数字无快照源、无法仓库内独立核验
- **F825（M）** **multi-chapter-example/ 5 章为弱证据"真实历史输出"**（正文互不相同、格式自洽、commit 6bab764 批量引入、round 已清理无 provenance）；索引 multi-chapter-example.md 死文件；字数声称（24,180）与实测 CJK 计数（4,851/5,329/5,042/4,953/5,583）偏差约 6% 但索引内自洽
- **F827（M）** **parent-canon-example.md 死文件**：声称 chapters: 100 的 parent canon，仓库内无 100 章语料支撑；全库零引用（并入 F813 清单）
- **F853（M）** 铁律编号系统性漂移（测试引铁律1/2/3 vs SKILL.md 铁律2/4 错位；"培育超期=warning"无对应条款；plant_chapter vs planted_chapter 字段名不一致；跨技能铁律引用）
- **F854（M）** 快照"11 个 truth 文件"硬编码与真实数量漂移
- **F858（M）** test_bootstrap_subset_of_yaml 伪属性（@given(st.data()) 未使用 _data）
- **F859（M）** 陈旧注释（docstring 声称 54==54 实际 70==70；"54→70"注释漂移）
- **F860（M）** .hypothesis 实际 11 个 0 字节文件 + 12 patch 共 17 个已发现失败（任务称 44 样本不符），17 个失败全部已修复
- **T814（M）** **calibration README 过期**："No anchors are authored yet"与 27 个锚点现状矛盾；README schema 要求"Never invented or hand-crafted"，与锚点实际手写矛盾

## 统一验收
- 全量 scenario 引用闭包扫描 0 断链；fixtures provenance 标注完成；`just check` 全绿
