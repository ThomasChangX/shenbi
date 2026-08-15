# Z6 分区独立复核报告 r1（fresh-context）

- 轮次: 2026-08-15 全项目深度审查 · Z6 区独立复核（与初审无关的 fresh-context 全量重读）
- 被复核报告: docs/superpowers/audit-runs/2026-08-15/zone-reports/Z6.md（初审 F601-F628）
- 清单: docs/superpowers/audit-runs/2026-08-15/zones/Z6.files（49 文件全部重读，无缺漏）
- 本轮角度: (a) docstring/注释声称的行为与消费方 vs 实际接线（声称的调用方存在性 + 引用断链）；(b) trace/records 的写入计数 vs 读取计数对账（写而不读 / 读而不写的键与文件）
- findings 编号段: F629-F699（实际使用 F629-F642，共 14 条：P0×1，P1×2，P2×8，M×3）
- 只读禁令遵守: 除本文件外未创建/修改/删除任何仓库文件；未运行 pytest/shenbi-dispatch/pipeline；动态验证均在 /tmp 临时目录

## 汇总

| 类别 | 数量 | 编号 |
|---|---|---|
| 漏报 | 14 | F629-F642（P0×1: F630；P1×2: F629, F637；P2×8: F631-F636, F638, F639；M×3: F640-F642） |
| 误报 | 2 项更正 | F616 数字错误；cjk 条目消费方表述不精确（另 1 项escalation表述归入 F635） |
| 覆盖空洞 | 3 项 | trace/ 目录 vs trace.jsonl 路径接缝；trace actions 写读集合对账缺失；audit/record.py 第三写入方 |
| 严重度异议 | 2 项 | F601 P1→P2 建议；初审 update_genre_config "可接受" 判断 → F636 P2 |

核心结论：**初审对本区模块的"内部正确性"审计质量很高（28 条 findings 中我抽查的 12 条全部独立复核成立），但完全遗漏了"外部接线对账"维度**——本轮角度 (b) 的写读三方对账发现：materialize 消费的 INIT/MARK_DONE 事件全仓库零写入方、materialize 周期性整体重建会覆盖 dispatcher 与 G3 写入的 progress.json 键（P0）、compact/migrate_from_progress/第 4 触发器/content-looping 检测全部零接线、escalation 六触发器中两个生产不可达、治理入口 update_genre_config 零接线但 docstring 声称"Every change flows through"。

---

## 一、漏报（F629-F642）

### F630 | materialize_progress 周期性整体重建 progress.json，静默覆盖 dispatcher 与 G3 写入的键（记录覆盖）| 接线/数据丢失 | P0
- 证据: src/shenbi/trace/materialize.py:80-93（`out` 全新构造，schema 仅含 round/tier/test_cycle_phase/subagent_completion_count/completed_skill_names/skills/remaining_*/gate_blockers/total_framework_skills/expected_chapters，经 safe_write 整体替换）+ src/shenbi/pipeline/chapter_loop.py:3065（每个成功步骤后调用 `_maybe_materialize_progress`，`steps_done % 5 == 0` 触发，即约每章一次）+ src/shenbi/pipeline/dispatch_helper.py:1978-1990（G3 仅在 progress.json **不存在**时创建 `current_scorer_agent`/`scoring_history`）+ src/shenbi/dispatcher/modes/codex.py:19-50（`_record_completion` 把 `completed_skill_names`/`skills` 合并写入同一 `round_dir/progress.json`；dispatch_helper.py:1902 显示 chapter 流水线 round_dir 缺省即 project_dir，与 materialize 的 `state.project_dir` 同一文件）
- 根因: materialize 是"从 trace 派生 progress.json"的重建器，但 (i) 它无条件整体替换文件而非合并；(ii) 它的派生源（INIT/MARK_DONE 事件）在生产中从未被写入（见 F629），因此重建结果是全 pending 空视图；(iii) `_maybe_materialize_progress` 以 `except Exception: pass` 吞掉一切失败（chapter_loop.py:699）。三因叠加：每 5 步一次，progress.json 被"重置"——codex dispatcher 累积的完成记录被清空；G3 独立性证据键（`current_scorer_agent`/`scoring_history`/`agent_trace`）被抹除且**不会自愈**（run_gate_g3 只在文件不存在时写这些键）；随后 g3_independence.py:20-22 fail-closed 读到缺失 scorer → "no independent scorer recorded" FAIL。AGENTS.md 显式要求"Scoring MUST use an independent subagent (G3.4)"，该契约的生产证据链被本机制周期性摧毁。
- 验证（已运行）: `grep -rn "MARK_DONE" --include="*.py" src/` → 仅 chapter_loop 注释与 materialize 读取分支，零写入方；`grep -rn "trace_action=" src/` → 生产唯一传值 materialize.py:98 `"MATERIALIZE"`；`grep -rn "current_scorer_agent|agent_trace|scoring_history" src/` → 唯一写入点 dispatch_helper.py:1984-1985 且仅文件缺失时；读方 g3_independence.py:20-23、g1.py:263、g3.py:213-222、g_dispatch.py:45、g_transition.py:48。
- 建议方向: materialize 改为合并写（保留未知键）或把 G3/dispatcher 记录改为 trace 事件（补 MARK_DONE/SCORER_ASSIGN 写入方）后再整体重建；`except Exception: pass` 至少记 log.warning。

