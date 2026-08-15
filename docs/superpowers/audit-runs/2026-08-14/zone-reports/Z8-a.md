# Z8 分区初审报告（Z8-a 段：skills/ 部分 skill，25 个）

> 审查人：Z8-a 初审 agent（只读）
> 范围：清单 `zones/Z8-a.files`（34 行 = 25 个 SKILL.md + 4 个辅助参考 md + 5 个 .gitkeep）
> 方式：全部 deep-read；配合 `grep`/`read`/`python3 -c` 只读验证；未运行任何写入仓库的命令（仅写入本段文件 Z8-a.md）。
> 发现编号段：**F900–F949**。
> 只读声明：除本段文件外未创建/修改/删除任何仓库文件；未 git add/commit。

---

## 0. 总览

- deep-read skill 数：**25 / 25**（清单全部 SKILL.md 覆盖；辅助文件 chase-power.md / checklist.md / fanfic-modes.md / sensitive-words.md 作为所属 skill 目录的一部分深读；5 个 .gitkeep 为零字节占位）
- 未覆盖文件：**0**
- findings 数：**22**（P1 × 4，P2 × 11，M × 7）
- 已知外部登记（不重复编号，交叉引用）：`foreshadowing-lifecycle` 与 `review-group-*` 未登记 deps.json（F0-02，specced）；真实运行产物 decisions.json 大面积无效（Z11-01，specced）；skills 计数漂移（F0-01，specced）。
- 本段最重问题：
  1. **foreshadowing-resolve 的 Chase Power 公式/阈值三处互相矛盾且示例自相矛盾**（F903，P1）——同一 skill 主文件、auto-check 常量、辅助文件 chase-power.md 给出三套不兼容的 hook_power 量表与 GREEN/YELLOW/ORANGE/RED 阈值，且示例 "10×8×1.0=80 (RED)" 按自身表格 80 属 ORANGE。
  2. **review-sensitivity 双重调度**（F905，P1）：固定章节步骤 14 与 genre-circle（audit_layer GENRE_ACTIVATION_MATRIX 含 sensitivity 且不在 _CORE_CIRCLE_KEYS 排除集）在真实配置 `auditDimensions.sensitivity=true` 下每章重复调度同一 skill 并覆写同一报告路径。
  3. **genre-config.json 字段级 reads 漂移**（F906，P1）：4+ 个 review skill 读取 `prohibitions` / `climaxKeywords` / `prohibitedClimaxKeywords` / `povMode`，而 genre-config SKILL.md 字段规范（8 个顶层字段）与全部 3 份真实 genre-config.json 均无这些字段——敏感词合规检查（本书禁忌词 0 出现，blocking）依赖不存在的字段静默空转。
  4. **3 个 DEPRECATED skill 未传导**（F904，P2）：review-anti-ai / review-motivation / review-pov 在 SKILL.md 头部标注 "Do not dispatch"，但仍完整注册于 truth-files.index.json、deps.json、executor_config.toml、using-shenbi 触发表，且正文仍自称活跃。
  5. **确定性替换候选 6 组**（详见 §3）：其中 review-anti-ai/group-craft 的 anti-AI 检查清单（checklist.md 自述"零 LLM 成本"10 项确定性检查）与 foreshadowing-resolve 的 CP 计算为最强候选，直接可 Python 化。

---

## 1. findings（F900–F949）

### F900 | 2 个 skill 的 description 违反"只写触发条件"（foreshadowing-lifecycle / review-group-craft） | contract | P2
- 证据：`skills/shenbi-foreshadowing-lifecycle/SKILL.md:3`（"Combined foreshadowing lifecycle -- recall dormant hooks, track active hooks against chapter body, and plant new hooks from plan in a single call."——描述"做什么"而非"何时用"）；`skills/shenbi-review-group-craft/SKILL.md:3`（"Grouped audit for writing craft -- texture, reader-pull, and anti-AI patterns in one call; dispatches as a parallel wave via parallel_dispatch.py"）。两者均无 "Use when" 触发句式；其余 23 个 skill 的 description 均以 "Use when…" 开头（python 脚本验证，见下）。
- 根因：AGENTS.md 与 D1③ 契约要求 description 仅写触发条件；这两个 skill 写成功能描述。
- 验证命令+输出：`python3 -c` 遍历 25 个 frontmatter → `trig="Use when"…` 仅此 2 个为 False（其余 23 个 True）。
- 影响：description 驱动调度触发匹配；功能式描述可能在"任意写作任务"场景误触发或不触发（group-craft 由 chapter_loop 固定步骤调度，影响有限；foreshadowing-lifecycle 同为固定步骤，影响以文档契约为准）。
- 建议方向：改写为 "Use when a chapter has been drafted and hooks need recall/track/plant" 之类触发式表述；group-craft 改为 "Use when running the grouped craft audit wave"。

### F901 | foreshadowing-lifecycle 正文声明产出 audits/chapter-N-foreshadowing.md，frontmatter 却声明 writes: []（未声明写入 + index 无此生产者） | contract | P1
- 证据：`skills/shenbi-foreshadowing-lifecycle/SKILL.md:135`（"### FILE: audits/chapter-N-foreshadowing.md" + 完整报告模板 135-205 行）vs frontmatter `:11`（`writes: []`）；`truth-files.index.json` 的 `audits/chapter-N-foreshadowing.md => writes: ['shenbi-review-foreshadowing', 'shenbi-review-group-plan']`（不含 lifecycle）。
- 根因：输出格式段与契约段脱节——skill 明确要求 LLM 产出审计报告文件，但契约（与注册表）均不声明该写入；写所有权审计（write_audit）按契约判定，该文件会成未声明写入。
- 验证命令+输出：`read` 两处；`python3 -c` 读 index → `foreshadowing audit: {'reads': [], 'writes': ['shenbi-review-foreshadowing', 'shenbi-review-group-plan'], 'updates': []}`。
- 影响：LLM 产出的报告文件无法通过写审计/契约校验；或 LLM 被契约抑制不产出该报告，丢失伏笔生命周期审计证据。
- 建议方向：将 audits/chapter-N-foreshadowing.md 加入 writes（并同步 index 注册），或从正文删除该输出段。

