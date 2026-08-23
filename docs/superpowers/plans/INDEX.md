# Plan 执行索引

> **最后更新**：2026-08-24
> **活跃 plan 数**：0 | **已归档**：67（见 `archive/`）

Plan 文件在 spec 进入实施阶段后才创建。PR #39（Token-efficiency 总纲 P0+P1）已交付并归档。

---

## 活跃 Plan




## 待执行的 spec → plan 映射

活跃 spec 的执行队列、优先级、依赖关系见 [`specs/INDEX.md`](../specs/INDEX.md)。每个 spec 的「对应 plan」字段标记了 plan 是否已创建：

- `❌ 未写` → 该 spec 进入实施阶段时再创建 plan（避免过早规划）
- `✅ ready` → plan 已创建并位于本目录（执行 spec 时此页面会同步登记）

## 归档说明

63 个已完成的 plan 在 `archive/` 中，按日期排序（2026-06 ~ 07）。这些 plan 对应的 PR 已全部合并到 main（#1–#19），保留作历史记录。按系列：

- **P-1 基础卫生**（`2026-06-14` a/b/c/d，PR #3）— pyproject/uv/lint、pytest+CI+pre-commit、structlog+异常+ADR、重构清理
- **P-1.E 地基补完**（`2026-06-15` 01–07，PR #4）— src 布局、PR-fraud 填实、工具链、测试、CI 供应链、企业化、文档配置
- **测试与门体系**（`2026-06-11` gate-system / test-framework、`2026-06-13` integrity、`2026-06-16` coverage，PR #1/#2）— G0–G7、三层测试、完整性加固、90%/80% 覆盖率
- **契约单一信源**（`2026-06-21`、`2026-06-29` pillar 1–6，PR #6/#8）— contracts 骨架、门派生、CJK、trace、所有权、属性测试、文档 lint
- **质量门**（`2026-06-22`、`2026-06-28` wave 1–4，PR #7）— 正向门、分层系统 helper/memory/scoring/loop
- **文档重设计**（`2026-07-01`，PR #10）
- **Novel Pipeline**（`2026-07-02` wave 1–5 + root-cause + coverage-matrix、`2026-07-06` phase1-defect，PR #11/#13/#14）
- **性能与上下文交接**（`2026-07-07` perf-redesign、clean-context-handoff，PR #16/#17）
- **一致性基础设施**（`2026-07-08`，PR #17）
- **CI 优化**（`2026-07-09`，PR #18）
- **P0 阻塞修复**（`2026-07-16`，PR #19）
- **07-19 一致性与韧性集群**（`2026-07-19-01` ~ `-19`，19 个 plan，PR #19）

最近归档项：

- `2026-07-19-19-end-to-end-validation-protocol-plan.md`（4 阶段端到端验证，PR #19）
- `2026-07-19-17-pipeline-infrastructure-and-resilience-plan.md`（崩溃恢复 + tenacity 重试 + JSON mode，PR #19）
- `2026-07-16-p0-blocking-fixes.md`（4 个 P0 死路径/stub 修复，PR #19）
- `2026-07-09-ci-optimization.md`（CI 16.6min → 8min，PR #18）
- `2026-07-08-contract-consistency-infrastructure.md`（RoundPaths + 契约一致性，PR #17）
- `2026-07-07-clean-context-handoff.md`（decisions-sidecar + 字段级 reads，PR #16/#17）

> 技术细节查各 archive plan 正文，不在此复述。
