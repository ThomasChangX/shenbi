> **Date:** 2026-08-16 | **Status:** Design | **Severity:** 🟠 P1 | **方法:** systematic-debugging 四阶段
> **系列:** 2026-08-15 全项目审计 · 阶段 5 修复 spec（批次 C，簇 C30）| **依赖:** C3（truth 写路径/staging 提交路由——staging 语义先定稿）；与 C19（spec #26 快照三路裁决）共享 crash_recovery 面 | **范围:** src/shenbi/pipeline/{cli.py, machine.py, crash_recovery.py, chapter_loop.py}、staging 提交/清理语义 | **核心洞察:** 章循环状态机的生命周期不变量从未定义——staging 何时晋升、何时清理、崩溃后游标指向哪，四套直觉各自实现，交互模式下每 checkpoint 确定性销毁未提交产物（F318）

# C30 · 章循环状态机与 staging 生命周期修复（chapter-loop-staging）

## 元信息
- 簇：C30（章循环状态机/staging 生命周期缺陷），20 条，最高严重度 P1（F318/F371/T102/T1602/F305/F310 六条 P1，其中 5 条 verified），证据等级=实验佐证
- 成员：F318（代表）、F305、F310-F311、F323、F338、F357-F358、F371、F377、F379-F380、F797、F1110、F1112、F1114、F1153、T102、T1108、T1602
- 来源：Z3 初审/复核 r1-r3 + Z7-review-r2 + Z11-a/Z11-b + thread-reports/T1.md、T11.md、T16.md

## 背景与根因
状态机的"崩溃-恢复-staging"三角没有一份权威语义文档，各缺陷都是某条未定义不变量的实例化：
1. **staging 生命周期**（F318 P1：atexit 累积注册 + 紧急清 staging 丢未 commit 产物，交互模式主路径每 checkpoint 确定性销毁；T102 P1 verified：staging commit 丢 sidecar，plan/state-settling 的 decisions sidecar 永滞 staging，auto-commit 模式被 clear_staging 无条件删除；F1110：55 个 plan-decisions 仅存暂存；F323 P2：MODIFY commit staging 后又回退重派，LLM 重生成覆盖人工编辑）
2. **resume 游标**（F371 P1 verified：cmd_resume 的 phase 转换基于 checkpoint_history[-1] 且事件永不消费，auto 模式崩溃恢复把全书游标重置回第 1 章静默重生成覆盖；F1114：运行中断态与 state 尾部失真；F797：steps_done 55/55 章为旧代步名，跨代 resume 无迁移）
3. **步骤编排**（F358 M + T1602 P1 verified：step-2 chapter-planning 过早触发上下文装配，plan 尚不存在空跑装配 + fallback 写盘，每章 2× Route B 网络停顿；F380 M：C1 守卫跳过新章 step-1；F357 M：`_FORESHADOWING_LIFECYCLE_IDX = 6` 魔法索引；F338 M：clear_checkpoint 无 NONE 防御）
4. **缓存与产物状态失真**（F310 P1 verified：SCR 缓存无失效，修订后返回旧缓存；F1112：state 声称 context-composing 完成但 41 章无产物；F311 P2：curated 文档错位 P7 且零消费者）
5. **失败/审计路径**（F305 P1 verified：并行审计波零 G3/G4；F377 P2：触发器扇出无中途保存点，崩溃整段重放；F1153 P2：预算耗尽路径只设 ESCALATION checkpoint 不派发 escalation-review；T1108 P2：无离线可执行模式）

## 目标
1. 写出 staging 生命周期权威语义：staged 产物只在显式 commit/rollback 决策后清理；auto-commit 与人工模式同一清理谓词；sidecar 与主产物同生共死
2. resume 游标以"最后已提交章产物"为锚，跨代步名迁移有版本化迁移器与测试
3. 步骤表去魔法索引、装配触发点后移，消除每章空跑