### F902 | foreshadowing-lifecycle 引用不存在的参考文件 lifecycle-states.md / hook-types.md | error | P2
- 证据：`skills/shenbi-foreshadowing-lifecycle/SKILL.md:59`（"see `lifecycle-states.md`"）、`:103`（"Full type/dimension/curve/subtlety lookup table in `hook-types.md`"）；目录实况 `ls skills/shenbi-foreshadowing-lifecycle/` 仅 SKILL.md。
- 根因：参考文件从未创建（或已删除），引用未清理。
- 验证命令+输出：`ls` → `SKILL.md`（唯一）；`find` 全仓无 lifecycle-states.md/hook-types.md。
- 影响：LLM 无法获取状态转移表与 hook 类型表，Phase 2 状态转移（PLANTED→RELEVANT→…）与 Phase 3 subtlety 取值失去权威定义。
- 建议方向：补建两文件或把表内联进 SKILL.md。

### F903 | foreshadowing-resolve 的 Chase Power 公式/阈值三处不一致，且示例自相矛盾 | error | P1
- 证据：
  - auto-check 常量 `SKILL.md:24`：`CP_THRESHOLDS {'GREEN_MAX': 50, 'RED_NOW': 100, 'FORCE_NEXT_CHAPTER': 200}`；
  - 正文公式表 `SKILL.md:75-82`：`hook_power`（core_hook=10, main=5, side=2）、`escalation_factor`（FULL=1.0/PARTIAL=0.7/TWIST=0.8/FLAT=0.3）；
  - 区间判定 `SKILL.md:124`：`GREEN < 20, YELLOW 20-50, ORANGE 50-100, RED ≥ 100`；
  - 示例 `SKILL.md:85-86`：`hook-001: CP = 10 × 8 × 1.0 = 80 (RED 区)`——按 :124 表格 80 属 **ORANGE**（50-100），示例与自身表格矛盾；
  - 辅助文件 `chase-power.md:13-15`：`hook_power`（core_hook=2.0, 普通=1.0, 支线=0.5）、`escalation_factor`（FLAT=1.0, RISING=1.5, EXPONENTIAL=2.0，语义为 escalation_curve 而非 payoff 类型）；`chase-power.md:19-24`：`GREEN < 50, YELLOW 50-100, ORANGE 100-200, RED > 200`。
- 根因：公式演进（hook_power 量表、escalation_factor 语义、债务区间）在 SKILL.md 与 chase-power.md 及 auto-check 常量三处平行维护，从未对齐；auto-check 的 invariants（"debt consistent with hooks"）无真实校验方。
- 验证命令+输出：`read` 三处全文 + `grep -n "GREEN\|RED\|hook_power\|escalation"` 两文件 → 三套阈值/两套量表/两套 factor 语义并存。
- 影响：伏笔债务等级判定可复现性崩坏（同一 CP 值在三个权威处判为 GREEN/ORANGE/RED 不同结果），逐层兑现顺序与 RED 区强制行动依赖的阈值失去唯一语义。
- 建议方向：以 chase-power.md 或 SKILL.md 之一为唯一权威，同步 auto-check 常量；修正示例；补一个可执行的 CP 计算脚本并接 G4 校验。

### F904 | review-anti-ai / review-motivation / review-pov 的 DEPRECATED 标注未传导：仍注册于 index/deps/executor_config/using-shenbi，正文仍自称活跃 | error | P2
- 证据：三处 DEPRECATED 注释 `skills/shenbi-review-anti-ai/SKILL.md:16-17`、`shenbi-review-motivation/SKILL.md:18-19`、`shenbi-review-pov/SKILL.md:18-19`（"Do not dispatch"）；`truth-files.index.json`：`audits/chapter-N-anti-ai.md => writes: ['shenbi-review-anti-ai', …]`、`audits/chapter-N-motivation.md => writes: […, 'shenbi-review-motivation']`、`audits/chapter-N-pov.md => writes: […, 'shenbi-review-pov']`；`tests/tiers/deps.json:84,89,90` 仍列三 skill；`executor_config.toml:20` 仍有 `[overrides."shenbi-review-anti-ai"]`；`using-shenbi/SKILL.md:44,51,52` 触发表仍路由到它们；`review-anti-ai/SKILL.md:37` 正文仍称"这是默认激活的审计技能（每章必查）"，与头部 DEPRECATED 直接矛盾。
- 根因：DEPRECATED 仅为注释，无任何强制机制（无 is_active 字段、无 index/deps 清理、无 executor 剔除）；并行调度路径 `audit_layer.py:47` 的 GENRE_ACTIVATION_MATRIX 仍含 `"motivation": "shenbi-review-motivation"`，真实配置 `auditDimensions.motivation=true` 时会被调度。
- 验证命令+输出：`grep -rn` deps.json/executor_config.toml/audit_layer.py/using-shenbi → 全部命中；`read` 三处 SKILL.md 头部与正文。
- 影响：已废弃 skill 仍可被 dispatch（浪费预算 + 与 group-character/group-craft 重复审计）；文档自相矛盾（头部说废弃、正文说每章必查）。
- 建议方向：将 DEPRECATED 升级为契约字段（如 `deprecated: superseded-by`）并让 index/deps/audit_layer/executor 同步剔除；或至少把正文"默认激活"类声明删除。

