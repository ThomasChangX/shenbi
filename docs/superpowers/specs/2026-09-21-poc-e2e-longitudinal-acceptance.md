> **Date:** 2026-09-21 | **Status:** Design（Revised 2026-09-21 · 价值门驳斥复核后修订：吸收 compute_drift 既有物、逐章判据改 state 终态信号、resonance 数据源改权威序列、canary 人工环节与 fixture 构造路径订正） | **Severity:** 🟠 P1 | **方法:** 零 LLM 确定性工程——tools/ 只读判读层，`src/shenbi/` 运行时零改动
> **系列:** POC E2E 验收层（源自 goal-prompt.md 2026-09-21 复盘） | **依赖:** 无（数据源均已落盘，见 §2） | **范围:** 纵向验收判据、`tools/report_longitudinal.py`、失败分类学映射、扩展性观测、justfile e2e recipe、INDEX/goal-prompt 登记 | **核心洞察:** 采集层已齐且**部分判读已有**——逐章审计、逐章 resonance 权威序列（`truth/resonance_trend.md`）、运行时漂移检测（`compute_drift.py`）、逐派发 TokenLedger 都在写盘/在跑——缺的是**验收判定层**：把数据变成 exit-code verdict 的纵向判据 + 失败分类学 + 扩展性观测；现行验收（`tests/tiers/acceptance.json` = `{"t1":94,"t2":94,"t3":94}`）是快照式层均分，对「开头好、中后期劣化」的长度依赖型失效无验收级判别力（运行时漂移引导 ≠ 验收判定）

# POC E2E 纵向验收（poc-e2e-longitudinal-acceptance）

## 元信息

- 编号：#68（= 现有最大 #67 + 1，按 INDEX 登记约定）
- 登记来源：2026-09-21 goal-prompt.md 复盘会话。复盘结论：goal-prompt.md 按「小规模 POC E2E」定位评估，方向/规模/非确定性豁免均成立（20 万字是「千万字稳定」主张的最小必要探测长度——长度依赖型失效在 T1 单技能与 3 章金丝雀里结构性不可见）；不成立的是判读层——验收判据、失败分类、扩展性观测三处缺口，本 spec 补齐
- **修订记录（2026-09-21，SDD 价值门两轮驳斥复核驱动）**：第一轮——①原 §0.1「零判别力」修辞订正（main 已有 `compute_drift.py` 运行时漂移检测，本 spec 定位改为**消费既有物补验收层**）；②原 §1「每章 aggregate 无未解决 BLOCKING/CRITICAL」判据不可操作（aggregate 无解决状态字段且为修订前工件）——改 state 终态信号；③resonance 数据源改 `truth/resonance_trend.md` 权威序列（原重读 audits 散文件为重复基建）；④e2e-canary 补停机语义；⑤验收 fixture 面订正 + G0.9 构造路径。第二轮——⑥合并复用措辞订正（audit_aggregate 无可分离合并纯函数，可复用件 = `extract_finding_units`，回退路径自写同语义合并 glue；`write_audit_aggregate` 是写操作不得调用）；⑦resonance_trend 表头前置条件成文（框架写方不写表头，`parse_trend` 无表头静默空读——工具须显式报错或 positional 回退）；⑧escalation 裁决重置交互 + 增长曲线条件性两条设计注记
- 与既有裁决的一致性：spec #67 §3 T1108（离线可执行模式不做）不受影响——本 spec 的报告工具只读已落盘产物，无派发、无 LLM、无新生产面，与「认可的离线技术 = 只读面 + PATH-stub」先例同族

## 0. 问题定义

goal-prompt.md（2026-06-13 冻结的历史快照，正文 append-only 不改）的验收层有三个缺口：

1. **判据是快照不是纵向**：交付物 1 是 72 技能 T1 均分 + 9 phase T2 + 3 pipeline T3，衡量「每个零件好不好」，不衡量「整机随时间退化没有」。前半程 95 分、后半程 70 分的运行按层均分可能照样「通过」。**已有部分的非验收级判读**：`compute_drift.py` 提供运行时漂移检测（≥3 章单调下滑/mean-2σ/卷下滑 → `truth/audit_drift.md` → triggers 漂移引导修正），但它是**修正引导**不是**验收判定**——无 exit-code verdict、无保量判据、无逐章下限、无前/中/后分段判定，且不产出任何报告给人工判读。本 spec 补验收层并**复用**（import 其纯函数）而非重实现漂移判据。
2. **已知最重要失效模式不是被测对象**：「开头好、中后期大量离谱问题」是 T1 分数预测不了的经验事实，但没有任何交付物系统性回答「哪一段、哪一类问题、哪个子系统、花了多少钱」。
3. **无扩展性外推数据**：对千万字主张，20 万字 POC 最值钱的产出之一是每万字成本/墙钟、真相文件增长曲线、上下文预算占用——一个都不在交付物清单里（`cost/report.py` 只有 per-skill 汇总 + 自注「by-chapter buckets carry no independent signal」的章均成本）。