### F629 | trace 事件对账：INIT/MARK_DONE 读而不写——materialize 的派生源在生产恒为空 | 接线/读而不写 | P1
- 证据: src/shenbi/trace/materialize.py:49,53（replay 后仅识别 `INIT`/`MARK_DONE` 两类 action）vs 全仓库 grep：生产 TraceWriter 追加的 action 仅三种——`MATERIALIZE`（materialize.py:98）、`GATE_FAIL`/`AUDIT_PASS`（audit/record.py:44-46）、`LEGACY_MIGRATION`（migrate.py:33，且该函数本身零调用，见 F632）。INIT/MARK_DONE 只在 tests/unit/trace/test_materialize.py、test_event.py 中手工构造。
- 根因: "progress.json 降级为 trace 派生视图"（materialize docstring、chapter_loop.py:689 注释 "even though trace events record every MARK_DONE"）的写侧从未落地——事件生产者缺失，派生机制空转。chapter_loop.py:689 的注释本身即是"声称与接线不符"（角度 a）的实例。
- 验证（已运行）: `grep -rn "MARK_DONE" --include="*.py" --include="*.md" .`（排除 docs/superpowers）→ 仅上述四文件；`grep -rn "action=\"INIT\"\|'INIT'" src/` → 仅 materialize.py:49 读取分支。
- 建议方向: 在 dispatch 成功与 cmd_init 处补 `TraceWriter.append(action="MARK_DONE"/"INIT", ...)`；或删减 materialize 的事件消费设计。与 F630 合并修复。

### F637 | Rule 1 临界维度禁用可被非-False 假值绕过（0 / "false" / None）| 契约绕过 | P1
- 证据: src/shenbi/config/config_coherence.py:109（`if key.startswith("auditDimensions.") and new_value is False:` 用身份判定 `is False`）——与初审 F603（Rule 2 的 `isinstance(new_value, int)` float 绕过）同根但不同规则，初审未报。
- 根因: `0`、字符串 `"false"`、`None` 均不是 `False` 身份值 → Rule 1 完全跳过 → texture/antiAi/continuity 三个 critical 维度无需 50 字 rationale 即被"禁用值"写入 genre-config.json；消费方 audit_layer.py:100-105 直接读该 sub-dict 做真值判断，假值等价于禁用。spec §3.4 的安全网门槛（AGENTS.md 治理契约）被绕过。
- 验证（已运行，/tmp 临时目录）: `update_genre_config(d, {'auditDimensions.texture': 0}, rationale='short')` → 接受落盘 texture=0；`{'auditDimensions.texture': 'false'}` → 接受落盘 texture="false"（输出见下）。
  ```
  Rule1 bypass texture=0 written: 0
  Rule1 bypass texture=str: false
  ```
