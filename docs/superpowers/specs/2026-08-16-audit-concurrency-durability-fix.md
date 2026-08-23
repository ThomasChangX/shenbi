> **Date:** 2026-08-16 | **Status:** Design | **Severity:** 🟥 Critical | **方法:** systematic-debugging 四阶段
> **系列:** 2026-08-15 全项目深度审计 · 阶段 5（簇 C11，24 条）| **代表 finding:** T605（簇代表按"描述最系统"指定）| **严重度上限:** P0（F630）| **涉及文件面:** src/shenbi/utils/safe_write.py（WriteLock）、pipeline/cli.py（init/backfill）、parallel_dispatch（审计波）、trace/（writer、compaction、materialize）、ledger.py、gate_manifest.py、write_audit、truth_io/hook_planting 子进程面

# 并发/锁/durability 协议（audit-concurrency-durability）

## 背景

候选元根因 H：跨进程写（progress、trace、pipeline-state、truth 并发波）无互斥或锁纯建议性，无 fsync/顺序保证。多个 P0/P1 有实跑复现：

- **T605（簇代表，verified）**：WriteLock 纯建议性——emergency cleanup/backfill-context/init 前段/legacy worker 全部绕过，pipeline-state.json 跨进程静默丢更新（双进程实跑复现；协调者核验 crash_recovery/backfill 零锁引用）。
- **F630（P0，verified）**：materialize_progress 周期性整体重建 progress.json，静默覆盖 dispatcher 与 G3 写入的键；F1113 生产实证：progress.json 为 171B 空壳。
- **F531/F536（P1）**：并行审计波 legacy 路由并发 record_audit_outcome → TraceWriter TOCTOU → trace seq 重复+签名链分叉 → G7 对合法运行误报 tamper（实跑复现）；审计链无跨调用互斥，分钟级 pre→post 窗口内他方写入被错误归属。
- **锁原语自身缺陷**：T602（TokenLedger 每实例新建锁=零互斥 + state.token_usage += 绕过实例锁）；T603（safe_write M5 回退 1s 后无条件夺存活锁，互斥破坏，实跑复现）；F111（O_EXCL 回退 backoff/抢占段零测试，1s 无条件 stale-takeover 丢更新窗口）。
- **TOCTOU/check-then-act**：F327/T606（cmd_init 锁外检查后才取锁，三段式跨锁分裂）；F206（_record_completion 对 progress.json 无锁 read-modify-write）。
- **并行波读改写竞态**：F347/T601（同 项双立案：_append_integrity_findings 无 per-path 锁，同章并行审计互相覆盖 findings，实跑 5/5）。
- **durability 不对称**：F534（write-audit.jsonl 无 fsync/锁/时间戳）；F619（compact 绕过 safe_write 的 flock 协议）；F416（gate_manifest 损坏静默重置，threading.Lock 仅进程内）；F605（审计轨迹先写后校验，失败时不一致）。
- **读路径副作用与假锁**：F525/T407/T408（TokenLedger 读路径构造即创建 cost/ 目录；实例锁跨实例无效）。
- **子进程绕锁**：T709（truth_io 锁仅进程内 threading.Lock，技能 helper 子进程路径绕过外层 WriteLock）。
- **其他**：F510（ledger.py 实例锁跨实例无效）；T604（_emergency_cleanup 无 one-shot latch，优雅关机确定性双执行，实跑复现）；T607（genre 缓存键缺 project_dir + 锁注册表无界增长）；F1113（progress.json 空壳生产实证）。

## 修复目标

1. 共享可变文件（pipeline-state/progress/trace/write-audit/integrity-findings/manifest/ledger）的写路径全部经单一跨进程锁协议（safe_write + flock），无绕锁写方。
2. safe_write 自身互斥可靠：stale-takeover 不无条件、回退段有测试。
3. 覆盖式重建改合并式更新（materialize_progress 不再抹掉他方键）。
4. durability 基线：审计/账本类追加文件 fsync + 时间戳 + 锁一致。

## 任务分解

