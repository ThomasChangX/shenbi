# Spec 执行索引

> **最后更新**：2026-09-21（spec #68 POC E2E 纵向验收登记 Design——goal-prompt.md 复盘定稿的判读层缺口：纵向判据 v1 + report_longitudinal + 失败分类学 + 扩展性观测 + 金丝雀回路）
> **活跃 spec 数**：1

本页**只追踪活跃（待执行）spec**，按推荐执行顺序排列：优先级 🟥 Critical/🔴 P0 → 🟠 High/P1 → 🟡 Medium/P2 → ⚪ 批量，同级按编号升序。
已完成/合并/驳回的 spec 移至 `archive/`（按日期排序），**本页不追踪归档**——归档历史查 `archive/` 目录与 `git log`。

---

## 执行队列

### #68 · POC E2E 纵向验收（纵向判读层）

- **文件**：`2026-09-21-poc-e2e-longitudinal-acceptance.md`
- **系列**：POC E2E 验收层（源自 goal-prompt.md 2026-09-21 复盘）
- **状态**：Design | **优先级**：🟠 P1 | **方法**：零 LLM 确定性工程（tools/ 只读判读层，`src/shenbi/` 运行时零改动）
- **依赖**：无（audit aggregate / resonance trend / TokenLedger 三路数据源均已落盘）
- **内容**：纵向验收判据 v1（保量 95% + 逐章下限 + 前/中/后趋势条件，第一跑后校准）、`tools/report_longitudinal.py`（纯解析双报告 + verdict exit code）、失败分类学关键字映射（类别×章节热力图 + 责任子系统路由表）、扩展性观测（每万字成本/墙钟、真相文件增长曲线、上下文截断计数）、`just e2e-report` / `just e2e-canary` 接线；v1 不挂 G7 硬门、不动 acceptance.json 层均分

---

## 登记与编号约定

- 新增 spec 时在此登记：`### #NN · <title>` + 文件/系列/状态/优先级/方法/依赖/内容/对应 plan 字段；编号 = 现有最大号 +1
- spec 完成（Done）或驳回（Rejected）→ 移 `archive/` 并从本页删行；**编号是历史唯一标识，不重编号、不复用**（系列/依赖字段按编号交叉引用，重编号会断链）
- 本页不维护归档计数与归档分类汇总