- 建议方向: Rule 1 改为假值判定 `if ... and not new_value:`（或显式枚举 falsy 类型并校验类型），与 F603 的类型归一修复合并。

### F631 | compact() 全仓库零生产调用方——compaction 机制死线 | 接线/未接线 | P2
- 证据: `grep -rn "compact(" --include="*.py" src/ tests/` → 仅 tests/unit/trace/test_compaction.py:5,14,24,30 调用；src 内零调用（trace/__init__.py 仅 re-export）。初审详尽验证了双 compaction 链正确性（其 /tmp 实验），却未发现该函数无生产入口。
- 根因: 长流水线 trace.jsonl 只增不减；g7_trace.py:51 的 `verify_chain` compaction 链校验在生产恒见零 COMPACTION 事件（空转校验）。spec（判据 7 I6b/N4/New-G）承诺的截断-快照机制未接线。
- 验证（已运行）: 上述 grep（本轮实际执行，注意初审验证段未包含此对账）。
- 建议方向: 在章末/卷末钩子接线 compact（配合 F629/F630 的重放语义测试），或文档化弃用。

### F632 | migrate_from_progress() 零生产调用方——LEGACY 锚机制死线 | 接线/未接线 | P2
- 证据: `grep -rn "migrate_from_progress" src/ tests/ pyproject.toml justfile` → 仅 trace/__init__.py re-export + tests/unit/trace/test_migrate.py。
- 根因: "从现有 progress.json 反推 LEGACY_MIGRATION 事件作合法链首锚"（docstring:1-4）的 bootstrap 无入口；存量项目迁移路径不存在。G7 对无 LEGACY 锚容忍（g7_trace.py:35-37 缺文件 PASS），故静默不报错。
- 验证（已运行）: 上述 grep。
- 建议方向: 在 pipeline resume/legacy 入口接线，或弃用删除。

### F633 | check_linguistic_drift_trigger（drift-guidance 第 4 触发器）零调用方——连测试都没有 | 接线/未接线 | P2
- 证据: `grep -rn "check_linguistic_drift_trigger" src/ tests/` → 仅 compute_drift.py:150 定义 + drift_detection/__init__.py re-export。
- 根因: docstring 声称 "4th trigger: linguistic alarm metrics exceed thresholds ... Fires on HARD/ESCALATE linguistic drift only"（compute_drift.py:151-155），是 spec §8.3 与语言学漂移（独立于被污染的 resonance 评分）之间的桥接判据；但 main()（同文件 236-286）不调用它，生产也无调用。初审只把它记为"覆盖缺口 156-158 must-test"，未识别为彻底未接线。
- 验证（已运行）: 上述 grep。
- 建议方向: 在 drift CLI/章循环把 `_check_linguistic_drift` 的 DriftResult 喂给该触发器，或删除。

### F634 | check_window_redundancy / frequency_divergence_alarms 零生产调用 | 接线/未接线 | P2
- 证据: `grep -rn "check_window_redundancy|frequency_divergence_alarms" src/` → 零生产调用（仅 tests/unit/skill_utils/drift_detection/test_linguistic_drift.py）；chapter_loop.py:2030 只 import 了 check_opening_similarity（同文件三兄弟之一）。
- 根因: check_window_redundancy docstring 承诺 "Threshold: >0.35 flags content looping"（linguistic_drift.py:256-259）——内容循环（复读）检测安全网未接线；frequency_divergence_alarms 的二阶告警同样仅测试消费。
- 验证（已运行）: 上述 grep。
- 建议方向: 在 `_check_linguistic_drift`（chapter_loop.py:2022-2088，已接线但只用了 opening_similarity）补窗口冗余检测接线，或弃用。

