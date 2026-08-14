> **Date:** 2026-08-14 | **Status:** Design | **Severity:** 🟥 P0 | **方法:** systematic-debugging 四阶段
> **系列:** 2026-08-14 全项目审查 | **依赖:** 无 | **范围:** src/shenbi/pipeline/ + crash_recovery.py + trace/ | **核心洞察:** 4 个独立数据丢失路径，生产已实证累积数据被覆盖

# 数据丢失簇（4 独立根因）

## R1 · state-settling append_dedup no-op → 累积 truth 每章覆写（F397, P0）
- 症状：56 章书 `chapter_summaries.md` 仅存 2 章条目
- 证据：dispatch_helper.py:1165 注释 "append_dedup is intentionally NOT branched here"——writes/updates 全整文件覆写；state-settling 契约 reads 仅 `chapters/chapter-N.md`（LLM 拿不到既有 truth 内容）→ 每章把 6 个累积文件覆写为当章内容
- 从属：F312（upsert_yaml 丢 body）
- 修复：append_dedup 模式接回 `write_truth_file`（upsert 语义）或 state-settling 契约 reads 增加既有 truth 文件；**验收：连续 3 章后 chapter_summaries 含 3 章条目**

## R2 · atexit 正常退出清 staging（F364, P0）
- 症状：`pipeline review approve` 时 staging 已空 → plan/truth 永不提交；交互 pipeline 卡死
- 证据：crash_recovery.py:66 `atexit.register(_emergency_cleanup)` → :144-148 无条件 `clear_staging`；实测正常退出 staging 目录消失 + current_step 被篡改为 `EMERGENCY_SHUTDOWN_AT_<skill>`
- 从属：F3B6（钩子累积嵌套污染）、F3B7（atexit 无锁写竞态）
- 修复：_emergency_cleanup 仅在真正紧急（信号/未完成状态）时清 staging；atexit 注册前设置标志；补 `atexit.unregister`；**验收：正常退出 staging 保留、current_step 不变**

## R3 · materialize_progress 零生产者 → 覆盖 progress.json（F640, P0）
- 证据：materialize 期望 INIT/MARK_DONE 事件，全仓零生产者；任何调用把真实 progress.json（含 scoring_history）覆盖为"全 pending"视图
- 修复：接线 trace 事件生产或删除调用点；**验收：materialize 后 progress.json schema 保留**

## R4 · 并行 post-draft 写竞态（F326, P0）
- 证据：chapter_loop.py:2405-2419 ThreadPoolExecutor 并发 dispatch lifecycle + state-settling，两者契约均更新 `truth/pending_hooks.md`，未走 write_safety WRITE_SHARED 串行
- 从属：F505（TokenLedger 锁无效）、F3A4（integrity 无锁）、F253（非原子读改写）
- 修复：pending_hooks.md 写路径收敛到 write_truth_file(upsert) 或串行化；**验收：并发测试无 lost-update**
