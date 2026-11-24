# Spec #111 · extractor 形状契约与长跑哨兵（extractor-shape-contract）：threads_overview 形状失配修复、extractor 应用率断言、truth 增长曲线哨兵、matrix 全量读收编

**日期**：2026-11-15｜ **系列**：多专家审计批（expert-audit）｜ **状态**：Design（r2，2026-11-24 Revised）｜ **优先级**：🟠 P1
**动机证据**：`src/shenbi/pipeline/read_extractors.py:470-477`（`extract_threads_overview` 要求 `^## 线索总览表$` **AND** `^## 线索详情$` 两节齐备，缺即 return ""）vs `novel-xinghuo-vol1/outline/thread_map.md`（**全文无「详情」二字**——`## 线索总览表`（:3）后直接 `### A1: …` 详情节，producer `shenbi-plot-thread-weaver` 从不写 H2「线索详情」分隔）→ **44 次生产 threads_overview reads 全部空转降级全文**（observability/dispatches manifest：`('full','threads_overview')×44`）；`dispatch_helper.py:905-934`（空输出仅 log WARN `extractor_failed_fulltext` 后全文注入——**零计数零断言零 CI 面**，「保护从未生效」不可见）；尺寸面：thread_map 19KB@50 章（B 批为其建 extractor 的动机）→ ~~线性外推 ~400KB@1000 章~~（**r2 撤回**：14 次派发观测中 thread_map 仅从 8,624 升到 9,489 字符，系开书时一次性规划、不随章线性增长；降级的现行代价是每次 planning 消费全文与 52 次无痕降级，而非体积）；全量读面普查（2026-11-15，contract reads×尺寸）：`truth/character_matrix.md` 202KB（**7 读者 FULL-READ**〔r2 更正，原记 8；`context-composing` 已接 `recent_increments`〕；生产 105 次读仅 9 次走 `matrix_scoped`、63 次 3K 截断缓存、33 次全文——`shenbi-memory-distill`/`shenbi-context-composing`/legacy `shenbi-review-character` 契约无 extractor）→ 3.9MB@1000 章；`truth/current_state.md` 103KB（5 读者 FULL-READ〔r2 更正，原记 6〕；settle p50 52K tokens——#95 后稳定但 6 个 FULL 读者随章线性涨）；`audit_context_cache.py:75-105`（shared ctx 各面 3000/5000 截断有界——对照面）；`src/shenbi/pipeline/read_extractors.py:983-1033`（11 extractor 注册表——形状假设全部单方，无 producer 侧契约）；`tests/`（grep 无 threads_overview 真文件形状测试——extractor 测试用自造 fixture 形状，与 producer 输出漂移无感知）。

**触及的不变量维度**：无（读面基建——只影响注入给 LLM 的窗口，不触叙事维度槽）