### F635 | check_escalation 六触发器中 arc_score/stratum_axis_drift 两个生产不可达 | 接线/未接线 | P2
- 证据: src/shenbi/skill_utils/escalation/check.py:104-118（两触发器实现）vs 唯一生产调用方 src/shenbi/pipeline/chapter_loop.py:1029-1034（只传 resonance_scores/sensitivity_blocking/volume_objective_met/regeneration_attempts 四参，arc_score 缺省 None、stratum_axis_drift 缺省 False → 恒不触发）；会传这两参的 run_escalation_check（src/shenbi/orchestration/escalation_bridge.py:26-47）自身零生产消费（`grep -rn "from shenbi.orchestration" src/` → 零命中，仅 tests/orchestration/test_bridges.py）。
- 根因: docstring/注释声称 "All triggers" 按 spec §6.2 生效（check.py:4-7），实际 2/6 死线。初审 escalation 条目写"生产消费方 chapter_loop.py:80,1029 按真实签名调用…无漂移"——签名一致但参数缺席，结论掩盖了触发器不可达。
- 验证（已运行）: `grep -rn "check_escalation(" src/` → chapter_loop.py:1029（4 参）+ escalation_bridge.py:38（全参）+ check.py CLI；bridge 消费 grep 零生产命中。
- 建议方向: chapter_loop 调用点补 arc_score（卷弧分）/stratum_axis_drift 数据源，或接通 escalation_bridge。

### F636 | update_genre_config 零生产接线，与 docstring "Every change flows through" 声称不符 | 声称vs接线/治理死线 | P2
- 证据: src/shenbi/config/config_coherence.py:5-6（"Every change to genre-config.json (or the in-state resonance floor) flows through update_genre_config"）vs `grep -rn "update_genre_config" src/` → 零生产调用（仅 tests/unit/config/test_config_coherence.py）；skills/ 与 justfile 无引用（config-change-log 在 skills/docs 仅见于归档 plan 与 z11 spec 的 F1316 引述）。
- 根因: 治理契约（50 字 rationale、floor≥60、审计轨迹）完全没有强制入口——任何 agent/人直接编辑 genre-config.json 均不经过治理。初审在 config_coherence 条目写"生产无调用方，治理工具为人工/技能入口，可接受"，但既无 skill 入口引用也无 CLI 入口，"可接受"判定缺乏依据（此为严重度异议+漏报双重性质，按 P2 落 finding）。
- 验证（已运行）: 上述 grep（本轮实际执行）。
- 建议方向: 在 shenbi-genre-config skill 指令中强制经此入口，或降低 docstring 声称。

### F638 | recall.py docstring 引用断链：RAG 层 benchmarks/index/ 不存在 | 引用断链 | P2
- 证据: src/shenbi/skill_utils/foreshadowing_recall/recall.py:4-5（"The RAG layer (benchmarks/index/) retrieves candidate hooks by semantic similarity; this function applies the deterministic max_distance threshold"）vs `ls benchmarks/index` → "No such file or directory"（benchmarks/ 仅含 anchors/）。
- 根因: 模块的存在理由（包裹 RAG 召回层的最终确定性过滤）指向不存在的层——docstring 声称的集成方与消费链整体断链（角度 a 典型样本）；配合初审 F622（CLI 无引用、库函数仅测试消费），整个模块的"生产叙事"无一处成立。
- 验证（已运行）: `ls benchmarks/index` → No such file or directory；`ls benchmarks` → anchors。
- 建议方向: 修正 docstring 为"为未来 RAG 层预留的确定性过滤测试件"，或补齐被引用方。

### F639 | gate_blockers 恒为 []：GT.3 检查空转 | 写而不读/空转 | P2
- 证据: src/shenbi/trace/materialize.py:90（恒写 `"gate_blockers": []`，且为该键全仓库唯一写入点）+ src/shenbi/gates/g_transition.py:69-70（GT.3 读 `progress.get("gate_blockers", [])` 判空）+ src/shenbi/gates/g7.py:113（G7.8 "gate_blockers check not yet implemented"）。全仓库无非空写入方。
- 根因: 写读对账：读方期望的门禁阻塞列表永不为非空 → GT.3 是永真检查（vacuous pass），门禁失败状态在 progress 视图中不可表达——安全网检查形同虚设。
- 验证（已运行）: `grep -rn "gate_blockers" --include="*.py" src/` → 上述三处 + 无其他写入。
- 建议方向: gate FAIL 时写入 gate_blockers（或由 trace GATE_FAIL 事件派生），否则删除 GT.3。
- 附注: 该键又会被 F630 的周期重建反复重置为 []，两 finding 同向叠加。

