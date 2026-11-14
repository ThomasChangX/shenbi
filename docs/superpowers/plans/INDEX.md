# Plan 执行索引

> **最后更新**：2026-11-14（spec #90 plan 建立——四轮审查收敛 Ready to execute）
> **活跃 plan 数**：2 | **已归档**：141（见 `archive/`）

Plan 文件在 spec 进入实施阶段后才创建。PR #39（Token-efficiency 总纲 P0+P1）已交付并归档。

---

## 活跃 Plan

- **[2026-11-14-spec90-contract-data-single-source.md](2026-11-14-spec90-contract-data-single-source.md)** ✅ ready（对应 spec #90 r2.3d；5 task：lint 先行删面+守卫→原子迁移→T3 换源→T4a JSON+附带→演练汇跑；plan 审查四轮收敛——轮 2 R1 hash-lock 重锁必做步/R2 f-string 双大括号为高价值拦截）
- **[2026-11-06-spec97-precommit-rev-landing.md](2026-11-06-spec97-precommit-rev-landing.md)** ✅ ready（**执行完毕待归档**——T0-T3+首跑验收全落）——对应 spec #97；2026-11-06 建档时本 INDEX 漏登（陈旧漂移，2026-11-07 顺带清偿）

## 待执行的 spec → plan 映射

活跃 spec 的执行队列、优先级、依赖关系见 [`specs/INDEX.md`](../specs/INDEX.md)。每个 spec 的「对应 plan」字段标记了 plan 是否已创建：

- `❌ 未写` → 该 spec 进入实施阶段时再创建 plan（避免过早规划）
- `✅ ready` → plan 已创建并位于本目录（执行 spec 时此页面会同步登记）

- **spec #83 三面一致性之网**（`2026-10-31`，PR #271）— POST 引句两臂门/修订联动+stale 三站点/打摆计数+分族路由/follower 完成语义/计数三支路/余额双面锚+束级升格/来历锚/canon 回灌 lint/声口 token 族+口径清偿；§10 九支路 shadow 全闭环

## 归档说明

已完成的 plan 在 `archive/` 中按日期排序，保留作历史记录（数量与对应 PR 区间随归档持续增长，以页头计数为准）。按系列：

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
- **2026-11-14 spec89-gates-internal-repair**（PR #337）——CheckContext 拆分+五窄助手+章号单源+shared 出鞘+G0.12 真实现
- **2026-11-14 spec88-gate-finding-contract**（PR #334）——finding() 发射器+AST lint+三族改写+check_id 单源+精确匹配+id inventory

- `2026-11-12-spec87-god-file-decomposition.md`（SDD #87 完结：PR #331 · 2026-11-13——god 文件拆分与正名：五体制出鞘/ExtractSpec 注册表/BuiltPrompt NamedTuple/26 名 roster/正名+基线冻结）
- `2026-10-30-spec82-retention-engine-net.md`（SDD #82 完结：PR #263 · 2026-10-31——T0 快照/序列门×4/钩龄/母题触点/留存锚参数化/shadow 纪律；运行侧验收=卷一重生成窗口）

- `2026-09-18-spec40-master-closure.md`（SDD #40 收官 pass：ledger 回写补齐 44 行 + spec #67 登记 + 总纲归档）
- `2026-09-17-c26-shell-injection-fix.md`（SDD #64 C26 shell/just 包装层注入，PR #220）
- `2026-09-13-c25-ci-just-sync.md`（SDD #63 C25 CI/just 双向同步漂移，PR #217）
- `2026-09-07-c37-dead-code-enforcement.md`（SDD #51 C37 死代码清理与零接线执法，PR #179 + review 修复 #180）
- `2026-09-07-spec54-c16-fixture-authenticity.md`（SDD #54 C16 fixture 真实性与 G0.9 执法，PR #174）
- `2026-09-04-spec42-c28-perf-antipatterns.md`（SDD #42 C28 性能反模式，PR #153 + flake 修复 #154）
- `2026-08-31-spec34-status-vocab.md`（SDD #34 状态词表单源，PR #129）
- `2026-08-31-spec31-g3-independence.md`（SDD #31 G3 独立性 C5，PR #122）
- `2026-09-07-c33-retry-taxonomy.md`（SDD #47 C33 重试/失败分类统一，PR #164）
- `2026-08-31-spec30-decisions-chain.md`（SDD #30 decisions 链 C4，PR #120）
- `2026-08-30-snapshot-wiring-removal.md`（SDD #26 快照子系统路径 3 移除，PR #105）
- `2026-08-30-truth-write-path.md`（SDD #21 truth 写路径，PR #88）
- `2026-08-30-z11-output-contracts.md`（SDD #20 z11 产物契约，PR #82 + #83/#84/#85）
- `2026-08-30-security-injection.md`（SDD #22 安全与提示注入修订版，PR #90 修订 + #91 交付）

- `2026-07-19-19-end-to-end-validation-protocol-plan.md`（4 阶段端到端验证，PR #19）
- `2026-07-19-17-pipeline-infrastructure-and-resilience-plan.md`（崩溃恢复 + tenacity 重试 + JSON mode，PR #19）
- `2026-07-16-p0-blocking-fixes.md`（4 个 P0 死路径/stub 修复，PR #19）
- `2026-07-09-ci-optimization.md`（CI 16.6min → 8min，PR #18）
- `2026-07-08-contract-consistency-infrastructure.md`（RoundPaths + 契约一致性，PR #17）
- `2026-07-07-clean-context-handoff.md`（decisions-sidecar + 字段级 reads，PR #16/#17）

> 技术细节查各 archive plan 正文，不在此复述。
