# Spec #111 · extractor 形状契约与长跑哨兵（extractor-shape-contract）：threads_overview 形状失配修复、extractor 应用率断言、truth 增长曲线哨兵、matrix 全量读收编

**日期**：2026-11-15｜ **系列**：多专家审计批（expert-audit）｜ **状态**：Design（r1，2026-11-15）｜ **优先级**：🟠 P1
**动机证据**：`src/shenbi/pipeline/read_extractors.py:470-477`（`extract_threads_overview` 要求 `^## 线索总览表$` **AND** `^## 线索详情$` 两节齐备，缺即 return ""）vs `novel-xinghuo-vol1/outline/thread_map.md`（**全文无「详情」二字**——`## 线索总览表`（:3）后直接 `### A1: …` 详情节，producer `shenbi-plot-thread-weaver` 从不写 H2「线索详情」分隔）→ **44 次生产 threads_overview reads 全部空转降级全文**（observability/dispatches manifest：`('full','threads_overview')×44`）；`dispatch_helper.py:905-934`（空输出仅 log WARN `extractor_failed_fulltext` 后全文注入——**零计数零断言零 CI 面**，「保护从未生效」不可见）；尺寸面：thread_map 19KB@50 章（B 批为其建 extractor 的动机）→ 线性外推 ~400KB@1000 章，每次 planning/escalation 消费全文；全量读面普查（2026-11-15，contract reads×尺寸）：`truth/character_matrix.md` 202KB（**8 读者 FULL-READ**；生产 105 次读仅 9 次走 `matrix_scoped`、63 次 3K 截断缓存、33 次全文——`shenbi-memory-distill`/`shenbi-context-composing`/legacy `shenbi-review-character` 契约无 extractor）→ 3.9MB@1000 章；`truth/current_state.md` 103KB（6 读者 FULL-READ；settle p50 52K tokens——#95 后稳定但 6 个 FULL 读者随章线性涨）；`audit_context_cache.py:75-105`（shared ctx 各面 3000/5000 截断有界——对照面）；`src/shenbi/pipeline/read_extractors.py:983-1033`（11 extractor 注册表——形状假设全部单方，无 producer 侧契约）；`tests/`（grep 无 threads_overview 真文件形状测试——extractor 测试用自造 fixture 形状，与 producer 输出漂移无感知）。

**触及的不变量维度**：无（读面基建——只影响注入给 LLM 的窗口，不触叙事维度槽）

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