### F640 | progress.json 的 test_cycle_phase / subagent_completion_count 写而不读 | 写而不读 | M
- 证据: materialize.py:83-84 写入；`grep -rn "test_cycle_phase|subagent_completion_count" src/ tests/ skills/` → 除 materialize 自身外零读取（含 skills/）。
- 根因: 派生视图中两个键无任何消费方；test_cycle_phase 还被硬编码 "generative"（无论真实阶段）。F624（subagent_completion_count 双计数）的语义缺陷因零读方而无实际影响——亦构成对 F624 严重度维持 M 的支撑。
- 验证（已运行）: 上述 grep。
- 建议方向: 删除或接线消费方（如 g_transition 的阶段判定）。

### F641 | serialize_records / is_idempotent 零生产消费 | 未接线 | M
- 证据: `grep -rn "serialize_records|is_idempotent" src/` → 仅 records/__init__.py re-export；生产消费只有 parse_records（write_audit.py:16,54、snapshot.py:16,110）与 drift 两函数（write_audit.py:15,55-56）。
- 根因: parser 包 docstring 声称"本包解析、序列化、检测 cross-section drift"（records/__init__.py:1-2），序列化半边（写侧）与 round-trip 判据无生产接线——记录当前由 LLM/skill 直接编辑 markdown，无经 serialize_records 的规范化写路径，判据 12 的 round-trip 只有测试侧保障。
- 验证（已运行）: 上述 grep。
- 建议方向: 记录写路径（如 write_audit 修复建议）经 serialize_records 规范落盘，或降低 docstring 声称。

### F642 | text 模块半数导出零生产消费：count_words / tokenize / count_punctuation / PUNCTUATION_TOKENS | 未接线 | M
- 证据: `grep -rn "find_terms|count_words|count_punctuation|tokenize|PUNCTUATION_TOKENS" src/`（排除 text/ 自身）→ 生产仅 find_terms 两处（gates/g6.py:421、pipeline/truth_index.py:325-326）；其余四项零生产消费（tests/unit/text/test_cjk.py 测试消费）。
- 根因: F601 的 P1 定级依据"count_punctuation 是本模块对外的规范标点计数器，正常路径功能性错误"——但该函数无生产调用方（F609 建议的"改用 shenbi.text.count_punctuation"尚未发生），"正常路径"不成立（见严重度异议 1）。
- 验证（已运行）: 上述 grep。
- 建议方向: F609 修复时把 style_learning 切到本模块实现即同时接线；tokenize 维持骨架文档化。

---

## 二、误报（对初审结论的更正）

### M-误报-1 | F616 摘要"8 个兄弟 CLI 均用 sys.stdout.write"计数错误
- 证据: `grep -rln "sys.stdout.write" src/shenbi/skill_utils/` → 7 个文件（calibration/confidence.py、chapter_pattern/compute_pattern.py、drift_detection/compute_drift.py、review_resonance/routing.py、revision_routing/__main__.py、style_learning/compute_stats.py、trope_detection/match_tropes.py）；摘要说 8、正文说"六个"（列举 6 个遗漏 revision_routing/__main__），两个数字均不正确（实为 7）。print 方 2 个（escalation/check.py:149、foreshadowing_recall/recall.py:61）确认无误。
- 裁决维持: print=CLI 产品输出的边界裁决本身正确，仅数字更正（M 级）。

