> **Date:** 2026-09-21 | **Status:** Design（Revised 2026-09-21 · 价值门两轮驳斥 + 设计审查五轮收敛） | **Severity:** 🟠 P1 | **方法:** 零 LLM 确定性工程——tools/ 只读判读层，`src/shenbi/` 运行时零改动
> **系列:** POC E2E 验收层（源自 goal-prompt.md 2026-09-21 复盘） | **依赖:** 无（数据源均已落盘，见 §2） | **范围:** 纵向验收判据、`tools/report_longitudinal.py`、失败分类学映射、扩展性观测、justfile e2e recipe、INDEX/goal-prompt 登记 | **核心洞察:** 采集层已齐且**部分判读已有**——逐章审计、逐章 resonance 权威序列（`truth/resonance_trend.md`）、运行时漂移检测（`compute_drift.py`）、逐派发 TokenLedger 都在写盘/在跑——缺的是**验收判定层**：把数据变成 exit-code verdict 的纵向判据 + 失败分类学 + 扩展性观测；现行验收（`tests/tiers/acceptance.json` = `{"t1":94,"t2":94,"t3":94}`）是快照式层均分，对「开头好、中后期劣化」的长度依赖型失效无验收级判别力（运行时漂移引导 ≠ 验收判定）

# POC E2E 纵向验收（poc-e2e-longitudinal-acceptance）

## 元信息

- 编号：#68（= 现有最大 #67 + 1，按 INDEX 登记约定）
- 登记来源：2026-09-21 goal-prompt.md 复盘会话。复盘结论：goal-prompt.md 按「小规模 POC E2E」定位评估，方向/规模/非确定性豁免均成立（20 万字是「千万字稳定」主张的最小必要探测长度——长度依赖型失效在 T1 单技能与 3 章金丝雀里结构性不可见）；不成立的是判读层——验收判据、失败分类、扩展性观测三处缺口，本 spec 补齐
- **修订记录（2026-09-21，价值门两轮驳斥 + 阶段 3 设计审查驱动）**：
  - 价值门第一轮：①「零判别力」修辞订正（main 已有 `compute_drift.py` 运行时漂移检测，定位改为**消费既有物补验收层**）；②「aggregate 无未解决 BLOCKING/CRITICAL」判据不可操作（aggregate 无解决状态字段且为修订前工件）——改 state 终态信号；③resonance 数据源改 `truth/resonance_trend.md` 权威序列；④e2e-canary 补停机语义；⑤验收 fixture 面订正 + G0.9 构造路径
  - 价值门第二轮：⑥合并复用措辞订正（可复用件 = `extract_finding_units`，回退自写同语义 glue；`write_audit_aggregate` 是写操作不得调用）；⑦resonance_trend 表头前置条件成文；⑧escalation 重置交互 + 增长曲线条件性设计注记
  - 设计审查轮 1（1C/4I/5M 全修）：⑨**截断观测移除**（Critical——截断事件仅 structlog WARN 走 stderr 零持久化，`dispatch_helper.py:311/:787/:795` + `logging.py:52`，按原措辞是 dead-wire；v1 不含，复活条件见 §4）；⑩漂移检测归属订正（`detect_chapter_drift` 仅单调 ≥3 + mean-2σ 两检测，「卷下滑」在 `detect_volume_drift` 消费 `arc_payoff_trend.md`——v1 verdict 只纳前者）；⑪判据边界语义五条钉死（N 来源/分段规则/缺行 fail-closed/频率主源/漂移域，见 §1）；⑫工具自带 `{N}` 键行解析器（`parse_trend` 丢章节键不复用）；⑬exit code 2 = data error；⑭保量字数口径钉死；⑮报告 coverage 披露；⑯「可进 CI」措辞改人工 POC 消费者
  - 设计审查轮 2（0C/3I/5M 全修）：⑰chapter_states 缺章同 fail-closed（中段空洞 `committed_chapter_anchor` 取最大号不暴露）；⑱exit 2 输入面按 verdict 关键输入（novel.json/state/resonance）与观测面输入（ledger/快照→coverage 披露）枚举钉死；⑲pending_checkpoint 非 NONE 披露不计数 + `chapter=None` 事件排除披露；⑳CJK 区间计数口径钉死（U+4E00–U+9FFF，`_check_word_count_bounds` 同口径）；㉑双解析器引用订正（escalation_bridge 为 `parse_resonance_scores`）；㉒漂移转述补「累降 ≥3 分」+ 权威语义归属声明；㉓escalation 零基线注记；㉔canary 目录交接注记
  - 设计审查轮 3（0C/1I/5M 全修）：㉕保量口径改 `word_count_md`（G4 地板自身口径——剥元节防 ~15% 虚高侵蚀 5% 余量）；㉖重复 `{N}` 键 exit 2；㉗N_done>N_target 披露不 fail + total_chapters=0 同 key 缺失；㉘ledger attempt 不可重置信号入披露；㉙canary 预期重试噪音注记；㉚verdict schema 版本标识留 plan
  - 设计审查轮 4（0C/2I/5M 全修）：㉛**审计发现输入统一 raw glob 优先**（aggregate 三重缺陷：修订前陈旧性污染责任路由、渲染格式与 `extract_finding_units` 不兼容直跑零命中、内嵌 resonance 正文——aggregate 仅 raw glob 为空时回退且 coverage 标注）；㉜chapter 主文件缺失 fail-closed（第三输入面对称，防 0 字假通过）；㉝「四条件」改「三条件+一项披露」；㉞判定顺序钉死（data-error 先于完整性 fail 先于质量条件）；㉟「频率」残留改「计数」；㊱coverage 补 audits 章覆盖率（审查者 M5 引用线号自误——`AGGREGATE_SUFFIX` 实在 :31，spec 原值正确不改）
  - 设计审查轮 5（0C/1I/8M 全修）：㊲分段规则枚举钉死（r=0→(f,f,f)/r=1→(f,f,c)/r=2→(f,c,c)——字面「余数归后段」在 r=2 自相矛盾）；㊳total_chapters 锚点改 `_shared.py:140`；㊴target_word_count=0 同拦 exit 2；㊵列绑定按表头名；㊶ledger 跳行数披露；㊷e2e-report shebang 形式保三态传播；㊸测试清单补 N≡2 分段/aggregate 回退/N_done>N_target
