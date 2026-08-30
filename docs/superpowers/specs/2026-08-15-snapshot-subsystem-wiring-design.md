> **Date:** 2026-08-15 | **Status:** Design → 三路裁决定稿：路径 3（移除）· 2026-08-30（裁决依据见 .superpowers 归档记录：恢复消费者已被产品决策移除 + checkpoint-redo/skill-rollback/crash 三重覆盖 + prune 无界增长 + 双写冲突） | **Severity:** 🟠 P1 | **方法:** systematic-debugging 四阶段
> **系列:** 2026-08-14 全项目审查（自 #6 拆分——设计审查裁决：三路设计决策无法在 #6 一行方向化，见 #6 修订注）| **依赖:** 无硬依赖 | **下游:** #57（audit-snapshot-unify，簇 C19）显式依赖本 spec 三路裁决（路径 3 时其大部分失效）；#6 R3 已将 snapshot-manage manifest 命名钉进 SKILL 契约并声明「与 #26 验收对齐」——路径 3 或命名变更时须对账该契约面 | **范围:** src/shenbi/pipeline/{chapter_loop,crash_recovery,cli,snapshot_diff,state_heal}.py + tests 快照族 | **核心洞察:** 快照子系统**四机制并存、pre-revision 路径零接线**——①chapter_loop 差分三件套（零生产调用方）②crash_recovery 应急快照（已接线：chapter_loop.py:2665 register_emergency_handlers 信号路径）③LLM skill `shenbi-snapshot-manage`（已接线：pipeline/cli.py:836 卷边界派发 + chapter_loop.py:286 条件 step）④restore/rollback 面（全死：restore_from_snapshot 全 src 零引用、cmd_rollback 未实现且 subparser 已移除）。另：last_snapshot 非严格永不写入——state_heal.py:76 可从磁盘既有应急快照回填，但无生产 pre-revision 写入方

# 快照子系统接线（snapshot-subsystem-wiring）

## 症状
四机制并存、pre-revision 主路径零接线：①`create_differential_snapshot` / `_prune_old_snapshots` / `chapter_loop._snapshot_chapter_files`（带 `# pyright: ignore[reportUnusedFunction]` 标记）全部无生产调用方（`create_differential_snapshot` 唯一引用点在死函数内，`restore_from_snapshot` 全 src 零引用）；②crash_recovery.py:155 平行应急快照实现经信号处理器接线（仅 crash 触发）；③shenbi-snapshot-manage skill 路径已接线（卷边界/条件 step）；④cmd_rollback 未实现且 subparser 已移除（自身死代码）。pipeline step 15 "pre-revision-snapshot" 在 `pipeline-` 分支空转（仅 drift 特判有实现体）直接跳过；F303（台账 specced）。

## 根因与证据
- chapter_loop.py ~1613-1740：差分快照三件套（`_snapshot_chapter_files` 死函数内串联 `create_differential_snapshot` + `_prune_old_snapshots`）零调用方
- crash_recovery.py:154 起：平行的独立应急快照实现（平铺 `snapshots/chapter-N-{label}.md` 拷贝）——信号/atexit 上下文中调用的刻意极简实现
- pipeline/cli.py:921-943：rollback 未实现（deferred），subparser 注册已移除——该函数自身零调用方
- step 15（`pipeline-pre-revision-snapshot`，chapter_loop.py:248-254，`step_type="checkpoint"`）在 pipeline- 分支（chapter_loop.py ~2901-2906）无任何快照动作直接跳过
- **last_snapshot 格式分叉**：旧路径写 `.md` 文件路径，差分路径写目录路径；state_heal.py `_heal_last_snapshot` 仅 glob `chapter-*.md` 平铺格式（F317，详见 #57）

## 裁决边界（与 #57 的分工）
本 spec 只做**三路裁决 + 最小实施**（接线或移除，含恢复面处置）。布局单源化、命名统一（F792/F350/F306 三套并存）、TRUTH_FILES 覆盖集（F348）、state_heal 识别定稿布局（F317）、manifest 保留策略与生产实证复验（F1109）**均归 #57**（其 T0 显式以本 spec 裁决为前置）。#26 的实施不得顺带做 #57 的收口（单 spec 原子性），但裁决必须给 #57 留出一致的接口（布局/命名方向不被本 spec 决策锁死为 #57 无法收敛的形态）。

## 待裁决的三路设计（本 spec 的核心设计工作）
1. **接线**：step 15 调用 chapter_loop 差分快照三件套（接线点：pipeline- 分支 step 执行器，比照 `pipeline-linguistic-drift-check` 特判模式），pre-revision 前真实落盘快照 + last_snapshot 写入
2. **收敛后接线**：二选一收敛为单一信源再接线——语义三选：(a) crash 路径改调差分函数（**驳回输入**：信号/atexit 上下文中 rglob 全量哈希为 async/性能敌对，须实测评估）；(b) 仅共享文件清单 helper，两实现保留各自写入语义；(c) 正式分工声明——crash=应急平铺、主路径=差分目录，消除"平行实现"指控即止
3. **移除**：删除死代码，step 15 从步骤表移除，rollback 维持 deferred 并在文档明示

