# Z8-c 分区初审报告（skills/ 字母序后 1/3，34 文件）

- 审查轮次: 2026-08-15 全项目深度审查
- 分区: docs/superpowers/audit-runs/2026-08-15/zones/Z8-c.files（34 条）
- 审查方式: 只读语义深读；禁止 pytest / dispatch / pipeline 执行；仅运行 grep/ls/od/python-json 只读命令
- 编号段: F867-F899（实际使用 F867-F885，共 19 条）
- 覆盖: 34/34 文件全部 deep-read；未覆盖文件列表 = 空

## Findings 总表

| 编号 | 标题 | 类别 | 严重度 | 证据 file:line |
|------|------|------|--------|----------------|
| F867 | style-learning 输出模板编号/小节与真实产物及全部下游字段读不一致 | error | P1 | skills/shenbi-style-learning/SKILL.md:161-248 vs tests/fixtures/style-profile-example.md:160,232,260 |
| F868 | volume-consolidation 整文件覆写 volume_summaries 但 reads 不含该文件，追加语义下旧卷摘要丢失 | error | P0 | skills/shenbi-volume-consolidation/SKILL.md:7-13,72,114,169 |
| F869 | state-settling frontmatter(append_dedup) 与正文(replace) 对 current_state/particle_ledger/subplot_board 写模式互相矛盾 | error | P1 | skills/shenbi-state-settling/SKILL.md:12-23 vs 55-58,149-158 |
| F870 | state-settling 正文指示写 characters/protagonist.md（契约外写，字段所有权属他人） | error | P1 | skills/shenbi-state-settling/SKILL.md:276-286 |
| F871 | score-volume 声明写 volume_score_trend 但正文零步骤零格式，dedup key=chapter 应为 volume | error | P1 | skills/shenbi-score-volume/SKILL.md:15-17（正文 66-124 无提及） |
| F872 | score-stratum 声明 updates book_spine 但正文零说明（设计意图只存在于 triggers.py 注释） | error | P2 | skills/shenbi-score-stratum/SKILL.md:15-17 vs 63-121 |
| F873 | using-shenbi 触发表路由 14 个 DEPRECATED 技能，默认审计列 3 个 DEPRECATED，且 0 处路由到 group-*/foreshadowing-lifecycle 后继 | error | P1 | skills/using-shenbi/SKILL.md:44-63,73-74,124-126 |
| F874 | review-sensitivity 缺陷证据格式段引用残缺（"必须遵循␣␣定义的四要素格式"缺指代对象） | error | P2 | skills/shenbi-review-sensitivity/SKILL.md:74 |
| F875 | volume-outlining 跨卷钩子数量（铁律≥1 vs EXACT≥3）与张力曲线铺垫段范围（10-20% vs 15-25%）自相矛盾 | error | P2 | skills/shenbi-volume-outlining/SKILL.md:66,100,118 vs 175-184,202 |
| F876 | worldbuilding 声称初始化 11 个 truth files 实际列举 12 个；出现两个"## 铁律"节 | error | P2 | skills/shenbi-worldbuilding/SKILL.md:62-69,82,104-106 |
| F877 | shenbi-writing-skills description 含功能描述从句，违反自身与 AGENTS.md 契约 | error | P1 | skills/shenbi-writing-skills/SKILL.md:3 vs 37-44 |
| F878 | using-shenbi description 含功能描述从句（较轻，偏 scope 阐述） | error | P2 | skills/using-shenbi/SKILL.md:3 |
| F879 | using-shenbi 引用不存在路径 docs/specs/2026-06-08-shenbi-design.md（实际已移至 archive） | error | P2 | skills/using-shenbi/SKILL.md:96,112,120 |
| F880 | style-polishing DOT 声明读 prohibitions 但 frontmatter genre-config fields 只有 fatigueWords（字段过滤后不可见） | error | P2 | skills/shenbi-style-polishing/SKILL.md:9-11 vs 49 |
| F881 | short-drafting 写声明 short/short-N-decisions.json 但正文零描述（repo 通病，G4 中央校验兜底） | optimization | P2 | skills/shenbi-short-drafting/SKILL.md:24-25 vs 44-233 |
| F882 | state-settling mode-rules 节列出非本 skill 契约文件（resonance_trend/audit_drift），误导执行者越权写 | error | P2 | skills/shenbi-state-settling/SKILL.md:59-63 vs 8-29 |
| F883 | volume-consolidation 执行步骤双"5"编号 + 两个冲突的"## 输出格式"模板 | error | M | skills/shenbi-volume-consolidation/SKILL.md:112-113,68 vs 165-215 |
| F884 | truth-sync 操作范围多章（N..M）但 reads 仅单章 parametric chapters/chapter-N.md | error | P2 | skills/shenbi-truth-sync/SKILL.md:9 vs 43,93 |
| F885 | score-arc/stratum/volume description 中英混排 + audit 技能评分刻度不统一（X/10 vs /100） | optimization | M | skills/shenbi-score-arc/SKILL.md:3；review-pov:130 / reader-pull:153 / texture:142 / world-rules:132 / spinoff:128 |

## Findings 详情

F867 | style-learning 模板与真实产物/下游字段读三方不一致 | error | P1 | 证据: skills/shenbi-style-learning/SKILL.md:161-248（模板 8 节：5. 修辞模式、8. 综合画像，无对白占比/各章统计）；tests/fixtures/style-profile-example.md:160,232,260（真实产物 11 节：6. 修辞模式、9. 对白占比、11. 综合画像）；下游字段读 skills/shenbi-chapter-drafting/SKILL.md:16-20、skills/shenbi-short-drafting/SKILL.md:16-20、skills/shenbi-review-resonance/SKILL.md:15-18、skills/shenbi-style-polishing/SKILL.md:13-17 全部声明 6/9/11（=真实产物编号） | 根因: profile 从 8 节扩到 11 节（拆分二元/三元、新增对白占比/各章统计）时 SKILL.md 模板未同步；且 compute_stats.py 输出键（sample/sentence_length/.../4grams/ai_markers/transition_density，compute_stats.py:336-355）不含 dialogue-ratio/per-chapter，fixture 中"对白占比: 18.9%"等精确数值无脚本来源 → 或为 LLM 估算（违反铁律 1"禁止 LLM 估算统计值"）或脚本已漂移 | 验证: `grep -n "^## " tests/fixtures/style-profile-example.md` → 11 节；`grep -n "对白占比\|dialogue_ratio\|各章统计" src/shenbi/skill_utils/style_learning/compute_stats.py` → 0 命中 | 建议方向: 模板重编号对齐 11 节真实结构；compute_stats.py 增加 dialogue_ratio/per_chapter 键，使"纯统计（零 LLM）"声明成立；否则下游 Layer B 字段读在新 profile 上必然走 escape-hatch（全文件注入 + WARN）

