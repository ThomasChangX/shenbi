> **Date:** 2026-08-15 | **Status:** Design | **Severity:** 🟠 P1 | **方法:** systematic-debugging 四阶段
> **系列:** 2026-08-14 全项目审查（自 #6 拆分——设计审查裁决：三路设计决策无法在 #6 一行方向化，见 #6 修订注）| **依赖:** 无 | **范围:** src/shenbi/pipeline/chapter_loop.py + crash_recovery.py + cli.py（rollback 面）| **核心洞察:** 快照子系统多机制并存、pre-revision 路径零接线（Revised 2026-08-30 · SDD #26 阶段 2 事实核实：实际为**四机制**——①chapter_loop 差分三件套[零生产调用方]②crash_recovery 应急快照[已接线：chapter_loop.py:2665 register_emergency_handlers 信号路径]③LLM skill `shenbi-snapshot-manage`[已接线：pipeline/cli.py:836 卷边界派发 + chapter_loop.py:286 条件 step]④restore/rollback 面[全死：restore_from_snapshot 全 src 零引用、cmd_rollback 未实现且 subparser 已移除]。另注：last_snapshot 非严格永不写入——state_heal.py:76 可从磁盘既有应急快照回填，但无生产 pre-revision 写入方）

# 快照子系统接线（snapshot-subsystem-wiring）

## 症状
快照子系统生产未接线：`create_differential_snapshot` / `restore_from_snapshot` / `_prune_old_snapshots` / `chapter_loop._snapshot_chapter_files`（带 `# pyright: ignore[reportUnusedFunction]` 标记）全部无生产调用方；pipeline step 15 "pre-revision-snapshot" 空转无快照动作；`last_snapshot` 永不写入（F303，台账 specced）。

## 根因与证据
- chapter_loop.py ~1613-1740：差分快照三件套（`_snapshot_chapter_files` 死函数内串联 `create_differential_snapshot` + `_prune_old_snapshots`）零调用方
- crash_recovery.py:154 起存在**平行的独立快照实现**——两套机制并存，未收敛
- cli.py ~921-943（pipeline/cli.py）：rollback 子命令显式将快照恢复标记为未实现（deferred），且 subparser 注册已移除——该函数自身即为零调用方死代码
- step 15（`pipeline-pre-revision-snapshot`，chapter_loop.py:248）在 pipeline- 分支无任何快照动作直接跳过

## 待裁决的三路设计（本 spec 的核心设计工作 · 裁决时须计入已接线的两机制：crash_recovery 应急快照与 shenbi-snapshot-manage skill 路径——收敛目标含全部四机制归一或明确分工）
1. **接线**：step 15 调用 chapter_loop 差分快照三件套，pre-revision 前真实落盘快照 + last_snapshot 写入
2. **收敛后接线**：二选一收敛 chapter_loop 三件套 vs crash_recovery 平行实现为单一信源，再接线
3. **移除**：删除死代码，step 15 从步骤表移除，rollback 维持 deferred 并在文档明示

裁决输入：两套实现的覆盖面 diff（哪些快照哪些文件、prune 策略、恢复语义）、`write_safety`/`WRITE_SHARED` 串行化约束（AGENTS.md 并发纪律）、磁盘成本（章级差分快照的体积增长曲线）。

## 验收（按裁决路径定稿）
- 路径 1/2：step 15 执行后快照目录存在且含 manifest、last_snapshot 写入、`_snapshot_chapter_files` 无 pyright unused 标记、`just check` 全绿
- 路径 3：死函数全删、步骤表与文档同步、`git grep create_differential_snapshot` 零残留、`just check` 全绿
