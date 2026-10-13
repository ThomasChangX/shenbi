> **Date:** 2026-10-13 | **Status:** Active（待执行）· Revised 2026-10-13（SDD 价值门两轮驳斥 + 设计审查一轮，v2.2） | **Severity:** 🟠 P1（F886 为 P1 verified） | **方法:** 契约声明式接线为主（reads 声明 + `sync_contracts.py` 再生成 + SKILL 正文同步），框架代码改动限 `seed_parser.py` / `g0.py` / `chapter_loop.py` 三处小面 + `cli.py` 注释改写一处 + `truth-files.yaml` globs 段一行加法（v2.2 订正改动面声明） | **系列:** 种子传递性（源自 2026-10-12/13 outline-example.md 大幅丰富前置审计会话，两轮批判性审核后定稿；第三轮 SDD 驳斥修正接线形态） | **依赖:** 无 | **范围:** F886 genesis 种子断流恢复、character-design 孤儿 reads 修正、配角可选节、丢弃键 WARN、G0.2 字数锚定、F368 残余收尾、NovelConfig 死 schema 删除、4.3 六项裁决固化 | **核心洞察:** 接线意图已半存在于仓库——character-design 契约已声明两条孤儿 reads（`outline/chapter_outline.md`/`outline/three_act.md`，全仓零写方）、`docs/framework/truth-files.yaml:91` 已注册 `genesis-context/*.md, kind: context, producer: pipeline`；缺的是写读两端路径对齐、五个 genesis 技能的 reads 补全、与注册表 globs 段一行（loader `resolves()` 对具体片段路径的硬前提，见 §1 修正 1）。两轮批判审核撤回三处过度工程候选（book-spine-init 双权威 / 疲劳词与每章字数 seed 键 / basic_info 死片段），净方案 = 纯接线 + 四项小清偿，零新框架机制

# seed 内容流恢复与传递性收尾（spec69-seed-content-flow）

## 元信息

- 编号：#69（= 现有最大 #68 + 1，按 INDEX 登记约定）
- 登记来源：2026-10-13 会话。用户拟大幅丰富 `outline-example.md`，前置审计发现 seed 设定传递链存在 F886 断流等缺口；经「推荐 → 对抗性审核 → 修正」两轮收敛后立本 spec
- **审核修正记录**（第二批判轮产物，防后人重蹈）：
  - **勘误 1**：`show_tell_ratio`/`deep_themes` 的消费面此前被夸大——唯一消费者是 `skills/shenbi-style-learning/SKILL.md:70` 的 bootstrap 种子指纹（`confidence: low`，前 3 章完成后被真实统计整体覆盖），不进章节循环、无门禁消费。认知从「有效通道」降级为「弱传递、终局无效」
  - **撤回 1**：book-spine-init 接三个冲突片段——制造双权威（story_frame.md 已承载冲突且 SKILL 未定义优先级），撤回，维持 story_frame 单源
  - **撤回 2**：疲劳词/每章字数两个 seed 键——前者经 genre-config 技能 LLM-merge 无结构保留保证（auto-check invariants 只查 count 与 keyset，不查值来源）；后者是第三自由度（`目标字数 × 目标章节数` 已二元锁定每章均值），坏值破坏保量数学且无 init 校验拦截
  - **撤回 3**：`genesis-context/basic_info.md`/`narrative.md` 存档片段——无消费者的新写点 = 复制 F886 的 write-only 模式，只保留丢弃键 WARN
  - **成本修正**：「每技能 1-3 行 YAML」实为三联动——frontmatter + `sync_contracts.py` 再生成 AUTO-GENERATED 段 + SKILL 正文路径引用与说明句（character-design 正文 5 处：44-45/105-106/201-203）
  - **新证据**：`_INPUT_MAX_CHARS_PER_FILE = 32000`（`dispatch_helper.py:313`，约 8K tokens/文件截断帽）；`_retry_key = f"ch{chapter}-{skill}"`（`chapter_loop.py:956-958`，dash 终结使前缀清扫无 ch1/ch10 误伤）；character-design 的 T1 scenario 零引用两条孤儿路径（改路径零 staging 风险）；`test_e2e.py:104` 仅断言 genesis-context 目录存在（接线不破坏）；`parse_seed` 的字数解析本就节内化（`_parse_list_items(basic)`），全文首匹配问题**仅在 G0.2**（`g0.py:355`），seed_parser 无需修
