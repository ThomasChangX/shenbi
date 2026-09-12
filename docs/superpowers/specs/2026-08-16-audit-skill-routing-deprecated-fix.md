> **Date:** 2026-08-16 | **Status:** Design (Revised 2026-09-12 · 价值门 GO + 事实核实 + 设计审查轮 1/2) | **Severity:** 🟠 P1
> **系列:** 2026-08-15 全项目深度审计 · 阶段 5 修复 spec（簇 C21）| **代表 finding:** F873 | **簇规模:** 12 条 | **严重度上限:** P1
> **范围:** skills/using-shenbi/SKILL.md（触发表）、tests/tiers/deps.json、src/shenbi/pipeline/genesis.py（GENESIS_STEPS）、src/shenbi/pipeline/triggers.py（TRIGGER_STEPS）、src/shenbi/pipeline/audit_layer.py（GENRE_ACTIVATION_MATRIX）、src/shenbi/pipeline/dispatch_helper.py（OPTIONAL_READS）、5+ 个技能 description、DEPRECATED 技能正文 | **证据等级:** 实验佐证（Z8-a/b/c/review-r1，F873 verified；F905 源自 2026-08-14 轮 verified）
> **与既有 spec 关系:** #23 的 DEPRECATED 接线拆除面（F904/F950/F1004）并入本 spec；#9 的 deps.json 补登归 C22 词表对账，本 spec 只管路由/触发/描述契约；#23 驳斥归档时补登其残留 **F905 双重调度语义面**（见 T1.6）
> **编号注记（2026-09-12 事实核实）:** 本文 F905 = `audit-runs/2026-08-14/findings-ledger.md`:691（review-sensitivity 双重调度，verified，#23 驳斥时补登）——与 `2026-08-15/findings-ledger.md`:401 的同名 F905（Z9-a deps.json 缺 5 技能）为两轮独立命名空间的异物（ID-NAMESPACE-MIGRATION.md 裁决，旧 ID 不改）

# C21 · 技能注册与触发路由漂移修复（skill-routing-deprecated）

## 背景（根因 + 证据 · 行号已按 2026-09-12 main HEAD fed00294 校正）

**根因**：技能退役走了"标 DEPRECATED"半步就停——deps.json 仍注册、using-shenbi 触发表仍路由（14 个 DEPRECATED 技能）、GENESIS_STEPS 仍派发、genre 激活矩阵仍路由 5 个 DEPRECATED 单体审计，后继技能（group-*、foreshadowing-lifecycle）零触发行；同时 description 契约（AGENTS.md：仅 when-to-use 触发条件）大面积违反——旧技能还在被路由、新技能没人路由得到，触发体系指向已死链路。

