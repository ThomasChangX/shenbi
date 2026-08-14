> **Date:** 2026-08-14 | **Status:** Design（Revised 2026-08-15 · 阶段 3 设计审查 4C/4I/6M 全修：R1 卷级作用域+负面验收 / R2 total=100 修正+temp-dir harness / R3 目录校验+契约对齐 / R4 per-step N 语义表 / R5 显式解析上下文 / +R6 节点桥接 / F303 拆至 #26 / F340/F341/F304 补方向与验收）| **Severity:** 🟥 P0（簇级；成员严重度对齐台账：F324=P0，F353/F371/F373/F379/F340/F341/F304=P1，F245/F380/F3B5=P2）| **方法:** systematic-debugging 四阶段
> **系列:** 2026-08-14 全项目审查 | **依赖:** 无硬依赖；N 占位解析语义面与 #10（F247 审计链 N 占位不一致）共享，合并顺序需协调（M5）| **范围:** src/shenbi/pipeline/ + contracts/paths.py + **src/shenbi/gates/g4/**（R3 目录校验器）| **核心洞察:** 5 个独立根因叠加使长篇小说 pipeline 永不进入 CLOSURE

# Pipeline 永不完成（5 独立根因）

## 症状
真实项目 novel-output/xinghuo-ranqiong（规划 5 卷 100 章，已写至 56 章）停在 chapter-loop、closure_step=0、novel.json.total_chapters=None；任何长篇小说无法通过 pipeline 完成。

## 根因与证据
### R1 · volume_map 中文格式 vs 英文解析器（F324, P0）
- `_shared.py:35-42` `_END_RE`/`_RANGE_RE` 只匹配英文 "Chapter End:"/"Chapters N-M"
- 生产格式（SKILL 模板 + 真实产物一致）：`**章节范围**: 第1章 - 第15章（共15章）`
- **两级同格式陷阱（设计审查 C3）**：卷级与 KR 级（`#### KR1` 下的 `- **章节范围**: 第1章 - 第5章`）用同一格式；卷内张力曲线表另有 `| 段 | 章节范围 |` 列。全局匹配会把 KR 子范围误收为边界
- 实证：`read_volume_boundaries(production) → set()`；`is_volume_boundary(15) → False`（第 15 章是第 1 卷末章应为 True）
- 影响链：卷边界触发全家失效 → total_chapters 永不写入 → `if total > 0:` 守卫（cli.py:219）跳过全部章间触发 → book_closure 永不触发

### R2 · total_chapters 写点自锁（F353, P1）
- 全仓仅两个 `_update_total_chapters` 写点（cli.py:748、triggers.py:623），均位于依赖 `total > 0` 守卫或 volume_boundary 触发的路径内
- total 初始 0 → 守卫永不进 → 写点永不执行 → 自锁。**即使修复 R1 仍无法完成**
- **加重因素（价值门升级）**：`_count_total_chapters`（triggers.py:371）只匹配 `章节数: N`，生产 `（共15章）` 同样返回 0——仅解锁守卫不够，须统一口径

### R3 · closure step 10 目录 G4（F371, P1）
- step 10 output_path=`final-snapshot/`（目录），`_resolve_closure_g4_path` 原样返回
- generic G4 对目录 `p.read_text()` → IsADirectoryError → G4.gen.read_error FAIL → 重试×3 → ESCALATION
- **契约不对齐（设计审查 I3）**：snapshot-manage 契约 writes 为 `snapshots/chapter-NNN/*`，`final-snapshot/` 与契约产物路径不匹配——纯跳过 G4 会给 pipeline 最后一步留下零输出校验，且即使跳过，产物也不在声明的路径上

### R4 · N 型触发步骤 G4 未解析路径（F373, P1）
- triggers.py 5 个触发步骤 output_path 含字面 N（`audits/arc-N-score.md` 等），G4 校验未解析路径 → not_found 恒 FAIL
- dispatch 侧写解析后路径——**但 N 的语义按步骤族各不相同（设计审查 C1）**：`arc-N` 的 N=chapter//12（memory-distill SKILL.md:94，chapter 60 → arc-5）；`stratum-N` 的 N=chapter//36；`volume-N` 的 N=卷索引（closure 侧 `_current_volume`=len(boundaries) 同口径）；仅 `chapter-N` 是章号。「extract_chapter + resolve_chapter_path」按章号替换对 5 路径中 4 个是错误机制——会把 G4 引向 `arc-60-score.md` 而技能写的是 `arc-5-score.md`