- **第三轮审核修正记录（SDD 阶段 1 驳斥复核 · 2026-10-13，fresh-context 子 agent 64 tool-calls + 协调者逐条实证）**——问题定义面 10 条主张全存活（F886 断流确证/三冲突死端/孤儿 reads/F368 残余/NovelConfig 零导入者/G0.2 首匹配/配角节兼容/注入链/reality-lock 无感/缺文件静默跳过），方案钉死面四处修正：
  - **修正 1（决定性）· reads 声明形态 = 具体片段路径 + 注册表 globs 段一行加法**：loader `_validate` 强制每条 read `resolves()`（`contracts/loader.py:285-291`）——实测 `resolves('genesis-context/chapter_outline.md') = False`（`genesis-context/*.md` 仅是 concepts 逐字条目、globs 段无此模式），按原稿字面声明具体路径会在 load_contract 处 ContractError（dispatch/G4/sync_contracts/CI 全断）。原稿「无需改注册表」主张作废。修法：truth-files.yaml globs 段新增 `- {pattern: genesis-context/*.md}`（一行）——具体路径经 fnmatch 通过 loader（`loader.py:216-231`），且 `dag_key` 把具体路径规范化到 `genesis-context/*.md`（`contracts/graph.py:42-53` patterns→globs→字面）→ 命中 lint_contract_graph 的 pipeline 概念豁免（`tools/lint_contract_graph.py:64/:73-74`，该概念 producer: pipeline）。与 `outline/*.md` glob + `outline/chapter_outline.md` concept 并存的既有先例同构。弃用另一形态（逐字声明 `genesis-context/*.md`）：`_resolve_read_path`（`dispatch_helper.py:558-573`）会 glob 展开**注入全部片段**，T1 表「片段→技能」精准映射不可表达，且十片段 × 32K 冲击 `_INPUT_MAX_CHARS_TOTAL=128000` 总预算
  - **修正 2 · T0「零风险面」作废**：`tests/pipeline/test_dispatch_reads_injection.py:32-40`（spec #58 C20 验收用例）恰好 staging 两条旧 outline/ 路径并断言注入——T0 改路径必然打破该用例，T0 任务内同步更新其 staging 路径
  - **修正 3 · T4 默认裁决翻转为 import**：原稿「gates→pipeline 跨包 import 无先例，复制 12 行纯函数」前提错误——`gates/g6.py:70`（chapter_loop）、`:130`（truth_readers）、`gates/g4/generic.py:236/:566`（llm_output_integrity）、`gates/g4/state_settling.py:16/:314`（truth_io）至少 6 处先例。改为 g0.py 函数内 lazy `from shenbi.pipeline.seed_parser import _extract_section`（g6 同形），零复制
  - **修正 4 · G5.2 验收从「零新增」改为「钉死 delta」+ 实弹探针降级**：G5.2 adjacent-pair（`gates/g5.py:138-160`）无 pipeline 豁免，接线后四对（genre-config→character-design、character-design→story-architecture、story-architecture→faction-builder、faction-builder→volume-outlining）各新增 missing 键 `genesis-context/*.md` 一条（dag_key 收敛，与片段数无关）——pipeline 产物无技能写方 = 预期形态，与既有 baseline 同类；G5 仅 CLI/测试面（`gates/cli.py:197`）不进生产循环，噪音影响限验收面。§3.4 实弹探针与 SDD 核心原则 8（禁真实 dispatch 取证）的张力按 spec68 裁决先例处理（e2e-canary 人工触发、不进 just check、独立于 SDD 证据链）——SDD 内验收改 fixture 驱动，实弹探针为交付后人工步骤
- **与既有裁决的一致性**：本 spec 是 spec #51（C37）F886 defer 行「内容恢复移交产品裁决」的执行件；T6 执行 spec #27 F240 已裁「倾向删除」的 NovelConfig；canon-import 不接 seed 触发与 spec #58 C20 对 fanfic.mode 的 YAGNI 删减同族；归档设计 spec（2026-07-01-novel-pipeline-design.md）append-only 不改，4.3 六项裁决以本 spec 为权威记录

## 0. 问题定义