代表证据（2026-09-12 驳斥复核后现状，全部协调者亲证）：
- **F873**（P1，verified，存活）：using-shenbi 触发表路由 **14 个 DEPRECATED 技能**（:44 anti-ai 默认行、:45 continuity、:46 character、:47 pacing、:48 foreshadowing、:49 world-rules、:50 dialogue、:51 motivation、:52 pov、:53 texture、:54 reader-pull、:63 memo-compliance、:73 plant、:74 track）；默认审计列 :124 含 3 个 DEPRECATED（anti-ai/continuity/character）；:126 条件审计 Phase 列表混入 9 个 DEPRECATED；**0 处路由到 group-*/foreshadowing-lifecycle 后继**（grep -c = 0×5）
- **F887**（P1，存活，面已扩展）：genesis.py:70 GENESIS_STEPS step 9 派发 DEPRECATED 的 shenbi-foreshadowing-plant；:97 `_INDEX_UPDATE_SKILLS` 仍含 plant；**triggers.py:297 TriggerStep plant（volume_boundary expand）是活派发面**（经 run_triggered_skills → dispatch_skill 直发 LLM，比原措辞"正文引用"更重）；陈旧正文引用现况：truth_readers.py:3、chapter_loop.py:1583、truth_index.py:177、chapter_loop.py:3200-3201 死分支（`if "foreshadowing-track" in step.skill:` 永假——STEP_NAME_MIGRATIONS :282-284 已把旧名迁移为 lifecycle）。原候选之一的 chapter_loop plant_hooks_from_plan 死 handler 已由 PR #127（00355661，spec #33）删除，退出本 spec
- **F816**（P1，存活）：plant DEPRECATED 但 using-shenbi :73 与 deps.json :48 仍路由/注册；lifecycle 未进触发表（deps.json :71 drafting 已含 lifecycle——注册面后继已进，路由面未进）
- **F834**（P1，存活）：触发映射路由 8 个 DEPRECATED 且 4 个 group-* 替代者零触发行；DEPRECATED 正文仍自称"默认激活/每章必查"（实证：review-continuity/SKILL.md:45、foreshadowing-track/SKILL.md:39）
- **F905**（P1，2026-08-14 轮，存活，行号漂移已校正）：chapter_loop.py:249-254 固定 ChapterStep 14 派发 shenbi-review-sensitivity（原 :241-246）；audit_layer.py:46 GENRE_ACTIVATION_MATRIX 含 `"sensitivity"` 同名路由——run_audit_layer :192-198 在固定审计步之后无条件派发全部激活项、**零去重护栏**（grep dedup/already/skip 零命中）；机制根因：get_active_genre_audits 的 `_CORE_CIRCLE_KEYS`（:58-68）漏列 sensitivity，与 :40-43 头注释"Core-circle dimensions are NOT here"自相矛盾；matrix :49 `"dialogue"` 路由 DEPRECATED 技能
- **路由面第四处（驳斥复核新发现，归 F873/F834 同族）**：GENRE_ACTIVATION_MATRIX（audit_layer.py:45-55）路由 **5 个 DEPRECATED 单体审计**——worldRules→review-world-rules（:47）、motivation（:48）、dialogue（:49）、texture（:50）、readerPull（:54）；BOUNDARY_TRIGGERS（:99-104）四项均非 DEPRECATED（干净）
- **F835**（P1，存活）：4 个 review-group-* 的 description 全部描述"做什么/怎么调度"、无 "Use when"（group-character/craft/factual/plan SKILL.md:3 原文在案）
- **F877**（P1，存活）：shenbi-writing-skills description 含功能描述从句（:3 破折号后 "guides the design, testing, and iteration"）
- **F815**（P1，**降级**）：四子项中 (d) 之半——bridge_tracker.md 写声明已由 PR #202（457450b5，spec #58 C20）补入 contract（writes: append_dedup key bridge_id + reads + 写纪律段），退出本 spec；存活子项：(a) description 非触发式（:3 "Combined foreshadowing lifecycle -- recall… track… plant… in a single call"）(b) lifecycle-states.md/hook-types.md 相对引用落在他 skill 目录（:64/:108，实际在 track/plant 目录内，lifecycle 自身目录仅 SKILL.md）(c) :84 "Set initial lifecycle_state to ACTIVE" 与输出示例 :161 PLANTED 及 :65 状态机起点矛盾 (d) 残半——audits/chapter-N-foreshadowing.md 输出（:140-142）仍不在 contract writes/updates
- P2：F355（OPTIONAL_READS 死条目——**收窄**：dispatch_helper.py:424-425 plant/track 两条确定死；context-composing 条**裁定保留**——该技能未标 DEPRECATED、仍被触发表 :40 路由、deps.json :49 注册、PR #202 刚修其契约、G4/G5/ownership/cli 注册齐全，条目服务活的显式派发；chapter_loop.py:135-136 注释误标其 deprecated 由 T1.2 纠正）、F817（recall DEPRECATED 仍注册 deps.json :69 + 「last_reinformed」拼写漂移在 recall SKILL.md:58——正名 last_reinforced 见同文件 :48）、F819（track DEPRECATED 仍注册 deps.json :64 + 字段分工与 DOT 矛盾 + foreshadowing_ledger.md 死引用 :156——现为 lint_contract_prose.py:91-92 allowlist 豁免，修复后须同步撤该 allowlist 条目）、F842（location-builder description 含功能子句）、F878（using-shenbi description 功能从句 :3，较轻）

