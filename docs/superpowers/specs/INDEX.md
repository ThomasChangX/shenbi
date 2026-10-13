# Spec 执行索引

> **最后更新**：2026-10-13（spec #69 seed 内容流恢复登记——F886 defer 执行件 + 孤儿 reads 修正 + 4.3 六项裁决固化）
> **活跃 spec 数**：1

本页**只追踪活跃（待执行）spec**，按推荐执行顺序排列：优先级 🟥 Critical/🔴 P0 → 🟠 High/P1 → 🟡 Medium/P2 → ⚪ 批量，同级按编号升序。
已完成/合并/驳回的 spec 移至 `archive/`（按日期排序），**本页不追踪归档**——归档历史查 `archive/` 目录与 `git log`。

---

## 执行队列

### #69 · seed 内容流恢复与传递性收尾

- **文件**：`2026-10-13-spec69-seed-content-flow.md`
- **系列**：种子传递性（源自 2026-10-12/13 outline-example.md 大幅丰富前置审计会话）
- **状态**：Active（待执行）
- **优先级**：🟠 P1（F886 为 P1 verified）
- **方法**：契约声明式接线（reads 声明 + sync_contracts 再生成 + SKILL 正文同步 + truth-files.yaml globs 段一行加法）；框架代码改动限 seed_parser/g0/chapter_loop 三处小面
- **依赖**：无
- **内容**：T0 character-design 孤儿 reads 修正（先行件）→ T1 genesis-context 五技能接线（worldbuilding/character-design/story-architecture/faction-builder/volume-outlining）→ T2 配角可选节 → T3 丢弃键 WARN → T4 G0.2 字数锚定 → T5 F368 章节关闭清扫三小件 → T6 NovelConfig 删除（spec #27 F240 执行）→ T7 4.3 六项裁决固化（3 做 3 不做含理由）
- **对应 plan**：未建（spec §2 任务粒度可直接起 plan）

---

## 登记与编号约定

- 新增 spec 时在此登记：`### #NN · <title>` + 文件/系列/状态/优先级/方法/依赖/内容/对应 plan 字段；编号 = 现有最大号 +1
- spec 完成（Done）或驳回（Rejected）→ 移 `archive/` 并从本页删行；**编号是历史唯一标识，不重编号、不复用**（系列/依赖字段按编号交叉引用，重编号会断链）
- 本页不维护归档计数与归档分类汇总
