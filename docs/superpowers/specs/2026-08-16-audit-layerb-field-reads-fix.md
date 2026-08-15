> **Date:** 2026-08-16 | **Status:** Design | **Severity:** 🟠 P1 | **方法:** systematic-debugging 四阶段
> **系列:** 2026-08-15 全项目深度审计 · 阶段 5（簇 C2，13 条）| **代表 finding:** F224 | **严重度上限:** P1（F224/F201）| **涉及文件面:** src/shenbi/dispatcher/（过滤链）、src/shenbi/contracts/fields.py、35 个技能 SKILL.md frontmatter fields 声明、truth 文件真实结构

# Layer B 字段级 reads 机制修复（audit-layerb-field-reads）

## 背景

AGENTS.md 承诺的 Layer B 字段级读取（技能以 dict-form `reads` 声明消费字段，dispatcher 过滤后注入，声明字段缺失时 escape-hatch 返回全文 + WARN）实现链断裂且声明面漂移，双面失效：

1. **实现层死线**：F224——字段过滤唯一生产调用点是不可达死代码（dd1fc62 回归），dispatcher 实际从不按字段过滤；F201——部分匹配时静默丢弃缺失声明字段（违反 escape-hatch 契约，无 WARN 无全文回退）。
2. **声明层漂移**：F239 系统化全貌——19/35 个 dict-form fields 声明对真实 truth 文件零命中，另 4 个目标文件不存在。典型：F227（review-group-character 声明 `povMode`，genre-config.json 无此键）、F824（幻影 genre-config 键 prohibitions/maxNgramRepetition/coreImages）、F826/F827（pending_hooks 节名零命中 / chapter_summaries 节名分裂）、F839（review-arc-payoff 声明 volume_promise/arc_beats 不存在于真实 volume_map.md）、F844（pacingRules 幻影键 + 不存在的 REVIEW_EVIDENCE.md）、F845（current_state.md 目标节名在生产树 xinghuo-ranqiong 中不存在而 fixture 中存在）、F867（style-learning 模板编号/小节与全部下游字段读不一致）、F880（style-polishing DOT 读 prohibitions 但 frontmatter fields 只有 fatigueWords，过滤后不可见）、T303（AGENTS.md 示例字段自身零命中）。

证据细节见 zone-reports/Z2、Z2-review-r1/r3、Z8-review-r2、Z8-b、Z8-c 与 thread-reports/T3.md。

## 修复目标

1. 恢复实现链：dispatcher 字段过滤在生产路径真实执行；声明字段缺失时按 AGENTS.md escape-hatch 返回全文 + WARN。
2. 恢复声明链：35 个 dict-form fields 声明对真实 truth 文件 100% 命中（或目标文件确不存在时修订声明）。
3. 防复发：字段存在性 lint（声明字段 ∈ 真实文件节名/键集）进入 `just check`。

## 任务分解

- **T1 · 过滤链接线（F224）**：恢复 dispatcher 字段过滤的生产调用点（dd1fc62 回归点），并对 API/codex/IDE 三条派发路由各验证一次过滤生效。修复形状建议：过滤入口收敛到单一函数，路由层无法绕过。
- **T2 · escape-hatch 兑现（F201）**：`contracts/fields.py:59-64` 部分匹配语义改为"任一声明字段缺失 → 全文返回 + WARN 日志"（对齐 AGENTS.md 契约原文），删除静默丢弃分支。
- **T3 · 声明对账修复（F227/F239/F824/F826/F827/F839/F844/F845/F867/F880）**：以生产树（novel-output/xinghuo-ranqiong）+ tests/fixtures 真实产物为基准，逐技能二选一：修订 SKILL.md fields 声明至真实节名/键，或修订写方模板使声明节名真实存在。F845 类"生产树与 fixture 分裂"以生产树为准并修 fixture；F867 需同步全部下游字段读。
- **T4 · 双匹配语义统一（T302 关联）**：extract_h2_sections（exact）与 lint（normalize lower）匹配语义统一为一个共享实现，避免 lint 说命中而运行时零命中。
- **T5 · 字段存在性 lint**：扩展 `tools/lint_contracts.py`（或新增 lint_contract_fields.py——已在 justfile 但未入 CI，与 C25 联动）校验每个 dict-form reads 声明的字段/节名在对应 truth 文件（fixtures 或生产树快照）中存在。
- **T6 · 文档同步（T303）**：AGENTS.md Layer B 示例字段改为经 T5 校验的真实字段。

## 批量清理（纯 M 成员）

本簇无 M 级成员（13 条全为 P1/P2）。

## 验收标准

1. 单测：构造部分匹配 truth 文件 → dispatcher 注入内容为全文且日志含 WARN（F201 断言）；三路由各一条过滤生效断言（F224 断言）。
2. `uv run python tools/lint_contract_fields.py` exit 0，覆盖全部 35 个 dict-form 声明（F239 复验：零命中数从 19 降到 0）。
3. 以 xinghuo-ranqiong 生产树 current_state.md 实跑任一声明技能派发的 dry-run，注入上下文含「主角状态」等声明字段（F845 断言）。
4. `just check` 全绿。

## 风险与回滚

- 风险：T1 接线后过滤真实生效，可能暴露此前被"全文注入"掩盖的下游技能缺字段故障——需先跑 T5 lint 清零再开 T1，顺序不可倒置。F845 裁决"生产树为准"可能改变技能可见内容，随审回滚单技能声明即可。
- 回滚：T1 过滤开关保留配置项（默认关→lint 清零后开），可单 PR revert；声明修订逐技能独立提交。

## 簇成员清单（与 phase4-clustering.md §2 机械对照）

C2（13 条，代表 F224）：

F201 F224 F227 F239 F824 F826 F827 F839 F844 F845 F867 F880 T303