## 目标

1. **路由一致**：触发表 / deps.json / GENESIS_STEPS / TRIGGER_STEPS / GENRE_ACTIVATION_MATRIX 五处路由面对 DEPRECATED 技能零路由、零注册、零派发；后继技能全部有触发行
2. **description 契约合规**：全仓 74 个 skill 的 description 仅为 when-to-use 触发条件（≤500 字符，AGENTS.md 契约），违规者改写；契约检查器能检出全部存活违规形态（当前启发式漏检，见 T2.7）
3. 防回潮：lint 检查"DEPRECATED ⇒ 不得出现在任何路由面"+"description 契约"

## 任务分解

### T1 · 路由与派发面拆除（P1 核心）

1. **using-shenbi 触发表**（F873/F834）：删 14 个 DEPRECATED 路由行（:44-54/:63/:73-74）；为 4 个 group-* 与 foreshadowing-lifecycle 补触发行；默认审计列 :124 同步——3 个 DEPRECATED 出列、后继进列；:126 条件审计 Phase 列表的 DEPRECATED 项同步清理或改指后继
2. **GENESIS_STEPS 换 lifecycle**（F887，D 连锁——七处接线面同步）：genesis.py:70 step 9 skill 换 shenbi-foreshadowing-lifecycle（契约就绪：lifecycle genesis 模式读 story_frame/volume_map、输出 truth/pending_hooks.md 与现 output_path 一致）；:97 `_INDEX_UPDATE_SKILLS` 同步换名（否则 Route A 索引不刷新）；**配套接线**：①gates/g4/generic.py:327-328 与 gates/shared.py G4_CHECKER_SKILLS :416-417——lifecycle 需专属 G4 checker（现仅 plant/track 注册，lifecycle 落 generic 检查会丢 pending_hooks 结构校验）；g4/foreshadowing_{plant,track}.py 两 checker 模块的处置随此定稿（改造为 lifecycle checker 或删除——模块内 `G4-foreshadowing-{plant,track}` 标识串与 docstring 不得残留，否则验收 1 永红）②contracts/ownership.py:82-85 pending_hooks.md FileOwnership 增 lifecycle 行（genesis 首写 record_create 与每章 record_field 两义与单级模型的取舍在 plan 定稿）③gates/g5.py:289-290 期望输出映射同步 ④lifecycle SKILL.md:115 genesis 模式 "writes: same as default mode" 措辞与 frontmatter writes（仅 bridge_tracker.md）矛盾的定稿（genesis 新项目无 bridge_tracker.md，首写语义须明确）⑤contracts/schemas/hooks.py:3-4 与 :26 两处以 foreshadowing-track/SKILL.md 为六态权威源——改指 lifecycle SKILL.md 或改自证（DEPRECATED 正文不得充当活 schema 权威，与 T1.5 同理）⑥deps.json `_tool_hashes` :255-256 钉住 g4/foreshadowing_{track,plant}.py 哈希——checker 模块被触后须重跑 tests/lock-tool-hashes.sh 对账 ⑦tools/migrate_contract_to_frontmatter.py:205/:211 硬编码 plant/track（一次性迁移工具，顺手清）。**triggers.py:290-301 TriggerStep plant 活派发面删除**（volume_boundary expand 项——若卷界伏笔扩展仍需触发，改派 lifecycle 并核对 mode 语义，裁决在 plan）；陈旧正文引用同步：truth_readers.py:3、chapter_loop.py:1583、truth_index.py:177、chapter_loop.py:3200-3201 死分支、chapter_loop.py:135-136 退役注释中 context-composing 误标纠正（该技能未 DEPRECATED，见 T1.4 裁决）
3. **deps.json 拆注册**（F816/F817/F819，E 连锁）：移除 DEPRECATED 技能注册（plant :48、track :64、recall :69 + audit 段 :87-:102 的 dialogue/pacing/texture/pov/motivation/world-rules 等 DEPRECATED 项）；**tier 归属注记**：lifecycle 现仅 drafting 注册（:71），plant 原 planning 前置（:48）——planning tier 是否需 lifecycle 后继由 plan 按 T2 阶段门禁语义裁决；**连锁处置**：tools/lint_repo_consistency.py:237-251 `check_skill_deps_closure` 是双向闭包（磁盘目录必须在册）——本 spec 不做物理删除（风险节明示），删注册必触发 "skill dirs not registered" 红灯 → 闭包检查同步加 DEPRECATED 豁免（DEPRECATED 技能从"须注册"改判"禁注册"，与 T3 防回潮 lint 语义合一）；gates/cli.py:37-38 短名映射与 g5.py/generic.py/ownership.py 的 plant/track 注册行按 T1.2 换名后继处置（换 lifecycle 或删除，plan 裁决）；与 C22 F231 对账门禁协同——本 spec 删条目 + 立豁免，C22 立三向闭包
4. **F355 收窄执行**：OPTIONAL_READS 删 plant/track 两条死条目（dispatch_helper.py:424-425）；**context-composing 裁决为保留**（设计审查轮 1 定案）：该技能活性多方实证——触发式 description、using-shenbi :40 路由、deps.json :49 注册、PR #202 刚修过其契约、G4/G5/ownership/cli 注册齐全——其 OPTIONAL_READS 条目服务活的显式派发，非死条目；chapter_loop.py:135-136 注释误标其为 deprecated 由 T1.2 纠正
5. **DEPRECATED 技能正文**（F834）：自称"默认激活/每章必查"等现行语气改为明确的退役说明 + 后继指针（防 LLM 读正文复活旧链路）；逐个过 15 个 DEPRECATED 技能正文；**同步收尾**：F819 修复后撤 lint_contract_prose.py:91-92 的 track 死引用 allowlist 条目（豁免非修复，残留即 stale）；F817 "last_reinformed" 拼写漂移（recall SKILL.md:58）随正文重写消亡
6. **F905 双重调度裁决 + 矩阵 DEPRECATED 拆除**（自 #23 补登；设计审查轮 2 依派发拓扑重构）：sensitivity 去重——`"sensitivity"` 出矩阵（固定步 ChapterStep 14 为单一触发源，符合 :40-43 头注释自身声明的 core-circle 逻辑，`_CORE_CIRCLE_KEYS` 补 sensitivity 或直接删矩阵行二选一，plan 裁决）；matrix 5 个 DEPRECATED 行（worldRules/motivation/dialogue/texture/readerPull）**默认矩阵退出 + 五维并入 `_CORE_CIRCLE_KEYS`**（设计审查轮 2 定案，推翻轮 1 的"改指 group-*"）：MERGE-2 后四 group-* 已是 CHAPTER_STEPS 固定审计步（chapter_loop.py:209-235，wave-1 每章无条件派发且 "core audits never skipped"），五维全部被组覆盖——矩阵行改指 group 会在并行路径 wave-2（:2751）/串行路径 run_audit_layer（:3213）复刻 F905 双派发形（两路径对 wave-1 已派发的组零去重护栏）；维度键经 core-key 过滤保持 genre-config 合法词表（resolve_audit_dimensions 仅对非 dict 形状报 malformed，删行不炸）。**拓扑注记（plan 须核实活路径）**：并行路径（首审计步两波派发后跳步）不经过 run_audit_layer → BOUNDARY_TRIGGERS（long-span/arc-payoff/spinoff/chapter-pattern，:99-104）仅串行路径可达——并行模式下的 boundary 圈现状即死线，属本 spec 外的疑似独立 finding，记录不扩scope；`_CRITICAL_GENRE_DIMS`（:71-72）与头注释随之自洽（texture 出 critical 集因 critical 性由组固定步结构保证）；`AUDIT_SAFETY_MATRIX`（src/shenbi/config/thresholds.py:48-84，texture/antiAi/continuity critical=True，g0_config_coherence 与 config/config_coherence 消费）与 genre-config SKILL.md:174-180 维度词表保持自洽——词表键不删（仍是合法配置词汇，语义变为"由固定组步承接"）