### R5 · closure prompt 构建期失败（F379, P1）
- closure 5/10 步（2/4/5/6/10）契约 writes 含 N/NNN 占位符，prompt 无 "chapter N" → `extract_chapter`→None → `resolve_chapter_path(None)` 抛 UnresolvedPathError → prompt build 失败（被 dispatch_helper try/except 转为 DispatchResult 失败，效果等同：5 步永不派发）
- **机制缺口（设计审查 I1）**：无 `extract_volume` 对应物；`dispatch_skill` 不接受章/卷参数，章号靠 prompt 文本抓取。朴素「prompt 注入 chapter N」会用章号解析 `volume-N-score.md`，与 G4 侧卷号再次错位（R4 同类错误）
- 关联：F313（closure step 6 的 `chapter-N-long-span.md` 被 `resolve_volume_path` 按卷号解析——应为章号）；F380（genesis step 16 anchor-curate 因 `AC-NNN.md` + chapter=None 抛异常，被 optional=True 伪装成跳过）；F3B5（genesis 升级 `escalation-N-report.md` + chapter=None 同样失败）；F245（N 占位语义碰撞总纲）

### R6 · 章节节点与跨卷桥接中文提取失效（设计审查 I2，spec 原「影响」第 3 条的修复面）
- `_extract_chapter_node_from_map`（chapter_loop.py:2182）匹配 `\|\s*N\s*\|`，生产节点表行是 `| 第1章 |`——正则只误中跨卷桥接表的 `| 1 |` 行（1-4 章取到垃圾节点，5+ 章取 None）
- `context_assemble.py:254` / `plan_skeleton.py:208` 按 `"## Cross-Volume Bridges"` 切分桥接段，生产是 `### 跨卷桥接`——桥接永不浮现。与 R1 同族中英不匹配，双实现待去重

## 影响
- 长篇小说无法完成（P0 级产品功能缺失）
- 卷级特性全家静默失效（foreshadowing-resolve/volume-consolidation/score-volume 等）
- 章节节点数据污染 + 桥接上下文缺失（R6 修复）

## 假设 + 验证命令
- H1: 修复 R1 后 `read_volume_boundaries(production)` 返回 `{15,35,55,75,100}` → `uv run python -c "from pathlib import Path; from shenbi.pipeline._shared import read_volume_boundaries; print(read_volume_boundaries(Path('novel-output/xinghuo-ranqiong')))"`
- H2: 修复 R2 后 genesis 完成即固化 total_chapters——在 temp-dir 项目副本上验证（**禁止写 tracked 生产目录**）：novel.json.total_chapters==100（=max(boundaries)，规划总章数；非 56——56 是已写章数，强行写 56 会在 triggers.py:443 `chapter >= total` 提前触发 book_closure 截断后 44 章）
- H3: 修复 R3/R4/R5 后 closure 全步骤 G4 PASS → G4 CLI 全步骤实测（fixture 项目副本）