F868 | volume-consolidation 覆写 volume_summaries 数据丢失路径 | error | P0 | 证据: skills/shenbi-volume-consolidation/SKILL.md:7-10（reads: chapters/chapter-N.md、chapter_summaries、pending_hooks——不含 volume_summaries.md）；:12-13（writes truth/volume_summaries.md mode: create_or_overwrite）；:72/:114/:169（三处指示"追加到 truth/volume_summaries.md"）| 根因: 追加语义 + 整文件覆写模式 + 目标文件不在 reads。dispatch 通用路径按 `### FILE:` 块整文件写入（dispatch_helper.py:1160-1180），内容缩小防护只覆盖 chapters/*.md（dispatch_helper.py:940-975 `_check_content_size_guard`: `if path.parent.name != "chapters": return False`）。第二卷 consolidation 时执行 agent 看不到既有卷摘要（不在 reads，dispatcher 只注入 reads），按"追加"指令只能产出新卷内容 → 旧卷摘要被整文件覆写丢失，且无任何守卫拦截 | 验证: `grep -n "volume_summaries" src/shenbi/pipeline/dispatch_helper.py` → 仅 1 处（374 行 dispatch 提示词过滤词，非内容注入）；`sed -n 940,975p` 确认防护仅 chapters/ | 建议方向: 将 truth/volume_summaries.md 加入 reads（对齐 volume-outlining 的正确做法），或改 mode 为 upsert/append 并由 caller 走 write_truth_file

F869 | state-settling 写模式声明与正文矛盾 | error | P1 | 证据: frontmatter :12-14 current_state.md `mode: append_dedup`、:15-17 particle_ledger `append_dedup`、:21-23 subplot_board `append_dedup`；正文 :55-57 "replace-mode files (output the ENTIRE file content): current_state.md"；:151-153/:156 更新规则表 位置→current_state replace、资源→particle_ledger replace、线索→subplot_board replace | 根因: 两套写语义体系（truth_io 的 write_truth_file upsert vs 全文件输出）各自演化未对齐；G0.16 校验 frontmatter，G4/执行遵循正文，二者必然有一侧失真 | 验证: 读文件对照（行号如上）；dispatch_helper.py:1070-1078 注释确认 append_dedup 由 caller 语义性 upsert | 建议方向: 以 truth_files 的 update_mode 权威表为准统一 frontmatter 与正文三处清单

F870 | state-settling 契约外写 characters/protagonist.md | error | P1 | 证据: skills/shenbi-state-settling/SKILL.md:276-286 "For the protagonist specifically, append an `arc_log` entry to `characters/protagonist.md` frontmatter"；contract writes/updates（:8-29）无该文件；truth-files.index.json: characters/protagonist.md writers = [shenbi-character-design, shenbi-character-extraction] | 根因: "Character Matrix Update (NEW)" 增量节未同步契约；dispatcher 只写声明路径（literal+wildcard），该指示要么被静默丢弃（arc_log 状态丢失）要么成为越权写（绕过字段所有权审计） | 验证: `python3 -c "...index.json...['characters/protagonist.md']"` → writers 不含 state-settling | 建议方向: 在 updates 声明（merge/append 语义）或把 arc_log 移交 character-design/truth-sync

F871 | score-volume trend 写声明成孤儿 | error | P1 | 证据: skills/shenbi-score-volume/SKILL.md:15-17（`truth/volume_score_trend.md, mode: append_dedup, key: chapter`）；正文 :65-124 通篇无 volume_score_trend 步骤/格式；wave3 设计稿含 trend 追加行格式且键为 volume（docs/superpowers/plans/archive/2026-06-28-hierarchical-system-wave3-scoring.md:594-597 `| volume | objective_achieved | ... |`）；pipeline 触发器 output_path 只登记 audits/volume-N-score.md（src/shenbi/pipeline/triggers.py:241-246）；G4 score_volume.py:27-30 只查 RouteC/RouteA 节 | 根因: SKILL.md 从设计稿裁剪时丢失 trend 段；key: chapter 系从 chapter 级技能复制 | 验证: `grep -n "def \|Route\|trend" src/shenbi/gates/g4/score_volume.py` → 无 trend 检查；`grep -rn "volume_score_trend" src/shenbi/pipeline/*.py` → 0 命中（无 upsert caller） | 建议方向: 恢复设计稿的 trend 追加行模板，key 改为 volume；drift-guidance（reads 该文件）依赖机器可解析行

F872 | score-stratum book_spine 更新无执行说明 | error | P2 | 证据: skills/shenbi-score-stratum/SKILL.md:15-17（updates: truth/book_spine.md, create_or_overwrite）；正文 :63-121 无任何 spine 写入说明；设计意图仅存于 src/shenbi/pipeline/triggers.py:31-33 注释（"score-stratum writes diagnostic fields" [I14]） | 根因: 写序约束的知识放在代码注释而非技能正文 | 验证: `grep -rn "score-stratum\|score_stratum" src/shenbi/pipeline/*.py | head` → 注释命中 | 建议方向: 正文补"向 book_spine 追加/更新 stratum 诊断字段"步骤与字段清单

F873 | using-shenbi 路由残留大规模指向 DEPRECATED 技能 | error | P1 | 证据: skills/using-shenbi/SKILL.md:44（默认审计 review-anti-ai→DEPRECATED, group-craft）、:45 continuity（group-factual）、:46 character（group-character）、:47 pacing（group-factual）、:48 foreshadowing（group-plan）、:49 world-rules（group-factual）、:50 dialogue（group-character）、:51 motivation（group-character）、:52 pov（group-character）、:53 texture（group-craft）、:54 reader-pull（group-craft）、:63 memo-compliance（group-plan）、:73-74 foreshadowing-plant/track（→foreshadowing-lifecycle）；:124 默认审计列 "review-anti-ai, review-continuity, review-character"（3 个均 DEPRECATED）；:126 条件审计列 9 个 DEPRECATED | 根因: 2026-07-19 分组审计重构后元技能未更新；grep 确认 using-shenbi 中 group-character/group-craft/group-factual/group-plan/foreshadowing-lifecycle 命中数 = 0（后继完全无路由）；dispatcher 无 DEPRECATED 拦截（grep = 0），交互路径按表加载即违反"Do not dispatch"标记。佐证系统性残留: src/shenbi/pipeline/audit_layer.py:39-49 GENRE_ACTIVATION_MATRIX 仍路由 5 个 DEPRECATED 技能（world-rules/motivation/dialogue/texture/reader-pull） | 验证: `grep -l "DEPRECATED" skills/*/SKILL.md` → 15 个；`grep -c "group-" skills/using-shenbi/SKILL.md` → 0 | 建议方向: 重写触发表与默认/条件审计清单指向 group-* 与 foreshadowing-lifecycle；标注 P0 边界——若认定交互路由也算"契约被静默违反致错误执行"可升 P0（本报告按 P1 报，因 deprecated 技能本体完整可执行、危害为重复审计与规范漂移）

F874 | review-sensitivity 引用残缺句 | error | P2 | 证据: skills/shenbi-review-sensitivity/SKILL.md:74 "每条缺陷报告必须遵循␣␣定义的四要素格式："（od -c 确认"循"后连续两个空格，指代对象缺失）；同族技能（pov:146、texture:160、spinoff:146）均为完整句"必须遵循四要素格式：" | 根因: 某次编辑删除了引用名（疑似指向被合并的审计格式来源）留下空位 | 验证: `awk 'NR==74' ... | od -c` → `循 ** ** 空 空 定` | 建议方向: 补全或改为与其他技能一致的完整句式

F875 | volume-outlining 数量/区间规则内部矛盾 | error | P2 | 证据: skills/shenbi-volume-outlining/SKILL.md:66（铁律 3"至少 1 个实体钩子"）、:118（核心设计"至少 1 个，理想 2-3 个"）vs :202（EXACT"至少 3 个实体钩子，且类型分布 ≥ 2 种"）与 :239（自动检查"跨卷钩子数 ≥ 3"）；:100（铺垫段 10-20%）vs :175（EXACT 表允许范围 15-25%）vs :184（检查规则"15-25%｜不合格 <10% 或 >35%"——规则列与不合格列自身也不一致） | 根因: EXACT 模板收紧规则时未回改铁律/核心设计段 | 验证: 行号对照（如上）；G4 volume_outlining.py 已存在做部分自动校验 | 建议方向: 以 EXACT 模板（≥3 钩子、15-25% 铺垫）为权威回改铁律与核心设计，或明确两套阈值适用场景

F876 | worldbuilding truth 初始化计数与结构错误 | error | P2 | 证据: skills/shenbi-worldbuilding/SKILL.md:82 声称"创建以下 **全部 11 个** truth files"后列举 state 类 8（current_state/chapter_summaries/particle_ledger/subplot_board/audit_drift/volume_summaries/pending_hooks/drift_guidance）+ character 类 2 + intent 类 2 = 12 个；:62-69 与 :104-106 出现两个"## 铁律"节，第二节的条目编号"7."游离 | 根因: truth 清单扩容后计数未更新；铁律 7 追加时插入了新的节标题 | 验证: 手数列举项 12 个；`grep -n "^## 铁律" skills/shenbi-worldbuilding/SKILL.md` → 2 处 | 建议方向: 计数改 12（或对齐 yaml 词表）；合并铁律节

F877 | writing-skills description 违反自身契约 | error | P1 | 证据: skills/shenbi-writing-skills/SKILL.md:3 "Use when creating or modifying any shenbi skill — guides the design, testing, and iteration of new novel-writing skills"；同文件 :40-41 自己规定"description: Use when ... # 只描述触发条件"；AGENTS.md 显式契约"Never describes what the skill does"，severity 表 P1 例"description 写功能" | 根因: 破折号后补了功能摘要 | 验证: 长度脚本输出 119 chars（≤500 合规，但内容违规） | 建议方向: 删除破折号后从句

F878 | using-shenbi description 含功能从句 | error | P2 | 证据: skills/using-shenbi/SKILL.md:3 "— establishes skill discovery and trigger rules for the shenbi novel writing skill system" | 根因: 同 F877 模式；因该从句偏系统机制陈述、且为 meta 技能，降为 P2 | 验证: 同上脚本 124 chars | 建议方向: 截断为纯触发条件

F879 | using-shenbi 引用失效路径 | error | P2 | 证据: skills/using-shenbi/SKILL.md:96 "design spec Section 8"、:112 "Section 4 of design spec"、:120 "docs/specs/2026-06-08-shenbi-design.md" | 根因: 设计文档已迁移至 docs/superpowers/specs/archive/2026-06-08-shenbi-design.md，元技能未跟随 | 验证: `ls docs/specs/2026-06-08-shenbi-design.md` → 不存在；`find docs -name 2026-06-08-shenbi-design.md` → archive 下命中 | 建议方向: 更新三处引用路径

F880 | style-polishing 字段读与 DOT 不一致 | error | P2 | 证据: skills/shenbi-style-polishing/SKILL.md:9-11（genre-config fields 仅 [fatigueWords]）vs :49 DOT "Read genre-config.json (fatigueWords + prohibitions)" | 根因: prohibitions 未进 dict-form reads 的 fields；Layer B 过滤后执行者看不到 prohibitions，与流程图指令冲突 | 验证: frontmatter/DOT 行号对照 | 建议方向: fields 增加 prohibitions 或改 DOT

F881 | short-drafting decisions sidecar 正文零描述 | optimization | P2 | 证据: skills/shenbi-short-drafting/SKILL.md:24-25（writes short/short-N-decisions.json）vs 正文 :44-233 无一句提及 | 根因: repo 通病——chapter-drafting/context-composing/market-radar 同样仅 frontmatter 声明（grep 全库仅 5 文件含 decisions 字样）；schema 由 G2/G4 decisions_validator.py 中央校验兜底 | 验证: `grep -rln "decisions" skills/*/SKILL.md` → 5 个，均在 frontmatter | 建议方向: 接受为规范（中央校验）或在正文加一行 sidecar 说明；不建议单改此技能

F882 | state-settling mode-rules 列出非契约文件 | error | P2 | 证据: skills/shenbi-state-settling/SKILL.md:59-63 把 resonance_trend.md、audit_drift.md 列入"upsert_markdown_row files (output ONLY the new chapter's row)"清单，但二者不在本 skill 契约（:8-29），分别是 review-resonance/各审计的 updates | 根因: 该节把全局 truth 文件模式表误植为执行指令 | 验证: frontmatter updates 列表对照 | 建议方向: 标注"参考：全局模式表"或裁剪到本 skill 所有权文件

F883 | volume-consolidation 结构性小错 | error | M | 证据: skills/shenbi-volume-consolidation/SKILL.md:112-113 连续两个"5."步骤；:68 与 :165 两个"## 输出格式"节且模板不一致（第一版 `## 第一卷` 宽松示例 vs 第二版 `## 第X卷` "必须严格遵循"EXACT 模板） | 根因: EXACT 模板后补未删旧示例 | 验证: 行号对照 | 建议方向: 重编号、删除旧模板保留 EXACT 版

F884 | truth-sync 多章操作 vs 单章 reads | error | P2 | 证据: skills/shenbi-truth-sync/SKILL.md:9（reads 仅 chapters/chapter-N.md）vs :43 DOT "For each modified chapter"、:93 报告"同步范围: 第N章 至 第M章"、:78 交叉校验 characters/**/*.md | 根因: 契约以单章 parametric 表达批量操作；dispatcher 只注入声明 reads，跨章比对缺输入 | 验证: frontmatter/DOT 对照 | 建议方向: reads 扩为 chapters/*.md（或 dispatch 逐章迭代 + 汇总）

F885 | 评分刻度与 description 风格不统一 | optimization | M | 证据: skills/shenbi-score-arc/SKILL.md:3、score-stratum:3、score-volume:3（"Use when scoring 弧段级评分..."中英混排）；审计输出刻度 review-pov:130 / reader-pull:153 / texture:142 / world-rules:132 / spinoff:128 用 "评分: X/10"，resonance:133 与 score-* 用 /100 | 根因: 不同波次技能未统一刻度/语言约定；X/10 为审计内部分、/100 为框架分，混用增加下游解析歧义 | 验证: grep "评分: X" | 建议方向: 统一为 /100 或在输出格式注明刻度语义

## Per-file 报告

### skills/shenbi-review-pov/SKILL.md
- 处置: deep-read
- 声称检查的不变量: [description 只写触发条件且 ≤500；kind:report 无需 decisions sidecar；reads/writes 对齐 truth-files.yaml 词表（chapters/chapter-N.md、genre-config.json、truth/character_matrix.md、truth/current_state.md、audits/chapter-N-<dim>.md glob）；DOT 与正文一致；反合理化表存在；DEPRECATED 标记与路由]
- findings: [F873（被 using-shenbi:52 路由的残留，本文件自身合规）]
- 验证命令: [读全文；`grep -n "truth/character_matrix\|truth/current_state" docs/framework/truth-files.yaml` → 均注册（行 30,33）；description 82 chars ≤500；DOT 节点与"检查执行"5 节一一对应；铁律 5 条对应正文 3 个检查维度；DEPRECATED 注释行 18-19 完整（group-character, 2026-07-19, Do not dispatch）]
- 置信度: high

### skills/shenbi-review-reader-pull/SKILL.md
- 处置: deep-read
- 声称检查的不变量: [同上 + reads 含 plans/chapter-N-plan.md、truth/pending_hooks.md；激活条件引用 genre-config.json auditDimensions 维度 32（本 skill 不直接读 genre-config，声明一致性 OK）]
- findings: [F873（using-shenbi:54 路由残留）]
- 验证命令: [读全文；truth/pending_hooks.md 在词表（yaml:31）；plans parametric 在 patterns（yaml:99）；DOT 与 5 个检查小节对应；备忘第 2 段引用与 chapter-planning 输出格式段 2"读者此刻在等什么"一致（chapter-planning SKILL.md:178）；DEPRECATED 行 17-18 完整]
- 置信度: high

### skills/shenbi-review-resonance/SKILL.md
- 处置: deep-read
- 声称检查的不变量: [kind:report + updates audit_drift/resonance_trend（append_dedup key: chapter，逐章正确）；字段读 POST_WRITE_SELF_CHECK、"1. 当前任务"、style 11/6 与真实文件实况一致；DOT 与正文一致；确定性 helper 引用存在；锚点 AC-001/002/004/005 存在；反合理化表完整；P2.5/评分 0-100 规则正确]
- findings: [F867（其 style 字段声明 11/6 匹配 fixture 而非 style-learning 模板——矛盾根源在 style-learning 侧）；DOT:74 引用 "voice_fingerprint" 字样不在声明 fields 中（并入 F867 附注，M 级）]
- 验证命令: [读全文；`grep -n "POST_WRITE_SELF_CHECK" docs/framework/chapter-file-format.md` → 行 26 存在该标题；chapter-planning:144 `## 1. 当前任务` 存在；`ls benchmarks/anchors/` → AC-001..AC-011；`ls src/shenbi/skill_utils/review_resonance/ calibration/` → 均存在（routing.py/confidence.py）；G4 review_resonance.py:22 `_DETAIL_COLS` 含裸"证据"列与 SKILL:143 声明一致；resonance_trend 行格式与 chapter_loop.py:1352-1365 的 7 列行构建兼容]
- 置信度: high

### skills/shenbi-review-sensitivity/SKILL.md
- 处置: deep-read
- 声称检查的不变量: [description 合规（125 chars）；reads（genre-config/novel.json）注册；kind:report；DOT 一致；反合理化表；默认激活声明；无 warning 级语义与 sensitive-words.md:126 一致]
- findings: [F874]
- 验证命令: [读全文；`awk 'NR==74' | od -c` → "循"+双空格+"定义的"；novel.json/genre-config.json 在词表（yaml:11-12）]
- 置信度: high

### skills/shenbi-review-sensitivity/sensitive-words.md
- 处置: deep-read
- 声称检查的不变量: [被 SKILL.md:65 引用存在；与 SKILL 检查执行 4 步对应（平台禁忌词/本书禁忌词/内容边界/合规综合）；与 review-anti-ai 的 prohibitions 分工描述（error vs blocking error）与 anti-ai 现行契约一致（anti-ai 已 DEPRECATED→group-craft，该协作段属文档漂移但引用对象正确）]
- findings: [无（anti-ai 协作段指向已弃用技能属轻微漂移，低于 M 阈值不立案；F873 已覆盖根因）]
- 验证命令: [读全文；4 节结构与 SKILL.md:67-70 执行顺序一一对应；`grep -n "review-anti-ai" sensitive-words.md` → 行 87-90]
- 置信度: medium（平台政策性内容无法本地验证，仅结构与一致性审查）

### skills/shenbi-review-spinoff/SKILL.md
- 处置: deep-read
- 声称检查的不变量: [description（152 chars）；reads parent_canon/world/rules/pending_hooks 均在词表；kind:report；DOT 一致；反合理化表；激活条件=parent_canon 存在]
- findings: [F885（输出"评分: X/10"刻度，行 128）]
- 验证命令: [读全文；`grep -n "parent_canon\|world/rules" docs/framework/truth-files.yaml` → 行 43/24 注册；spinoff-violations.md 存在且被 :71 引用；非 DEPRECATED（grep 确认不在 15 个弃用名单），using-shenbi:61 路由合法]
- 置信度: high

### skills/shenbi-review-spinoff/spinoff-violations.md
- 处置: deep-read
- 声称检查的不变量: [4 类违规与 SKILL.md 检查执行 4 节一一对应；严重度统一为 error 与 SKILL 铁律一致；parent_canon.md 必备字段模板与 SKILL 输出格式可对接]
- findings: [无]
- 验证命令: [读全文；节 1-4 ↔ SKILL "### 1-4" 步骤对照一致；节 7"统一为 error（无 warning）"与 SKILL 铁律 2-5 的 error 语义一致；SKILL 输出格式含 WARNING 行（:132）与 violations"无 warning"有轻微张力——SKILL 的 WARNING 行针对建议修复列表模板，可解释，不立案]
- 置信度: high

### skills/shenbi-review-texture/SKILL.md
- 处置: deep-read
- 声称检查的不变量: [description（137 chars）；reads 注册；DOT 与 5 个检查小节一致；与 pacing/anti-ai 的边界消歧段（AGENTS.md 认可的消歧括号例外）；反合理化表；DEPRECATED 标记]
- findings: [F873（using-shenbi:53 路由残留）；F885（X/10 刻度，行 142）]
- 验证命令: [读全文；DEPRECATED 行 17-18（group-craft）；genre-config.json/plans 注册；消歧段 :43 与 anti-ai 分工表述无功能描述违规]
- 置信度: high

### skills/shenbi-review-world-rules/SKILL.md
- 处置: deep-read
- 声称检查的不变量: [description（118 chars）；reads 7 文件均注册（world/ 五件 + truth/chapter_summaries/current_state）；DOT 与 4 检查节一致；反合理化表；DEPRECATED 标记]
- findings: [F873（using-shenbi:49 路由残留 + audit_layer.py:44 运行时矩阵残留）；F885（X/10 刻度，行 132）]
- 验证命令: [读全文；`grep -n "world/power_system\|world/locations\|world/story_bible\|truth/chapter_summaries" docs/framework/truth-files.yaml` → 行 14-15,27,22 注册；DEPRECATED 行 21-22（group-factual）]
- 置信度: high

### skills/shenbi-score-arc/SKILL.md
- 处置: deep-read
- 声称检查的不变量: [description ≤500；reads（truth/arcs/arc-N.md、book_spine、volume_summaries、book_strata、benchmarks/anchors/）均注册；writes audits/arc-N-score.md 注册（Wave 3）；updates audit_drift append_dedup 且正文:69 有 append 说明（与 score-volume 对照为正确做法）；auto-check 常量（90/0.4/0.6/94）与 AGENTS.md 阈值（≥94 晋级、≥90 通过）一致；锚点 AC-003/AC-009 存在；反合理化表；DOT 一致]
- findings: [F885（description 混排）；key: chapter 用于弧段级 audit_drift 条目语义偏宽（弧段≈12 章粒度），按 dispatch_helper:1072-1076 key 为 caller 语义职责，不单独立案（附注）]
- 验证命令: [读全文；`grep -n "audits/arc-N-score\|truth/arcs/arc-N" docs/framework/truth-files.yaml` → 行 49,59 注册；`ls benchmarks/anchors/` → AC-003/009 在列；auto-check "invariants: hard binary pass le total" 为生成器占位文本（M 级，三 score 技能同源，不立案）]
- 置信度: high

### skills/shenbi-score-stratum/SKILL.md
- 处置: deep-read
- 声称检查的不变量: [同 score-arc；writes audits/stratum-N-score.md 注册；触发=每 36 章+滚动 与 triggers.py:66-67 注释一致；锚点 AC-004/AC-008 存在]
- findings: [F872, F885]
- 验证命令: [读全文；`grep -rn "score-stratum" src/shenbi/pipeline/triggers.py` → :15,33,67（L4 先写数据、stratum 后写诊断字段的写序约束存在于代码注释而非技能正文）；`ls benchmarks/anchors/` → AC-004/008 在列]
- 置信度: high（F872 严重度为 medium 置信：设计意图从 triggers.py 注释推断）

### skills/shenbi-score-volume/SKILL.md
- 处置: deep-read
- 声称检查的不变量: [同 score-arc；writes audits/volume-N-score.md + truth/volume_score_trend.md 注册；触发=卷边界且在 volume-consolidation 后 与 triggers.py:234-247 顺序一致；锚点 AC-003/AC-006 存在；硬二元 4 项与 wave3 设计稿一致]
- findings: [F871, F885]
- 验证命令: [读全文；`grep -n "volume_score_trend" docs/framework/truth-files.yaml` → 行 45 注册但无技能正文支撑；`grep -n "def \|Route\|trend" src/shenbi/gates/g4/score_volume.py` → 只校验 RouteC/RouteA；`sed -n 241,246p src/shenbi/pipeline/triggers.py` → output_path 仅 audits/volume-N-score.md；wave3 设计稿 :594-597 含被丢失的 trend 行格式（键=volume）]
- 置信度: high

### skills/shenbi-sequel-writing/SKILL.md
- 处置: deep-read
- 声称检查的不变量: [description（171 chars）；reads snapshots/chapter-NNN/*（glob 注册 snapshots/chapter-*/*）+ truth/*.md（glob）+ outline 两件；updates truth/*.md create_or_overwrite 有专门的范围说明段（:39 限定为断点恢复一次性操作、字段所有权归属原 skill）；DOT 与 4 步一致；反合理化表；续写链路 5 技能引用全部存在；测试模式人工确认隔离段合规]
- findings: [无（snapshots/chapter-NNN/ 目录概念与 D20 平文件快照并存——yaml 注释行 93-96 已声明 2026-08-15 起 manifest.json 为真实 snapshot-manage 契约写且 glob snapshots/chapter-*/* 覆盖，sequel 的目录式读取合法）]
- 验证命令: [读全文；`python3 -c "...index.json...['snapshots/chapter-NNN/*']"` → reads=[sequel-writing] writes=[snapshot-manage] 闭环；链路引用 shenbi-chapter-planning/foreshadowing-plant/chapter-drafting/state-settling/snapshot-manage 目录均存在（ls skills/）；truth/*.md 在 globs（yaml:120）]
- 置信度: high

### skills/shenbi-short-drafting/SKILL.md
- 处置: deep-read
- 声称检查的不变量: [description（168 chars）；reads 字段（genre-config fatigueWords/pacing/chapterTypes 在代码验证存在、style 11/6/9 匹配真实产物）；writes chapters/chapter-N.md + short/short-N-decisions.json（词表 yaml:141 注册）；DOT 三步流程一致；EXACT 模板列名/自动检查规则完备；反合理化表]
- findings: [F881, F867（其 style 字段依赖的真实结构由 style-learning 模板漂移威胁）]
- 验证命令: [读全文；`grep -rn "fatigueWords" src/shenbi/pipeline/chapter_loop.py` → 存在（字段名正确）；`grep -n "short/short-N-decisions" docs/framework/truth-files.yaml` → 行 141 + glob 行 151；正文审计清单/汇总表 EXACT 模板与"可自动检查的计数规则"表内部一致]
- 置信度: high

### skills/shenbi-short-outline/SKILL.md
- 处置: deep-read
- 声称检查的不变量: [description（168 chars）；reads（novel.json、truth/author_intent.md、outline/story_frame.md）注册；writes outline/short_story_map.md 注册（yaml:33）；≤30 章阈值全文一致（铁律 2/短篇特征表/复核 6 项）；DOT 三步一致；反合理化表]
- findings: [无]
- 验证命令: [读全文；`grep -n "outline/short_story_map" docs/framework/truth-files.yaml` → 行 33 注册；下游 short-drafting reads 引用同一文件闭环；下游任务清单引用 shenbi-short-drafting 存在]
- 置信度: high

### skills/shenbi-short-packaging/SKILL.md
- 处置: deep-read
- 声称检查的不变量: [description（153 chars）；reads（short_story_map、chapters/*.md glob、story_bible、author_intent）注册；writes import/packaging/*（glob 注册 yaml:137 + index.json 写者=本技能）；6 步流程与 DOT 一致；多版本人工选定铁律；反合理化表]
- findings: [无（kind:artifact 产自然语言包装候选、含人工选定环节——按 AGENTS.md decisions-sidecar 规则属可选增强而非违规：artifact 类且选定由人类在文件内"选定"栏完成，不单独立案，记为确定性替换候选附注）]
- 验证命令: [读全文；`grep -n "import/packaging" docs/framework/truth-files.yaml` → 行 72（概念）+ 137（glob）；index.json 确认 import/packaging/* 写者=shenbi-short-packaging]
- 置信度: high

### skills/shenbi-snapshot-manage/SKILL.md
- 处置: deep-read
- 声明检查的不变量: [description（152 chars）；writes snapshots/chapter-NNN/* + manifest.json 被 glob snapshots/chapter-*/* 与 2026-08-15 yaml 超越注释覆盖；checksum 强制命令确定性（禁止 LLM 生成）+ 随机复算；回滚 HARD-GATE 人类确认；回滚后强制 truth-sync；保留策略引用 config.snapshot_retention_chapters；DOT 与 4 操作一致；反合理化表]
- findings: [无（truth/foreshadowing_recall_result.md 在 :69/:118 被 truth/*.md glob 涵盖且该文件为 foreshadowing-recall 注册写者（index.json:624），引用合法）]
- 验证命令: [读全文；`python3 -c "...index.json...['snapshots/chapter-NNN/manifest.json']"` → writes=[snapshot-manage]；`grep -n "snapshot_retention" src/shenbi/pipeline/*.py` → 配置项存在（triggers/snapshot 模块引用）；yaml 行 93-96 超越注释与本 skill 契约对齐]
- 置信度: high

### skills/shenbi-state-settling/.gitkeep
- 处置: deep-read
- 声称检查的不变量: [空占位文件，无内容]
- findings: [无]
- 验证命令: [`stat -f%z` → 0 字节]
- 置信度: high

### skills/shenbi-state-settling/SKILL.md
- 处置: deep-read
- 声称检查的不变量: [description（109 chars，带引号包裹的合法 YAML）；writes/updates 7 文件均注册；HARD-GATE 逐章强制；DOT 9 类变化与提取模板 9 节一致；人工审批门禁模板；pending_hooks 4 写者字段分工边界（:160-165）与 foreshadowing 技能族一致；反合理化表；truth-files-reference.md 引用存在]
- findings: [F869, F870, F882]
- 验证命令: [读全文；frontmatter :12-23 vs 正文 :55-58/:149-158 模式矛盾对照；index.json protagonist.md 写者不含本技能；mode-rules :59-63 文件清单 vs 契约 updates 清单；truth/state-settling-decisions.json 曾在 writes 后被 2026-08-02 token-efficiency 计划删除（archive plan :489-515），现行契约与删除决策一致（yaml:58 残留注册属框架侧已立案问题 T1-05，不重复立案）]
- 置信度: high

### skills/shenbi-state-settling/truth-files-reference.md
- 处置: deep-read
- 声称检查的不变量: [10 文件清单与 state-settling 契约文件一致；9 类事实与 SKILL DOT/模板一致；"只追加不修改/增量"原则与 SKILL 铁律 4 一致]
- findings: [无（"audit_drift.md 每章"更新频率表述与本 skill 无 audit_drift 写权一致——该表为全文件参考而非本技能写权声明，可接受）]
- 验证命令: [读全文；文件清单与 truth-files.yaml 词表行 30-46 对照（10 文件全部注册）；9 类编号与 SKILL.md:117-145 模板逐一对应]
- 置信度: high

### skills/shenbi-story-architecture/.gitkeep
- 处置: deep-read
- 声称检查的不变量: [空占位文件]
- findings: [无]
- 验证命令: [`stat -f%z` → 0 字节]
- 置信度: high

### skills/shenbi-story-architecture/SKILL.md
- 处置: deep-read
- 声称检查的不变量: [description（123 chars）；reads（world/story_bible、characters/**/*.md glob）注册；writes story_frame/volume_map/rhythm_principles 三件注册且 index.json 写者=本技能；职责边界段与 pacing-design/volume-outlining 闭环；DOT 一致；散文骨架铁律；反合理化表]
- findings: [无（novel.json 的 genre/core_concept/themes 键被 seed_parser.py:120-121 验证存在）]
- 验证命令: [读全文；`python3 -c "...index.json..."` → outline/rhythm_principles.md writes=[story-architecture] updates=[pacing-design]（骨架→细化分工在词表层面闭环）；genesis.py:64 将本技能挂到 story_frame 输出，与契约一致]
- 置信度: high