**裁决输入**：四机制的覆盖面 diff（快照哪些文件、prune 策略、恢复语义）；`write_safety`/`WRITE_SHARED` 串行化约束（AGENTS.md 并发纪律）；磁盘成本（章级差分快照体积增长曲线——注意 `_prune_old_snapshots` 仅清 manifest 登记的平铺文件，差分目录与应急快照**永不 prune**，接线即无界增长，裁决须同时定 prune 策略或显式移交 #57）；**双写冲突**（路径 1/2 接线后 ③ skill 路径与差分路径并发写 `snapshots/` 的格式碰撞与分工——skill 写 `snapshots/chapter-NNN/*` 目录格式，与差分路径同名目录存在碰撞面）；**恢复面处置**（每条路径必须显式裁决 restore_from_snapshot 与 cmd_rollback 的归宿，禁止接线后残留零调用方的 restore 实现——那会复刻 F303 失败类）。

**路径 3 死符号清单**（零残留的界定范围）：
- src：`create_differential_snapshot` / `restore_from_snapshot`（snapshot_diff.py，模块整体去留随裁决——若无存活的库消费者则整模块删除）、`_prune_old_snapshots` / `_snapshot_chapter_files`（chapter_loop.py）、`cmd_rollback`（pipeline/cli.py）、`last_snapshot` state 字段与 `_heal_last_snapshot`（state_heal.py，处置规则见下）
- tests（须同步删/改，否则 `just check` 悬挂 import 红；实际路径已核）：tests/pipeline/test_snapshot_diff.py、tests/unit/pipeline/{test_snapshot_pruning,test_last_snapshot,test_snapshot_coverage,test_adaptive_triggers,test_state_heal}.py（test_state_heal.py 的 `test_heals_last_snapshot` 随字段删除而删）、tests/unit/pipeline/test_cli_rollback_removed.py:14（直接 import cmd_rollback）、tests/unit/pipeline/test_cli.py:517-532（断言 cmd_rollback 保留——随其删除而反转向：断言不再存在）、tests/unit/contracts/test_registry_pipeline_producers.py:42（D20 注释面——若删 chapter_loop 版而 crash_recovery.py:155 同名函数存活，注释须改指向而非删）
- **last_snapshot 路径 3 处置规则**（消除循环对账）：字段与 `_heal_last_snapshot` 一并删除——#57 路径 3 存活面 T4 不涉及该字段，且"永不写入仅可 heal 回填"的字段无存在价值；#57 如后续需要快照状态指针属其自身设计面
- 文档同步面（M2 界定）：`grep -rn "pre-revision-snapshot"` 命中的非 archive 文档（**audit-runs 历史审计记录与 tests 内注释不计入同步面**）+ step 表注释（chapter_loop.py:133）+ pipeline/cli.py:785 的 last_snapshot 注释 + 本 spec + INDEX

## 验收（按裁决路径定稿）
- 路径 1/2：
  - step 15 执行后（fixtures 驱动测试表达，G0.9——scenario 输入引用 tests/fixtures/ 真实产物）快照目录存在且含 manifest（**命名权威单源 = #57 T1「命名三套收敛为一套」；本 spec 钉契约现值 `snapshots/chapter-NNN/manifest.json`（SKILL.md writes 现值）为过渡值**，差分默认 `snapshot-manifest.json` 与契约现值的分歧由 #57 T1 终裁，#26 不锁死命名——若 #26 先于 #57 执行，接线实现按契约现值对齐）
  - last_snapshot 写入（格式权威单源同上归 #57 T2/F317 终裁；#26 接线实现采用与 state_heal `_heal_last_snapshot` 现行识别逻辑兼容的格式，不许留下 heal 识别不了的写入格式——终格式的 heal 侧改造归 #57）
  - restore/rollback 面有显式归宿：cmd_rollback 实现接线，或删除，或保留 deferred 但**落可验证工件**（SKILL.md 契约注记或 pipeline 文档章节，验收 = `git grep` 该注记存在；纯口头"注记"不合格）三选一，禁止默认漂过
  - `_snapshot_chapter_files` 无 pyright unused 标记
  - `just check` 全绿（含 prune 策略或其显式移交 #57 的注记）
- 路径 3：死符号清单全清、上列 tests/文档同步面处理、`git grep create_differential_snapshot` 在 src/ 零残留（tests 按清单处理，归档文档不计）、`just check` 全绿