- 与既有裁决的一致性：spec #67 §3 T1108（离线可执行模式不做）不受影响——本 spec 的报告工具只读已落盘产物，无派发、无 LLM、无新生产面，与「认可的离线技术 = 只读面 + PATH-stub」先例同族

## 0. 问题定义

goal-prompt.md（2026-06-13 冻结的历史快照，正文 append-only 不改）的验收层有三个缺口：

1. **判据是快照不是纵向**：交付物 1 是 72 技能 T1 均分 + 9 phase T2 + 3 pipeline T3，衡量「每个零件好不好」，不衡量「整机随时间退化没有」。前半程 95 分、后半程 70 分的运行按层均分可能照样「通过」。**已有部分的非验收级判读**：`compute_drift.py` 提供运行时漂移检测（≥3 章单调下滑/mean-2σ → `truth/audit_drift.md` → triggers 漂移引导修正），但它是**修正引导**不是**验收判定**——无 exit-code verdict、无保量判据、无逐章下限、无前/中/后分段判定，且不产出任何报告给人工判读。本 spec 补验收层并**复用**（import 其纯函数）而非重实现漂移判据。
2. **已知最重要失效模式不是被测对象**：「开头好、中后期大量离谱问题」是 T1 分数预测不了的经验事实，但没有任何交付物系统性回答「哪一段、哪一类问题、哪个子系统、花了多少钱」。
3. **无扩展性外推数据**：对千万字主张，20 万字 POC 最值钱的产出之一是每万字成本/墙钟、真相文件增长曲线——不在交付物清单里（`cost/report.py` 只有 per-skill 汇总 + 自注「by-chapter buckets carry no independent signal」的章均成本）。

## 1. 纵向验收判据（v1 初值，第一跑后校准）

判定对象：一个 pipeline 项目目录（`pipeline init` 产物）。**三条件全部满足 = pass**（另有一项不可重置信号披露，不进判据）：