### T2 · description 契约整改

7. **检查器强化先行**（驳斥复核新事实）：tools/audit-skill-descriptions.py 现报全绿但 F835/F877/F878/F842 全部存活——根因：单一规则源 `_desc_has_behavioral_text`（g0_skill_contract.py:56-59）仅 `startswith` 小标志表匹配，漏检两类形态：①"Grouped audit for…" 非 "Use when" 开头且不含标志词开头 ②"Use when X — Y" 破折号后功能从句。强化启发式（开头触发结构存在性 + 尾部功能从句检测 + 中段行为动词），保持单一规则源（g0_skill_contract 改、工具与 G0 门同步受益）；**落地序列钉死**（G0.16 对 desc_has_behavior 硬 FAIL——g0.py:810-833，无 WARN 档；工具本身 exit 1 即清单。乱序会使 G0.sc 中途爆红，靠同 PR 内 task 顺序保 CI 不见中间态）：①强化共享函数 + 本地跑工具，exit-1 清单即人工过目材料 → ②改写全部违规者 → ③T2.10 接线即 FAIL 承载——三步同 PR 内按 task 顺序落
8. 违规清单机械收集：强化后脚本解析 74 个 SKILL.md description，标记违规者——覆盖 F835/F842/F877/F878 + F815(a)；逐个改写为 when-to-use 形式
9. F815 存活子项按契约闭合处理并在此登记：(a) description 改写 (b) lifecycle-states.md/hook-types.md 跨目录引用改同目录拷贝或内联（C20 R1 闭合口径）(c) ACTIVE/PLANTED 初始态定稿 (d) 残半——audits 输出声明入 contract 或输出下线
10. audit-skill-descriptions.py 接线（Z10 F1011：现零接线——workflows/justfile/src 全域零引用）——**挂载点须在 just check 调用链内**（独立 workflow-only 挂载不满足验收 6；并入 lint_contracts 或 justfile 直挂二选一，plan 裁决）——与 C25 T3 协同 CI 承载