## 任务分解
### R1 · staging 清理谓词定稿（F318 + T102 + F1110 + F323，最高优先）
- atexit 紧急清理只清"从未进入 checkpoint 的临时文件"；checkpoint approve/reject 时 commit（含 sidecar 整目录）或显式 discard，二者必居其一且留审计日志
- MODIFY 语义裁决：人工编辑后重派 = 以人工编辑为基线（不 commit 旧 staging 再覆盖）；`pipeline-review MODIFY` 路径重写
- **验收**：交互模式跑 1 章 fixture——staged decisions sidecar 在 approve 后出现在 committed truth；F318 的 atexit 用例（注册两次 + 中断）不丢产物

### R2 · resume 游标锚定（F371 + F1114 + F797）
- 游标 = max(已提交章号, checkpoint 显式锚)，phase 转换事件化并消费（不再读 history[-1] 猜）
- steps_done 步名版本化：`PIPELINE_STEPS_VERSION` 常量 + 迁移表（旧名→新名），resume 时迁移并 WARN
- **验收**：F371 复现场景（auto 模式中断于章中）恢复后从断点章继续且零覆盖；旧 state fixture 迁移测试

### R3 · 步骤表与装配触发（T1602 + F358 + F380 + F357 + F338）
- 装配触发移到 step-3 首入口（plan 存在性守卫）；C1 守卫补新章 step-1；魔法索引改推导式（与 `_FIRST_AUDIT_IDX` 同法）；clear_checkpoint 对 None checkpoint no-op
- **验收**：T16 实测场景回归——每章 Route B 停顿 ≤1 次；`git grep _FORESHADOWING_LIFECYCLE_IDX` 零字面量

### R4 · 缓存失效与状态真实性（F310 + F1112 + F311）
- SCR 缓存键加 (path, mtime)；state 标记完成前校验产物存在（不存在则降级未完成 + WARN）；curated 文档错位归 P7 的分层修正（若 C37 裁决删除死输出则从其裁决）
- **验收**：修订后 SCR 提取含新文本；state claims 与磁盘产物一致性检查器（可并入 G7 面，与 C1 对账 lint 衔接）

### R5 · 失败路径补全（F305 + F377 + F1153）
- 并行审计波对 requires_independent 技能强制 G3/结构校验（与 C5 独立性接线协同）；触发器扇出/审计波加中途保存点；预算耗尽路径补派 escalation-review（与 C33 失败分类对接）
- T1108（离线模式）登记为独立设计裁决，本 spec 不实现，只在 spec 尾注移交
- **验收**：崩溃注入测试（中途 kill）重放范围 ≤ 当前触发器段；escalation 派发产物存在

## 验收（簇级）
- `just check` 全绿；新增 `tests/integration/pipeline/` 生命周期用例（真实 fixture，覆盖 R1/R2/R5 崩溃注入）
- C30 全部 20 条 merged-into F318 回写关闭

## 风险
- R1 语义变更影响 C4（decisions sidecar 链）与 C3（staging 提交路由）——三簇联合验收，C3 spec 定稿写路径后本 spec R1 才能合入
- F371 修复涉及 checkpoint 事件模型，改动面大——先写迁移测试锁定现行为再改（C14 弱断言治理协同，避免新测试 pin 旧 bug）

## 验证命令
- staging 生命周期：`pytest tests/integration/pipeline/ -k "staging or checkpoint" -q`（含 F318 atexit 用例与 T102 sidecar 用例）
- resume 游标：`pytest tests/integration/pipeline/ -k resume -q`（F371 场景：auto 模式中断恢复不回退章号）
- 旧步名迁移：`pytest tests/unit/pipeline/ -k steps_migration -q`（F797）
- 状态真实性：对真实 round 跑 `shenbi-pipeline status`，state claims 与磁盘产物 diff 为空
- 回归：`just check` 全绿

## 回写
- merged 关系（phase4 §3）：`F318 <- F305, F310-F311, F323, F338, F357-F358, F371, F377, F379-F380, F797, F1110, F1112, F1114, F1153, T102, T1108, T1602`
- 移交注记：T1108（离线可执行模式）为独立设计裁决，本 spec 尾注移交不计入验收；F311 curated 零消费者面若 C37 R0 裁决删除则随 C37 关闭