### F905 | review-sensitivity 双重调度：固定章节步骤 14 与 genre-circle 均调度同一 skill，真实配置下每章重复执行 | error | P1
- 证据：`src/shenbi/pipeline/chapter_loop.py:238-244`（CHAPTER_STEPS 步骤 14 = `shenbi-review-sensitivity`，is_audit=True）；`src/shenbi/pipeline/audit_layer.py:44-45`（GENRE_ACTIVATION_MATRIX 含 `"sensitivity": "shenbi-review-sensitivity"`）、`:57-67`（_CORE_CIRCLE_KEYS = {antiAi, character, pacing, continuity, foreshadowing, memoCompliance, pov}，**不含 sensitivity**）；`chapter_loop.py:2550-2584`（Wave1 = 全部 CHAPTER_STEPS review skill，Wave2 = get_active_genre_audits）；真实 `novel-output/xinghuo-ranqiong/genre-config.json` 的 `auditDimensions.sensitivity=true`。
- 根因：sensitivity 既是固定核心步骤又被 genre 激活矩阵登记，且排除集漏掉 "sensitivity"；两条并行 wave 无章内去重，均写 `audits/chapter-N-sensitivity.md`（create_or_overwrite 互相覆写）。
- 验证命令+输出：`python3 -c` 断言 → `chapter_loop has shenbi-review-sensitivity step: True` / `audit_layer matrix has sensitivity: True` / core keys 不含 sensitivity。
- 影响：每章重复执行同一审计（双倍 token 成本）、报告互相覆写、G4 二次校验可能因并发竞态 FAIL；同源问题在 serial 路径的 run_audit_layer（`chapter_loop.py:2932`）同样出现。
- 建议方向：把 "sensitivity" 加入 _CORE_CIRCLE_KEYS（或从 GENRE_ACTIVATION_MATRIX 移除），并在 parallel_dispatch 加 core/genre 去重。

### F906 | genre-config.json 字段级 reads 漂移：prohibitions / climaxKeywords / prohibitedClimaxKeywords / povMode / maxClimaxPerChapter 被 4+ skill 读取但 schema 与真实文件均无 | error | P1
- 证据：`shenbi-review-sensitivity/SKILL.md:60,68`（"genre-config.json 的 prohibitions 列表"）、`shenbi-review-anti-ai/checklist.md:36,60`（"从 genre-config.json 的 prohibitions 读取"）、`shenbi-review-highpoint/SKILL.md:88,46`（climaxKeywords / prohibitedClimaxKeywords / maxClimaxPerChapter）、`shenbi-review-pov/SKILL.md:74`（povMode）、`shenbi-review-sensitivity/sensitive-words.md:106`（"genre-config.json 的 genre 字段"——实际该字段在 novel.json）；对侧：`shenbi-genre-config/SKILL.md:270-286` 字段规范（恰好 8 个顶层字段：version/updated/fatigueWords/pacing/chapterTypes/auditDimensions/customRules/approval，**无上述任何字段**）；全部 3 份真实 genre-config.json（xinghuo-ranqiong / test-validation / d1-g4-tmp-round）均为同一 8 键结构。
- 根因：review 层按旧 spec 记忆读取字段，genre-config 字段规范演进后未回写 review skill；sensitive-words.md:106 把 novel.json.genre 错记到 genre-config.json。
- 验证命令+输出：`grep -rn "prohibitions" skills/` → 5 个文件命中；`python3` 遍历 3 份 genre-config.json → `keys: ['version','updated','fatigueWords','pacing','chapterTypes','auditDimensions','customRules','approval']`，prohibitions/climaxKeywords/povMode 全无。
- 影响：敏感内容审计的"本书禁忌词必须 0 出现"（blocking 级，SKILL.md:60）依赖不存在的字段 → 检查静默空转，合规门失效；anti-ai 禁忌词检查同理。
- 建议方向：genre-config schema 增补 prohibitions（由 genre-config skill 产出）或 review skill 改读 customRules/novel.json；两处同步，并加字段存在性校验。

### F907 | review skill 激活条件使用存档 spec 的数值维度 ID（维度 15/9/19/11/17/32），与运行时 named-key 机制脱节 | error | P2
- 证据：`shenbi-review-highpoint/SKILL.md:37`（"auditDimensions 包含维度 15"）、`shenbi-review-pov/SKILL.md:41`（"维度 9 或 19"）、`shenbi-review-motivation/SKILL.md:41`（"维度 11"）、`shenbi-review-group-craft/SKILL.md:67,136`（"dimension 17"/"dimension 32"）；运行时 `audit_layer.py:44-54` 用 camelCase 命名键（sensitivity/worldRules/motivation/…）匹配，src 全仓无数值维度映射；数值 ID 仅存在于归档 spec `docs/superpowers/specs/archive/2026-06-08-shenbi-design.md:782,860`。
- 根因：review 层激活条件沿袭旧 spec 的数值编号，运行时改为命名键后未回写。
- 验证命令+输出：`grep -rn "维度 [0-9]\|dimension [0-9]" skills/` → 14 处命中（含本段 4 skill）；`grep -rn "auditDimensions" src/shenbi/` → 仅 audit_layer/config/g0 用命名键。
- 影响：SKILL.md 给 LLM 的激活说明与真实调度机制（audit_layer）不符——文档语义失效；同源问题跨 Z8-b/c 多个 review skill。
- 建议方向：把激活条件统一改为命名键（"auditDimensions.texture 为 true 时激活"）并指向 audit_layer 的 GENRE_ACTIVATION_MATRIX。

### F908 | character-design expand 模式读取 characters/**/*.md 未在 frontmatter 声明，且正文引用未注册文件 outline/chapter_outline.md、outline/three_act.md | contract | P2
- 证据：`shenbi-character-design/SKILL.md:224`（expand 模式"读取 characters/**/*.md 全部已有角色"）vs frontmatter reads `:8-9`（仅 world/story_bible.md、world/rules.md）；`truth-files.index.json` 的 `characters/**/*.md => reads: [faction-builder, foundation-review, relationship-map, snapshot-manage, story-architecture, truth-sync]`（**不含 character-design**）；正文 `:40-41,197-199` 的 IRON LAW 引用 `outline/chapter_outline.md` 与 `outline/three_act.md`——两文件不在 `truth-files.yaml` 规范词表（真实产物中位于 `genesis-context/`，词表登记为 `genesis-context/*.md`）。
- 根因：expand 模式（--mode expand）是后加模式，reads 未同步；IRON LAW 引用的文件名是旧目录布局。
- 验证命令+输出：`read` frontmatter 与正文；`grep -n "chapter_outline\|three_act" docs/framework/truth-files.yaml` → 无命中；`find` → 仅 novel-output/genesis-context/ 存在。
- 影响：expand 模式下 executor 不会注入已有角色卡（未声明 reads），去重检查（铁律 2）形同虚设，可能重复造角色；完整性校验引用的文件按词表不存在。
- 建议方向：expand 模式把 characters/**/*.md 加入 reads（或拆分为独立 contract）；IRON LAW 改指 genesis-context/chapter_outline.md 或删除。