- **保量**：`chapters/chapter-1..N.md` 正文总字数 ≥ 目标字数 × 95%。目标字数读 `novel.json`（seed 解析落盘）；**字数口径**：`word_count_md`（gates/shared.py:107——G4 地板自身口径：剥 frontmatter/代码块/`PRE_WRITE_CHECK`/`POST_WRITE_SELF_CHECK` 等元节后 CJK 计数；裸全文计数会被元节抬高 ~15%，对 5% 余量是实质侵蚀），仅精确 `chapter-N.md` 主文件计入（`committed_chapter_anchor` 同口径——pre-rev/快照/label 副本不计，chapter_loop.py:329-343 先例）。
- **保质·逐章终态健康**：`pipeline-state.json` 每章 `chapter_states[N]`（键 = `str(N)`）：`status` 为 `complete`（`ChapterStatus`，state.py:97）且 `audit_retry_count` == 0（v1 从严；首跑校准）；每章 resonance 总分 ≥85 且全程均值 ≥90（读 `truth/resonance_trend.md`，见 §2 表头前置条件）。**重置交互注记**：resolve ESCALATION checkpoint 会清零受影响章的 `audit_retry_count`/`revision_count`（machine.py:119-137）——「==0」可被人因 approve 后置满足，escalation 事件只在 `checkpoint_history` 留痕，故趋势条件以 `checkpoint_history` 为主源（见下）。
- **保质·趋势**：章节序等分前/中/后三段——后段 resonance 均值相对前段降幅 ≤5 分；后段 escalation 计数 ≤ 前段 ×2（**计数语义非速率**；**主源 = `checkpoint_history` 的 ESCALATION 事件按段计数**；state 计数器因重置是低估量，仅作披露不进判据。**零基线注记**：前段计数为 0 时 cap = 0，后段任一 escalation 即 fail——从严预期，非 bug，阈值首跑校准。**pending 注记**：`checkpoint_history` 仅在 resolve 时 append——`state.pending_checkpoint` 非 NONE（运行停在未裁决 checkpoint，恰是失败运行的典型输入态）→ 报告显式披露，不计入分段；`chapter=None` 的事件排除出分段计数并披露）；**漂移检测零 finding**——复用 `compute_drift.detect_chapter_drift`（两检测：连续 ≥3 章单调下滑且 smoothed 累降 ≥3 分 + mean-2σ；**以被 import 函数实现为权威语义，本节转述仅为导读**；**域 = overall 序列**，占位行子维为 "-" 不构成序列；`min_samples_sigma=6` → 章数 <6 时 2σ 检测不触发，属预期——canary 3 章即此情形）。
- **不可重置重试信号披露**：逐章 `audit_retry_count == 0` 可被 escalation-approve 后置清零（见上重置交互）——verdict JSON 披露 ledger `attempt` 字段聚合的每章派发尝试数（`cost/ledger.py:50`，不可重置），供首跑校准对照；v1 不进判据。
- **判定输出**：`metrics/longitudinal-report.json`（机器可读 verdict + 三段曲线 + 逐章明细 + coverage 披露；字段集与 schema 版本标识 `shenbi-longitudinal-verdict-v1` 在 plan 定稿），exit code **0=pass / 1=fail / 2=data error**（fail-closed，禁止静默零数据通过）。**exit 2 输入面枚举**：verdict 关键输入缺失或结构不完整——`novel.json` 缺失/坏 JSON/缺 `total_chapters` 或目标字数键**或值为 0**（volume-outlining 未跑时 `total_chapters` 根本不存在，`update_total_chapters` 静默返 0；`target_word_count: 0` 令保量平凡通过，同拦）、`pipeline-state.json` 缺失/坏 JSON、`truth/resonance_trend.md` 缺失/无表头/零数据行/重复键。**观测面输入**（`cost/token-ledger.jsonl` 缺失/空、truth 快照缺失）→ verdict 不受影响，coverage 披露 0%。

**边界语义（钉死，plan 阶段照抄不发明）**：

