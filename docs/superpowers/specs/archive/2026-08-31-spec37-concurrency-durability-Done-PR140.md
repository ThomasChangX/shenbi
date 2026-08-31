> **Date:** 2026-08-16 | **Status:** Done (PR #140) · Revised 2026-08-31（v2 证据重钉；v3 两轮设计审查收敛——统一锁协议+归属表+层级规则、T604 latch 入 T1、F531/F536/T709 归任务、F206 重定性、T4 裁定 (b)、豁免机制、T0 红测先行+确定性策略、原语粒度勘误、L1 重入规则、trace seam 勘误） | **Severity:** 🟥 Critical | **方法:** systematic-debugging 四阶段
> **系列:** 2026-08-15 全项目深度审计 · 阶段 5（簇 C11，24 条）| **代表 finding:** T605 | **严重度上限:** P0（F630）| **涉及文件面（v2 校正）:** src/shenbi/safe_write.py、src/shenbi/pipeline/filelock_utils.py（WriteLock 现居处）、pipeline/cli.py（init/backfill）、pipeline/crash_recovery.py、pipeline/dispatch_helper.py、pipeline/truth_io.py、dispatcher/modes/codex.py、trace/（writer、compaction、materialize）、cost/ledger.py、gates/gate_manifest.py、audit/record.py

# 并发/锁/durability 协议（audit-concurrency-durability）

## 背景

候选元根因 H：跨进程写（progress、trace、pipeline-state、truth 并发波）无互斥或锁纯建议性，无 fsync/顺序保证。

**v2 复核结论（2026-08-31，驳斥子 agent 13/13 主张逐条亲验）**：自 2026-08-16 以来 ~15 个修复 PR 合入后，本簇核心缺陷**全部仍存活**，但部分引用面已变形。

**已在 main 修复、剔除的面**：cmd_next/review/resume/init 落盘段已持 WriteLock（cli.py:501/600/700/789）；WriteLock 已移 `pipeline/filelock_utils.py`（超时+ReadLock/WriteLock 分级+Windows filelock）；compaction durability 半面已修（compaction.py:48-76）；write-audit 经 TraceWriter seam 发时间戳事件（record.py:44-51）；spec #36 未触及 ledger 锁/mkdir 面。

**存活缺陷清单（行号全为 main HEAD 亲验）**：

- **T605（簇代表）**：WriteLock 绕锁写方——`_emergency_cleanup`（crash_recovery.py:67 atexit + :88 直调 + :93 def，调 save_state 无锁）；`cmd_backfill_context`（cli.py:929 起无 WriteLock）；`cmd_init` 种子写段（cli.py:468-485 无锁）先于 :501；TraceWriter 自述非线程/进程安全（trace/writer.py:6-7）。
- **F630（P0）**：`materialize_progress`（trace/materialize.py:79-96）整体重建 progress.json 从不读旧键；调用面 chapter_loop.py:768-782/:801-825/:2745/:3060；**全仓 INIT/MARK_DONE 零生产者**。
- **T603/F111**：safe_write.py:75-91——1s 退避后无条件 `os.unlink` 夺锁；回退/抢占段零测试（tests/unit/test_safe_write.py 仅 :48/:62）。
- **T602/F510/F525**：cost/ledger.py:62 构造 mkdir；:63 每实例 threading.Lock 零跨实例互斥；:95-96 仅持实例锁。
- **F327/T606**：cmd_init 新形态 TOCTOU——ReadLock 检查（cli.py:424-460）→ 无锁种子写（:468-485）→ WriteLock 仅包 save（:501）。
- **F347/T601**：`_append_integrity_findings`（dispatch_helper.py:1126-1141）读在锁外、写在锁内的读改写竞态。
- **F206（v3 重定性）**：`_record_completion`（codex.py:23-67）**写已走 safe_write，缺陷是读在临界区外**——与 F347 同形的 TOCTOU 读改写，非"绕锁写方"；T1 的"迁移入口"处方对其无效，须用锁定读改写 helper（见统一协议）。
- **F534**：audit/record.py:36-39 裸 `open("a")`，无 fsync/锁/时间戳。
- **F416**：gate_manifest.py:33-35 损坏静默重置；:14-24 `_MANIFEST_LOCKS` 进程内且无界。
- **F619（降级存活）**：compaction.py:48-76 手搓 temp+replace 不经 flock——与并发 TraceWriter append 无互斥。
- **T604**：crash_recovery.py:67/:88 双触发 `_emergency_cleanup` 无 one-shot latch。
- **T607**：dispatch_helper.py:212-221 genre 缓存键仅 chapter；truth_io.py:55-71 与 gate_manifest.py:14-24 锁注册表无界。
- **T709**：pipeline/truth_io.py:2-6/33 自述 threading.Lock 仅进程内；技能 helper 子进程路径绕过外层锁。
- **F531/F536（P1）**：并行审计波 legacy 路由并发 record_audit_outcome → TraceWriter TOCTOU → trace seq 重复+签名链分叉 → G7 误报 tamper；审计链无跨调用互斥。

## 统一锁协议（v3 · 本 spec 核心设计决策）

现状三锁域互不相斥：WriteLock/ReadLock flock `pipeline-state.json.lockfile`（filelock_utils.py:24,93）；safe_write flock **父目录 fd**（safe_write.py:58-59）；O_EXCL 回退用第三机制 `<name>.lock`。v3 定死如下协议：

**文件族 → 守护原语归属表（每文件唯一守护者）**：

| 文件族 | 守护原语 | 理由 |
|---|---|---|
| pipeline-state.json 及 init 种子文件（novel.json/genre-config/genesis-context）与 backfill 写的 context 文件 | WriteLock（项目级） | cmd_next/review/resume 已收敛于此；多文件事务需项目级临界区 |
| progress.json | safe_write flock（目录级） | 派发子进程在 pipeline 持 WriteLock 长临界期内写它，不可夺 WriteLock |
| snapshots/ 与 chapters/（派发产物） | safe_write flock（目录级，L2） | 派发模型事实：子进程不可夺 L1；emergency/backfill 归档段在父进程 L1 临界区内落盘 |
| trace/*.jsonl | per-path 锁（`<file>.lockfile`，flock） | append（TraceWriter，含 safe_write trace seam 事件）与 compaction（整文件替换）互斥 |
| write-audit.jsonl / .integrity-findings-*.jsonl / cost/token-ledger.jsonl | safe_write flock（同目录互斥）+ 统一 append helper（fsync+时间戳） | 同目录追加类 |
| gate pipeline-manifest.json | per-path 跨进程锁（替换 threading.Lock） | 跨进程读改写 |
| truth/**（含 pending_hooks 等记录文件）与 .staging-meta.json | per-path 跨进程锁（truth_io `_path_lock` 升级为锁文件；staging-meta 既有序即 per-path，dispatch_helper.py:1192-1215） | T709：技能 helper 子进程与进程内写方同域互斥；与目录 flock 的组合序依 L2 内部固定序 |

**配套机制**：
- **锁定读改写**：safe_write 增 `locked_transact(path, mutator)`——同临界区内 read→mutate→write（覆盖 F206/F347/F630-merge 面）；目录 flock 在 read 前获取。
- **层级与死锁防**：两级序 = WriteLock（L1）> L2 锁（L2）。允许 L1 内嵌套获取 L2（cmd_next 持 WriteLock 后 safe_write 落盘）。**禁止持 L2 时代码路径再获取 L1**（含间接调用）。**L2 内部固定序：per-path 锁 → 目录 flock**（gate_manifest/staging-meta 类先取 per-path 再进 safe_write；任何路径不得逆序）。

**原语粒度事实（v3r2 勘误）**：L2 的 POSIX 原语是**目录级**（flock 父目录 fd，safe_write.py:58-59——同目录所有文件共用一把锁）；O_EXCL 回退是**文件级**（`<name>.lock`）。归属表按文件族指定守护者，同目录文件天然共享目录锁——表中的"唯一守护者"指**每个写方必须经该族指定原语进入**，非物理上一文件一把锁。

**L1 不可重入与 emergency 路径规则（v3r2/r4）**：flock 冲突跨 fd 即使同进程。`filelock_utils` 增**进程内 holder 自检**（模块级 holder 标志，**记录锁模式与持有线程，finally 中清除——含超时/失败路径**）：`_emergency_cleanup`/`_check_emergency_flag` 获取 L1 前检测本进程持锁——**仅当已持 WriteLock（独占）**时直接在既有临界区内落盘（同进程已互斥），不二次加锁（否则自阻塞至 300s 超时，filelock_utils.py:25）。**仅持 ReadLock 时禁止直接升级获取 WriteLock**（ReadLock/WriteLock 各持独立 fd，LOCK_EX 会与本进程自己的 LOCK_SH 冲突=确定性自死锁）——处方：先释放 ReadLock → 获取 WriteLock → **重验状态**（重验覆盖释放窗口的 TOCTOU）再落盘。

**派发模型事实（v4）**：章稿/快照由派发技能子进程产出，子进程**不可获取**父进程侧 WriteLock（且 L2→L1 禁止、父进程 orchestration 循环全程持 L1 cli.py:700——子进程夺 L1 必阻塞 300s）。故 snapshots/chapters 归 L2：子进程产物写经 safe_write 目录 flock；emergency/backfill 的快照归档段在父进程 L1 临界区内落盘。

**trace seam 事实（v3r2 勘误）**：safe_write 自带 trace seam（safe_write.py:126-140）在 `finally`（:117-125）**释放锁之后**执行——trace 事件追加不在写临界区内。TraceWriter append 将走 trace per-path 锁（T1），seam 发射的事件经同一 per-path 锁互斥；locked_transact 的原子性不依赖 trace seam。

**T0 确定性策略（v3r2）**：race 复现红测不得依赖纯时序——每用例声明确定性交错策略（threading barrier / 预置半写状态 / monkeypatch 定位点），30s 墙钟为上界非依赖。
- **stale-takeover 平台权威性**：活性证明（pid/mtime 双检）权威于 POSIX；Windows/网络 FS 回退路径保留纯超时夺锁并打 WARN（与现状等价），不引入无 Windows 等价物的 pid 语义。并发回归套件 POSIX-only（skipif 非 POSIX）。

## 修复目标

1. 共享可变文件写路径全部经归属表唯一守护原语，无绕锁写方。
2. safe_write 自身互斥可靠：stale-takeover 不无条件（POSIX）、回退段有测试。
3. 覆盖式重建改合并式更新 + 物化调用点按裁定 (b) 处置。
4. durability 基线：追加类文件 fsync + 时间戳 + 锁一致。

## 任务分解（v3：T0 复现先行，全 TDD 红-绿）

- **T0 · 复现用例先行（红）**：T605 双进程丢更新（受测写方=`save_state` 经 cmd 路径）、T601 5 并发 findings 覆盖、F531 trace seq 分叉、T604 双执行、F630 预置键被物化抹掉——全部先写为**红**测试，每用例声明 POSIX-only、墙钟上界（单用例 ≤30s）与**确定性交错策略**（barrier/预置半写状态/monkeypatch 定位点，不依赖纯时序）；T1-T5 修复后翻绿。
- **T1 · 锁协议收敛（T605/F619/F206/F347/T601/F416/F531/F536/T709/T604）**：按归属表逐文件族迁移——`_emergency_cleanup`/`cmd_backfill_context`/`cmd_init` 种子段改持 WriteLock（含 v3r2 进程内 holder 自检，防同进程自阻塞）；`_emergency_cleanup` 加 one-shot latch（T604 修复：模块级 latch 标志，atexit 与信号路径二次进入直接返回）；compaction 与 TraceWriter 统一 trace per-path 锁；`_record_completion` 与 `_append_integrity_findings` 改 `locked_transact`；gate_manifest threading.Lock 改 per-path 跨进程锁；truth_io `_path_lock` 升级跨进程锁文件（T709：truth 文件族与 .staging-meta 同域，子进程写方经同一原语）；并行审计波 record_audit_outcome 互斥（F531/F536）。清点口径：`git grep -nE "(open\([^)]*['\"](a|w|ab|wb|w\+|r\+)['\"]|mkstemp|os\.fdopen.*w|write_text|shutil\.(move|copy))" src/shenbi` 全量清点逐个迁移或带豁免注记。
- **T2 · 锁原语修复（T603/F111/T602/F510/T408/T607）**：stale-takeover POSIX 改 pid/mtime 活性双检（Windows 回退纯超时+WARN）；补回退/抢占段单测；TokenLedger 实例锁改目录 flock（与其 ledger 落盘同域）；genre 缓存键补 project_dir；锁注册表加淘汰上界——**获取时在 `_REGISTRY_LOCK` 下置 held/refcount 标志，仅淘汰从未持有且闲置超阈的条目**（`locked()` 快照有取锁-获锁窗口竞态，不采用）；T1 完成后 gate_manifest/truth_io 注册表已改跨进程锁文件（flock 无状态、无注册表可淘汰），本项仅适用于**存续的进程内注册表**（含过渡期形态）。
- **T3 · TOCTOU 修复（F327/T606/F525/T407）**：cmd_init 三段式收进单 WriteLock 临界区（检查+种子写+save 全入）；TokenLedger 读路径去掉 mkdir 副作用（惰性创建仅写路径）。
- **T4 · 物化处置（F630/F1113，v3 已裁定）**：裁定准则「除 materialize 自身外全仓无 INIT/MARK_DONE 消费方 → 选 (b)」已由 grep 亲验成立，**裁定 (b)：降级/删除调用点**——chapter_loop.py:768-782（每 5 步）与 :801-825（resume 面）的 materialize 调用移除（或降级为仅当 trace 事件非空时执行）；materialize 本体改键级 merge（防御性保留非自有键）。空壳 progress.json 的恢复不在本 spec 范围（既有 crash_recovery/state_heal 已覆盖加载面）。
- **T5 · durability 基线（F534/F605-审计轨迹/F416 重置半面）**（注：F605 为 config_coherence 审计轨迹写序，与簇代表 T605 无关；F416 锁半面在 T1，此处为静默重置半面）：write-audit.jsonl/ledger 追加统一 fsync+时间戳+锁（append helper）；审计轨迹先校验后写；gate_manifest 损坏 fail-loud（结构化错误信封，不静默重置）。
- **T6 · 回归翻绿与固化**：T0 全部复现用例翻绿断言（验证互斥而非复现）；`just check` 全绿。

## 批量清理（纯 M 成员）

- T407/T408（读路径 mkdir 副作用/假锁）随 T3；T607（genre 缓存键 + 锁注册表无界）随 T2 批量。

## 验收标准

1. T0 并发回归套件全绿：双进程 100 次交替经 `save_state` 写 pipeline-state.json 零丢失（T605）；5 并发 integrity-findings 追加行数守恒（T601）；T604 优雅关机单次执行断言（atexit+信号双触发路径）；单用例墙钟 ≤30s 且不依赖纯时序。
2. 清点 grep（T1 口径含 mkstemp/write_text/shutil，模式含 `"a"|"w"|"ab"|"wb"|"w+"` 与 `os.fdopen` 写）清单为零或每项带 `# write-audit-exempt: <理由>` 行内注记，注记存在性由 lint 校验（新增或扩展 tools/ 纯净性 lint，进 `just check`）；清单为下界而非穷尽，豁免注记机制兜底。
3. materialize 调用点移除后，chapter_loop 主循环与 resume 路径不再产出全 pending 空壳 progress.json，且既有 dispatcher/G3 写入键不被物化抹掉（F630/F1113 断言：预置 completed 键 → 走原先触发物化的循环路径 → 键仍在且无空壳重建）。
4. 并行审计 dry-run 后 trace.jsonl seq 无重复、G7 零 tamper 误报（F531 断言）。
5. 审计轨迹写序断言：损坏/不一致输入下 config_coherence 审计轨迹不落盘（先校验后写，F605 断言，fixtures 驱动测试）。
6. `just check` 全绿。

**lockfile 产物卫生**：per-path 锁文件（`*.lockfile`）沿用 `pipeline-state.json.lockfile` 先例——不进 git（.gitignore 增模式，**同时覆盖 O_EXCL 回退的 `<name>.lock` 崩溃残骸**）、运行结束惰性留存由下次复用，洁净 lint 不将其计入未声明产物。

## 风险与回滚

- 风险：全量收敛是大改动——按文件族分批 commit（pipeline-state 先、trace 次之、truth 最后），每批独立验证；两级锁序（L1> L2、禁 L2→L1）防死锁；per-path 锁粒度与并行波性能权衡。stale-takeover 收紧可能使真实崩溃场景锁不释放——POSIX 活性检测覆盖，Windows 保留超时夺锁。
- 回滚：每文件族独立 commit；safe_write 协议变更单列可 revert；并发回归套件常驻。

## 簇成员清单（与 phase4-clustering.md §2 机械对照）

C11（24 条，代表 T605）：

F111 F206 F327 F347 F416 F510 F525 F531 F534 F536 F605 F619 F630 F1113
T407 T408 T601 T602 T603 T604 T605 T606 T607 T709