### F909 | market-radar 声明写 context/market-radar-decisions.json 但正文输出格式无任何 decisions 指令，且 index 显示零消费者 | contract | P2
- 证据：`shenbi-market-radar/SKILL.md:12`（frontmatter writes context/market-radar-decisions.json）+ `:27`（AUTO-GENERATED 数据契约）vs 正文输出格式 `:68-107`（仅"市场雷达报告"+"作者决策清单"markdown，**无 decisions.json 说明**）；DOT `:38-47` 终点为 "Present report to human"，无写 decisions 节点；`truth-files.index.json` 的 `context/market-radar-decisions.json => reads: [], writes: ['shenbi-market-radar']`（零读者）；`find novel-output -name "*market-radar*"` → 无此文件。
- 根因：sidecar 契约（decisions-schema.md:97 也登记 market-radar）与 skill 正文未衔接——LLM 无指令产出该文件。
- 验证命令+输出：`grep -n "decisions" shenbi-market-radar/SKILL.md` → 仅 frontmatter:12 与 AUTO-GENERATED:27；`find` 无产物。
- 影响：声明产出与实际产出不符；即便产出也无下游消费（dead sidecar），与 decisions-schema.md:97 的 per-skill 表不一致。
- 建议方向：正文补"决策清单同步写入 context/market-radar-decisions.json"输出段（含 selections/basis），或从 writes 移除并同步 decisions-schema。

### F910 | chapter-planning 实际产出未声明的 plans/chapter-N-plan-decisions.json（55 个中 38 个无效 JSON），index 无此条目 | contract | P2
- 证据：frontmatter `shenbi-chapter-planning/SKILL.md:24-27` 仅声明 writes `plans/chapter-N-plan.md`；真实产物 `novel-output/xinghuo-ranqiong/staging/plans/` 有 55 个 `chapter-N-plan-decisions.json`（38 个 json.loads 失败，如 "Extra data: line 81 column 1"）；`truth-files.index.json` 的 `plans/chapter-N-plan-decisions.json` 条目 **不存在**（None）；`decisions-schema.md:99` 的 per-skill 表却登记 chapter-planning 产 plan decisions。
- 根因：sidecar 产出由调度侧（JSON mode 的 decisions 字段）驱动，但 skill 契约、index 均未声明；产出质量无 G4 decisions 校验守护（Z11-01 同根因：写路径未剥离 LLM 尾部 markdown）。
- 验证命令+输出：`python3` 遍历 → `plan-decisions total: 55 invalid: 38`（样例 chapter-8/9/55 均 "Extra data"）。
- 影响：契约三源（SKILL.md / index / decisions-schema.md）不一致；38 个无效 sidecar 为 G4 decisions 校验的固定失败源（若被校验）或静默落盘（若未校验）。
- 建议方向：将 plan-decisions.json 写入声明进 chapter-planning writes 并补 index 条目；修写路径剥离尾缀（对接 Z11-01）。

### F911 | chapter-planning 字段级 reads 漂移：主角状态/当前世界局势/活跃线索/已完成章节/伏笔统计 在真实 truth 文件中不存在 | error | P2
- 证据：`shenbi-chapter-planning/SKILL.md:8-22` 声明 `truth/current_state.md` 字段 [主角状态, 当前世界局势, 活跃线索]、`truth/pending_hooks.md` 字段 [活跃伏笔, 伏笔统计]、`truth/chapter_summaries.md` 字段 [已完成章节]；真实 `novel-output/xinghuo-ranqiong/truth/current_state.md` 结构为 `## 系统演化阶段` / `## 参数当前位置`（无上述字段），`pending_hooks.md` 仅近似命中 "活跃伏笔数"（:117，无"伏笔统计"），`chapter_summaries.md` 为 `## 第N章` 段落（无"已完成章节"）。
- 根因：字段名沿袭旧模板；truth 文件结构由 state-settling 演化后未回写 reads。
- 验证命令+输出：`grep -n "主角状态\|当前世界局势\|活跃线索\|已完成章节\|伏笔统计" skills/` → 仅 chapter-planning 与 review-continuity（另一 zone）frontmatter 出现；`grep -rln "主角状态" novel-output/` → 仅 staging decisions/快照文本，truth 文件无。
- 影响：字段级过滤（dispatcher 按声明字段裁剪）命中缺失字段 → 触发 escape hatch 返回全文件 + WARN（F262/T301 已知类）；字段过滤机制实际失效。
- 建议方向：按 state-settling 当前模板更新字段名，或删除字段级声明改为整文件 reads。

### F912 | sequel-writing 引用已废弃的 snapshots/chapter-NNN/ 目录概念（D20 已声明废弃，真实布局为平文件） | error | P2
- 证据：`shenbi-sequel-writing/SKILL.md:9`（reads `snapshots/chapter-NNN/*`）、`:68`（"最近的 `snapshots/chapter-NNN/`"）、`:226`（"新增快照: snapshots/chapter-(N+1)/"）；`truth-files.yaml:72-75` 明示 "the fictional snapshots/chapter-NNN/ directory concept is deprecated. Register the real flatfile"；真实布局 `novel-output/xinghuo-ranqiong/snapshots/chapter-005-20260715T232231.md`（平文件）；`truth-files.index.json` 仍登记 `snapshots/chapter-NNN/*`（reads: [sequel-writing]）。
- 根因：D20 改造快照为平文件后，skill 与 index 未同步。
- 验证命令+输出：`ls novel-output/xinghuo-ranqiong/snapshots/` → `chapter-005-*.md` 平文件；`read` truth-files.yaml:72-75。
- 影响：续写按废弃目录找断点 → 找不到快照，回退到低优先级断点（章节文件/卷摘要），上下文重建降级。
- 建议方向：reads/正文改为 `snapshots/chapter-NNN-*.md`（或 `snapshots/chapter-*`），同步 index。

