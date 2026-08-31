> **Date:** 2026-08-16 | **Revised:** 2026-08-31（SDD #33 阶段 1 价值门：F376/F604 已被 PR #70/#14 承接，删除并收窄；T1440/T1441/T1442 复核存活）| **Status:** Design (Revised 2026-08-31) | **Severity:** 🟠 P1 | **方法:** systematic-debugging 四阶段
> **系列:** 2026-08-15 全项目深度审计 · 阶段 5（簇 C7，原 5 条，修订后 3 条）| **代表 finding:** T1442 | **严重度上限:** P1 | **涉及文件面:** src/shenbi/skill_utils/（compute_stats、compute_pattern、recall、calibration、review_resonance.routing、review_checklist）、pipeline/（chapter_loop、dispatch_helper、hook_planting、genesis、triggers）、skills/（shenbi-review-anti-ai、shenbi-chapter-drafting、shenbi-review-resonance、shenbi-foreshadowing-plant 等正文改引 helper 输出）、tools/lint_helper_usage.py（新增）

# 确定性 helper 派发接线（audit-deterministic-helper-wiring）· v2

## 背景

候选元根因 C（边界收窄版）：确定性统计/检查 helper 已实现但派发仍纯 prompt——LLM 每章手算机器已能算的量，并**复刻其 bug**。

**v2 修订记录（2026-08-31 价值门驳斥复核，agent 全量 + 协调者 file:line VERIFY）**：

- ~~F376/F604（baseline 生产者零调用死线）~~：**已修**——`establish_baseline` 生产调用已存在（chapter_loop.py:1964-1966，PR #70 spec #11 R1 引入，PR #124 spec #32 加固）；原验收条件 1/2 已在 main 满足。本 spec 删除该任务（原 T1）。
- T1440/T1441/T1442 复核存活（证据见各任务节）。

修订后核心 3 条：

- **T1440**：hook_planting 确定性替换是**不可达死代码**——`plant_hooks_from_plan` 唯一调用点 chapter_loop.py:2819 的分支条件 `step.skill == "shenbi-foreshadowing-plant"`，但该技能已弃用不在 CHAPTER_STEPS（:129 注释、:192 仅存合并体 shenbi-foreshadowing-lifecycle）；plant 三个活跃面（genesis.py GenesisStep(9)、triggers.py:297 卷边界 TriggerStep、skills/shenbi-foreshadowing-plant/SKILL.md 手动路由）仍全走 LLM dispatch。
- **T1441**：anti-ai 检查清单与 G4 确定性检查构成双重体系——10 项确定性检查只存在于 `skills/shenbi-review-anti-ai/checklist.md` prompt 资产，由 LLM 每章重算（`review_checklist.inject_checklist_into_prompt` 只注入词表/预算，不注入预计算计数）；同名检查阈值三面分裂：转折词密度 G4 `max(5, wc//1000)`（gates/g4/chapter_drafting.py:200）vs checklist.md:25 `max(1, floor(字数/3000))` vs anti-ai-reference.md:22 `每3000字≤1`。
- **T1442**：确定性统计 helper 五件套（compute_stats/compute_pattern/recall/calibration/review_resonance.routing）仍纯 prompt 级接线——src 生产代码零调用（仅 `__main__` CLI），dispatch_helper 无派发前预计算注入钩子，SKILL.md 正文要求 LLM 自行执行 `python -m shenbi.skill_utils...`（如 shenbi-review-resonance/SKILL.md:65-66）。

先例佐证：仓库已 16 次实现该模式但仅 ~5 个代码层接线（T14-07 母模式）；归档 spec #3（确定性技能替换审计）已给出提升判据（纯文件操作/键值 upsert/计数/固定模板填充/阈值比较），#14 已覆盖统计**正确性**、#11/#32 已覆盖 baseline 接线——本 spec v2 只管五件套/anti-ai/plant 的**接线与死面**。

## 修复目标