1. **F886（P1 verified，spec #51 defer）**：`pipeline init` 把 seed 九节原文写成 `genesis-context/*.md` 片段后，全仓零消费者（`cli.py:834-841` 注释如实标注）。后果：用户在 主角设定/世界观设定/势力组织/情节线/章节大纲/三幕结构 六节与核心冲突三层上写的设定，对生成的小说**零影响**——genesis 技能只读到 novel.json 的结构化字段（title/genre/era/core_concept/target_* /ending_direction）。
2. **核心冲突的最差组合**：`validate_seed:143-151` 强制三键（表层/个人/深层）存在，但解析产物只进死端——「被校验强制 + 被运行忽略」同时成立。
3. **孤儿 reads**：`skills/shenbi-character-design/SKILL.md:10-11` 声明读 `outline/chapter_outline.md` 与 `outline/three_act.md`，正文三处（44-45/105-106/201-203）据此立铁律「两文件点名的角色一个不能漏」——但全仓无任何写方产出这两个路径（init 写的是 `genesis-context/` 同名文件）。契约承诺了不存在的输入。
4. **附带清偿**（同会话审计发现）：F368 残余（章节关闭无清扫，弃章键永驻 state）；`contracts/schemas/novel.py` NovelConfig 零导入者且 docstring 失真（spec #27 F240 已裁未执行）；基本信息/叙事技巧非白名单键静默丢弃；G0.2 `目标字数` 全文首匹配在 seed 大幅丰富后可能误读。

## 1. 方案总则与边界（钉死，plan 阶段照抄不发明）

- **机制**：复用契约 `reads:` 声明式通道。`genesis-context/*.md` 已是注册表登记的 pipeline-produced context（`docs/framework/truth-files.yaml:91` concepts 逐字条目）；**具体片段路径（如 `genesis-context/world_rules.md`）要过 loader `resolves()` 强制（`contracts/loader.py:285-291`），须在 truth-files.yaml globs 段加一行 `- {pattern: genesis-context/*.md}`**（修正 1，与 `outline/*.md` glob + 具体概念并存的先例同构）。加法后：loader fnmatch 通过 ✓、`dag_key` 规范化到 glob 键命中 lint_contract_graph pipeline 豁免（`tools/lint_contract_graph.py:64/:73-74`）✓、dispatch 按具体路径精准注入（不做全目录 glob 展开）✓。
- **接线范围 = 仅 genesis 技能**：worldbuilding（step 1）/ character-design（step 3）/ story-architecture（step 4）/ faction-builder（step 5）/ volume-outlining（step 6）。**不接章节循环技能**——长跑中 truth 文件是权威，seed 章纲只覆盖开篇；**book-spine-init 不接**（撤回 1：story_frame 单源）。
- **缺文件语义**：片段不存在（USER-mode 老项目 / 配角节缺省）→ `_resolve_read_path`（`dispatch_helper.py:554-578`）返回空 → 静默跳过（reads loop 零迭代，无 WARN 无报错），零迁移成本。
- **权威序**：genesis 链内，上游已产出 truth > seed 原文片段。seed 片段定位 = 人类伙伴原始意向输入；与上游 truth 冲突时以上游为准，如技能据此做调整，**在其既有产物文件内以显式小节披露**（如「seed 意向与 truth 冲突的处理记录」，含调整理由一句）——各接线技能正文加一句（v2.2 修正：五技能均未声明 `*-decisions.json` sidecar，原「记 decisions.json」指契约外写点 = dead-wire，会撞 write-safety；为五技能补 sidecar 声明属扩面、与零新框架机制矛盾，显式不做）。
- **截断事实**：接线后片段走既有 `_budgeted_truncate`（`dispatch_helper.py:402-451`）——`_INPUT_MAX_CHARS_PER_FILE = 32000` 字符/文件硬帽 + **`_INPUT_MAX_CHARS_TOTAL = 128000` 总预算**（超限时按 `_FILE_PRIORITY_WEIGHTS` 权重**等比分配**再二次再分配，:1148-1156 调用点）：`chapter_outline.md` 含 "chapter" → 1.0、`world_rules.md` → 0.8、其余片段（protagonist/supporting/three_act/plot_lines/三冲突/forces）→ default 0.5。**软约束（v2.2 修正：总量面）**：单节 < 32K 且 **genesis 九节合计建议 < ~100K 字符**（为 novel.json/story_bible/characters 等共注入输入留余量）——极端超限时 0.5 权重片段被等比切开（WARN + TruncateRecord 披露），核心冲突三层恰在此暴露面；**裁决：不为冲突片段提权重**（`_FILE_PRIORITY_WEIGHTS` 加法与零新框架机制冲突；取舍 = 极端丰富下冲突设定受披露性截断，属可接受——防后人当 bug 修）。
- **G5.2 影响注记（修正 4 · v2.1 按实际 pair 源订正）**：G5.2 adjacent-pair 的 pair 源 = `deps.json t2-phases.<phase>.prerequisites` 顺序（`gates/g5.py:95` 取数、:126-160 相邻对循环），**非 GENESIS_STEPS 执行顺序**。接线后新 missing 键 `genesis-context/*.md`（`dag_key` 收敛，与片段数无关）：genesis phase 恰四对——power-system→faction-builder、location-builder→character-design、relationship-map→story-architecture、story-architecture→volume-outlining（worldbuilding 为 prereqs[0] 无上游不查）；architecture phase spillover 一对——story-architecture→volume-outlining。baseline genesis 单相 26 条 → 30 条（可复算）。pipeline 产物无技能写方为预期形态；G5 仅 CLI/测试面（`gates/cli.py:197`）不进生产循环。**不改 g5.py**（零新框架机制纪律；pipeline 豁免若未来要做属独立 spec）。
- **R3 工具哈希再锁（v2.1 新增）**：`deps.json:_tool_hashes` 活锁恰覆盖本 spec 全部三个框架文件（seed_parser/g0/chapter_loop）——T2/T3/T4/T5 任一改动后须 `bash tests/lock-tool-hashes.sh` 再锁（`sync_contracts` 不再锁此段），否则 `just check` R3 面必 FAIL。
- **conflict 三层不写入 novel.json**（裁决）：novel.json 是 framework-owned 文件（`FRAMEWORK_OWNED_WRITES`，`dispatch_helper.py:587-590`），不为传递扩 schema；冲突经 story-architecture 消化进 story_frame 后自然到达 book-spine。