### F913 | truth-sync 铁律 3"增量更新不重写整个文件"与 frontmatter updates mode: create_or_overwrite 矛盾 | contract | P2
- 证据：`shenbi-truth-sync/SKILL.md:15-16`（`updates: truth/*.md, mode: create_or_overwrite`）vs `:57`（铁律 3"只更新变化的部分，不重写整个文件"）；`:37` 写范围说明重申"仅从正文重新提取并经人工仲裁后同步"。
- 根因：契约 mode 与执行语义（增量补丁）不一致——mode 是文件级覆盖声明，正文要求段级增量。
- 验证命令+输出：`read` 两处。
- 影响：mode 声明暗示可整体覆写，与增量铁律冲突；写所有权审计/快照恢复可能按覆盖语义处理。
- 建议方向：mode 改 append/merge 语义或新增 mode 枚举（如 `patch`），或正文明示"文件级 create_or_overwrite + 内容级增量"。

### F914 | review-highpoint DOT 引用 maxClimaxPerChapter，正文检查项实际用 climaxKeywords/prohibitedClimaxKeywords（DOT 与正文不一致） | error | M
- 证据：`shenbi-review-highpoint/SKILL.md:46`（DOT："Read genre-config.json (climaxKeywords + maxClimaxPerChapter)"）vs `:88`（正文读取 climaxKeywords 与 prohibitedClimaxKeywords；全文无 maxClimaxPerChapter）。
- 根因：DOT 节点文案与检查实现不同步（且两者涉及的字段均不在真实 config，见 F906）。
- 验证命令+输出：`grep -n "maxClimaxPerChapter" skills/` → 仅 :46 一处。
- 影响：DOT 作为权威流程定义与正文冲突，读者/执行者对配置字段产生歧义。
- 建议方向：统一 DOT 与正文字段名（climaxKeywords/prohibitedClimaxKeywords），随 F906 一并修正。

### F916 | review-fanfic 激活/读取字段路径不一致：novel.json.mode vs novel.json.fanfic.mode | error | M
- 证据：`shenbi-review-fanfic/SKILL.md:39`（"激活条件：`novel.json.mode` = `"fanfic"`"）vs `:76`（"读取 `novel.json.fanfic.mode`"）与 `fanfic-modes.md:138`（"读取 novel.json.fanfic.mode"）；两份真实 novel.json（xinghuo-ranqiong / test-validation）均无 mode/fanfic 字段（keys: title/genre/era/core_concept/…）。
- 根因：字段路径两处写法不一（顶层 vs 嵌套），且 schema 未登记该字段。
- 验证命令+输出：`read` 两处 + fanfic-modes.md:138；`python3` → `mode: None | fanfic: None`。
- 影响：激活条件字段路径歧义；无 fanfic 项目时不影响，但契约无字段级登记。
- 建议方向：统一为单一路径（建议 novel.json.fanfic.mode 或顶层 mode 二选一）并在 schema 登记。

### F917 | short-packaging 书名候选类型"情绪"不在 Step 1 类型表（直白/隐喻/钩子/系列） | error | M
- 证据：`shenbi-short-packaging/SKILL.md:64`（"类型：直白型 / 隐喻型 / 钩子型 / 系列型"）vs `:116`（输出示例第 5 行 `| 5 | [标题] | 情绪 | N 字 |`）。
- 根因：类型表与示例模板不同步。
- 验证命令+输出：`read` 两处。
- 影响：低；示例引入未定义类型，模板校验（若有）会误报。
- 建议方向：类型表补"情绪"或示例改回四类之一。

### F918 | genre-config 备份文件名不一致：铁律 4 用 .bak，输出格式用 .bak.YYYYMMDD | error | M
- 证据：`shenbi-genre-config/SKILL.md:67`（"cp genre-config.json genre-config.json.bak"）vs `:183`（"cp genre-config.json genre-config.json.bak.YYYYMMDD"）与 `:213`（"**备份**: genre-config.json.bak.YYYYMMDD"）。
- 根因：备份命名约定两处演进不一致。
- 验证命令+输出：`read` 三处。
- 影响：低；回滚时按哪种命名查找备份存在歧义。
- 建议方向：统一为带日期后缀命名。

### F919 | review-sensitivity 缺陷证据格式句残缺（"遵循  定义的四要素格式"缺主语/引用） | error | M
- 证据：`shenbi-review-sensitivity/SKILL.md:74`（"每条缺陷报告必须遵循  定义的四要素格式："——双空格处缺引用对象）。
- 根因：从其它 review skill 复制时引用丢失。
- 验证命令+输出：`read` :74。
- 影响：文案残缺；四要素规则本身完整（:75-78）。
- 建议方向：补引用（如"遵循下方定义的四要素格式"）。

### F920 | sensitive-words.md 引用已废弃 review-anti-ai 协作，且引用 genre-config.json.genre（不存在，实为 novel.json.genre） | error | M
- 证据：`shenbi-review-sensitivity/sensitive-words.md:87`（"与 `review-anti-ai` 协作"——该 skill 已 DEPRECATED，见 F904）、`:106`（"`genre-config.json` 的 `genre` 字段决定基线"——真实 genre-config.json 无 genre 字段，novel.json 有）。
- 根因：参考文件未随 anti-ai 废弃与字段迁移更新。
- 验证命令+输出：`read` 两处；`python3` 打印 genre-config.json keys（无 genre）。
- 影响：低；协作对象指向废弃 skill，字段来源错文件。
- 建议方向：协作对象改为 shenbi-review-group-craft（Dimension 3）；genre 字段改指 novel.json。