### skills/shenbi-style-learning/SKILL.md
- 处置: deep-read
- 声称检查的不变量: [description（173 chars）；reads（chapters/*.md、import/source/*.txt、novel.json、genre-config.json）注册；writes style/style_profile.md 注册；compute_stats.py 确定性优先（铁律 1 + 强制命令行）；Bootstrap 双分支 DOT；反合理化表；可重现性铁律]
- findings: [F867；附注 M：模板头部"生成方式: 纯统计（零 LLM）"（:168）与 DOT"LLM writes style_profile.md (stats + prose)"（:46）表述矛盾——综合画像为 LLM 散文，非零 LLM]
- 验证命令: [读全文；`grep -n "^## " tests/fixtures/style-profile-example.md` → 11 节（6/9/11 编号）；`grep -n "^## " 本文件` → 模板 8 节（5/8 编号）；`grep -rn "对白占比\|dialogue_ratio\|各章统计" src/shenbi/skill_utils/style_learning/compute_stats.py` → 0 命中（脚本输出键仅 sample/sentence_length/paragraph_length/ttr/bigrams/trigrams/4grams/punctuation/connectives/rhetoric/ai_markers/transition_density，compute_stats.py:336-355）；模板缺四元节但统计指标表 :126 声明四元]
- 置信度: high

### skills/shenbi-style-polishing/SKILL.md
- 处置: deep-read
- 声称检查的不变量: [description（138 chars）；updates chapters/chapter-N.md mode: merge_prose + no_op_behavior: skip_write（mode 声明完整）；style 字段 11/6/1/2 匹配真实产物编号；边界铁律 5 与 shenbi-anti-detect 分工（目录存在已验证）；反合理化表；字数 ±15% 约束]
- findings: [F880]
- 验证命令: [读全文；`ls -d skills/shenbi-anti-detect` → 存在；frontmatter :9-11 vs DOT :49 字段不一致对照]
- 置信度: high

### skills/shenbi-truth-sync/SKILL.md
- 处置: deep-read
- 声称检查的不变量: [description（187 chars）；updates truth/*.md create_or_overwrite 配专门范围说明（:37 人工仲裁+离线对齐限定）；9 类提取与 state-settling 对齐；提取/推断分离铁律（≤20% + [inferred] 标注）；角色档案交叉校验对应 reads characters/**/*.md；DOT 一致；反合理化表（2 条偏少但存在）]
- findings: [F884]
- 验证命令: [读全文；reads :9 单章 vs DOT :43 多章对照；铁律 3"增量更新"与 mode create_or_overwrite 的张力由 :37 范围说明缓解（仲裁后整文件写），不单独立案]
- 置信度: high