### M-误报-2 | 初审 cjk.py 条目"生产消费方 truth_index.py:325-326 与 g6.py:421 按签名调用一致"表述不精确
- 证据: 该两处调用的是 find_terms；count_words 在 src/ 零生产消费方（见 F642）。初审把 count_words 一并计入"生产消费方"不成立。对 F601/F615 的核心事实（引号恒 0、jieba 全局污染）无影响，两 finding 本身维持。

### 经复核确认不构成误报（初审正确，我实测/重验）
- 初审 config_coherence 附注"_set_nested 遇非 dict 中间节点抛裸 TypeError"——我实测 `str` 中间节点确实抛 `TypeError: 'str' object does not support item assignment`（末步赋值触发，非我最初猜测的 setdefault AttributeError）。初审正确。
- F601（引号计数恒 0）、F602（dialogue 崩塌永不触发）、F603（float 55.0 绕过落盘）、F608（torn-tail `_last_sig_existing` 抛 `json.decoder.JSONDecodeError: Unterminated string`）、F612（preserve_check 无 CLI 入口）、F614（round 字段逻辑）、F616 裁决、F622（两 CLI 零 skill 引用，grep 复验为零）、F626（理论死循环）、F628（`Path("truth/audit_drift.md")` CWD 相对；补充：读方 triggers.py:75 同为相对常量 `AUDIT_DRIFT_PATH = "truth/audit_drift.md"`，写读共享 CWD 假设，M 定级恰当）——全部独立复核成立。
- trace 签名链健康结论复核成立：我重跑 sign→dump→reload→verify 双事件链 → `roundtrip signature stable: True`。

---

## 三、覆盖空洞

### 空洞-1 | `_auto_rebuild_progress_if_stale` 的 trace/ 目录 vs trace.jsonl 文件路径接缝（跨区，无人覆盖）
- 证据: src/shenbi/pipeline/chapter_loop.py:713-718（`trace_dir = project_dir / "trace"`，glob `*.jsonl`）vs src/shenbi/trace/writer.py:18,42（TraceWriter 写 `<round_dir>/trace.jsonl` 平面文件）；全仓库无任何代码创建 `trace/` 目录（`grep -rn '"trace"' src/` 仅 chapter_loop 此处）。
- 后果: cmd_resume（cli.py:793 引用 Task 12）的"trace 比 progress 新则重建"自愈逻辑恒不触发（目录不存在 → 提前 return）。即便触发电只会落入 F630 的重建陷阱。chapter_loop.py 不在 Z6 清单，其所属区报告若有覆盖亦未见此接缝——按本轮角度 (b) 属于 trace 布局契约（Z6）与消费者（他区）的断链，任何单区内部审计都发现不了，属结构性覆盖空洞。

### 空洞-2 | trace actions 写读集合对账缺失
- 初审对 trace 区的验证全部是"内部一致性"（签名链、双 compaction、接续 seq）与"gates 消费"（G7 调 verify_chain/assert_monotonic），未做过"哪些 action 被写、哪些被读"的集合对账。本轮对账结果（角度 b 落表）：

| trace action | 生产写入方 | 数据读方 | 结论 |
|---|---|---|---|
| MATERIALIZE | materialize.py:98 | 无（仅链校验） | 写而不读（数据层） |
| GATE_FAIL / AUDIT_PASS | audit/record.py:44-46 | 无（仅链校验；payload 不消费） | 写而不读（数据层） |
| LEGACY_MIGRATION | migrate.py:33（零调用） | migrate.py:20-22（幂等检查，零调用） | 双死线 |
| INIT / MARK_DONE | **无** | materialize.py:49,53 | **读而不写**（F629/F630 根因） |

### 空洞-3 | audit/record.py 作为第三类 trace 写入方未被初审对账
- 证据: src/shenbi/audit/record.py:42-46（write-audit 结果以 GATE_FAIL/AUDIT_PASS 事件入链）。其 payload（violations/drift/checked_files）无任何读取方（materialize 忽略之；G7 只做链校验）。属可接受的审计目的写入，但初审在 writer.py 条目声称"生产 TraceWriter 追加经 safe_write"视角只覆盖了 safe_write 一条缝，漏了 record.py 这条直接 TraceWriter 缝（F608 的"直接构造方（如 migrate）"举例也漏了 record.py 这个实际高频写入方）。