### F921 | using-shenbi 未传导 MERGE-2：4 个 group auditor 完全缺席触发表，仍路由到已废弃 skill；docs/specs 路径已失效 | error | P2
- 证据：`using-shenbi/SKILL.md:44,51,52,53,54`（触发表仍映射"检查这章"→ shenbi-review-anti-ai、"动机"→ review-motivation、"视角"→ review-pov、"质感"→ review-texture、"吸引力"→ review-reader-pull）——全部为已废弃/被替代 skill，全表**无** review-group-craft/group-character/group-factual/group-plan 任何条目；`:124-126` 默认审计表与条件审计表（Phase 2/Phase 4b）同样未提 group 合并；`:120` 引用 `docs/specs/2026-06-08-shenbi-design.md`——该路径不存在（spec 已移至 `docs/superpowers/specs/archive/`）。
- 根因：MERGE-2（chapter_loop.py:201-244 的 4 个 group 步骤）落地后，meta skill 的触发表/审计表未同步；spec 归档后路径未更新。
- 验证命令+输出：`grep -rn "group-craft\|group-character\|group-factual\|group-plan" skills/using-shenbi/SKILL.md` → 0 命中；`ls docs/specs/` → 不存在；`ls docs/superpowers/specs/archive/2026-06-08-shenbi-design.md` → 存在。
- 影响：人类发起审计请求时被路由到废弃 skill；新合并审计无触发入口；spec 引用断链。
- 建议方向：触发表改用 group-craft/group-character/group-factual/group-plan（及仍独立的 review-*）；spec 路径改为 archive 路径或删去。

### F923 | anchor-curate / escalation-review 缺少 anti-rationalization 表（其余 21 个 skill 均有） | error | M
- 证据：`shenbi-anchor-curate/SKILL.md`（54 行，无 Anti-Rationalization 段）；`shenbi-escalation-review/SKILL.md`（68 行，无）；其余 21 个 skill 均有（如 canon-import:204、genre-config:330、plot-thread-weaver:243）。
- 根因：两个小型 skill 编写时未补表。
- 验证命令+输出：`grep -L "Anti-Rationalization" skills/shenbi-{anchor-curate,escalation-review}/SKILL.md` → 两文件均无。
- 影响：低；反合理化防线缺失（escalation-review 为人工决策汇总，风险低；anchor-curate 涉及版权边界，建议补）。

---

## 2. per-skill 报告（25/25）

### skills/shenbi-anchor-curate/
- 处置: deep-read
- 声称检查的不变量: 工艺分析非原文复制；9 类槽位映射；校准基准 88-97/75-87/<75 三档；source_ref 精确
- findings: [F923]（缺 anti-rationalization 表）
- 确定性替换候选: 无——核心为文学批评判断；校准区间（88-97/75-87/<75）为固定模板但映射需 LLM
- 置信度: high

### skills/shenbi-canon-import/
- 处置: deep-read
- 声称检查的不变量: 5 SECTION 必全；模式过滤透明；证据必带出处；不混用模式；OOC 必声明偏离
- findings: 无（DOT 与正文一致；reads source_canon/* 与 writes import/canon/*.md 均与 index 一致；anti-rationalization 4 行完整）
- 确定性替换候选: 无（提取与模式判定为 LLM 判断）
- 置信度: high

### skills/shenbi-chapter-planning/
- 处置: deep-read
- 声称检查的不变量: 8 段式 EXACT 标题；优先级来源声明；chapter_role 合法值；hook 账列名/操作/沉默规则；段 6 章尾改变规则
- findings: [F910]（实际产出未声明 plan-decisions.json，55 个中 38 无效）；[F911]（字段级 reads 漂移）
- 确定性替换候选: 有——hook 账列校验/操作枚举/沉默章数 ≥4 规则（SKILL.md:243-248）与段 8 计数规则（:261-271）为纯表格式校验（G4 已部分实现）；正文 8 段标题精确匹配可 Python 校验
- 置信度: high

### skills/shenbi-character-design/
- 处置: deep-read
- 声称检查的不变量: 4 phase 顺序；主角弧线单一权威；voice_profile 必填；一人一卡；去重原则；IRON LAW 完整性 5 条；expand 只追加
- findings: [F908]（expand 模式未声明 reads characters/**/*.md + 引用未注册文件 chapter_outline.md/three_act.md）
- 确定性替换候选: 无（角色设计为 LLM 创作；IRON LAW 的角色覆盖核对可脚本化但依赖 LLM 输出解析）
- 置信度: high

### skills/shenbi-escalation-review/
- 处置: deep-read
- 声称检查的不变量: 只读不评；决策选项 2-3 个；仅升级信号触发（chapter_loop 确认其由 revision_router 反应式调度，非固定步骤）
- findings: [F923]（缺 anti-rationalization 表）
- 确定性替换候选: 无
- 置信度: high

### skills/shenbi-foreshadowing-lifecycle/
- 处置: deep-read
- 声称检查的不变量: 状态转移表（PLANTED→RELEVANT→TRIGGERED→RESOLVED/EXPIRED/DORMANT）；每章全量评估；core_hook 不 ABANDON；密度预算 ≤8；overdue 确定性阈值过滤
- findings: [F900]（description 非触发式）；[F901]（正文声明写 audits/chapter-N-foreshadowing.md 而契约 writes:[]）；[F902]（引用不存在文件 lifecycle-states.md/hook-types.md）
- 确定性替换候选: 有——Phase 1 Rule 1 自述 "Deterministic threshold filtering"（SKILL.md:48）：overdue 判定 = last_reinforced/max_distance/cultivation_interval 对 current_chapter 的纯数值比较，可直接 Python 化；密度预算 ≤8 计数同理
- 置信度: high

### skills/shenbi-foreshadowing-resolve/
- 处置: deep-read
- 声称检查的不变量: CP 公式必写（铁律 5）；逐层兑现（低 CP 先）；core_hook ≥ PARTIAL_PAYOFF；卷尾盘点；ABANDON 需人类批准
- findings: [F903]（CP 公式/阈值三处不一致 + 示例自相矛盾）
- 确定性替换候选: 有——CP = hook_power×time_since_plant×escalation_factor 为纯算术；区间判定（GREEN/YELLOW/ORANGE/RED）、逐层兑现升序排序、CP 工作表/兑现计划表计数规则（SKILL.md:191-200）均可 Python 化（阈值需先按 F903 统一）
- 置信度: high

