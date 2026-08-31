> **Date:** 2026-08-16 | **Status:** Design · Revised 2026-08-31（v2：全部证据按 main HEAD c3888481 重钉行号；剔除 2026-08-16 后已被合并 PR 修复的面；F619/F327 重定范围；T4 零事件生产者事实从补录升级为主决策） | **Severity:** 🟥 Critical | **方法:** systematic-debugging 四阶段
> **系列:** 2026-08-15 全项目深度审计 · 阶段 5（簇 C11，24 条）| **代表 finding:** T605（簇代表按"描述最系统"指定）| **严重度上限:** P0（F630）| **涉及文件面（v2 校正）:** src/shenbi/safe_write.py、src/shenbi/pipeline/filelock_utils.py（WriteLock 现居处）、pipeline/cli.py（init/backfill）、pipeline/crash_recovery.py、pipeline/dispatch_helper.py、pipeline/truth_io.py、dispatcher/modes/codex.py、trace/（writer、compaction、materialize）、cost/ledger.py、gates/gate_manifest.py、audit/record.py

# 并发/锁/durability 协议（audit-concurrency-durability）

## 背景

候选元根因 H：跨进程写（progress、trace、pipeline-state、truth 并发波）无互斥或锁纯建议性，无 fsync/顺序保证。

**v2 复核结论（2026-08-31，驳斥子 agent 13/13 主张逐条亲验）**：自 2026-08-16 以来 ~15 个修复 PR 合入后，本簇核心缺陷**全部仍存活**，但部分引用面已变形：

**已在 main 修复、v2 剔除的面（不计入本 spec 工作量）**：
- cmd_next/cmd_review/cmd_resume/cmd_init 落盘段现已持 WriteLock（cli.py:501/600/700/789）
- WriteLock 原语已移入 `pipeline/filelock_utils.py`，带超时与 ReadLock/WriteLock 分级、Windows filelock 支持——「原语纯建议性」表述过期，但**绕锁调用方**仍在（见 T1）
- trace compaction 的 durability 半面已修（temp+fsync+os.replace+dir-fsync，compaction.py:48-76）——F619 仅剩互斥半面存活
- write-audit 在 trace/ 存在时经 TraceWriter seam 发时间戳 trace 事件（record.py:44-51）——F534 的 JSONL 落盘本体仍无 fsync/锁/时间戳
- spec #36（abf253de）改的是 ledger 字段/定价，**未触及** T602 锁/mkdir 面

**存活缺陷清单（v2 行号全为 main HEAD 亲验）**：

- **T605（簇代表，verified，存活）**：WriteLock 绕锁写方仍全面存在——`_emergency_cleanup`（crash_recovery.py:67 atexit + :88 直调 + :93 def，调 save_state 无锁）；`cmd_backfill_context`（cli.py:929 起，逐文件 safe_write 但整体无 WriteLock）；`cmd_init` 种子写段（cli.py:468-485 novel.json/genre-config/genesis-context 无锁）先于 :501 的 WriteLock；TraceWriter 自述非线程/进程安全（trace/writer.py:6-7）。
- **F630（P0，verified，存活且强化）**：`materialize_progress`（trace/materialize.py:79-96）纯从 total_skills+重放事件整体重建 progress.json，**从不读取/合并既有 progress.json 键**；调用面活跃：chapter_loop.py:768-782（每 5 步）、:801-825（resume 触发）、:2745、:3060。**全仓 grep `action="INIT"/"MARK_DONE"` 零生产者**（src/+tools/，仅 materialize 自身与测试）——零事件下重建结果为全 pending。
- **T603/F111（存活）**：safe_write.py:75-91——1s 退避后**无条件** `os.unlink(lockfile)` 夺锁（无 pid/mtime 活性检查）；回退/抢占段**零测试**（tests/unit/test_safe_write.py 仅覆盖泄漏 :48 与权限 :62）。
- **T602/F510/F525（存活）**：cost/ledger.py:62 构造即 `mkdir`（读路径副作用创建 cost/）；:63 `self._write_lock = threading.Lock()` 每实例一把=跨实例/跨进程零互斥；:95-96 append 仅持实例锁。
- **F327/T606（存活，形态已变）**：cmd_init TOCTOU 三段式新形态——存在性检查在 ReadLock 下（cli.py:424-460）→ 种子写**无锁**（:468-485）→ WriteLock 仅包住 save_state（:501）；两个并发 init 仍可同时通过检查。
- **F347/T601（存活）**：`_append_integrity_findings`（dispatch_helper.py:1126-1141）read_text→append→safe_write 整文件读改写——锁仅覆盖写不覆盖读，同章并行审计互相覆盖整份 JSONL。
- **F206（存活）**：`_record_completion`（dispatcher/modes/codex.py:23-67）progress.json 无锁读改写，且与 F630 联动（materialize 整体抹掉其写入键）。
- **F534（存活）**：audit/record.py:36-39 裸 `open("a")` 写 write-audit.jsonl，无 fsync、无跨进程锁、记录无时间戳字段。
- **F416（存活）**：gate_manifest.py:33-35 损坏静默重置（`log.warning("manifest_corrupt_reinitializing")` 后返回空骨架，非 fail-loud）；:14-24 `_MANIFEST_LOCKS` threading.Lock 注册表仅进程内且无界。
- **F619（降级存活）**：compaction.py:48-76 手搓 temp+replace，不经 safe_write/flock——与并发 TraceWriter append 无跨进程互斥（durability 半面已修）。
- **T604（存活）**：crash_recovery.py:67 atexit + :88 信号路径双触发 `_emergency_cleanup`，无 one-shot latch → 优雅关机确定性双执行（save_state 两次、双 emergency 快照）。
- **T607（存活）**：dispatch_helper.py:212-221 `_genre_config_cache: dict[int, ...]` 键仅 chapter 无 project_dir（跨项目串配置）且无界；truth_io.py:55-71 `_PATH_LOCKS` 与 gate_manifest.py:14-24 `_MANIFEST_LOCKS` 均无淘汰。
- **T709（存活）**：pipeline/truth_io.py:2-6/33 自述 threading.Lock 仅进程内；技能 helper 子进程路径绕过外层 WriteLock。
- **F531/F536（P1，存活）**：并行审计波 legacy 路由并发 record_audit_outcome → TraceWriter TOCTOU → trace seq 重复+签名链分叉 → G7 误报 tamper；审计链无跨调用互斥。