---

## 四、严重度异议

### 异议-1 | F601（引号计数恒 0）P1 → 建议 P2
- 依据: 严重度表 P1 要求"正常路径可复现功能错误"。count_punctuation 经 grep 零生产消费方（F642 证据），F601 描述的"正常路径"当前不存在；其影响域是导出 API 的正确性与 F609 修复的规范性（应切到本实现）。按证据驱动应降 P2；若按"不确定取更高"保留 P1 亦可辩护（API 是 spec 支柱 3 的规范入口）。提请聚合方裁决，倾向 P2。
- 关联: F602/F604 的 P1 定级不受影响——detect_drift/_check_linguistic_drift 有真实生产接线（chapter_loop.py:2050,2759），"正常路径"成立，F604 我方复验补充了更强证据（writer 唯一且零调用，reader 接线真实），维持 P1。

### 异议-2 | 初审对 update_genre_config "生产无调用方…可接受"的判断 → P2（已落 F636）
- 依据: docstring 的"Every change flows through"是 spec §3.4 治理契约的声称（角度 a），"人工/技能入口"辩护需要至少一个 skill/CLI 引用存在——grep 为零。与 F604 同构（docstring 声称接线点、全仓无调用），F604 初审判 P1，此处初审连 finding 都未立，标准不一致。

### 无异议确认
- F603 P1 维持（并扩展为 F637 的 Rule 1 姐妹绕过，同 P1）；F616 裁决维持、数字更正；F605-F615、F617-F628 的定级经复核未见偏移。

---

## 五、本轮角度发现摘要（引用断链重扫 + 计数三方对账）

1. **对账法有效性**: 以"生产 TraceWriter/safe_write(trace_action=) 写入了什么 action"与"replay/materialize/G7 读了什么 action"做集合差，一举暴露 F629/F630/F631/F632 四条接线缺陷——初审的逐文件深读法对这类跨文件缝隙结构性失明。
2. **docstring 声称 vs 接线的断链清单（角度 a 全量）**: baseline.py:8-9（wire-in point 无接线，初审已报 F604）、chapter_loop.py:689 注释（"trace events record every MARK_DONE"为假）、compute_drift.py:151（第 4 触发器）、check.py:4-7（"All triggers"）、linguistic_drift.py:256（content looping 阈值）、config_coherence.py:5-6（"Every change flows through"）、recall.py:4-5（benchmarks/index/ 断链）、records/__init__.py:2（序列化半边无接线）、escalation_bridge（"Bridge: parse resonance_trend.md -> check_escalation" 零消费）。
3. **写而不读终表**: config-change-log.jsonl（无读方，M 级注记——审计轨迹或为人工终读，但无 skill/CLI 声明）；truth/audit_drift.md 写读成对（CLI 写 + triggers/context_assemble 读，仅共享 CWD 假设）；progress.json 的 gate_blockers（恒 []，F639）、test_cycle_phase、subagent_completion_count（F640）。
4. **建议聚合方动作**: F630+F629 应作为本轮最高优先修复项（一个 PR 内同时补 MARK_DONE/INIT 写入方与 materialize 合并写），并回填 `just pipeline-status` 对 progress.json 的展示验证。

## 复核统计

- 重读清单文件: 49/49
- 独立动态验证: 12 组（F601/F602/F603/F607-类 Rule1 绕过/_set_nested 异常类型/trace round-trip/torn-tail/`ls benchmarks`/多组全仓 grep 对账；动态实验均在 /tmp，未触仓库）
- 未运行（禁令）: pytest、shenbi-validate/score/dispatch/pipeline、plugins 生成器
- 置信度: F630/F629/F637/F639 high（全链 grep + 实测）；F631-F636/F638/F640-F642 high（grep 零命中即结论）；F601 降级建议 medium（定级裁量）