### skills/shenbi-genre-config/
- 处置: deep-read
- 声称检查的不变量: 改前必读/改后必验/人类必批/可回滚/格式一致/审批留痕（铁律 1-6）；字段规范 8 顶层字段；计数规则 9 项
- findings: [F918]（备份命名 .bak vs .bak.YYYYMMDD 不一致）；[F906]（作为被读方：schema 未含 prohibitions 等字段，但下游 4+ skill 读取——本 skill 侧登记缺口）
- 确定性替换候选: 有——字段规范/计数规则（顶层字段数=8、禁用词 ≤50、替换全覆盖、章节类型 6-10、审计维度 5-10、禁用维度理由）为纯 JSON 结构校验，已由 G4.gc 覆盖；skill 内其余为 LLM 编辑决策
- 置信度: high

### skills/shenbi-intent-management/
- 处置: deep-read
- 声称检查的不变量: author_intent 由人类口述 AI 整理；current_focus 每次 chapter-planning 前更新；drift guidance 自动合并
- findings: 无（reads/updates 与 index 一致；DOT 一致；anti-rationalization 完整）
- 确定性替换候选: 无
- 置信度: high

### skills/shenbi-market-radar/
- 处置: deep-read
- 声称检查的不变量: 数据引用铁律（每条推荐必须引用具体数据行）；饱和阈值 >60%；决策清单可勾选
- findings: [F909]（声明 decisions.json 写入但正文无产出指令 + 零消费者）
- 确定性替换候选: 无（趋势分析与建议为 LLM；>60% 饱和阈值判定可脚本化但输入为 LLM 归纳结果，弱）
- 置信度: high

### skills/shenbi-plot-thread-weaver/
- 处置: deep-read
- 声称检查的不变量: 每章 ≥1 线索推进；P0/P1 max_gap 约束；C 线完结；线索总览表 8 列 EXACT；状态 4 值
- findings: 无（DOT 与正文一致；reads/updates 与 index 一致；P3=16 为补充非矛盾）
- 确定性替换候选: 有——约束检查表（max_gap 规定值 vs 实际值、违规 Y/N）与空白章检测（SKILL.md:188-196）为纯计数/比较/表格校验，可 Python 化（G4 候选）
- 置信度: high

### skills/shenbi-review-anti-ai/
- 处置: deep-read
- 声称检查的不变量: 10 项检查逐一执行；先确定性后判断；error 必修；3+ warning 需修；缺陷四要素
- findings: [F904]（DEPRECATED 未传导：index/deps/executor_config/using-shenbi 仍注册；正文:37 仍称"默认激活每章必查"与头部矛盾）；[F906]（checklist.md:36,60 读取不存在的 prohibitions）
- 确定性替换候选: 有——**最强候选**：checklist.md:5-67 全部 10 项为确定性检查（CV=标准差/均值、正则 `/不是[^，。！？\n]{0,30}[，,]?\s*而是/`、`includes("——")`、转折词/标记词计数阈值 max(1,floor(字数/3000))、疲劳词/禁忌词匹配），文件自述"零 LLM 成本"，可直接 Python 化
- 置信度: high

### skills/shenbi-review-fanfic/
- 处置: deep-read
- 声称检查的不变量: 模式严格度决定判定（canon/au/ooc/cp）；原作 = 公共契约；偏差未声明 = error；缺陷四要素
- findings: [F916]（novel.json.mode vs novel.json.fanfic.mode 路径不一致）
- 确定性替换候选: 无（还原度/关系动态判定为 LLM；模式选择可脚本化但依赖 novel.json 字段先修复 F916）
- 置信度: high

### skills/shenbi-review-group-craft/
- 处置: deep-read
- 声称检查的不变量: 三维度独立评分；并行 wave 调度（MERGE-2）；各维度激活条件；缺陷四要素
- findings: [F900]（description 非触发式）；[F907]（激活条件用数值维度 17/32）；[F906]（Dimension 3 读 genre-config prohibitions 不存在）；正文 Contract 段（:45-57）声明 `writes: []` + `updates: [三报告]`，与 frontmatter（:12-19，`writes: [三报告]`）**同一文件内两套矛盾契约表述**（P2 级文档矛盾，并入 F900 旁注）
- 确定性替换候选: 有——Dimension 3（Anti-AI）同 review-anti-ai 清单，全部 10 项确定性检查可 Python 化；Dimension 1 段长统计（最短/最长/平均/极端段计数）可脚本化
- 置信度: high

### skills/shenbi-review-highpoint/
- 处置: deep-read
- 声称检查的不变量: 蓄压 500+ 字；反转三段式；爽点关键词红线；虚化 ≥2 级 = error；FIRE/QUEST 节奏验证
- findings: [F914]（DOT maxClimaxPerChapter vs 正文 prohibitedClimaxKeywords）；[F907]（维度 15 数值激活条件）；[F906]（climaxKeywords/prohibitedClimaxKeywords 不存在于真实 config）
- 确定性替换候选: 弱——蓄压字数 ≥500 与关键词命中计数可脚本化，但蓄压/释放等级为主观评级（LLM）
- 置信度: high

### skills/shenbi-review-motivation/
- 处置: deep-read
- 声称检查的不变量: 利益驱动；动机可推导；行为链完整性；反派合理动机
- findings: [F904]（DEPRECATED 未传导：audit_layer.py:47 仍调度；deps.json:89 仍注册）；[F907]（维度 11 数值激活条件）
- 确定性替换候选: 无（动机判定为 LLM 判断）
- 置信度: high

### skills/shenbi-review-pov/
- 处置: deep-read
- 声称检查的不变量: POV 切换分隔；信息边界 = 物理定律；感官边界；心理边界
- findings: [F904]（DEPRECATED 未传导）；[F907]（维度 9 或 19 数值激活条件）；[F906]（povMode 字段不存在于真实 config）
- 确定性替换候选: 无（POV 判定为 LLM 判断；章内切换次数 >3 计数可脚本化，弱）
- 置信度: high