**r2 修订（2026-11-24 · 实现审计回写；证据＝八席实现审计之上下文成本席，协调者逐条重跑）**：
- **更正**：①thread_map 外推撤回（见动机证据行内）；matrix 整文件读者 7 个（原记 8）、current_state 5 个（原记 6）；②日志窗内 `extractor_failed_fulltext` 共 87 次＝threads_overview 真失败 52 次＋`recent_increments` 误报 33 次（单元数 ≤ 保留窗时实现返回空串并触发同一告警，`read_extractors.py:1030` 的 `empty_warn_predicate=has_chapter_units`）——照原样建哨兵，爬坡期会误红；③「44 次」为 2026-11-15 普查口径，保留。
- **新增证据**：(a) **截断已在发生**——`src/shenbi/pipeline/dispatch_helper.py:312-313`（`_INPUT_MAX_CHARS_PER_FILE = 32000`、`_INPUT_MAX_CHARS_TOTAL = 128000`）：vol1 ch50 的 `truth/character_matrix.md` 实 72,954 字符只送前约 31K、`current_state.md` 36,168 → 约 31.9K；矩阵顶部配对表（前言）约 1.5 行/章，把状态增量块挤出窗口（ch50 可见 15 块，按实测行速推演 ch100 约 10 块）；`shenbi-review-group-factual` 的 prompt 自 ch45 起停在 78–79K token（token 账本：ch29 58K → ch45 79K → ch49 79K）——不是不再增长，是多出来的部分被截掉；(b) **降级无痕**——`dispatch_helper.py:928-957`：切片器空转只 `log.warning`，派发清单对成功与降级都记 `"mode": "full", "matched_all": True`，trace 零记录——T2 的哨兵没有数据源；(c) **全书通配读面按比例硬切**——`:426`（`alloc = {name: int(budget * w / total_weight) …}`）与 `:451`（`content[:k] + "[TRUNCATED k/len chars]"`）：long-span／style-learning 每个章文件只留开头（ch50 约 35%），且混入修订前备份（见新增 T5）；(d) **归档工具同病**——`src/shenbi/pipeline/ledger_archive.py:163-166` 同样要求 `## 线索详情`，对 vol1 真文件抛 `ValueError`——线索滚动归档在真实项目上不可用；(e) weaver 的输出模板在 HEAD 写了 `## 线索详情`（`skills/shenbi-plot-thread-weaver/SKILL.md:165`），真文件偏离模板而 G4 不钉节名。
- **任务增补**：T1 加「`ledger_archive` 同步容形＋G4 钉节名」；T2 改为「派发清单记录 served／raw 字符数与 extractor 是否生效（弃面与截断同样入档）→ 哨兵读清单而非读日志」，并修 `recent_increments` 的空串误报；T3 加「逐技能 prompt 体量斜率（token 账本）与『已触预算帽』哨兵——触帽后报可见比例而非体量」；T4 加「`review-group-factual` 的 current_state／matrix 读面与 `name_registry`／`prop_registry` 窗口化（两表各涨约 300 字符/章，是 settle 超预算的结构性原因——与 #121 T1 的交界：#121 先保证据面，本件根治体积）」；T4 另加「全书通配读面（7 个 `chapters/*.md` 技能）改专用切片——近 N 章全文＋其余摘要，或展开超阈值时拒派」；**新增 T5**。
- **新增 T5 · 修订前备份隔离**：`src/shenbi/pipeline/chapter_loop.py:3054` 把修订前备份写成 `chapters/chapter-{N}-pre-rev.md`，与正章同目录；7 个技能契约整读 `chapters/*.md`（chapter-pattern／character-extraction／review-arc-payoff／review-long-span／short-packaging／style-learning／world-extraction），被否决的旧稿于是进入卷级审计、人物／世界抽取与风格统计，并挤占预算（vol1 现有 32 份）。判据：备份移出 `chapters/`（或读路径统一过滤）；契约通配展开结果不含 `*-pre-rev.md`（真项目副本红测）。
- **依赖与顺序**：#92／#105／#109 均已归档——原依赖链只剩名称；现排 #121 之后（`dispatch_helper.py` 降级序先行）与 #122 之后（`audit` 读面语义）。

---

## 0. 根因

**extractor 是消费者单方形状假设，producer 不被契约钉死节名，降级只有 log**：B 批为千万字建了 11 个窗口 extractor，但「形状对不对」没有任何双向契约或断言——threads_overview 从项目第一天起就对真实 thread_map 空转（44 次生产读全部降级），保护形同虚设；同理 matrix_scoped 只有 9/105 真实应用率。长跑风险不在 CPU（实测 extractor 计时线性且便宜：1MB 输入 17ms）而在 **LLM 载荷面**：失配降级=全文注入=无界增长，且体系对此无测量。

**用户裁定（2026-11-15）**：不考虑在飞项目——vol1 thread_map 不回改结构（修复走 extractor 容形侧，producer 契约面向新项目）；存量降级史仅入基线报告。

**备选案已评估并否决**：「producer 改写 `## 线索详情` 节名对齐 extractor」——会改写 vol1 在飞文件结构（违反裁定）且 producer 技能改动面更大；「删掉 threads_overview 直读全文」——放弃 B 批长窗保护，方向反了。

## 1. 任务分解