- **N 的来源**：目标章数 `N_target` = `novel.json` 的 `total_chapters`（volume-outlining 后由 `update_total_chapters` 写入，`pipeline/_shared.py:140`，经 triggers.py 调用——init 时该键不存在，cli.py:481 注释明示）；完成锚点 `N_done` = `chapters/` 精确 `chapter-N.md` 最大号（`committed_chapter_anchor` 口径）。`N_done < N_target` → verdict fail 并披露差额（运行未完成或丢章）；`N_done > N_target` → 披露不 fail（锚点与元数据漂移，人工判读）；`total_chapters` 缺键或值为 0 → exit 2（同 key 缺失处理）。分段与逐章判据作用于 `1..N_done`。
- **分段规则**：三段等分，`r = N mod 3` 且 `f = floor(N/3)`、`c = ceil(N/3)`：**r=0 → (f,f,f)；r=1 → (f,f,c)；r=2 → (f,c,c)**——多出的章从后段起逐段各 +1，`len(seg_i) ∈ {f, c}` 恒成立，禁止 r=2 时全并入后段（字面「余数归后段」会得 (f,f,f+2) 违反约束）；`N_done < 3` → exit 2 data error（reason: insufficient chapters）——canary N=3 为每段 1 章的退化情形，判据语义成立但分辨率最低，报告注明。
- **resonance 缺行 / chapter_states 缺章 / chapter 主文件缺失 fail-closed（三输入面对称）**：`1..N_done` 中任一章在 `resonance_trend.md` 无 `{N}` 行、或 overall 单元格非数值（`pending`/`-`）、或在 `chapter_states` 无 `str(N)` 键（中段空洞——`committed_chapter_anchor` 取最大号不暴露洞）、或 `chapter-N.md` 主文件缺失（缺章静默贡献 0 字可令 98.3% ≥ 95% 假通过）→ 该章判 fail（exit 1，明细披露缺章）。**重复 `{N}` 键**（两写方结构性去重后理论上仅 malformed 键形可致）→ exit 2 data error。
- **趋势计数**：escalation 计数 = `checkpoint_history` 中 `type == "escalation"` 事件按所在段计数（条目含 type/chapter/decision/resolved_at，machine.py:110-118）；revision/audit_retry 计数器仅披露。**判定顺序钉死**：data-error 检查（exit 2 面）先于完整性 fail（`N_done < N_target` / 缺章缺行，exit 1），最后判质量条件（保量/趋势）——`N_done < 3` 归 data-error 先行短路。

阈值全部是 v1 初值：第一次真实 20 万字跑的数据落盘后校准，修订记入本 spec 的 deviation 注记，不静默改。

## 2. `tools/report_longitudinal.py` 报告工具

- **输入**（全部已落盘，零新采集）：
  - resonance 逐章分：`truth/resonance_trend.md`——框架自维护的权威序列（chapter_loop.py:1856-1873 每章 insert-only 落盘，`build_resonance_trend_row` 9 列、`{N}` 键去重）。**工具自带按 `{N}` 键的行解析器**产出 `(chapter, overall)` 对——不复用 `parse_trend`（compute_drift.py:164，丢章节键、静默跳过非数值行）与 `parse_resonance_scores`（`src/shenbi/orchestration/escalation_bridge.py:10-26`，同丢章节键），二者仅作列布局参考；**列绑定按表头名**（非固定下标——skill 侧未来列重排时显式报错而非静默误读数值邻列）。不重读 `audits/chapter-N-resonance.md` 散文件（重复基建，两套序列可能不一致）。**表头前置条件**：契约表头 `skills/shenbi-review-resonance/SKILL.md:174` 下 `overall` 恰在第 7 列；表头只由 skill 首写，框架两条写方（chapter_loop insert 路径 / confidence_calibration 回退）均不写——工具对「文件缺失/存在但无表头/零数据行」**exit 2 显式报错**（禁止静默零分通过）。
  - 漂移检测：复用 `compute_drift.detect_chapter_drift` 纯函数（import，不重实现；输入 = 工具自身解析器的 overall 序列，`human_overridden` 列真值作 `exclude_indices`）。
  - 章节终态：`pipeline-state.json`（`chapter_states`：status/resonance_score/revision_count/audit_retry_count；`checkpoint_history`；写方 `machine.py`）。
  - 审计发现文本（失败分类学输入）：**统一从 raw glob `chapter-N-*.md` 消费**——复用 `extract_finding_units` 纯件 + 自写 ~10 行同语义合并 glue（`(severity, text)` 键去重、reporters 并集——合并循环内联在 `write_audit_aggregate` :150-171 无可分离纯函数，且它是写操作、只读判读层不得调用；DOT 后缀 `audit_aggregate.py:31` 保证 aggregate 不自匹配 raw glob）。理由：①`chapter-N.aggregate.md` 是修订前工件（仅 chapter_loop.py:3021/:3220 两处生成，终审计重写 raw 报告但**不重生成** aggregate——按它分类会把已修复的 pre-revision 失败混进热力图，恰污染中后期章的责任路由）；②aggregate 渲染格式（severity 在 `## <SEV> Findings` H2、bullet 裸文本）与 `extract_finding_units` 的行内 severity 要求不兼容，直跑零命中；③aggregate 内嵌 resonance 逐字正文，raw 路径经 `_RESONANCE_NAME_RE`（audit_aggregate.py:47）结构性排除。**aggregate 仅在 raw glob 为空时作回退源**（此时按 aggregate 自身 H2 分节格式解析，回退在 coverage 披露中标注）。
  - cost ledger：`cost/token-ledger.jsonl`（`TokenLedger.record` 带 chapter 字段 + ISO 时间戳，按章对齐；墙钟 = 按章 timestamp min/max 差）。