### skills/shenbi-review-sensitivity/
- 处置: deep-read
- 声称检查的不变量: 敏感词 = blocking；依据目标平台规则；本书禁忌词 0 出现；平台合规综合
- findings: [F905]（双重调度：固定 step 14 + genre-circle）；[F906]（prohibitions 字段不存在，合规检查数据源缺失）；[F919]（:74 残缺句）；[F920]（sensitive-words.md:87 引用废弃 anti-ai；:106 genre 字段错文件）
- 确定性替换候选: 有——禁忌词精确匹配/大小写不敏感/简繁等价/空白变体（sensitive-words.md:79-85）+ 出现次数计数为纯文本处理，可 Python 化（接 F906 修复后数据源）
- 置信度: high

### skills/shenbi-score-arc/
- 处置: deep-read
- 声称检查的不变量: 硬二元驱动（route C）；读上级目标（book_spine L5）；对 audit_drift 仅 append；独立评分 HARD-GATE
- findings: 无（auto-check constants/formula 与正文 Route C/A 一致；reads/updates 与 index 一致）
- 确定性替换候选: 有——auto-check formula（SKILL.md:34-39）：`final_score = 0.6*route_c_soft + 0.4*route_a`、`passed = final>=90 AND hard_binary all pass`、`tier_advance = final>=94` 为纯加权聚合/阈值比较，可 Python 化（LLM 仅需产出子分）
- 置信度: high

### skills/shenbi-sequel-writing/
- 处置: deep-read
- 声称检查的不变量: 断点必为已审计章节；上下文必重建（6 类）；作者意图先确认；无意识漂移检测；不可重写历史；测试模式模拟确认标记
- findings: [F912]（引用已废弃 snapshots/chapter-NNN/ 目录概念）
- 确定性替换候选: 无（上下文重建为 LLM；断点定位"最新快照"为文件系统操作，可脚本化但需先修 F912 路径）
- 置信度: high

### skills/shenbi-short-packaging/
- 处置: deep-read
- 声称检查的不变量: 多版本不单选；简介不剧透；卖点可证；封面 prompt 视觉化；关键词平台匹配
- findings: [F917]（书名类型"情绪"不在类型表）
- 确定性替换候选: 无（文案生成与卖点提取为 LLM）
- 置信度: high

### skills/shenbi-story-architecture/
- 处置: deep-read
- 声称检查的不变量: 双线必写；OKR 递归分解；核心冲突三层；散文骨架；职责边界（骨架 vs 细化）
- findings: 无（writes 三 outline 文件均与 index 一致；DOT 一致；anti-rationalization 完整）
- 确定性替换候选: 无
- 置信度: high

### skills/shenbi-truth-sync/
- 处置: deep-read
- 声称检查的不变量: 正文权威；冲突人工仲裁；增量更新；保留历史；提取与推断分离（推断 ≤20%）
- findings: [F913]（增量铁律 vs create_or_overwrite mode）
- 确定性替换候选: 弱——推断条目占比 ≤20% 计数（SKILL.md:59）为阈值比较，可脚本化（输入为 LLM 标注）
- 置信度: high

### skills/shenbi-world-extraction/
- 处置: deep-read
- 声称检查的不变量: 从违规反推规则；4 段式散文；rules ≤10 条且每条 ≥2 证据；力量体系从行为反推；未确认项必标
- findings: 无（reads 三个 import/analysis 文件与 writes 五个 world 文件均与 index 一致；DOT 一致）
- 确定性替换候选: 弱——rules.md 条数 ≤10 上限（SKILL.md:69）为计数校验，可 G4 化
- 置信度: high

### skills/using-shenbi/
- 处置: deep-read
- 声称检查的不变量: 1% 规则；skill 检查先于澄清问题；HARD-GATE 无大纲不写正文；默认审计集
- findings: [F921]（group auditor 全缺 + 路由到废弃 skill + docs/specs 路径失效）
- 确定性替换候选: 无（meta 触发规则，无确定性环节）
- 置信度: high

---

## 3. 确定性替换候选清单（交 T14）

| # | skill | 可替换环节 | 判据 | 证据 |
|---|-------|-----------|------|------|
| 1 | shenbi-review-anti-ai / shenbi-review-group-craft(Dim3) | 10 项 anti-AI 确定性检查（CV、正则句式、破折号、转折词/标记词/疲劳词/禁忌词计数与阈值） | 纯文件文本处理 + 键值计数 + 阈值比较 | checklist.md:5-67（自述"零 LLM 成本"）；group-craft SKILL.md:213-226 |
| 2 | shenbi-foreshadowing-resolve | CP 公式计算、区间判定、逐层兑现升序排序、计数规则 | 纯算术 + 比较 + 排序 + 固定模板填充 | SKILL.md:74-82,124,191-200（阈值需先按 F903 统一） |
| 3 | shenbi-foreshadowing-lifecycle | overdue 判定（last_reinforced/max_distance/cultivation_interval vs current_chapter）、密度预算 ≤8 | 纯数值比较（skill 自述 deterministic）| SKILL.md:48,83 |
| 4 | shenbi-score-arc | final_score 加权聚合、passed/tier_advance 阈值判定 | 加权算术 + 阈值比较 | SKILL.md:34-39 |
| 5 | shenbi-plot-thread-weaver | max_gap 违规检测、空白章检测、线索总览表 8 列校验 | 计数 + 比较 + 表格式校验 | SKILL.md:188-196 |
| 6 | shenbi-review-sensitivity | 禁忌词匹配（精确/大小写/简繁/空白变体）与计数 | 纯字符串处理 | sensitive-words.md:79-85（数据源需先修 F906） |
| 7（弱） | shenbi-truth-sync | 推断条目占比 ≤20% 计数 | 阈值比较（输入为 LLM 标注） | SKILL.md:59 |
| 8（弱） | shenbi-chapter-planning | hook 账列校验/操作枚举/沉默规则、8 段标题精确匹配 | 表格式校验（G4 已部分实现） | SKILL.md:243-248,261-271 |

---

## 4. 覆盖统计与未覆盖

- deep-read skill 数：**25 / 25**
- 清单文件覆盖：34/34（25 SKILL.md + 4 辅助 md：chase-power.md/checklist.md/fanfic-modes.md/sensitive-words.md + 5 .gitkeep 零字节占位）
- 未覆盖文件：**0**
