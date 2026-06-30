# 契约强制执行与生产路径接入设计 v1

**状态**：草案待审阅
**日期**：2026-06-30
**关联**：2026-06-29-contract-single-source-design.md v5.2（骨架层已完成）；本 spec 补齐其遗留的 6 个生产路径缺口

## 起因与根因诊断

前序 spec 建完了六支柱机制基础设施，经三轮代码审查确认 9/10。但 6 个生产路径缺口仍未闭合：

| # | 缺口 | 根因 |
|---|------|------|
| 1 | 67 技能仍是 TypedDict，未迁移到 Pydantic | contract.py 仍是生产 loader；67 技能有结构验证但无语义验证 |
| 2 | 门未路由到 safe_write | gates/shared.py、g1.py、update_progress.py、summarize_round.py、phase_runner.py 仍直接 write_text |
| 3 | audit_trace 未接入 gate_G7 | g7_trace.py 是独立函数，gate_G7 不调用它 |
| 4 | update_progress 命令未迁到 trace | cmd_init/cmd_mark_done 直接写 progress.json，不写 trace |
| 5 | G1 .bak shutil.copy2 仍在门内 | 决策抽了但执行未迁 |
| 6 | transitional allowlist 仍 14 文件 | safe_write 未被采用 |

**深层根因**：67 个 skill 的 SKILL.md body 包含 368 条语义约束（如 pacing-design 的「四拍占比之和必须=100%」），但现有 G4 checker 用关键词存在性检查（"铺垫" in content），不检查数值正确性。这些约束是经过多轮测试的领域质量资产，但全部是散文——没有类型化强制。

## 目标

1. 把已有 67 skill 的语义约束从散文提升为 CI 强制的类型化不变量（不改 skill body 内容，只改执行机制）。
2. 把 safe_write/audit_trace/materialize_progress/dispatch_with_write_audit 接入生产路径。
3. 删除 contract.py（单一源闭环）。
4. transitional allowlist 缩减到仅永久条目。
5. 每个改动像手术一样精准——只改目标行，不重写函数体。

## 非目标

- 不改 skill body 内容（领域知识不动）。
- 不改 frontmatter contract: 块的 I/O 结构（已能工作）。
- subprocess read-provenance（FUSE/ptrace）仍是 future work。

## 设计原则：修改而非重建

现有 67 skill 经过多轮测试，包含 68 个 DOT 流程图、368 条 MUST/禁止约束、39 个 anti-rationalization 表。这些是驱动小说质量的领域资产。本 spec 的全部工作是把这些已有的散文约束编码为可执行代码——提取、验证、强制——而非重写 skill。

## 工作流 A：语义约束编码（核心质量提升）

### A1：约束分类

67 skill 的 368 条约束按可执行性分三类：

| 类型 | 数量(估) | 可机器执行 | 示例 |
|------|---------|-----------|------|
| 数值不变量 | ~60 | 直接编码 | 四拍占比之和=100%；场景类型数 6-10；禁用词数<=50 |
| 存在性不变量 | ~180 | 结构化检查 | 三线比例必同时存在；approval.decision 合法值 |
| 散文指导 | ~128 | 留为散文 | 改前必读；人类必批；可回滚 |

只编码前两类（~240 条），第三类保持散文。

### A2：逐 skill 迁移（分 5 批）

每批迁移的精确步骤（以 genre-config 为例）：
1. 读 SKILL.md 的「可自动检查的计数规则」表
2. 读 tests/fixtures/genre-config.json 的真实顶层键（9 个）
3. 写 contracts/skills/genre_config.py：Pydantic 模型，字段集以 fixture 为准
4. 重写 gates/g4/genre_config.py：从字符串搜索改为 model_validate 调用
5. 加 property test
6. commit

关键：SKILL.md body 不动；frontmatter 不动；只新增 Pydantic 模型 + 重写 G4 检查方式。

## 工作流 B：生产路径接入（精准行级修改）

### B1：safe_write 接入（6 文件，每文件改 1-3 行）

每个文件只改写操作的调用方式。

### B2：trace 接入 update_progress 命令

三个写命令改为 trace 事件 + materialize_progress。

### B3：audit_trace 接入 gate_G7（3 行）

### B4：contract.py 重定向 + 删除

### B5：transitional allowlist 缩减

## 实现顺序（高杠杆优先）

1. 工作流 B（生产路径接入）：先接入 safe_write + trace + audit_trace
2. 工作流 A 批次 1-2（高密度约束编码）
3. 工作流 A 批次 3-5（其余技能迁移）
4. 工作流 B4（contract.py 删除）
5. 工作流 B5（allowlist 清零）

## 成功判据

1. safe_write 是框架状态的唯一写入口；transitional allowlist <= 4
2. gate_G7 调用 audit_trace
3. update_progress 命令通过 trace 运行
4. 67/69 技能有 Pydantic 模型
5. G4 checker 从字符串搜索改为 model_validate 结构化验证
6. contract.py 已删除
7. 每条可自动检查规则有对应 property test
8. 全量测试套件 green