1. T14 候选表按优先级接线：T1403 anti-ai dim3 前置 + T1442 五件套派发前钩子注入。
2. 消除双重体系：anti-ai 同名检查 LLM 版删除或降级为"引用 helper 输出"，阈值口径对齐 G4 单值。
3. 清除 T1440 不可达死分支，plant 活跃面二选一裁决（确定性路由或删死码保留 LLM 面）。
4. 防复发：派发前钩子 lint——凡 helper 已覆盖的统计类输出，SKILL.md 正文必须引用 helper 结果而非要求 LLM 重算。

## 任务分解

- **T1 · 五件套程序强制（T1442）**：dispatch_helper 派发前钩子——对声明了对应 helper 的技能，注入 helper 预计算结果并从 prompt 中删除"请计算"指令；compute_stats/compute_pattern/recall/calibration/review_resonance.routing 逐个接线。修复形状：钩子层做（一处改动覆盖全部技能），带 per-skill 开关可回退纯 prompt 路径。
- **T2 · hook_planting 死分支裁决（T1440）**：二选一——(a) 三个 plant 活跃面（genesis step 9 / triggers 卷边界）路由到 `plant_hooks_from_plan` 确定性实现；(b) 删除不可达分支与死实现、保留 LLM 面。裁决记录进 spec-deviations。倾向 (b)：plant 输出依赖 plan 语义扩展（expand 模式），确定性实现仅覆盖固定场景，路由会缩小能力面。
- **T3 · anti-ai 双重体系收敛（T1441/T1403）**：dim3 的 10 项确定性检查中可程序化项（转折词计数、AI 标记词计数、CV 等）派发前算好注入 prompt；LLM 清单只保留非确定性项；转折词阈值三面收敛到 G4 口径 `max(5, wc//1000)` 单值（checklist.md 与 anti-ai-reference.md 改引该口径；thresholds.py 全局单源归 spec #35/C9，本处不越界）。
- **T4 · lint 防复发**：`tools/lint_helper_usage.py`——SKILL.md 中"计算/统计/计数"类指令若命中 helper 能力清单则 WARN，要求改引 helper 输出；接入 just check。
- **T5 · 后续候选（T1404-T1419）**：P2 候选（T1404-T1409）按 T14 评估表在上述完成后排期，本 spec 不展开；P3 候选归批量清理储备。

## 批量清理（纯 M 成员）

本簇无 M 级成员（T1440-T1442 为 P2，T1403 为 P1 联动）。

## 验收标准

1. （原 1/2 已由 PR #70/#124 在 main 满足，v2 移除）派发 prompt 快照断言：style-learning/chapter-pattern/review-resonance 类派发的 prompt 含 helper 预计算结果块、不含"请计算"指令（T1442 断言，fixtures 驱动测试表达，禁现场 dispatch）。
2. T1440 裁决落地：选 (a) 则 genesis/triggers plant 面走 `plant_hooks_from_plan`（grep 生产调用点）；选 (b) 则 chapter_loop.py:2819 死分支与 hook_planting 死面删除（`git grep plant_hooks_from_plan src/` 零残留或仅保留活跃调用）。
3. anti-ai 派发 prompt 含确定性检查预计算块（计数/CV），checklist.md/anti-ai-reference.md 转折词阈值与 G4 一致（同值断言测试）。
4. `uv run python tools/lint_helper_usage.py` exit 0（或输出仅剩已裁决豁免项）。
5. `just check` 全绿。

## 风险与回滚

- 风险：派发前钩子增加每派发延迟；预计算注入扩大 prompt 体积——与 C28（冗余注入）联动监控 token 面。helper 结果注入后 LLM 可能"照抄"错误值——统计正确性由 #14 的度量修复保障，本 spec 只保证接线。
- 回滚：钩子层带 per-skill 开关，可单技能回退纯 prompt 路径；T2 选 (b) 时删除为纯减法。

## 簇成员清单（与 phase4-clustering.md §2 机械对照，v2 修订）

C7（原 5 条，v2 存活 3 条）：

- FIXED：F376 F604（PR #70 4263df55 + PR #14/#124 承接）
- LIVE：T1440 T1441 T1442