### skills/shenbi-volume-consolidation/SKILL.md
- 处置: deep-read
- 声称检查的不变量: [description（105 chars）；reads 3 文件注册；writes truth/volume_summaries.md + updates chapter_summaries append_dedup key:chapter（正确：逐章）；CP 术语消歧段；弧门阈值（≥80 且兑现质量≥15）与 review-arc-payoff、using-shenbi:135 三方一致；字数统计验证表；反合理化表]
- findings: [F868, F883]
- 验证命令: [读全文；reads :7-10 无 volume_summaries.md；writes :12-13 create_or_overwrite；"追加到"三处 :72/:114/:169；`sed -n 940,975p src/shenbi/pipeline/dispatch_helper.py` → 内容缩小防护仅 chapters/；`grep -rn "volume_summaries" src/shenbi/pipeline/dispatch_helper.py` → 无内容注入点；双"5"步骤 :112-113；双"## 输出格式" :68/:165]
- 置信度: high

### skills/shenbi-volume-outlining/SKILL.md
- 处置: deep-read
- 声称检查的不变量: [description（166 chars）；reads 含 volume_map.md（覆写前先读，与 F868 形成正确对照）；updates outline/volume_map.md create_or_overwrite（index.json 注册）；EXACT 节标题校验规则 6 项；auto-check invariants（entity hooks/kr count/tension sum）与 G4 volume_outlining.py 存在对应；反合理化表；职责边界与 story-architecture 闭环]
- findings: [F875；附注 P2/M："追加到 volume_map.md"（:58/:122）与 create_or_overwrite 模式并存——因文件在 reads 中可整文件重 emit，无数据丢失，仅措辞与模式不一致（对照 F868 的关键差异）]
- 验证命令: [读全文；:66 vs :202/:239 钩子数矛盾；:100 vs :175/:184 铺垫段区间矛盾；`ls src/shenbi/gates/g4/volume_outlining.py` → 自动校验器存在]
- 置信度: high

