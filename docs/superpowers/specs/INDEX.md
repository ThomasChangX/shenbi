# Spec 执行索引

> **最后更新**：2026-10-28（spec #81 observability-net 登记——观测完备性，Track A 挖矿五发现的框架归宿）
> **活跃 spec 数**：1

本页**只追踪活跃（待执行）spec**，按推荐执行顺序排列：优先级 🟥 Critical/🔴 P0 → 🟠 High/P1 → 🟡 Medium/P2 → ⚪ 批量，同级按编号升序。
已完成/合并/驳回的 spec 移至 `archive/`（按日期排序），**本页不追踪归档**——归档历史查 `archive/` 目录与 `git log`。

---

## 执行队列

### #81 · 观测完备性之网：dispatch 归档、消费者契约、逃逸舱硬化（observability-net）
- **文件**：`2026-10-28-spec81-observability-net.md` ｜ **系列**：regen-vol1 收尾 ｜ **状态**：Active
- **优先级**：🔴 P0 ｜ **方法**：SDD（观测即契约——每记录必具名消费者）
- **依赖**：#80 §1/§3/§5（归档的消费方）；动机证据 `docs/regen-vol1-observability-mining.md`
- **内容**：dispatch 归档+blobs 去重／trace 加性字段（loop_id/feedback_ref）／RETRY 事件／逃逸舱 fail-fast／lint_reads_reconcile／observe_report／滚动归档
- **对应 plan**：P1=归档+三字段+fail-fast+报表骨架；P2=对账 lint+replay；P3=A/B harness+跨卷看板
- **触及的不变量维度**：无（观测域——dispatch 归档/trace 字段/逃逸舱，不直接触及 13 维普查任何维度；其产物供 #80 mutant 重放与 `--as-of` 回放消费）

---

## 登记与编号约定

- 新增 spec 时在此登记：`### #NN · <title>` + 文件/系列/状态/优先级/方法/依赖/内容/对应 plan 字段；编号 = 现有最大号 +1
- **「触及的不变量维度」必填节**（spec #80 T10）：每个活跃 spec 的登记块须含一行 `- **触及的不变量维度**：<清单 或 无>`——引用 `docs/framework/invariants.md` 普查表的维度名（如 `恒等 identity/持有与经手 props`）；不触及任何维度写 `无`。`lint_invariant_coverage` 校验活跃项该节存在性（P1 只校 P1 期相维度）
- spec 完成（Done）或驳回（Rejected）→ 移 `archive/` 并从本页删行；**编号是历史唯一标识，不重编号、不复用**（系列/依赖字段按编号交叉引用，重编号会断链）
- 本页不维护归档计数与归档分类汇总