## 修复方向（数值化标准）
1. **R1 卷级作用域解析**：`_shared` 中文解析**只认卷级**——判别锚为卷头 `## 第N卷：…（第A-B章）` 与其下首个（`### Key Results` 之前的）`**章节范围**` 行；模式含可选空格与全/半角括号（`第\s*N\s*章\s*[-–—~～]\s*第\s*M\s*章`、`共\s*K\s*章`）。**`| 第N章 |` 模式不得入 `_shared`**（属 R6 节点提取）。**验收（正）**：真实项目边界集=={15,35,55,75,100}、卷数==5、is_volume_boundary(15/35/55/75/100)==True；**验收（负）**：is_volume_boundary(5/10/56)==False（KR 子范围不得入集）。fixture：从 `novel-output/xinghuo-ranqiong/outline/volume_map.md` 拷贝至 `tests/fixtures/`（G0.9 真实产物，G0.11 哈希镜像）
2. **R2 genesis 固化 + 口径统一**：total_chapters := max(read_volume_boundaries())（=规划总章数；与 cli.py 卷扩展路径的 `new_total = max(boundaries)` 既有惯例同源）；genesis step 6（volume-outlining）成功钩子处由代码固化（genesis.py 成功路径，无后续步骤重写 volume_map——已核对 GENESIS_STEPS）；`_count_total_chapters`/`_update_total_chapters` 统一收敛到 `_shared.py`（避免 cli↔genesis 循环 import）。**验收**：temp-dir 项目副本上 novel.json.total_chapters==100
3. **R3 目录内容校验 + 契约对齐**（二选一中取校验，不留静默 SKIP）：gates/g4 增目录纯检查器（目录存在 + ≥1 产物文件 + manifest 存在，幂等无副作用）；closure step 10 的 output_path 与 snapshot-manage 契约对齐（`snapshots/chapter-NNN/*` 解析为最终章号目录，或按契约实际产物校验目录），BOOK_CLOSURE artifact 路径同步。**验收**：closure step 10 在 fixture 项目 G4 PASS
4. **R4 per-step N 语义解析表**（F245 的处置面，单一信源置于 contracts/paths.py）：`arc-N`→N=chapter//12；`stratum-N`→N=chapter//36；`volume-N`→N=边界集中 ≤chapter 的边界计数（与 closure `_current_volume` 同口径）；`chapter-N`→N=章号。触发步骤 G4 校验经该表解析。**验收**：chapter 60 arc 场景 G4 查 `arc-5-score.md`（非 arc-60）；卷末章 55 volume 场景查 `volume-3-score.md`
5. **R5 显式路径解析上下文**：dispatch/prompt-build 增可选 context 参数（占位族→值；缺省回落现行 prompt 文本提取，向后兼容）。closure per-step 表：步骤 2（memory-distill）→最终弧号；4/5（review-arc-payoff/score-volume）→卷号；6（review-long-span）→**最终章号**（=total_chapters，F313 同修）；10→契约目录。F3B5（genesis escalation）传入显式上下文（失败章号或 book 级哨兵）；F380（anchor-curate）`AC-NNN` 标记为 book 级延迟解析（不因 chapter=None 抛异常，optional 跳过须留 structlog 原因）。**验收**：closure 10 步 prompt-build 全通过（fixture）；escalation 派发不抛 UnresolvedPathError；anchor-curate 不再伪装 optional 跳过
6. **R6 中文节点/桥接提取**：`_shared` 增章节节点提取（`| 第N章 |` 表行）与桥接段定位（`### 跨卷桥接`，兼容英文 `## Cross-Volume Bridges`）；chapter_loop.py:2182 与 plan_skeleton 双实现去重共享之；context_assemble.py:254 / plan_skeleton.py:208 切分改双语。**验收**：生产 map 第 5+ 章节点非 None；桥接段可提取
7. **F340 REJECT 重做语义**：cmd_review REJECT → 重做产生该 checkpoint 的步骤（逐类型语义表）；GENESIS_COMPLETE reject → genesis 状态重置到最后一步重跑（破除 resume 恒 True 空转死锁）。**验收**：模拟 genesis-complete reject 后 resume 重跑 step 17 而非 no-op（单测）
8. **F341 并行分支守卫镜像**：并行 post-draft 分支（chapter_loop.py:2702 一带）镜像串行路径既有守卫（chapter_loop.py:1086-1087 的 `state_settle_review_required` 检查）。**验收**：--auto 并行模式不设 STATE_SETTLE checkpoint（单测）
9. **F304 RetryExhaustedError 捕获**：next/resume 调用链捕获（chapter_loop.py:626/2882 两 raise 点的可达路径）→ escalation checkpoint + structlog error，而非 CLI 裸崩。**验收**：预算耗尽路径产出 checkpoint 状态非 traceback（单测）
10. **回归**：`just check` 全绿 + 新增上述验收测试

**F303 拆分声明（设计审查 C4）**：快照子系统接线（create/restore/prune 零调用方、step 15 空转、crash_recovery.py 平行实现并存）是三路设计决策（接线三件套 vs 移除死代码 vs 维持 cli rollback 延迟），无法在本 spec 一行方向化——拆为独立 spec **#26（snapshot-subsystem-wiring）**，INDEX 已登记；本 spec 不再包含 F303。

## 测试分层与 fixture 来源（I4）
- R1/R6 → T1 单测（真实 fixture + 负面断言）
- R2/F340/F341/F304 → T1/T2（temp-dir 项目副本 / 状态机单测，禁写 tracked 生产目录）
- R3/R4/R5 → fixture 项目副本上 G4 CLI 级检查
- 全部纳入 `just check`；评分场景（若有）走 G3.4 独立子 agent，dispatcher 自评无效