### skills/shenbi-world-extraction/SKILL.md
- 处置: deep-read
- 声称检查的不变量: [description（205 chars）；reads（import/analysis/03_world.md、04_plot.md 被 import/analysis/*.md glob 覆盖 + chapters/*.md）；writes world/ 五件全注册；反向/正向职责消歧段；DOT 与 4 提取维度一致；铁律 3 rules ≤10 条与模板一致；反合理化表 + 缺陷证据四要素格式完整]
- findings: [无]
- 验证命令: [读全文；`grep -n "import/analysis" docs/framework/truth-files.yaml` → 概念行 70 + glob 行 132；world 五件词表行 20-24；`grep -rn "world-extraction" skills/using-shenbi/SKILL.md` → :79 路由合法（非弃用）]
- 置信度: high

### skills/shenbi-worldbuilding/.gitkeep
- 处置: deep-read
- 声称检查的不变量: [空占位文件]
- findings: [无]
- 验证命令: [`stat -f%z` → 0 字节]
- 置信度: high

### skills/shenbi-worldbuilding/SKILL.md
- 处置: deep-read
- 声称检查的不变量: [description（120 chars）；reads novel.json；writes（novel.json、genre-config.json、world/ 三件、truth/*.md glob）注册；HARD-GATE 世界观前置；genre-config stub 与 shenbi-genre-config 细化分工；story_bible 四段式模板；反合理化表；询问流程逐问等待]
- findings: [F876；附注：writes truth/*.md create_or_overwrite 仅限 genesis 初始化（DOT 有 novel.json 存在性分支），非新项目上运行有覆写既有 truth 风险——技能定位为创建期技能，不单独立案（P2 边界，建议正文加"仅当目录不存在"守卫说明）]
- 验证命令: [读全文；:82 计数 11 vs 列举 12（8 state + 2 character + 2 intent）；`grep -n "^## 铁律" 本文件` → 2 处；词表 truth 概念行 30-46 全部覆盖其列举文件]
- 置信度: high

### skills/shenbi-writing-skills/.gitkeep
- 处置: deep-read
- 声称检查的不变量: [空占位文件]
- findings: [无]
- 验证命令: [`stat -f%z` → 0 字节]
- 置信度: high

### skills/shenbi-writing-skills/SKILL.md
- 处置: deep-read
- 声称检查的不变量: [meta:true 无 contract（元技能豁免）；自身践行 DOT 流程图/铁律/反理性化三要素；description 陷阱表与 AGENTS.md 契约一致；说服心理学原则表；RED/GREEN/REFACTOR 压力测试方法；领域理性化模式表]
- findings: [F877]
- 验证命令: [读全文；:3 破折号后功能从句 vs :37-44 自身 frontmatter 规则；长度 119 chars]
- 置信度: high

### skills/using-shenbi/.gitkeep
- 处置: deep-read
- 声称检查的不变量: [空占位文件]
- findings: [无]
- 验证命令: [`stat -f%z` → 0 字节]
- 置信度: high

### skills/using-shenbi/SKILL.md
- 处置: deep-read
- 声称检查的不变量: [meta:true；1% 规则；技能检查顺序 DOT；触发映射表路由目标全部存在且非弃用；默认/条件审计清单与现行技能族一致；正向质量门（resonance/arc-payoff）描述与两技能契约一致；resonance_pending 路径与 drift 解析器行为一致；HARD-GATE 无基础不写作]
- findings: [F873, F878, F879]
- 验证命令: [读全文；`grep -l "DEPRECATED" skills/*/SKILL.md` → 15 个，其中 14 个出现在本文件触发表/审计清单（行 44-63,73-74,124-126）；`grep -c "group-" skills/using-shenbi/SKILL.md` → 0；`ls docs/specs/2026-06-08-shenbi-design.md` → 不存在（实际在 docs/superpowers/specs/archive/）；`grep -n "pending" src/shenbi/skill_utils/drift_detection/compute_drift.py` → :166,:207 确认 pending 行跳过语义（resonance_pending 描述正确）；触发表中非弃用技能抽查（shenbi-length-normalizing、shenbi-review-highpoint、shenbi-review-era、shenbi-review-fanfic、shenbi-market-radar、shenbi-genre-config、shenbi-foundation-review、shenbi-drift-guidance、shenbi-intent-management、shenbi-chapter-pattern、shenbi-canon-import、shenbi-import-analysis、shenbi-review-long-span）目录均存在且无 DEPRECATED 标记]
- 置信度: high

## 确定性替换候选清单（rubric #8）

| skill | 环节 | 理由 |
|-------|------|------|
| shenbi-style-learning | style_profile.md 组装 | compute_stats.py 已产 JSON；模板渲染（含 11 节表格）可由 Python 确定性生成，仅综合画像散文需 LLM——可消除 F867 类漂移（fixture 声称"纯统计（零 LLM）"） |
| shenbi-snapshot-manage | 快照创建/清单/checksum | 纯文件操作（复制 + sha256 + manifest JSON）；SKILL 已给出确定 性 checksum 命令，整套 create/list/rollback 均可 Python 化，LLM 无增量价值 |
| shenbi-score-arc / score-stratum / score-volume | final_score 与 passed/tier 计算 | auto-check 已声明公式（0.6/0.4 加权 + 阈值 90/94 + 硬二元门）；LLM 只应产维度分，合成与判定应为 Python（对齐 resonance 的 review_resonance/calibration helper 模式） |
| shenbi-review-sensitivity | 本书禁忌词匹配 | sensitive-words.md §3 定义精确串匹配/大小写不敏感/空白变体——纯字符串运算可 Python 化；LLM 保留上下文严重度判断 |
| shenbi-short-drafting | 审计清单计数与字数 floor 校验 | SKILL 自带"可自动检查的计数规则"表（列名/格式/6 维计数/floor=target_word_count/章节数），全部可确定性校验 |
| shenbi-volume-outlining | EXACT 模板结构校验 | 节标题 6 项/KR 3-5/张力 100%/钩子 ≥3 已有 G4 checker，可再前置为写前 lint（规则矛盾 F875 修后） |
| shenbi-state-settling | 跨文件一致性验证表 | 6 行固定字段对照（位置/资源/关系/情绪/伏笔/摘要）为确定性 diff，可脚本化 |
| shenbi-sequel-writing | Step 1 断点定位 | "最近 snapshots/chapter-NNN/ 或最后一章"为目录扫描 + 排序，Python 可定 |
| shenbi-short-packaging | 候选数量/平台覆盖统计 | 汇总表候选计数与平台准备度矩阵可确定性汇总（弱候选，收益低） |

## 低置信度文件列表

- skills/shenbi-review-sensitivity/sensitive-words.md — 结构/一致性 high，平台政策内容本身无法本地验证（medium 已在条目标注）
- skills/shenbi-score-stratum/SKILL.md — F872 的"设计意图存在性"由 triggers.py 注释推断（正文无实证），严重度判定 medium 置信
- skills/shenbi-short-packaging/SKILL.md — decisions-sidecar 可选性的判断（AGENTS.md 规则边界：artifact+人类选定栏 vs decisions.json）属规则解释
- skills/shenbi-using-shenbi（F873 严重度 P1 vs P0 边界）— "Do not dispatch 契约被路由静默违反"字面符合 P0，但因弃用技能本体完整可执行、危害为重复审计/漂移而非错误数据，按 P1 报；终审可上调

## 未覆盖文件列表

（无——34/34 全部 deep-read）