## 1. 纵向验收判据（v1 初值，第一跑后校准）

判定对象：一个 pipeline 项目目录（`pipeline init` 产物）。四条件全部满足 = pass：

- **保量**：`chapters/chapter-1..N.md` 正文总字数 ≥ 目标字数 × 95%（目标字数读 seed 解析结果）。
- **保质·逐章终态健康**：`pipeline-state.json` 每章 `chapter_states[N]`（键 = `str(N)`）：`status` 为 `complete`（`ChapterStatus`，state.py:97）且 `audit_retry_count` == 0（v1 从严；首跑校准）——替代原「aggregate 无未解决 BLOCKING/CRITICAL」（aggregate 无解决状态字段且不保证逐章存在，见 §2）；每章 resonance 总分 ≥85 且全程均值 ≥90（读 `truth/resonance_trend.md`，见 §2 表头前置条件）。**重置交互注记**：resolve ESCALATION checkpoint 会清零受影响章的 `audit_retry_count`/`revision_count`（machine.py:119-137）——「==0」可被人因 approve 后置满足，escalation 事件只在 `checkpoint_history` 留痕，故趋势条件必须同时读计数器与 `checkpoint_history` 两面。
- **保质·趋势**：章节序等分前/中/后三段——后段 resonance 均值相对前段降幅 ≤5 分；后段 escalation/revision 频率 ≤ 前段 ×2（读 `chapter_states` 的 `revision_count`/`audit_retry_count` 与 `checkpoint_history`）；**漂移检测零 finding**——复用 `compute_drift.detect_chapter_drift`（连续 ≥3 章单调下滑/mean-2σ/卷下滑三检测，吸收并严于原「连续 ≥10 章单调下滑」条件）。
- **判定输出**：`metrics/longitudinal-report.json`（机器可读 verdict + 三段曲线 + 逐章明细），exit code 0=pass / 1=fail。

阈值全部是 v1 初值：第一次真实 20 万字跑的数据落盘后校准，修订记入本 spec 的 deviation 注记，不静默改。

## 2. `tools/report_longitudinal.py` 报告工具

- **输入**（全部已落盘，零新采集）：
  - resonance 逐章分：`truth/resonance_trend.md`——框架自维护的权威序列（chapter_loop.py:1856-1873 每章 insert-only 落盘，`build_resonance_trend_row` 9 列、`{N}` 键去重）。不重读 `audits/chapter-N-resonance.md` 散文件（重复基建，两套序列可能不一致）。**表头前置条件**：`parse_trend` 按表头名映射列（契约表头 `skills/shenbi-review-resonance/SKILL.md:174` 下 `overall` 恰在第 7 列）；表头只由 skill 首写，框架两条写方（chapter_loop insert 路径 / confidence_calibration 回退）均不写——无表头文件 `parse_trend` 静默返回空序列。工具须对「文件存在但无表头/零数据行」**显式报错**（禁止静默零分通过），或采用 positional 第 7 列回退（先例 `src/shenbi/orchestration/escalation_bridge.py:14-27`）。
  - 漂移检测：复用 `compute_drift.detect_chapter_drift` 纯函数（import，不重实现）。
  - 章节终态：`pipeline-state.json`（`chapter_states`：status/resonance_score/revision_count/audit_retry_count；`checkpoint_history`；写方 `machine.py`）。
  - 审计发现文本（失败分类学输入）：`audits/` 逐章审计报告——`chapter-N.aggregate.md` 存在则直接消费；不存在则对 raw glob `chapter-N-*.md` 复用 `extract_finding_units` 纯件 + 自写 ~10 行同语义合并 glue（`(severity, text)` 键去重、reporters 并集——合并循环内联在 `write_audit_aggregate` :150-171 无可分离纯函数，且它是写操作、只读判读层不得调用）（aggregate 是修订前工件：仅 chapter_loop.py:3021 revision 派发前 / :3220 audit-blocking 重试两处生成，**不保证逐章存在**；audit_aggregate.py:31 的 DOT 后缀设计保证 aggregate 不自匹配 raw glob）。
  - cost ledger：`cost/token-ledger.jsonl`（`TokenLedger.record` 带 chapter 字段，按章对齐）。
- **输出**：`metrics/longitudinal-report.md`（人读：曲线表 + 类别×章节热力图 + 责任子系统路由）+ `metrics/longitudinal-report.json`（机读 verdict）。
- **风格约束**：照 `audit_aggregate.py` 先例——纯解析、零 LLM、幂等、无副作用；放 `tools/`（同 `lint_audit_run.py` 先例；pyproject `"tools/**" = ["T201"]` 豁免 no-print、coverage floors 零 tools 键——注意 basedpyright 经测试 import 将其拉入 strict 类型检查面，属常规成本）。
- **关系**：`cost/report.py` 的 `render_report`/`write_report` 保留不动（其 `_try_avg_g3_score` 是均分口径）；本工具是纵向口径的独立消费者，不共享判定逻辑。