- **输出**：项目目录下 `metrics/longitudinal-report.md`（人读：曲线表 + 类别×章节热力图 + 责任子系统路由）+ `metrics/longitudinal-report.json`（机读 verdict + coverage 披露：resonance 行数/章数比、audits 章覆盖率、ledger 章覆盖率 + 跳行数（`iter_records` 兼容性静默跳过坏行——章内行损失不可见，须单独披露）、失败分类命中率/未分类占比——任一 <100% 显式披露，防静默数据缺口）。
- **风格约束**：照 `audit_aggregate.py` 先例——纯解析、零 LLM、幂等、无副作用；放 `tools/`（同 `lint_audit_run.py` 先例；pyproject `"tools/**" = ["T201"]` 豁免 no-print、coverage floors 零 tools 键——注意 basedpyright 经测试 import 将其拉入 strict 类型检查面，属常规成本）。
- **关系**：`cost/report.py` 的 `render_report`/`write_report` 保留不动（其 `_try_avg_g3_score` 是均分口径）；本工具是纵向口径的独立消费者，不共享判定逻辑。

## 3. 失败分类学映射（确定性先行）

- **类别集合**（v1，与 review-* 技能族发现面对齐）：连续性断裂 / 人物漂移 / 世界规则违反 / 伏笔丢失 / 风格衰减 / 重复 / 节奏崩溃 / 敏感性。
- **实现**：关键字/正则 → 类别的映射表（数据为主，独立可测函数），作用于 §2 审计发现文本；报告输出类别 × 章节号热力图 + 未分类占比（v1 关键词语料以 `tests/fixtures/audits/` 真实产物 + `audit-report-example.md` 为校准基准，覆盖度如实披露）。确定性正则保证可重复、零成本；LLM 辅助分类另立裁决，不在本 spec。
- **责任子系统路由表**：类别 → 嫌疑子系统（state-settling、truth-sync、context-assemble、style-learning、foreshadowing-track、对应 review-*），让每次失败运行自动指向该修的面。

## 4. 扩展性观测（POC 第一交付物）

纵向报告按章节对齐输出：

- 每万字成本与墙钟（TokenLedger 按章聚合，`dispatch_helper.py:55` 已 import 使用；墙钟 = 章内首末记录 timestamp 差）
- 真相文件大小随章节增长曲线（`truth/` 各文件尺寸按章）。**条件性注记**：框架自动 truth 快照已按 spec #26 path 3 移除，快照由条件技能步骤写——逐章历史序列不保证落盘，观测按实际存在的快照面输出并披露覆盖度
- 分段 checkpoint/escalation 计数（`checkpoint_history` 主源）

这些是对「千万字可行性」外推的依据，交付优先级排在小说文件本身之前。

**v1 明确不含：上下文截断事件按章分布。** 截断事件当前仅以 structlog WARN 走 stderr（`dispatch_helper.py:311/:787/:795`，`logging.py:52` stderr factory），零持久化——采集它须先裁决：截断点追加 JSONL（动运行时，越本 spec 边界）或 POC 运行手册统一 stderr 捕获标准（越 goal-prompt 执行协议面）。二者均另立裁决；**复活条件**：上述任一持久化机制落地后，本观测作为 report 的增量面恢复（工具输入面 + coverage 披露天然容纳）。

## 5. justfile 接线 + 金丝雀快速回路

