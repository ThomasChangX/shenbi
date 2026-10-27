# Spec 执行索引

> **最后更新**：2026-10-28（spec #81 observability-net 登记——观测完备性，Track A 挖矿五发现的框架归宿）
> **活跃 spec 数**：2

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
- **配对**：#81（其 mutant 重放/金丝雀/`--as-of` 回放消费 #81 §1 归档）

### #81 · 观测完备性之网：dispatch 归档、消费者契约、逃逸舱硬化（observability-net）
- **文件**：`2026-10-28-spec81-observability-net.md` ｜ **系列**：regen-vol1 收尾 ｜ **状态**：Active
- **优先级**：🔴 P0 ｜ **方法**：SDD（观测即契约——每记录必具名消费者）
- **依赖**：#80 §1/§3/§5（归档的消费方）；动机证据 `docs/regen-vol1-observability-mining.md`
- **内容**：dispatch 归档+blobs 去重／trace 加性字段（loop_id/feedback_ref）／RETRY 事件／逃逸舱 fail-fast／lint_reads_reconcile／observe_report／滚动归档
- **对应 plan**：P1=归档+三字段+fail-fast+报表骨架；P2=对账 lint+replay；P3=A/B harness+跨卷看板

---

## 登记与编号约定

- 新增 spec 时在此登记：`### #NN · <title>` + 文件/系列/状态/优先级/方法/依赖/内容/对应 plan 字段；编号 = 现有最大号 +1
- spec 完成（Done）或驳回（Rejected）→ 移 `archive/` 并从本页删行；**编号是历史唯一标识，不重编号、不复用**（系列/依赖字段按编号交叉引用，重编号会断链）
- 本页不维护归档计数与归档分类汇总