## 2. 任务分解

### T0 · character-design 孤儿路径修正（先行件，可独立落地）

- frontmatter `reads:`：`outline/chapter_outline.md` → `genesis-context/chapter_outline.md`；`outline/three_act.md` → `genesis-context/three_act.md`
- **前置（与 T1 共享）**：truth-files.yaml globs 段加 `- {pattern: genesis-context/*.md}`——否则 loader `resolves()` 对新路径抛 ContractError（修正 1）
- **顺带清偿（v2.1）**：删除 truth-files.yaml concepts 段 `outline/chapter_outline.md`/`outline/three_act.md` 两行（`:103-104`，producer: skill 但全仓零写方零读者的陈旧登记；T0 后唯一读者消失，保留将转 R2 orphan-concept WARN）
- `uv run python -m shenbi.sync_contracts` 再生成 AUTO-GENERATED 数据契约段（`sync_contracts.py:165` main 入口）
- 正文 5 处路径引用同步改（SKILL.md 44-45/105-106/201-203 行带）
- 风险面（修正 2）：T1 scenario 无 staging 引用（已验证）；`test_e2e.py:104` 只断言目录存在；**但 `tests/pipeline/test_dispatch_reads_injection.py:32-40` 恰 staging 两条旧 outline/ 路径并断言注入（spec #58 C20 用例）——T0 须同步更新其 staging 路径为新 genesis-context/ 路径**

### T1 · genesis-context 接线（本 spec 主体）