### T1 · threads_overview 容形修复
- `extract_threads_overview` 容形：`### <THREAD_ID>:` 详情节直挂总览表后（无 H2 分隔）为合法形状——`m_det` 缺席时详情体起点回退为总览表区块之后首个 `### ` 节（`read_extractors.py:470-477` 改造，保留旧形状兼容——两形状并认）；
- 红测用 vol1 真文件副本入 `tests/fixtures`（G0.9 真产物基座）：断言输出非空、含全部活跃线（`### A1…C7` 计数）、RESOLVED 省略与归档索引逻辑过。

**判据**：单测（vol1 真形状→非空切片；旧形状 fixture→行为逐字节不变——差分）；`just judge-reliability` 无关，此处 `python -m pytest tests/…threads…` 绿。

### T2 · extractor 应用率哨兵
- 降级计数落 `escape-hatch-state.json`（#81 deviation ② 既有面）按 extractor 名聚合计次；
- CI 断言工具（`just extractor-lint <dir>` 或并入既有 lint）：对声明了 extractor 的 reads，运行窗内降级率 >50% → 红（附 extractor 名与文件）；零应用（声明过但一次未用）→ WARN；
- 红测：构造形状失配 fixture → 哨兵红；真形状 → 绿。

**判据**：`just extractor-lint` 对 vol1 回放输出 threads_overview 降级 44/44 红（基线证明哨兵有牙）；修后对新 fixture 绿。

### T3 · truth 增长曲线哨兵
- `tools/truth_growth_report.py`（或并入 T2 工具）：各 truth/outline 面「KB/章」线性拟合斜率表 + @1000 章外推值对照阈值表（阈值初版：单面注入 LLM 的全文读 @1000 章不得超过 200KB——超出的面进 T4 收编清单）；
- 基线表入 `docs/framework/`（体积预算文档，#95 T3③ SKILL_TOTAL_CHAR_BUDGET 的数据面配套）。

**判据**：报告产出（vol1 基线：matrix 3.9MB/current_state 2.0MB/thread_map 0.4MB@1000 章外推在册）；阈值超限面清单非空（matrix/current_state 必入——证明哨兵能抓）。

### T4 · matrix/current_state 全量读收编
- 8 个 matrix FULL-READ 读者逐一裁定：弧级/全局技能（memory-distill、context-composing）接 `matrix_scoped` 或新窗口 extractor（`matrix_rows_scoped`?——plan 期按各技能真实消费字段定形）；legacy `shenbi-review-character` 若为 DEPRECATED 单列（audit_layer 注释先例）走登记豁免；
- current_state 6 读者同查（`recent_increments` 已存在——接线的成本面先例 session32 实测 -23%~-52%）；
- 判据型消费（G4/gate 面）不动——只收编 LLM 注入面。

**判据**：收编后 dry-run manifest 显示 extractor 键命中（对照 33 次全文→0）；未收编者豁免表登记（理由列）。

## 2. 验收
1. T1-T4 判据全绿；
2. 长跑推演：以本批 `/tmp` 原型脚本口径（tiling+renumber 合成 1000 章等价输入）入库为 tests 工具，断言各 extractor 输出 @K=1 与 K=20 的固定章窗口输出一致（窗口不变性）+ 计时曲线线性（回归护栏）；
3. 对 vol1 回放：threads_overview 修复后对真文件切片非空（44 次降级→0 级——对照基线）；
4. bug-hunt：producer 改节名（模拟漂移）→ T2 哨兵红。

## 3. 风险
- 容形放宽=切片承诺弱化（两形状并认须双向钉：weaver SKILL 输出格式节加「总览表后直挂 ### 节」声明——extractor 断言与 producer 格式节同批改，防第三形状再漂）；
- T4 收编改变注入内容可能影响技能行为（消费面 diff 验证：收编前后同 fixture 派发 dry-run 的 prompt 面差异仅窗口化——不新增语义）；
- 增长阈值拍脑袋风险——首版只报不拦（P2 批再议硬门）；
- **共享文件面**：`read_extractors.py` 与 #87 已完结（无在飞冲突）；`dispatch_helper.py` 读组装面与 #92（在飞 T2a）/#105/#107/#109 同文件——**#92 → #105/#107 → #109 → #111** 顺序，本件 plan 首步 re-anchor；SKILL 契约改动过 `lint_registry_reconcile`（#90 机制现成）。