### T3 · 防回潮 lint

11. 新增对账规则（**独立工具挂载**，设计审查轮 1 裁决：lint_contract_graph 是 reads/writes 闭包检查器，路由面规则塞入属语义拉伸——立 `tools/lint_routing_faces.py` 类独立工具挂 justfile check 链，与 C25 CI 承载协同）：(a) DEPRECATED skill 名出现在 deps.json/using-shenbi/GENESIS_STEPS/TRIGGER_STEPS/GENRE_ACTIVATION_MATRIX/**CHAPTER_STEPS** 任一路由面即 FAIL（设计审查轮 2 补 CHAPTER_STEPS——最直接的每章派发面，F905 之半即生于此；与 T1.3 的 lint_repo_consistency 豁免语义合一，单一信源——**DEPRECATED 判定须共享同一探测 helper**，防两份标志表漂移，helper 归宿 plan 定稿，标志 regex 契约随 DEPRECATED 正文形态钉死）(b) 触发表路由的每个技能必须存在于 skills/ 磁盘且非 DEPRECATED (c) description 契约（长度 + 触发式结构——接 T2.7 强化后规则源）
12. 规则对当前树跑基线 = 0 违规（T1/T2 完成后），注入假路由行验证 FAIL（红灯）

### 批量清理（M 级成员）

本簇无 M 级成员（12 条全 P1/P2）。

## 验收标准（真实数据可复验 · 2026-09-12 校正）

1. `grep -rn "foreshadowing-plant\|foreshadowing-track\|foreshadowing-recall" tests/tiers/deps.json skills/using-shenbi/SKILL.md src/shenbi/` 三路由面清零，**许可残留白名单**（逐处枚举，设计审查轮 1 补全）：chapter_loop.py:135-136 退役说明注释（context-composing 误标已纠）、:282-284 STEP_NAME_MIGRATIONS 迁移映射、DEPRECATED 技能自身目录（skills/shenbi-foreshadowing-{plant,track,recall}/）；GENESIS_STEPS/TRIGGER_STEPS/matrix 零命中；gates/contracts 注册行按 T1.2/T1.3 裁决后清零或换名——含 g4 checker 模块标识串（`G4-foreshadowing-{plant,track}`）与 contracts/schemas/hooks.py docstring 权威源改指后零命中；deps.json `_tool_hashes` 两钉随 checker 处置同步（重锁后键名换为实际存在的模块）
2. 4 个 group-* + foreshadowing-lifecycle 在 using-shenbi 触发表各 ≥1 行（`grep -c` 对照，现状基线 0/0/0/0/0）
3. 强化后 description 契约脚本全仓跑批 0 违规；对 5 个已修技能（group-* 四件 + writing-skills）人工复核 when-to-use 形式
4. 防回潮 lint 红灯验证：临时在 deps.json 加回一个 DEPRECATED 条目 → lint FAIL（记录后还原）
5. `just check` 全绿；**后继路由可达性以离线断言表达（F947 口径，#58 先例——shenbi-dispatch 无 dry-run 模式，dispatcher/cli.py 为 33 行薄壳）**：单元级断言 GENESIS_STEPS step 9 解析为 lifecycle + `_build_skill_prompt` 对 lifecycle 的 prompt 组装可达 + 触发表解析（using-shenbi 路由解析函数若存在，否则静态断言表格行）——禁止真实 dispatch 取证（核心原则 8）
6. **接线实证（设计审查轮 1 新增，防 F1011 式零接线绿灯）**：`just check` 输出可证地调用新路由 lint（lint_routing_faces）与 description 契约检查（audit-skill-descriptions 或并入 lint_contracts 的等效步）——未挂载的 lint 不算存在

## 风险与回滚

- **风险**：删路由后旧技能彻底失联——若生产 prompt 仍按旧名调用会 404；保留 DEPRECATED 正文内的"后继指针"作为迁移说明，观察一轮后再议物理删除（物理删除不在本 spec）
- **风险**：GENESIS_STEPS 换 lifecycle 影响管线黄金路径——改动排在 C3/C20 的契约定稿之后（两者均已合并：c112a95a / PR #202），跑一次 T2 短链验证（离线 fixtures 驱动）
- **风险**：matrix 五维退出 + 并入 core-keys 改变 genre-config 语义（曾显式开这些维度的既有配置变为 no-op——由固定组步承接，行为等价但配置面静默）——plan 阶段对 genre-config 文档同步说明；BOUNDARY_TRIGGERS 仅串行路径可达的疑似死线记录为独立线索不扩 scope
- **风险**：description 启发式强化引入误判——强化后 exit-1 清单先人工过目再改写（T2.7 落地序列①），避免把合法触发描述改坏
- **回滚**：触发表/deps.json/GENESIS_STEPS/矩阵四处改动各自独立 commit；lint 规则可降 WARN

## 簇成员清单（12 条，自查用 · 2026-09-12 驳斥复核标注）

F355（收窄：plant/track 死条目删；context-composing 条目裁定保留）, F815（降级：(d) bridge_tracker 半项已修 @PR #202；余 (a)(b)(c)+(d)audits 残半存活）, F816（存活）, F817（存活）, F819（存活）, F834（存活，面扩矩阵）, F835（存活）, F842（存活）, F873（存活，14 行亲证）, F877（存活）, F878（存活）, F887（存活，triggers.py:297 活派发面加重；plant_hooks_from_plan 死 handler 已修 @PR #127 退出）, F905（存活，2026-08-14 轮命名空间；行号 :241-246→:249-254 已校正）（代表 F873）