## 3. 失败分类学映射（确定性先行）

- **类别集合**（v1，与 review-* 技能族发现面对齐）：连续性断裂 / 人物漂移 / 世界规则违反 / 伏笔丢失 / 风格衰减 / 重复 / 节奏崩溃 / 敏感性。
- **实现**：关键字/正则 → 类别的映射表（数据为主，独立可测函数），作用于 §2 审计发现文本；报告输出类别 × 章节号热力图。确定性正则保证可重复、零成本；LLM 辅助分类另立裁决，不在本 spec。
- **责任子系统路由表**：类别 → 嫌疑子系统（state-settling、truth-sync、context-assemble、style-learning、foreshadowing-track、对应 review-*），让每次失败运行自动指向该修的面。

## 4. 扩展性观测（POC 第一交付物）

纵向报告按章节对齐输出：

- 每万字成本与墙钟（TokenLedger 按章聚合，`dispatch_helper.py:55` 已 import 使用）
- 真相文件大小随章节增长曲线（`truth/` 各文件尺寸按章）。**条件性注记**：框架自动 truth 快照已按 spec #26 path 3 移除，快照由条件技能步骤写——逐章历史序列不保证落盘，观测按实际存在的快照面输出并披露覆盖度
- 上下文预算压力：`dispatch_helper.py:241-242`（`_INPUT_MAX_CHARS_PER_FILE=32000` / `_INPUT_MAX_CHARS_TOTAL=128000`）截断事件计数按章分布
- 分段 checkpoint/escalation 频率

这些是对「千万字可行性」外推的依据，交付优先级排在小说文件本身之前。

## 5. justfile 接线 + 金丝雀快速回路

- `just e2e-report <dir>`：调用报告工具，exit code 即 verdict（可进 CI）。
- `just e2e-canary`：`pipeline init tests/fixtures/canary-3-chapter-seed.md`（目标字数 3000、3 章）+ `run_pipeline.sh` 驱动。**停机语义**（run_pipeline.sh 头注）：脚本驱动 `pipeline resume` 循环至首个 checkpoint/error 即停（exit 3 = blocked checkpoint），从不自动 approve——「跑通」= 到 checkpoint 后人工 `just pipeline-review <dir> <decision>` 裁决再续跑的回路。定位是两次昂贵 E2E 之间的分钟级回归，不是 20 万字 POC 的替代；recipe 注释写明人工环节，`just check` 不调用它（不触发付费派发）。

## 6. 登记与指针改动（随本 spec 登记已完成）

- INDEX.md：登记行 + 头部计数同步（`count_active_specs.py` lint 面）。
- goal-prompt.md：顶部历史快照标注下追加一行指针——验收层由 spec #68 接替，执行协议与三不原则继续有效。正文不动。

## 边界

- **不挂 G7 硬门**（v1 明确不做）：动 gates 牵出 marker、summarize-round 联动与一片测试合规面（估 +200–300 行）；先以 `just e2e-report` 供人工/CI 调用，第一跑校准阈值后另立裁决是否硬化。
- **不动 `src/shenbi/` 运行时**：全部新代码是已落盘产物的只读消费者（import 既有纯函数不改它们），回归风险≈0。
- **不改 goal-prompt.md 正文**：历史快照 append-only 先例（同 spec #67 对 audit-runs 的处理）。
- **不做 LLM 辅助失败分类、不做离线派发 stub**：前者另立，后者 spec #67 §3 已裁决不做。
- **不动 acceptance.json 的 T1/T2/T3 层均分阈值**：层均分继续管零件质量；本 spec 的纵向判据管整机退化，两套并行不互斥。

## 验收（可执行）

- `uv run python tools/count_active_specs.py` 通过（INDEX 头 = 目录扫描 = 1）
- `grep -n "spec #68" goal-prompt.md` 命中指针行
- `tools/report_longitudinal.py` 在测试构造的项目目录上跑出双报告且 verdict JSON 结构符合 §1。输入构造（G0.9：禁手写 mock，须经真实生产写方生成；单测 tmp_path 内联构造不属 G0.9 强制面——其只扫 T1 scenario.md，先例 tests/pipeline/test_audit_aggregate.py）：`truth/resonance_trend.md` 契约表头按 SKILL.md:174 写入 + 数据行经 `write_truth_file`/`build_resonance_trend_row` 写入、audits 面种子取 `tests/fixtures/audits/` 真实产物经生产写方入 tmp_path、ledger 经 `TokenLedger.record` 追加、state 经 pipeline state 机序列化；`tests/fixtures/snapshots/chapter-025/`（真实产物）提供 truth 面基准（增长曲线观测）
- 新增测试（tools 侧 2–3 文件，覆盖：三段趋势判定边界、分类映射表、ledger 按章对齐、verdict exit code）`uv run pytest -q` 全绿
- `just check` 全绿