## 修复目标

1. 共享可变文件（pipeline-state/progress/trace/write-audit/integrity-findings/manifest/ledger）的写路径全部经单一跨进程锁协议（safe_write + flock），无绕锁写方。
2. safe_write 自身互斥可靠：stale-takeover 不无条件、回退段有测试。
3. 覆盖式重建改合并式更新（materialize_progress 不再抹掉他方键），并解决零事件生产者问题。
4. durability 基线：审计/账本类追加文件 fsync + 时间戳 + 锁一致。

## 任务分解

- **T1 · 锁协议收敛（T605/F619/F206/F347/T601/F416）**：以 safe_write(+flock) 为唯一跨进程写入口；绕锁写方逐个改经协议——`_emergency_cleanup`、`cmd_backfill_context`、`cmd_init` 种子写段、legacy worker、compaction（改经 flock 或与 TraceWriter 协调互斥）、`_record_completion`、`_append_integrity_findings`（读改写收进锁临界区）、gate_manifest（进程内锁改跨进程）。清点口径：`git grep -nE "open\([^)]*['\"](a|w)['\"]" src/shenbi` 全量清点后逐个迁移或带豁免注记。
- **T2 · 锁原语修复（T603/F111/T602/F510/T408/T607）**：stale-takeover 改带活性证明（锁文件内 pid/mtime 双检 + 心跳）或删除 1s 无条件夺锁；补回退/抢占段单测（当前零测试）；TokenLedger 实例锁改锁文件或全局注册表；genre 缓存键补 project_dir；锁注册表（truth_io/_MANIFEST_LOCKS）加淘汰上界。
- **T3 · TOCTOU 修复（F327/T606/F525/T407）**：cmd_init 新形态三段式（ReadLock 检查 :424-460 → 无锁种子写 :468-485 → WriteLock save :501）收进单 WriteLock 临界区；TokenLedger 读路径去掉 mkdir 副作用（惰性创建仅写路径）。
- **T4 · 覆盖改合并 + 零事件决策（F630/F1113，主决策）**：materialize_progress 改键级 merge（保留非自有键）**不够**——零 INIT/MARK_DONE 事件生产者（v2 grep 亲验）下 materialize 仍把自有键重建为全 pending。**二选一必须落定**：(a) 补齐事件生产者（chapter_loop/dispatch 链发射 INIT/MARK_DONE）；(b) 降级/删除调用点（chapter_loop.py:768-782 每 5 步 + :801-825 resume 面实现上无收益）。plan 阶段定夺并给证据。
- **T5 · durability 基线（F534/F605/F416）**：write-audit.jsonl 追加统一 fsync+时间戳+锁；审计轨迹先校验后写；gate_manifest 损坏 fail-loud（不静默重置）。
- **T6 · 并发回归套件**：双进程/多线程实跑用例固化——T605 双进程丢更新复现用例、T601 5 并发 findings 覆盖用例、F531 trace 分叉用例、T604 双执行用例，全部从"复现 bug"翻转为"验证互斥"。

## 批量清理（纯 M 成员）

- T407/T408（读路径 mkdir 副作用/假锁）随 T3；T607（genre 缓存键 + 锁注册表无界）随 T2 批量。

## 验收标准

1. 并发回归套件（T6）在 CI 绿：双进程 100 次交替写 pipeline-state.json 零丢失；5 并发 integrity-findings 追加行数守恒（T605/T601 断言）；T604 优雅关机单次执行断言。
2. `git grep -nE "open\([^)]*['\"](a|w)['\"]" src/shenbi | grep -v safe_write` 清单为零或每项带豁免注记（T1 断言）。
3. materialize 后 progress.json 保留 dispatcher/G3 写入键，且 T4 二选一决策落地后 progress.json 不再出现全 pending 空壳重建（F630/F1113 断言，用例：预置键 → 物化 → 键仍在；有事件时 completed 面正确）。
4. 并行审计 dry-run 后 trace.jsonl seq 无重复、G7 零 tamper 误报（F531 断言）。
5. `just check` 全绿。

## 风险与回滚

- 风险：全量收敛写入口是大改动——按文件族分批（pipeline-state 先、trace 次之、truth 最后），每批独立验证；锁粒度过粗会死锁（与并行波性能权衡），per-path 锁优先。stale-takeover 收紧可能使真实崩溃场景的锁永不释放——需配活性检测而非纯超时。
- 回滚：每文件族独立 commit；safe_write 协议变更单列可 revert；并发回归套件常驻。

## 簇成员清单（与 phase4-clustering.md §2 机械对照）

C11（24 条，代表 T605）：

F111 F206 F327 F347 F416 F510 F525 F531 F534 F536 F605 F619 F630 F1113
T407 T408 T601 T602 T603 T604 T605 T606 T607 T709
