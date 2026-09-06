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
> **Scope 裁决（2026-09-06 驳斥复核）**：T102/F1110（PR #120）、F305（PR #63）、F1153（PR #6 链）、F379 已在 main 修复——本 spec 不重复实现，归档回写记 closed-by 对应 PR；F380/F311/F1112/F1114 降级承接（见各 R 条目）；R5 缩为 F377 单条。

### R1 · staging 清理谓词定稿（F318 + F323，最高优先；T102/F1110 已修剔除）
- 谓词单一信源 = 扩展现有 staging meta（`checkpoint.py` `_load_staging_meta` 所辖登记，非新建平行 manifest 文件）：产物进入 checkpoint 时落盘标记，经 `write_safety` 原子写，崩溃后新进程由该登记重建 staged/committed 边界——"从未进入 checkpoint"必须跨进程可推导，不得依赖进程内记忆
- atexit 紧急清理只清"manifest 中从未进入 checkpoint 的临时文件"；checkpoint approve/reject 时 commit（含 sidecar 整目录）或显式 discard，二者必居其一且留审计日志（structlog）
- atexit/信号路径复用 spec #37（PR #140）one-shot latch，清理谓词在锁协议约束下求值；新增清理入口不得盲取 WriteLock（atexit 盲取 = 确定性自死锁，crash_recovery.py:136-156 已有不变量）；与 C11 联合回归验收
- MODIFY 语义裁决：人工编辑后重派 = 以人工编辑为基线 = 对旧 staging 显式 discard（走同一审计日志谓词），不构成第三种清理路径；`pipeline-review MODIFY` 路径重写
- **验收**：交互模式跑 1 章 fixture（确定性故障注入，非真实信号 kill）——staged decisions sidecar 在 approve 后出现在 committed truth；F318 的 atexit 用例（latch 复用 + 崩溃后 manifest 重建）不丢产物

### R2 · resume 游标锚定（F371 + F1114 + F797）
- 游标 = 已提交章产物号（R1 commit 语义定稿后唯一来源），checkpoint 显式锚仅作下界校验（显式锚 > 已提交章号时 WARN 并取已提交章号——防未提交章被 resume 重生成覆盖）；phase 转换事件化并消费（不再读 history[-1] 猜）；新事件/状态字面量以 `Literal` 定义于 `src/shenbi/contracts/enums.py`
- steps_done 步名版本化：`PIPELINE_STEPS_VERSION` 常量（步骤表任何重命名/重排即 +1，由 pin 步骤表快照的回归测试强制——快照与版本常量不一致即测试红）+ 迁移表（旧名→新名），resume 时迁移并 WARN（structlog）
- **验收**：F371 复现场景（auto 模式中断于章中）恢复后从断点章继续且零覆盖；旧 state fixture 迁移测试

### R3 · 步骤表与装配触发（T1602 + F358 + F380 + F357 + F338）
- 装配触发移到 step-3 首入口（plan 存在性守卫）；C1 守卫补新章 step-1（F380 表象已修，补回归锁定测试）；魔法索引改推导式（与 `_FIRST_AUDIT_IDX` 同法）；clear_checkpoint 对 None checkpoint no-op
- **验收**：T16 实测场景回归——step-2 不再空跑装配/写废弃 fallback（可测代理指标：每章装配/派发调用计数 ≤1，注入计数器断言，等价于网络停顿 ≤1 次）；`git grep _FORESHADOWING_LIFECYCLE_IDX` 零字面量；F380 回归测试锁定新章从 step-1 起

### R4 · 缓存失效与状态真实性（F310 + F1112 + F311）
- SCR 缓存键加 (path, size, mtime)（mtime 单字段在 git checkout/同秒修订下假命中或假失效）；state 标记完成前校验产物存在（不存在则降级未完成 + WARN，structlog；降级态字面量入 enums.py）；F311 仅剩零消费者面——若 C37 R0 裁决删除死输出则从其裁决，本 spec 不实现 curated 消费方
- **验收**：修订后 SCR 提取含新文本（fixture 驱动）；state claims 与磁盘产物一致性检查器（可并入 G7 面，与 C1 对账 lint 衔接）

### R5 · 失败路径补全（仅剩 F377；F305/F1153/F379 已修剔除）
- 触发器扇出/审计波加中途保存点（每 skill 段完成后落盘进度，崩溃重放范围 ≤ 当前段）
- T1108（离线模式）登记为独立设计裁决，本 spec 不实现，只在 spec 尾注移交
- **验收**：确定性崩溃注入（故障 hook，fixture 取 `tests/fixtures/` 真实归档 round）重放范围 ≤ 当前触发器段

## 验收（簇级）
- `just check` 全绿；新增 `tests/integration/pipeline/` 生命周期用例（真实 fixture，覆盖 R1/R2/R5 确定性崩溃注入）
- 19 条关闭（20 − T1108 移交不计），其中 5 条 closed-by 既有 PR（T102/F1110→#120、F305→#63、F1153→#6 链、F379）、14 条本 spec 关闭（含 F311 零消费面视 C37 裁决分支）——回写按此口径，不双重计数

## 风险
- 前置已满足：C3 = PR #117 Done、C4 = PR #120 Done（2026-09-06 复核）；剩 C19（#26 已归档）共享面回归与 C37 对 F311 的分支裁决
- R1 改动叠在 spec #37（PR #140）one-shot latch/锁协议之上——联合回归验收，不得破坏其不变量（依赖图：R2 的"已提交章号"依赖 R1 commit 语义定稿，R1 先行）
- F371 修复涉及 checkpoint 事件模型，改动面大——先写迁移测试锁定现行为再改（C14 弱断言治理协同，避免新测试 pin 旧 bug）

## 验证命令
- staging 生命周期：`pytest tests/integration/pipeline/ -k "staging or checkpoint" -q`（T102 sidecar 用例指复用 PR #120 既有测试作回归基线，本 spec 不新增 T102 实现）
- resume 游标：`pytest tests/integration/pipeline/ -k resume -q`（F371 场景：auto 模式中断恢复不回退章号）
- 旧步名迁移：`pytest tests/unit/pipeline/ -k steps_migration -q`（F797）
- 状态真实性：对真实 round 跑 `shenbi-pipeline status`，state claims 与磁盘产物 diff 为空
- 回归：`just check` 全绿

## 回写
- merged 关系（phase4 §3）：`F318 <- F305, F310-F311, F323, F338, F357-F358, F371, F377, F379-F380, F797, F1110, F1112, F1114, F1153, T102, T1108, T1602`
- closed-by 标签（机器可读，防回写工具重开已修项）：T102/F1110 closed-by PR #120 · F305 closed-by PR #63 · F1153 closed-by ac466632 (PR #42, spec #6 F304) + 2b00ff53 · F379 closed-by 8d3f5c7e (PR #11)；其余 14 条本 spec 关闭
- 移交注记：T1108（离线可执行模式）为独立设计裁决，本 spec 尾注移交不计入验收；F311 curated 零消费者面若 C37 R0 裁决删除则随 C37 关闭
