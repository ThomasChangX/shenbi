# Spec 执行索引

> **最后更新**：2026-09-18（spec #40 总纲收官归档——37 簇修复计划完结：回写补齐 44 行、F519 假注记纠偏、08-14 跨轮卫生、孤儿残留登记 #67。现序 #67）
> **活跃 spec 数**：1

本页**只追踪活跃（待执行）spec**，按推荐执行顺序排列：优先级 🟥 Critical/🔴 P0 → 🟠 High/P1 → 🟡 Medium/P2 → ⚪ 批量，同级按编号升序。
已完成/合并/驳回的 spec 移至 `archive/`（按日期排序），**本页不追踪归档**——归档历史查 `archive/` 目录与 `git log`。

---

## 执行队列

### #67 · 孤儿残留收口（F519/F513 + F311 + T1108）

- **文件**：`2026-09-18-orphan-residuals-closure.md`
- **系列**：2026-08-15 审计修复 · spec #40 收官 pass 登记（本 pass 实施并关闭）
- **状态**：Design (Revised 2026-09-18) | **优先级**：🟠 P1（最高面 F513 P1）
- **依赖**：无（三面证据已由收官 pass 勘定）
- **内容**：① F519/F513 legacy CLI 路由写审计快照根错位——修复定稿：快照根 = `round_dir` 参数、executor PROJECT_DIR/REPO_ROOT 常量整体删除、run_g2 省略第 5 参保现行为、三处测试掩蔽揭除 ② F311 curated 层零消费者——裁决 **remove**（context_curation 整模块删除、ENDING_PATTERNS 迁 review_checklist、写方/测试/docstring 全清单）③ T1108 离线可执行模式——裁决 **不做**（三既有 seam + PATH-stub 先例 + G3.4 不可满足；复活条件成文）。边界：不含 T1608 增量化与 C28 token 架构（spec #40 §9 deviations）

---

## 登记与编号约定

- 新增 spec 时在此登记：`### #NN · <title>` + 文件/系列/状态/优先级/方法/依赖/内容/对应 plan 字段；编号 = 现有最大号 +1
- spec 完成（Done）或驳回（Rejected）→ 移 `archive/` 并从本页删行；**编号是历史唯一标识，不重编号、不复用**（系列/依赖字段按编号交叉引用，重编号会断链）
- 本页不维护归档计数与归档分类汇总
