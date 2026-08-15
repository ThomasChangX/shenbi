> **Date:** 2026-08-16 | **Status:** Design | **Severity:** 🟠 P1 | **方法:** systematic-debugging 四阶段
> **系列:** 2026-08-15 全项目深度审计 · 阶段 5（簇 C5，6 条）| **代表 finding:** F794 | **严重度上限:** P1（F794）| **涉及文件面:** src/shenbi/scoring.py、orchestration/scoring_bridge.py、escalation_bridge.py、gates/g3*、pipeline/dispatch_helper.py（run_gate_g3）、phase_runner 接线

# G3 独立性与评分防坍缩接线（audit-g3-independence）

## 背景

AGENTS.md 的评分纪律（"Scoring MUST use an independent subagent (G3.4)；dispatcher-scored results are invalid"）配套的机制层全部空转——机制已写但零消费者，且 G3 自身可被自我满足：

- **F794（簇代表，verified）**：run_gate_g3 在缺 progress.json 时**自造** progress.json（真实盘 uuid4-hex12 模板铁证，协调者核验）使 G3 通过；G3.3 output_files 无写入者——生产 G3 三项实质检查全空转。F320 同族：缺 progress.json 时伪造 scorer 身份使 G3 可通过（gate 完整性洞，security 面）。
- **F114**：反坍缩/双评分一致性机制（check_scorer_agreement、flag_score_collapse）仅经 scoring_bridge 包装，而 scoring_bridge 无任何消费者——spec §5.5 补丁 2/3 未接线；F506：scoring_bridge + escalation_bridge 两 bridge 生产零调用（dead-wire）。
- **F113**：_provenance.scored_by 把文件模式（非交互）标为 "interactive"，审计来源标注失真。
- **F120**：flag_score_collapse 对单维/全零（合法 kill-switch 结果）也报 all_identical 坍缩（误报）。

## 修复目标

1. run_gate_g3 不再自造输入：缺 progress.json 时 G3 FAIL（fail-closed），不得自建模板。
2. scoring_bridge 反坍缩链生产接线：独立评分派发后 check_scorer_agreement/flag_score_collapse 真实执行，结果进 gate marker。
3. provenance 标注真实（文件模式 ≠ interactive）；坍缩检测无误报面。

## 任务分解

- **T1 · G3 自足性修复（F794/F320）**：删除 run_gate_g3 的 progress.json 自造分支（dispatch_helper.py:1977-1990 一带），缺输入 → 结构化 BLOCKED/FAIL + 指明缺失文件；伪造 scorer 身份路径同步删除。
- **T2 · 反坍缩链接线（F114/F506）**：scoring_bridge 接入生产评分流（独立 subagent 评分完成后调用 check_scorer_agreement + flag_score_collapse，分歧超阈走 escalation_bridge）；escalation_bridge 的消费者面一并接线（与 C37 死代码簇边界：本 spec 只接 bridge，bridge 内部缺陷归 C37/C13）。
- **T3 · provenance 真实化（F113）**：scored_by 按真实调用模式标注（file/interactive/subagent 三值，词表归 C8 单源）。
- **T4 · 坍缩判定修正（F120）**：flag_score_collapse 对单维 rubric 与全零 kill-switch 合法结果豁免（坍缩定义 = 多维且非全零下全同）。
- **T5 · 护栏**：集成测试断言"缺 progress.json 的 round → G3 FAIL"（防自造复发）与"双评分分歧 → escalation 记录"（防 bridge 再脱线）。

## 批量清理（纯 M 成员）

- F120（坍缩误报）已列为 T4 正式任务（虽为 M，但属接线语义核心，不并入批量）。

## 验收标准

1. 构造无 progress.json 的 round 目录跑 G3：marker 为 FAIL/BLOCKED 且目录内**不出现**新生成 progress.json（F794 断言）。
2. `git grep -n "scoring_bridge\|escalation_bridge" src/shenbi -- ':!*/orchestration/*'` 出现生产调用点 ≥ 1（F506 断言：bridge 不再零消费者）。
3. 单测：双评分一致/分歧两用例分别产出正常通过/escalation 记录（F114 断言）；单维全零 rubric 不报坍缩（F120 断言）。
4. `just check` 全绿。

## 风险与回滚

- 风险：T1 收紧后，此前靠自造 progress.json "通过" 的轮次将显性 FAIL——需先跑一轮存量 round 盘点影响面；T2 接线引入双评分成本（每轮多一次评分派发），按 AGENTS.md 独立性契约这是必要成本，但可配置为仅 T1 晋级轮启用。
- 回滚：T1 删除分支独立提交可 revert；T2 桥接层带开关（默认开，紧急可关回旧路径）。

## 簇成员清单（与 phase4-clustering.md §2 机械对照）

C5（6 条，代表 F794）：

F113 F114 F120 F320 F506 F794
