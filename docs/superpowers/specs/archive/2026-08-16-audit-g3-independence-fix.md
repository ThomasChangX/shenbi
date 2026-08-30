> **Date:** 2026-08-16 | **Status:** Done (PR #122) · Revised 2026-08-31（阶段 3 设计审查后重定基线：T1 已由 PR #8 承接移除；T2 dispute 路径与第二评分来源重设） | **Severity:** 🟠 P1 | **方法:** systematic-debugging 四阶段
> **系列:** 2026-08-15 全项目深度审计 · 阶段 5（簇 C5，6 条）| **代表 finding:** F114/F506（原代表 F794 已修）| **严重度上限:** P1 | **涉及文件面:** src/shenbi/scoring.py、orchestration/scoring_bridge.py、escalation_bridge.py、pipeline/chapter_loop.py、dispatcher/modes/codex.py、pipeline/dispatch_helper.py（run_gate_g3）

# G3 独立性与评分防坍缩接线（audit-g3-independence）

## 背景

AGENTS.md 的评分纪律（"Scoring MUST use an independent subagent (G3.4)；dispatcher-scored results are invalid"）配套的机制层部分空转：

- ~~F794/F320~~：**已由 PR #8 R1 承接修复**（dispatch_helper.py `run_gate_g3` 现 fail-closed，注释标 F408）——2026-08-31 阶段 1 复核确认。本 spec 不再重复实施，仅由 T5 护栏测试锁定防复发。
- **F114/F506（verified 2026-08-31 复核）**：反坍缩/双评分一致性机制（check_scorer_agreement、flag_score_collapse）仅经 `orchestration/scoring_bridge.py` 包装，而 scoring_bridge 在 orchestration/ 之外**生产零调用**（唯一外部引用是 chapter_loop.py/truth_io.py 的注释）；escalation_bridge 的文件包装层（parse_resonance_scores/run_escalation_check）同样零调用——check_escalation 本体已在 chapter_loop:1094-1127 被直接消费，死线仅指 bridge 包装层。
- **F113（残余面）**：_provenance.scored_by（scoring.py:506-507）以 `"--subagent" in sys.argv` 判定——subagent 路由已能正确标注（codex.py:125），但无该 flag 的人工批文件模式仍被标为 "interactive"，且 argv 嗅探脆弱。
- **F120**：flag_score_collapse（scoring.py:310-330）对单维 rubric、全零 kill-switch 合法结果误报坍缩——`all_identical` 信号无最小维度下限与全零豁免；`majority_at_single_value` 信号对全零多维结果同样误报。

## 修复目标

1. scoring_bridge 反坍缩链生产接线：独立评分（dispatcher/modes/codex.py:75-133）完成后 flag_score_collapse 真实执行并落记录；双评分一致性（validate_dual_scorer）经显式配置开关接线。
2. escalation_bridge 的文件包装层接线到其语义归属点（chapter_loop 既有 escalation 路径的共振分数收集）。
3. provenance 标注真实（file/interactive/subagent 三值，词表落 `src/shenbi/contracts/enums.py`）。
4. 坍缩检测无误报面（单维、全零豁免，覆盖两个信号）。

## 设计裁决（2026-08-31 修订）

- **评分分歧不走 escalation_bridge**（阶段 3 审查 C2）：`check_escalation` 的真实签名是共振趋势下滑检测（resonance_scores 跨轮斜率），与「双评分单轮维度分歧」语义不匹配，硬接等于伪造参数。分歧处置改为**仲裁记录**：分歧超阈 → 写 arbitration 记录进 gate/评分 manifest + structlog WARN，交人工复核（与 checkpoint 机制语义一致）。
- **双评分成本**（阶段 3 审查 C3/I7）：双评分 = 每轮多一次付费派发。开关**默认 OFF**（成本纪律优先；AGENTS.md 独立性契约的最低要求是「dispatcher 不得自评」，已由 subagent 路由满足；双评分是加强项）。开关落 pipeline config 既有模式（与 thresholds/genre-config 同层），字段 `dual_scorer: bool = false`。原 spec「默认开」与「仅 T1 晋级轮启用」的矛盾以「默认 OFF」收口。

## 任务分解

- **T1 · ~~G3 自足性修复~~**：已由 PR #8 承接（F408 fail-closed），删除原任务。防复发断言归 T5。
- **T2 · 反坍缩链接线（F114/F506）**：
  - **T2a 单评分坍缩检测（默认路径，零额外派发）**：codex.py 独立评分落地后（scores-subagent.json 解析处，~:99-106），调用 `scoring_bridge.check_single_scorer_collapse(scores)`；结果写入 t1-reports 旁的**独立产物** `*-collapse-check.json`（不得写入 scores-subagent.json 本体——非数值键会被 parse_scores_dict 以 non_numeric_score_keys_dropped 丢弃并每次 WARN）+ 疑似坍缩时 structlog WARN。确定性计算，无 token 成本。**T4（坍缩语义修正）必须先于或随 T2a 落地**——否则早期 collapse_check 记录建立在误报语义上。
  - **T2b 双评分一致性（opt-in）**：config `dual_scorer=true` 时，codex 派发点追加第二次独立评分派发（prompt 同源；`dispatch_codex` 增加评分文件名后缀参数使第二次输出落 `*-scores-subagent-2.json`，不覆盖首份），两份分数经 `scoring_bridge.validate_dual_scorer` 比对；`needs_arbitration=true` → 写 arbitration 记录（进 gate manifest，经 `_record_gate_manifest` 同层设施——T1 轮无 phase/chapter，manifest 键以 skill/test_type 维度自行定义并在实现中固化）+ WARN。测试一律 fixtures 驱动（G0.9 + 核心原则 8：禁止为验证触发真实 dispatch；受控 delta 须脚本化最小改动——仅一个维度数值）。
  - **T2c escalation_bridge 对账（2026-08-31 二轮审查修正前提）**：阶段 3 二轮实读确认 chapter_loop 既有 escalation 路径的共振分数收集走 `_get_recent_resonance_scores`/`_parse_resonance_score` 读 `audits/chapter-N-resonance.md`，**不读 resonance_trend.md**——原「改经 parse_resonance_scores」前提不成立。T2c 改为对账任务：核实 `resonance_trend.md` 在生产是否有真实读方；(a) 若有（或 T5 能以 fixtures 驱动其语义归属点）则接线 `run_escalation_check`（注意 parse_resonance_scores 丢弃 val≤0 的行为须与该读方语义兼容）；(b) 若无 → escalation_bridge 包装层判定冗余，记 deviation 移交 C37（#51 死代码簇）删除处置；deviation 记录须同时点名 chapter_loop.py:1448 docstring 的过期行号引用（_parse_resonance_score 实位于 :1389 非 :667）与「格式兼容 parse_resonance_scores」幻影消费者注释——真实格式消费者是 `skill_utils/drift_detection/compute_drift.py:246` 的 parse_trend。两结局都消灭「实现但零调用」态；**验收 2 的 escalation_bridge 分量按结局 (b) 自动豁免**。
- **T3 · provenance 真实化（F113 残余）**：scored_by 改三值 `file | interactive | subagent`，词表以 `ScoredBy = Literal[...]` 落 `src/shenbi/contracts/enums.py`（lint_status_strings 只管 status/state/classification 键，非状态字面量不适用；既有消费者 `src/shenbi/contracts/schemas/scores.py:24` 的 `scored_by: str = ""` 保持宽松 str、不强制收窄——避免破坏既有调用方）；判定机制弃 argv 嗅探，改显式：codex 派发路由传 `--subagent`（既有）、CLI 交互模式传 `--interactive`、缺省（批文件调用）= `file`。
- **T4 · 坍缩判定修正（F120）**：坍缩定义 = 多维（≥2 有效维度）且非全零下全同；两个信号（all_identical、majority_at_single_value）同受豁免——全零结果两信号均不触发，单维结果 all_identical 不触发（majority 信号已有 ≥3 下限）。
- **T5 · 护栏**：集成/单测断言——(a) 缺 progress.json 的 round → G3 FAIL 且目录内不出现新生成 progress.json（F794 防复发）；(b) T2a 坍缩检测结果出现在评分产物；(c) T2b 分歧用例产出 arbitration 记录、一致用例不产出（fixtures 驱动）；(d) 单维/全零 rubric 不报坍缩（F120）；(e) provenance 三值标注正确。

## 验收标准

1. 构造无 progress.json 的 round 目录跑 G3：marker 为 **FAIL**（现行实现形态，无 BLOCKED 变体）且目录内**不出现**新生成 progress.json（F794 断言——注：该能力已由 PR #8 落地，本 spec 以 T5 测试锁定）。
2. `git grep -n "scoring_bridge" src/shenbi -- ':!*/orchestration/*'` 出现**调用表达式**（非注释/import-only）≥ 1（scoring_bridge 的 T2a/T2b 接线；以 T5 集成测试的行为断言为准，grep 仅辅助）。escalation_bridge 分量条件于 T2c 结局：结局 (a) 接线则同样要求调用表达式 ≥1；结局 (b) deviation 移交 C37 则豁免。
3. 单测（fixtures 驱动）：双评分一致/分歧两用例分别产出无 arbitration / 有 arbitration 记录（F114 断言；fixture 约定：第二评分文件 = 真实 subagent 评分产物的精确副本 + 脚本化最小受控 delta（仅一个维度数值）——G0.9 下不手写整份 fixture）；单维、全零、多维非全零全同三用例的坍缩判定符合 T4 定义（F120 断言）。
4. `just check` 全绿。

## 风险与回滚

- 风险：T2b 引入双评分成本——默认 OFF 规避；启用者自负。T2c 若 chapter_loop 收集点与预期不符，按 deviation 降级为 C37 移交，不硬接。
- 回滚：T2a/T2b 独立提交可 revert；T2b 有开关天然可回退；T4 语义修正附 characterization 测试锁定旧行为中合法的部分。

## 簇成员清单（与 phase4-clustering.md §2 机械对照）

C5（6 条，原代表 F794 已修，现代表 F114/F506）：

F113（残余面）F114 F120 F320（已修）F506 F794（已修）