- `just e2e-report <dir>`：调用报告工具，exit code 即 verdict（recipe 用 shebang 形式保三态 exit 传播——linewise 形式可能坍缩 2→1，plan 阶段验证）。**v1 消费者 = 人工 20 万字 POC 验收**（goal-prompt.md 指针行委托）；CI 接线属后续另立裁决（需可提交的 fixture 项目目录作 CI 输入，v1 不做）。
- `just e2e-canary`：`pipeline init tests/fixtures/canary-3-chapter-seed.md`（目标字数 3000、3 章）+ `run_pipeline.sh` 驱动。**停机语义**（run_pipeline.sh 头注）：脚本驱动 `pipeline resume` 循环至首个 checkpoint/error 即停（exit 3 = blocked checkpoint），从不自动 approve——「跑通」= 到 checkpoint 后人工 `just pipeline-review <dir> <decision>` 裁决再续跑的回路。定位是两次昂贵 E2E 之间的分钟级回归，不是 20 万字 POC 的替代；recipe 注释写明人工环节，`just check` 不调用它（不触发付费派发）。**预期重试噪音注记**：seed 目标 3000 总字（~1000/章）低于 G4 章地板 `CHAPTER_WORD_FLOOR = 3000`（gates/shared.py:29）——每章会走 G4 失败→纠正重试→auto-continue 路径（chapter_loop.py:3121-3146），canary 每章双倍 drafting 派发成本属预期非 bug；如需消除，plan 阶段裁决 seed/地板关系（调 seed 或豁免面）。项目目录交接（`pipeline init` 自动命名 → `run_pipeline.sh` 以 arg1 接收）是 recipe 布线细节，用固定/已 gitignore 目录（`.gitignore` 已含 `/novel-*/` 与 `/pipeline.log`）——具体布线留 plan。

## 6. 登记与指针改动（随本 spec 登记已完成）

- INDEX.md：登记行 + 头部计数同步（`count_active_specs.py` lint 面）。
- goal-prompt.md：顶部历史快照标注下追加一行指针——验收层由 spec #68 接替，执行协议与三不原则继续有效。正文不动。

## 边界

- **不挂 G7 硬门**（v1 明确不做）：动 gates 牵出 marker、summarize-round 联动与一片测试合规面（估 +200–300 行）；先以 `just e2e-report` 供人工调用，第一跑校准阈值后另立裁决是否硬化。
- **不动 `src/shenbi/` 运行时**：全部新代码是已落盘产物的只读消费者（import 既有纯函数不改它们），回归风险≈0。
- **不改 goal-prompt.md 正文**：历史快照 append-only 先例（同 spec #67 对 audit-runs 的处理）。
- **不做 LLM 辅助失败分类、不做离线派发 stub**：前者另立，后者 spec #67 §3 已裁决不做。
- **不动 acceptance.json 的 T1/T2/T3 层均分阈值**：层均分继续管零件质量；本 spec 的纵向判据管整机退化，两套并行不互斥。
- **不采集上下文截断事件**（v1）：见 §4 复活条件。

## 验收（可执行）

- `uv run python tools/count_active_specs.py` 通过（INDEX 头 = 目录扫描 = 1）
- `grep -n "spec #68" goal-prompt.md` 命中指针行
- `tools/report_longitudinal.py` 在测试构造的项目目录上跑出双报告且 verdict JSON 结构符合 §1（含边界语义：N_done < N_target fail、缺行章 fail-closed、exit 2 data error 面、分段余数归后段）。输入构造（G0.9：禁手写 mock，须经真实生产写方生成；单测 tmp_path 内联构造不属 G0.9 强制面——其只扫 T1 scenario.md，先例 tests/pipeline/test_audit_aggregate.py）：`truth/resonance_trend.md` 契约表头按 SKILL.md:174 写入 + 数据行经 `write_truth_file`/`build_resonance_trend_row` 写入、audits 面种子取 `tests/fixtures/audits/` 真实产物经生产写方入 tmp_path、ledger 经 `TokenLedger.record` 追加、state 经 pipeline state 机序列化、`novel.json` 经 `safe_write`/seed 解析面写入；`tests/fixtures/snapshots/chapter-025/`（真实产物）提供 truth 面基准（增长曲线观测）
- 新增测试（tools 侧 2–3 文件，覆盖：三段趋势判定边界（含 N=3 退化、**N≡2 mod 3 分段 (f,c,c)**、N<3 error）、分类映射表（未分类占比披露）、ledger 按章对齐与墙钟、verdict exit code 三态、coverage 披露、**aggregate 回退解析 + coverage 标注**、**N_done > N_target 披露**）`uv run pytest -q` 全绿
- `just check` 全绿