| 片段（init 写点 `cli.py:839-841`） | 接入技能 | 现有 reads 基线 |
|---|---|---|
| `world_rules.md` | shenbi-worldbuilding | novel.json |
| `protagonist.md`、`supporting.md`(T2) | shenbi-character-design | world/story_bible.md、world/rules.md、characters/**（+T0 两修正项） |
| `three_act.md`、`plot_lines.md`、`surface_conflict.md`、`personal_conflict.md`、`deep_conflict.md` | shenbi-story-architecture | novel.json、world/story_bible.md、characters/**、genre-config.json |
| `forces.md` | shenbi-faction-builder | novel.json、world/story_bible.md、world/rules.md、characters/**、outline/story_frame.md、outline/volume_map.md |
| `chapter_outline.md` | shenbi-volume-outlining | novel.json、outline/story_frame.md、outline/volume_map.md、truth/author_intent.md、genre-config.json |

每技能三联动：frontmatter reads + sync_contracts 再生成 + 正文一句（片段定位 + §1 权威序）。

### T2 · 配角可选节（4.3 唯一新增解析面）

- `seed_parser.py`：`genesis_context["supporting"] = _extract_section(text, "Supporting Cast|配角设定|配角")`——**不进 REQUIRED_SECTIONS**（可选节，缺席合法）
- `validate_seed` 不动（可选节零校验）
- character-design reads 加 `genesis-context/supporting.md`；正文「点名角色不可漏」规则来源扩一句到 supporting
- 缺省：节缺席 → 不写文件 → reads 跳过 → 技能从 world/protagonist 自行发明（现行行为）

### T3 · 丢弃键 WARN

- `seed_parser.py`：Basic Info / 叙事技巧 两节的 list items 中，命中不了白名单分支的键 → `log.warning("seed_key_dropped", section=..., keys=[...])`（一次汇总，不逐键刷屏）
- **不做**（撤回 3）：basic_info/narrative 存档片段；通用透传进 novel.json（侵蚀 `extra: forbid` 纪律）

### T4 · G0.2 目标字数锚定

- `g0.py:355`：先取基本信息节再匹配——函数内 lazy `from shenbi.pipeline.seed_parser import _extract_section`（修正 3：gates→pipeline import 有先例——`gates/g6.py:70`/:130、`gates/g4/generic.py:236`/:566、`gates/g4/state_settling.py:16`/:314；零复制）。匹配域 = 基本信息节；节缺席时回退全文（legacy 兼容），节存在且节内无「目标字数」→ 维持现行 FAIL 路径
- seed_parser 无需改（审核修正：其解析本就节内化）

### T5 · F368 收尾三小件

1. **章节关闭清扫**：`_complete_chapter`（`chapter_loop.py:1463`）内 pop 所有 `startswith(f"ch{chapter}-")` 的 retry_feedback 键。安全性已验证：`_retry_key` dash 终结章节 token，`ch1-` 不误伤 `ch10-*`；legacy 键形（`chapter_loop.py:1197` 的 `f"ch{chapter}-{step.skill}"`）同前缀同覆盖
2. **台账更新**：c37-triage F368 defer 行注记「成功即清已由 probe23 #18-4 与 canary pop 落地（:3276/:3477），残余=章节关闭清扫，随 spec #69 T5 closed」
3. **单测 ×2**：失败→重试→成功→键消失；章节关闭→该章全部键消失

### T6 · NovelConfig 删除

- 删 `src/shenbi/contracts/schemas/novel.py`（代码与 tests 零导入者已验证；docs 归档 plan 的历史引用不阻碍）
- 引 spec #27 F240 先例（`genre: str` vs 真实 list 类型漂移，裁决倾向删除）
- 删后 `just check` 验证 sync_contracts / lint 面零引用残留

### T7 · 4.3 六项裁决固化（纯文档）

- **权威记录 = 本节**；归档设计 spec（2026-07-01）append-only 不改
- 裁决表：风格参考文件路径 → 目录约定 `import/source/*.txt`（**契约级**通道，`shenbi-style-learning` reads 已声明）；参考作品/canon-import → USER-mode 手动派发（spec #58 C20 YAGNI 先例）；关键配角草图 → T2 落地；卷数偏好 → 写入章节大纲节散文随片段流向 volume-outlining（需 volume-outlining 正文注明「seed 偏好为软约束，volume_map 为结构权威」）；题材疲劳词列表 → **不做**（撤回 2）；每章目标字数 → **不做**（撤回 2，`目标字数 × 目标章节数` 已锁定每章均值）
- `docs/getting-started/first-novel.md` 核对是否残留 4.3 失真表述，有则修（plan 阶段核对）

## 3. 验收标准

1. `just check` 全绿（含 G0.16 契约面、G0.5b rubric-SKILL 一致面、lint_registry_reconcile R1/R2、lint_contract_graph closure、reality-lock CI、fixture mirror 锁）
2. **G5 实跑 delta 钉死**（修正 4 改写 · v2.1 订正 pair 源）：fixture 项目上经 `shenbi-validate G5`（无 round 面，G5.1/5.3/5.4 跳过形态）跑 G5——G5.2 新增 missing 键**恰为** `genesis-context/*.md`：genesis phase 恰四对（power-system→faction-builder、location-builder→character-design、relationship-map→story-architecture、story-architecture→volume-outlining，pair 源 = deps.json prerequisites 非 GENESIS_STEPS）+ architecture phase spillover 一对（story-architecture→volume-outlining），无其他新增（genesis baseline 26→30 可复算）；这些 WARN 为 pipeline 产物无技能写方的预期形态，非 spurious
3. 单测清单：
   - T0/T1：契约加载面断言 reads 含目标片段路径；派发组装测试——片段文件存在时对应 genesis 技能 prompt 含其内容、`reads_manifest` 记录注入，文件缺失时 prompt 不含且不失败（复用 dispatch 组装测试基建）
   - T2：seed 含 `## 配角设定` → `genesis-context/supporting.md` 写盘；缺省不写
   - T3：非白名单键触发 `seed_key_dropped` WARN（caplog 断言）
   - T4：正文他处先出现「目标字数：」字样时 G0.2 仍取基本信息节值
   - T5：两测（见 T5.3）
   - T6：代码面 grep NovelConfig 零命中（`grep -r NovelConfig --include='*.py' src/ tests/ tools/`；spec 自身与 docs/归档的历史引用不阻碍——append-only）
4. **丰富版 seed fixture 化验收 + 实弹探针降级为交付后人工步骤**（修正 4）：SDD 内验收（核心原则 8 禁真实 dispatch 取证，spec68 裁决先例——e2e-canary 人工触发、不进 just check、独立于 SDD 证据链）：
   - **丰富版 seed 以测试内字面量 / tmp_path 构造**（v2.1 消歧：不落 `tests/fixtures/`——先例 `tests/unit/pipeline/conftest.py` `sample_seed_content`；`tests/fixtures/` 镜像丰富属 §3.6 交付后动作），各节 < 32K 字符断言 = 「丰富软约束」实测锚点；经真实 `parse_seed`/init 写方（tmp_path，G0.9）断言全部片段写盘
   - 派发组装断言：worldbuilding/story-architecture 的 reads_manifest 含 world_rules/three_act/三冲突、prompt 含片段内容、无截断 WARN（dispatch 组装测试基建 `test_dispatch_reads_injection.py` 同族，离线 F947）
   - **交付后人工探针（非 SDD 验收项）**：用户以 e2e-canary 形态跑 1 章探针（注意 run_pipeline.sh 语义 = 完整 genesis 链 + 章循环到 checkpoint，成本非「1 章」字面）；观测清单含「无 `input_over_budget` 类截断 WARN」（v2.2：总预算超限观测项，见 §1 截断事实）；探针 seed 模板随 spec 交付
5. **T7 验收（v2.2 补）**：4.3 六项裁决逐项含做/不做 + 理由（对照归档设计 spec 4.3 六项：风格参考文件路径/参考作品路径/关键配角草图/卷数偏好/题材疲劳词/每章目标字数）；`docs/getting-started/first-novel.md` 核对结果记录（预期：无 4.3 失真表述，空操作——审查者已预 grep，plan 阶段复核）
6. **挂账闭合**：c37-triage F886 行 closed（注 spec #69）；F368 行按 T5.2 更新；`cli.py:834-841` 注释改写（「write-only 零消费者」谎称面清除，spec #51 Step2 注释的后续收尾）；findings-ledger 登记本 spec 对应行
7. **顺序注记**：本 spec 验收后才执行 `outline-example.md` 大幅丰富 + fixture 镜像同步（provenance 头保留，G0.18 强制）；丰富后跑 `test_seed_parser.py` 真实断言面确认既有键值未被改写

## 4. 执行顺序与依赖

T0（先行独立件，含注册表 globs 行 + test_dispatch_reads_injection 同步）→ T1（主体，依赖 T0 的 character-design 基线）→ T2（搭 T1 的车）→ T3/T4（并行小件）→ T5（独立）→ T6（独立）→ T7（纯文档）→ §3 验收收口。

非目标（防过度工程，全量裁决见 §1/§2/T7）：疲劳词与每章字数 seed 键、book-spine-init 接线（原文「book-spice」系笔误，仓库无此技能）、basic_info/narrative 死片段、language 开放（G4 检查 language + CJK 统计面 = 假承诺）、canon-import seed 触发路由、conflict 写入 novel.json、G5.2 pipeline 豁免（§1 G5.2 注记）、新框架机制。
