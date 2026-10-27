# Spec 执行索引

> **最后更新**：2026-10-28（spec #80 invariant-net 登记——regen-vol1 G3.4 根因的框架根治）
> **活跃 spec 数**：1

本页**只追踪活跃（待执行）spec**，按推荐执行顺序排列：优先级 🟥 Critical/🔴 P0 → 🟠 High/P1 → 🟡 Medium/P2 → ⚪ 批量，同级按编号升序。
已完成/合并/驳回的 spec 移至 `archive/`（按日期排序），**本页不追踪归档**——归档历史查 `archive/` 目录与 `git log`。

---

## 执行队列

### #80 · 不变量之网：规范事实库、四槽门检、变异测试覆盖（invariant-net）
- **文件**：`2026-10-28-spec80-invariant-net.md` ｜ **系列**：regen-vol1 收尾 ｜ **状态**：Active
- **优先级**：🔴 P0 ｜ **方法**：SDD（declare-then-verify 推广 + mutation-tested coverage）
- **依赖**：无（消费 regen-vol1 伤口语料为 fixtures）
- **内容**：facts store+查询面／四槽不变量普查／六门 F15-F20／mutant CI／金丝雀审计
- **对应 plan**：P1=骨架三维度+三门+mutant 导入；P2=余门+实弹；P3=全量迁移

---

## 登记与编号约定

- 新增 spec 时在此登记：`### #NN · <title>` + 文件/系列/状态/优先级/方法/依赖/内容/对应 plan 字段；编号 = 现有最大号 +1
- spec 完成（Done）或驳回（Rejected）→ 移 `archive/` 并从本页删行；**编号是历史唯一标识，不重编号、不复用**（系列/依赖字段按编号交叉引用，重编号会断链）
- 本页不维护归档计数与归档分类汇总
