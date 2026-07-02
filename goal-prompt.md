## 目标

从 `command-to-give.md` 的执行协议出发，推进 Shenbi 三层测试框架全量执行+T1+T2+T3，产出基于 `outline-example.md`（星火燃穹）的真实完整的 20 万字小说文件。

## 所需技能

- brainstorming
- test-driven-development
- systematic-debugging
- verification-before-completion
- subagent-driven-development（用于拆分并行任务时参考）

## 起始环境 2026-06-13

项目根目录: `/Users/xiaotiac/Documents/GitHub/shenbi`

### 文件结构

- 59 个 skill: `skills/<skill-name>/SKILL.md`
- 60 个 T1 测试目录（59 skill + `_template`）: `tests/tiers/t1-skill/<skill-name>/`（含 rubric.md/bug-hunt/clean/generative）
- 9 个 T2 phase: `tests/tiers/t2-phase/<phase>/`
- 3 个 T3 pipeline: `tests/tiers/t3-pipeline/<pipeline>/`
- 115 个 fixture（83 文件 + 32 目录）: `tests/fixtures/`
- 工具脚本（entry points）: `shenbi-score`, `shenbi-validate`, `shenbi-phase`, `shenbi-dispatch`（源码在 `src/shenbi/`）
- 辅助脚本: `tests/round-exec.sh`（round 创建 + G0 验证）, `tests/lock-tool-hashes.sh`（工具哈希锁定）
- 接受阈值：T1≥94, T2≥94, T3≥94（`tests/tiers/acceptance.json`）
- 执行协议: `command-to-give.md`

### 当前进度（2026-06-13 修复后）

- Round 005 已废弃（含幻影 T2/T3 数据）——不再使用
- **目标**：创建 Round 006，从零开始全量 T1+T2+T3 执行
- 系统性根因已修复：gate 硬化、authoring 对齐、progress.json 一致性、评分独立性、工具哈希锁定
- G0 全 19 项检查 PASS（含 G0.13-16 工具哈希验证、progress.json 内部一致性、summary.json 预填充防护）

## 执行协议

以 `command-to-give.md` 为权威执行协议。关键约束：

- **打分独立性**：Dispatcher（父 session/主 agent）不得给输出打分。如有 subagent 能力则新 session 独立评分；否则退而求其次在主 session 内部隔离评分（先清空生成上下文后评分）。协议原文：`Dispatcher 不得评分`
- **Gate 不可跳**：G0 阻断必须修好重过；G2/G4 失败不评分
- **Fixtures 优先**：所有 skill 输入路径必须以 `tests/fixtures/` 开头（G0.9 强校验）
- **中断规则**：同一类 gate 失败模式达 3 次→暂停，先修根因再继续（SKILL.md/G4 checker/scoring.py/fixture）

## 实施策略

### Phase 1: T1 首轮全量打通（generative 优先）（generative 优先）

按依赖拓扑依次测试剩余 47 个 skill：

- **先跑 foundation skill**（worldbuilding、character-design、story-architecture、volume-outlining、power-system、faction-builder、location-builder、relationship-map、pacing-design、plot-thread-weaver、genre-config）
- **再跑 planning/drafting skill**（chapter-planning、foreshadowing-plant、context-composing、chapter-drafting、style-polishing、anti-detect、length-normalizing）
- **再跑 truth/state skill**（state-settling、foreshadowing-track、foreshadowing-resolve、chapter-pattern、style-learning、truth-sync）
- **再跑 review skill**（review-character、review-continuity、review-dialogue、review-pacing、review-anti-ai、review-foreshadowing、review-world-rules、review-sensitivity、review-memo-compliance、review-motivation、review-era、review-fanfic、review-highpoint、review-long-span、review-pov、review-reader-pull、review-texture、review-spinoff）
- **再跑辅助 skill**（chapter-revision、volume-consolidation、drift-guidance、intent-management、snapshot-manage、foundation-review、short-outline、short-drafting、short-packaging、sequel-writing、import-analysis、character-extraction、world-extraction、canon-import、market-radar、writing-skills、using-shenbi）

每个 skill 跑完 generative 立即跟进 bug-hunt 和 clean，三种类型完成后再推进到下一个 skill。

### Phase 2: 评分 <94 的修复循环

读评分报告，定位扣分维度；区分 SKILL.md 缺失模板、rubric 矛盾、输出内容缺陷，逐项修复后重跑。

### Phase 3: T2 Phase 和 T3 Pipeline

全部 59 skill 三种测试均 ≥94 后，按 `deps.json` 顺序执行 T2 phase，再按 T3 pipeline 执行端到端长篇小说生成。

## 预期最终交付物

1. 完整测试报告：59 skill 的 T1 评分，9 phase 的 T2 评分，3 pipeline 的 T3 评分
2. 59 skill 中所有 <100 分的已修复并增强到 ≥94
3. 基于星火燃穹的一部长篇小说（20 万字目标），包含完整的世界观设定、角色档案、章节草稿、审核报告等全部中间产物
4. 每轮 round 目录持久化，跨 session 可恢复

## 三不原则

- 不跳过 gate
- 不手写 mock 替代 skill 输出
- 不将 Dispatcher 评分当作独立评分


## 完整性约束（2026-06-13 最终强化）

以下约束是硬性要求，不可绕过：

1. **Tool Hash Lock**：`tests/tiers/deps.json` 的 `_tool_hashes` 锁定了 validate-gate.py、scoring.py、phase-runner.py、summarize-round.py 的 SHA256。**G0.13 在 round 创建时验证**（已实现），G7.17 在 round 关闭时重新验证。任何 mid-round 修改都会被检测到。修改工具后运行 `bash tests/lock-tool-hashes.sh`。
2. **Gate Marker 强制**：scoring.py 在计算分数前必须检查 gate markers 存在（`--round-dir` 模式）。缺 marker → exit(3) `MARKER_MISSING`，拒绝评分。**G4 gate markers 覆盖 generative、bug-hunt、clean 三种测试类型。**
3. **G7 Post-Round 审计**：summarize-round.py 必须运行 G7。G7 返回 FAIL（含 TOOL_TAMPER 或 GATE_MISMATCH）→ 拒绝生成 summary。
4. **评分独立性**：Dispatcher 不得评分。`shenbi-score` 的 `_provenance` 字段记录评分者身份（`scored_by`）和 gate markers 验证状态。使用 `shenbi-dispatch` 进行独立 dispatch。
5. **G0 强化阻断**：G0.5b（rubric-SKILL.md 对齐）和 G0.9c（scenario fixture 纯度）现在是 **FAIL 硬阻断**，不再是 WARN。
6. **progress.json 一致性**：G0.14 验证 `completed_skill_names` 与 `skills` dict 一致。G0.15 验证 `remaining_*` 队列准确。G0.16 验证 summary.json 无预填充幻影分数。
