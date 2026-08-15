> **Date:** 2026-08-16 | **Status:** Design | **Severity:** 🟠 P1 | **方法:** systematic-debugging 四阶段
> **系列:** 2026-08-15 全项目深度审计 · 阶段 5（簇 C7，5 条）| **代表 finding:** F376 | **严重度上限:** P1（F376/F604，阶段 4 提案升 P1）| **涉及文件面:** src/shenbi/skill_utils/（drift_detection/baseline.py、compute_stats、compute_pattern、recall、calibration、review_resonance、hook_planting）、pipeline/（chapter_loop、dispatch_helper 派发前钩子）、相关技能 SKILL.md 正文改引 helper 输出

# 确定性 helper 派发接线（audit-deterministic-helper-wiring）

## 背景

候选元根因 C（边界收窄版）：确定性统计/检查 helper 已实现但派发仍纯 prompt——LLM 每章手算机器已能算的量，并**复刻其 bug**。核心 5 条：

- **F376/F604**：`establish_baseline`（baseline.py:78 唯一 writer）零生产调用者，唯一 reader 在 chapter_loop.py:2042——语言学漂移安全网整体死线（Z3/Z6 双区立案，阶段 4 提案统一 P1）。
- **T1440**：hook_planting 确定性替换是死代码，plant 三个活跃面仍 LLM dispatch。
- **T1441**：anti-ai 检查清单与 G4 确定性检查构成双重体系——LLM 每章重算 G4 已算过的计数，且同名检查三套阈值不一致（与 C9 F818 关联）。
- **T1442**：确定性统计 helper 五件套（compute_stats/compute_pattern/recall/calibration/review_resonance.routing）仍纯 prompt 级接线，无程序强制。

先例佐证：仓库已 16 次实现该模式但仅 ~5 个代码层接线（T14-07 母模式）；postmortem 证明确定性写路径是数据丢失类 bug 的根因修复。归档 spec #3（确定性技能替换审计）已给出提升判据（纯文件操作/键值 upsert/计数/固定模板填充/阈值比较），#14 覆盖统计正确性——本 spec 只管**接线**。

## 修复目标

1. baseline 生产者接线：drift 链每次检查前基线存在（或显式 bootstrap），F376/F604 死线消除。
2. T14 候选表按优先级接线：P1 三项（T1401 style-learning 统计半、T1402 state-settling 写半→已由 C3 T2 承接、T1403 anti-ai dim3 前置）+ T1442 五件套。
3. 消除双重体系：同名检查 LLM 版删除或降级为"引用 helper 输出"，阈值单源（与 C9 联动）。
4. 防复发：派发前钩子 lint——凡 helper 已覆盖的统计类输出，SKILL.md 正文必须引用 helper 结果而非要求 LLM 重算。

## 任务分解

- **T1 · baseline 接线（F376/F604）**：chapter_loop 在 drift 检查前调用 establish_baseline（基线缺失时首 N 章 bootstrap）；与 C6 T3 的基线体系收敛统一裁决，避免两套基线再次分叉。
- **T2 · 五件套程序强制（T1442）**：dispatch_helper 派发前钩子——对声明了对应 helper 的技能，注入 helper 预计算结果并从 prompt 中删除"请计算"指令；compute_stats/compute_pattern/recall/calibration/review_resonance.routing 逐个接线。修复形状建议：钩子层做（而非改技能正文逐个提醒），一处改动覆盖全部技能。
- **T3 · hook_planting 死代码接线或删除（T1440）**：三个 plant 活跃面二选一——路由到已有确定性实现，或删除死实现并保留 LLM 面（裁决记录进 spec 修订）。
- **T4 · anti-ai 双重体系收敛（T1441/T1403）**：dim3 的 10 项确定性检查前置（派发前算好注入），LLM 清单只保留非确定性项；三套阈值收敛到单源（C9 T3）。
- **T5 · lint 防复发**：`tools/lint_helper_usage.py`——SKILL.md 中"计算/统计/计数"类指令若命中 helper 能力清单则 WARN，要求改引 helper 输出；接入 just check。
- **T6 · 后续候选（T1404-T1419）**：P2 候选（T1404-T1409）按 T14 评估表在上述完成后排期，本 spec 不展开；P3 候选归批量清理储备。

## 批量清理（纯 M 成员）

本簇无 M 级成员（F376/F604 为 P1，T1440-T1442 为 P2）。

## 验收标准

1. 集成测试：跑 3 章 dry-run 后基线文件存在且 drift 检查读到基线（F376/F604 断言：chapter_loop.py:2042 reader 不再空读）。
2. `git grep -n "establish_baseline" src/shenbi/pipeline/` 出现生产调用点（当前零）。
3. 派发 prompt 快照断言：style-learning/chapter-pattern/review-resonance 类派发的 prompt 含 helper 预计算结果块、不含"请计算"指令（T1442 断言）。
4. `uv run python tools/lint_helper_usage.py` exit 0（或输出仅剩已裁决豁免项）。
5. `just check` 全绿。

## 风险与回滚

- 风险：派发前钩子增加每派发延迟（helper 计算耗时）；预计算注入扩大 prompt 体积——与 C28（冗余注入）联动监控 token 面。helper 结果注入后 LLM 可能"照抄"错误值——统计正确性由 #14 spec 的度量修复保障，本 spec 只保证接线。
- 回滚：钩子层带 per-skill 开关，可单技能回退纯 prompt 路径；T1 baseline 接线独立 PR。

## 簇成员清单（与 phase4-clustering.md §2 机械对照）

C7（5 条，代表 F376）：

F376 F604 T1440 T1441 T1442