- **T1 · 锁协议收敛（T605/F619/F206/F347/T601/F416）**：以 safe_write(+flock) 为唯一跨进程写入口；WriteLock 的全部绕锁写方（emergency cleanup/backfill/init/legacy worker/compact/_record_completion/_append_integrity_findings/gate_manifest）逐个改经协议；并行波 JSONL 追加加 per-path 锁。修复形状建议：不新增锁机制，收敛入口——凡绕过 safe_write 的裸 open 写（`git grep -n "open(.*['\"]a\?['\"]" src/shenbi`）全量清点后逐个迁移（与 C3 T704/T711、C32 写审计联动）。
- **T2 · 锁原语修复（T603/F111/T602/F510/T408）**：stale-takeover 改带活性证明（锁文件内 pid/mtime 双检 + 心跳）或直接删除 1s 无条件夺锁；补回退/抢占段单测（当前零测试）；实例锁改锁文件或全局注册表（跨实例有效）。
- **T3 · TOCTOU 修复（F327/T606/F525/T407）**：cmd_init 三段式收进单锁临界区；TokenLedger 读路径去掉 mkdir 副作用（惰性创建仅写路径）。
- **T4 · 覆盖改合并（F630/F1113）**：materialize_progress 改键级 merge（保留非自有键），或物化频率降级+锁内读改写；生产空壳 progress.json 由恢复路径重建。
  - **T4 显式输入（2026-08-23 spec #7 REJECT 补录，F640 事实补强）**：INIT/MARK_DONE trace 事件全仓零生产者（src/+tools/ grep 无任何发射点；trace_action= 全仓仅 materialize 自身出现）——键级 merge 只防覆盖他方键，不解决「重放结果为空」本身：零事件下 materialize 仍会把自有键重建为全 pending。T4 落地时须二选一：补齐事件生产者，或降级/删除调用点（chapter_loop.py:687-746 每 5 步 + resume 触发面）。
- **T5 · durability 基线（F534/F605/F416）**：write-audit.jsonl/trace 追加统一 fsync+时间戳；审计轨迹先校验后写；gate_manifest 损坏 fail-loud（不静默重置）。
- **T6 · 并发回归套件**：双进程/多线程实跑用例固化——T605 双进程丢更新复现用例、T601 5 并发 findings 覆盖用例、F531 trace 分叉用例，全部从"复现 bug"翻转为"验证互斥"。

## 批量清理（纯 M 成员）

- T407/T408（读路径 mkdir 副作用/假锁）随 T3；T607（genre 缓存键 + 锁注册表无界）随 T2 批量。

## 验收标准

1. 并发回归套件（T6）在 CI 绿：双进程 100 次交替写 pipeline-state.json 零丢失；5 并发 integrity-findings 追加行数守恒（T605/T601 断言）。
2. `git grep -nE "open\([^)]*['\"](a|w)['\"]" src/shenbi | grep -v safe_write` 清单为零或每项带豁免注记（T1 断言）。
3. materialize 后 progress.json 保留 dispatcher/G3 写入键（F630 断言，用例：预置键 → 物化 → 键仍在）。
4. 并行审计 dry-run 后 trace.jsonl seq 无重复、G7 零 tamper 误报（F531 断言）。
5. `just check` 全绿。

## 风险与回滚

- 风险：全量收敛写入口是大改动——按文件族分批（pipeline-state 先、trace 次之、truth 最后），每批独立验证；锁粒度过粗会死锁（与并行波性能权衡），per-path 锁优先。stale-takeover 收紧可能使真实崩溃场景的锁永不释放——需配活性检测而非纯超时。
- 回滚：每文件族独立 PR；safe_write 协议变更单列 PR 可 revert；并发回归套件常驻。

## 簇成员清单（与 phase4-clustering.md §2 机械对照）

C11（24 条，代表 T605）：

F111 F206 F327 F347 F416 F510 F525 F531 F534 F536 F605 F619 F630 F1113
T407 T408 T601 T602 T603 T604 T605 T606 T607 T709
