> **Date:** 2026-08-14 | **Status:** Design（Revised 2026-08-15 · 阶段 3 设计审查 6 轮收敛 · 末轮 0C/0I。R1 卷级作用域+负面验收 / R2 total=100+在途 heal / R3 参数化目录校验+manifest 钉契约 / R4 per-step N 语义表+四消费者+[path-context] 跨路由通道 / R5 显式解析上下文 / R6 三消费方+全桥接段聚合 / F303 拆至 #26 / F340 重试计数重置+全类型表 / F341 全守卫体镜像 / F304 捕获定位 / F380 哨兵路径）| **Severity:** 🟥 P0（簇级；成员严重度对齐台账：F324=P0，F353/F371/F373/F379/F340/F341/F304=P1，F245/F380/F3B5=P2）| **方法:** systematic-debugging 四阶段
> **系列:** 2026-08-14 全项目审查 | **依赖:** 无硬依赖；N 占位解析语义面与 #10（F247 审计链 N 占位不一致）共享，合并顺序需协调（M5）| **范围:** src/shenbi/pipeline/ + contracts/paths.py + src/shenbi/gates/g4/ + dispatcher/executor.py + audit/_shared.py + skills/shenbi-snapshot-manage | **核心洞察:** 5 个独立根因叠加使长篇小说 pipeline 永不进入 CLOSURE

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
- dispatch 侧写解析后路径——**但 N 的语义按步骤族各不相同（设计审查 C1）**：`arc-N` 的 N=chapter//12（memory-distill SKILL.md:94，chapter 60 → arc-5）；`stratum-N` 的 N=chapter//36；`volume-N` 的 N=卷索引（closure 侧 `_current_volume`=len(boundaries) 同口径）；仅 `chapter-N` 是章号。「extract_chapter + resolve_chapter_path」按章号替换对 5 个 N 路径**全部**是错误机制——会把 G4 引向 `arc-60-score.md` 而技能写的是 `arc-5-score.md`

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
1. **R1 卷级作用域解析**：`_shared` 中文解析**只认卷级**——判别锚为卷头 `^## 第<序数>卷[：:]`（序数含阿拉伯与中文数字 0-9一二三四五六七八九十百；`（第A-B章）` 后缀是生产样本巧合**非模板契约**（volume-outlining SKILL.md 契约为 `## 第N卷：{卷名}`），锚不得依赖后缀；边界值只取卷头下首个（`### Key Results` 之前的）`**章节范围**` 行）；模式含可选空格与全/半角括号（`第\s*N\s*章\s*[-–—~～]\s*第\s*M\s*章`、`共\s*K\s*章`）。**`| 第N章 |` 模式不得入 `_shared 的边界解析`**（属 R6 节点提取）。**验收（正）**：真实项目边界集=={15,35,55,75,100}、卷数==5、is_volume_boundary(15/35/55/75/100)==True；**验收（负）**：is_volume_boundary(5/10/56)==False（KR 子范围不得入集）。fixture：从 `novel-output/xinghuo-ranqiong/outline/volume_map.md` 拷贝至 `tests/fixtures/`（G0.9 真实产物，G0.11 哈希镜像 MIRROR_MAP；**注**：源是活产物（卷扩展会追加卷、桥接状态会推进），生产演进后 fixture 须重新拷贝同步，G0.11 会如实拦住漂移）
2. **R2 genesis 固化 + 口径统一 + 在途 heal**：total_chapters := max(read_volume_boundaries())（=规划总章数；与 cli.py 卷扩展路径的 `new_total = max(boundaries)` 既有惯例同源）；**双写路径**——(a) genesis step 6（volume-outlining）成功钩子处由代码固化（genesis.py 成功路径，无后续步骤重写 volume_map——已核对 GENESIS_STEPS）；(b) **在途 heal**：cmd_next/cmd_resume 进入 CHAPTER_LOOP 时若 `total <= 0`，先从 volume_map 重算（边界集非空才写）再过守卫——否则已过 genesis 的存量项目（生产实证：56 章、total=None）固化钩子永不再触发，自锁原样保留，`current_chapter` 盲递增写 57…∞。`_count_total_chapters`/`_update_total_chapters` 统一收敛到 `_shared.py`（避免 cli↔genesis 循环 import；签名 `(project_dir) -> int` 走 safe_write——safe_write 为非 pipeline-cycle 依赖，模块 docstring 声明相应改为「stdlib + safe_write leaf」）。**验收**：(i) temp-dir 项目副本 genesis 流程后 novel.json.total_chapters==100；(ii) **中卷 heal**——fixture 项目副本（56 章、total=None）执行 next 后 novel.json.total_chapters==100 且 `check_triggers(55, 100).volume_boundary==True`（heal 后卷边界触发可达；第 56 章态下一个边界是 75，验收用 check_triggers(55,100) 直接断言而非跑到边界章）
3. **R3 目录内容校验 + 契约对齐**（二选一中取校验，不留静默 SKIP）：gates/g4 增目录纯检查器（幂等无副作用），**检查项按路径参数化**：snapshot 类目录（closure step 10）= 目录存在 + ≥1 产物文件 + manifest 存在（**manifest 文件名钉进 snapshot-manage SKILL 契约**（frontmatter writes 细化 + auto-generated 数据契约段，走 `just generate` 三源同步）——只钉 checker 会被 LLM 命名漂移打回：技能可写 `manifest.md`/`snapshot-manifest.json` 任一命名，closure 最后一步 G4 因命名方差 FAIL×3→ESCALATION，语义上复刻 R3 失败类；checker 对 manifest 判定放宽为「manifest 命名的条目存在」，权威命名以契约为准并与 #26 验收对齐）；非 snapshot 目录（`characters/`，triggers.py:274 卷扩展步骤）= 目录存在 + ≥1 产物文件（**无 manifest 检查**）；closure step 10 的 output_path 与 snapshot-manage 契约对齐（`snapshots/chapter-NNN/*` 解析为最终章号目录，或按契约实际产物校验目录），BOOK_CLOSURE artifact 路径同步；与 #8（F163 G4 目录参）衔接面协调注记同 M5 模式。**验收 fixture 来源**：生产 `snapshots/` 现存的是 crash_recovery 平铺格式——**不能**当 snapshot-manage 目录格式的 fixture（G0.9）；fixture 须为真实 snapshot-manage 格式产物（实现时现场产出后拷贝登记 MIRROR_MAP）。**验收**：closure step 10 在 fixture 项目 G4 PASS；`characters/` 场景（无 manifest）同 PASS
4. **R4 per-step N 语义解析表**（F245 的处置面，单一信源置于 contracts/paths.py）：`arc-N`→N=chapter//12；`stratum-N`→N=chapter//36；`volume-N`→N=边界集中 ≤chapter 的边界计数（注意：**不是** closure `_current_volume` 的 `len(boundaries)`——两者只在最后一卷的末章（ch 100）相等，任何 mid-book 章节都会错卷）；`chapter-N`→N=章号。**两个消费者都要接线**：(a) 触发步骤 G4 校验经该表解析；(b) **触发派发侧**——`run_triggered_skills`（triggers.py:561）须从同一张表构造 `{chapter, arc=chapter//12, stratum=chapter//36, volume=count(boundaries≤chapter)}` 上下文传给 `dispatch_skill`，否则 `_build_skill_prompt` 继续按章号解析契约 writes（dispatch_helper.py:653-658）——ch 60 时 prompt 指令写 `arc-60.md` 而修后 G4 查 `arc-5`，「触发不 fire」变「fire 即永久 ESCALATION」。**跨路由通道**：dispatch_skill 三路由中 legacy 子进程路由（`shenbi-dispatch <skill> <type> <dir> <prompt>`，dispatch_helper.py:1826-1865）无 kwargs 通道且在子进程内用 `extract_chapter(prompt)` 重derive——**上下文必须经 prompt 文本载体跨进程**：prompt 追加结构化行（如 `[path-context] arc=5 volume=3 for chapter 60`），**子进程侧解析点是 `dispatch()`/`dispatch_with_write_audit()`（dispatcher/executor.py:161-162/242），解析结果须流入 `derive_input_files`/`derive_output_files`（第四消费者）**——二者现只收 chapter 并对一切 N 族走 `resolve_or_skip(p, chapter)`，不接则 score-arc 的读路径 `truth/arcs/arc-N.md` 解析成 `arc-60.md` → 缺失 → G1.1 FAIL（gates/g1.py:200），且 `_audit_watch_paths`（executor.py:220-225）监视错路径（write-audit 盲区）；resolver 优先解析该行、无该行才回落现行章号提取（回落语义不变，向后兼容）。**该行是对执行 LLM 可见的刻意指令**（与 "Files to create" 清单互为印证，不剥离；注入面按 #22 线程口径视为受控前缀——机器生成、非用户内容拼接）；**`_resolve_closure_g4_path`（closure.py:148）是第三消费者**——步骤 6 经表取章号语义（F313 的接线点），不得继续对一切 N 统一按卷号替换。**验收**：chapter 60 arc 场景 G4 查 `arc-5-score.md`（非 arc-60）；**派发 prompt 含 `[path-context]` 结构化行且 "Files to create" 列 `arc-5` 路径；resolver（纯函数单测）优先解析该行、无该行回落章号提取行为不变；`derive_input_files`/`derive_output_files` 从解析行做 per-family 解析（score-arc 读路径解析为 `arc-5.md` 非 `arc-60.md`）**（不触发真实 dispatch——核心原则 8，fixtures/单测表达）；卷末章 55 volume 场景查 `volume-3-score.md`；closure step 6 G4 查 `chapter-100-long-span.md`（最终章语义）
5. **R5 显式路径解析上下文**：dispatch/prompt-build 增可选 context 参数（占位族→值；**跨子进程路由经 prompt 内 `[path-context]` 结构化行携带**（同方向 4(b)），缺省回落现行 prompt 文本提取，向后兼容）。closure per-step 表：步骤 2（memory-distill）→**最终弧号 = total_chapters//12（=8）**（ch 85-96 周期已写过 arc-8——closure L2 覆写为 85-100 综合是**预期行为**，声明之）；4/5（review-arc-payoff/score-volume）→卷号；6（review-long-span）→**最终章号**（=total_chapters，F313 同修）；10→契约目录。F3B5（genesis escalation）传入显式上下文（失败章号或 book 级哨兵）——**哨兵值须与 genesis checkpoint artifact 字符串同步**（现为 `audits/escalation-genesis-report.md`，genesis.py:260，而契约是 `escalation-N-report.md`——两处必须一致，否则人工被指向技能永不写的路径）；F380（anchor-curate）`AC-NNN` 用 genesis 表既有 book 级哨兵形态（`AC-001.md`，genesis.py:78）——**不得仅从 output_paths 剔除了事**（剔除后 "Files to create" 为空 → "No output files written" → optional 跳过原样复现），跳过须留 structlog 原因。**验收**：closure 10 步 prompt-build 全通过（fixture）；escalation 派发不抛 UnresolvedPathError；anchor-curate 真实派发（prompt 含具体 AC 路径）而非伪装 optional 跳过
6. **R6 中文节点/桥接/卷上下文提取**：`_shared` 增章节节点提取（`| 第N章 |` 表行）、桥接提取、卷头/卷目标双语识别；**三处**节点消费方全部接线去重——chapter_loop.py:2182、plan_skeleton.py:197、context_assemble.py:243（第三处内联 `chapter_node_pattern`，漏接则上下文装配路径污染原样保留）；第四处 `volume_align.extract_chapter_node`（英文 `## Chapter N` 模式，仅测试引用零生产调用方）**显式移交 #16/#25 死代码批次处置**，R6 不接线它。桥接**段级**：生产 map 有**五个** `### 跨卷桥接` 表（各卷一个）——共享提取器须**聚合全部桥接段**（现 `split(...)[1]` 只吃第一卷的表，4/5 桥接永不浮现）；段定位双语（`### 跨卷桥接` / `## Cross-Volume Bridges`），context_assemble.py:254 / plan_skeleton.py:208 切分同步。桥接**行级语义**（6 列中文表 `| # | 钩子内容 | 类型 | 带入卷 | 预期激活章 | 当前状态 |`，激活值含区间 `第26-28章` 与非数值 `展开主线`）：激活章=区间最小值；非数值行跳过 + structlog WARN；**带入卷非本书卷的行（续作行，如 vol-5 表的 `《星火燃穹》续作` + 激活 `第1章`）跳过**——判定谓词用格式法（带入卷 匹配 `^第N卷$` 才算本书卷；非该格式（书名号/续作等）即跳过），否则续作钩子从第 1 章起污染每章上下文。卷上下文：`_resolve_volume_at_runtime` 的 `Volume {i}` 命名与 context_assemble.py:226-240 的 `## Volume N`/`**Objective:**` 匹配补中文（`## 第N卷`、`**Objective**:` 冒号在粗体外）。**验收**：生产 map 第 5+ 章节点非 None 且 role/content 非桥接表垃圾；**vol-1 桥接**：激活窗内的章（如第 26 章）出现 vol-1 表桥接条目；**vol-2 桥接**：第 36 章出现 vol-2 表（激活 `第36章`）的桥接条目、第 30 章不出现；**续作行**：第 1-10 章上下文不含 vol-5 续作桥接；卷上下文块在中文项目非空
7. **F340 REJECT 重做语义**：cmd_review REJECT → 重做产生该 checkpoint 的步骤。**逐类型语义表**（CheckpointType 全成员；现 MODIFY 分支 cli.py:543-548 已有 CHAPTER_MEMO/STATE_SETTLE/GENESIS_COMPLETE 的回退游标先例，REJECT 对齐补全；CHAPTER_MEMO/STATE_SETTLE→镜像 MODIFY 既有游标回退；VOLUME_BOUNDARY→重跑卷边界步骤、ESCALATION→重跑失败步骤、PER_CHAPTER→重跑当章评审、GENESIS_COMPLETE→genesis 状态重置到最后一步重跑；BOOK_CLOSURE 已有 reject 转移（cli.py:558-563）不动——`current_step` 回退但 `skills_done` 追加不去重是无害的（该列表**无逻辑消费方**，仅 state.py 序列化读写，state.py:236/328））。**REJECT-redo 须重置该步骤的重试计数**（retry_counts + retry_budget_consumed 对应键）——否则 ESCALATION 类 redo 立即再次耗尽重抛（计数已过 max_revision_retries/max_audit_retries）。**验收**：模拟 genesis-complete reject 后 resume 重跑 step 17 而非 no-op（单测）；escalation reject-redo 后步骤获得完整重试预算再执行（单测）
8. **F341 并行分支守卫镜像**：并行 post-draft 分支（chapter_loop.py:2702 一带）镜像串行路径**完整 elif 体**（chapter_loop.py:1086-1104）：不止 `state_settle_review_required` 条件，还含 staging 自动提交（`staging/truth/*.md` → `truth/*.md` 经 safe_write）+ `clear_staging`——只镜像条件不镜像提交体，state-settle 产物会滞留 staging/ 并被下次 resume 的 `_cleanup_residual_staging` 清掉（数据丢失陷阱；该步骤 `uses_staging=True`）。**注意**：串行 elif 分支本身已 vestigial（无 ChapterStep 声明 `checkpoint=STATE_SETTLE`，step 7 被并行分支无条件拦截）——以它为**模板**把条件+提交体镜像进**并行分支**，不是复活串行路径。**验收**：--auto 并行模式不设 STATE_SETTLE checkpoint **且 truth 文件真实落盘**（单测断言 staging 清空 + truth 存在）
9. **F304 RetryExhaustedError 捕获**：捕获点放**编排函数内部**（`_orchestrate_to_checkpoint` 一级，非 cmd_next/cmd_resume 顶层）——顶层捕获会让 raise 先跳出 WriteLock 块、`save_state`（cli.py:612）不再执行，`retry_budget_consumed` 递增（chapter_loop.py:613-617/2878-2880）不落盘，crash-resume 后预算风暴延迟一整轮重现。流程：捕获 → 设 escalation checkpoint → save_state → 结构化返回。**验收**：预算耗尽路径产出 checkpoint 状态非 traceback，且 budget 计数已持久化（单测）
10. **回归**：`just check` 全绿 + 新增上述验收测试

**F303 拆分声明（设计审查 C4）**：快照子系统接线（create/restore/prune 零调用方、step 15 空转、crash_recovery.py 平行实现并存）是三路设计决策（接线三件套 vs 移除死代码 vs 维持 cli rollback 延迟），无法在本 spec 一行方向化——拆为独立 spec **#26（snapshot-subsystem-wiring）**，INDEX 已登记；本 spec 不再包含 F303。

## 测试分层与 fixture 来源（I4）
- R1/R6 → T1 单测（真实 fixture + 负面断言）
- R2/F340/F341/F304 → T1/T2（temp-dir 项目副本 / 状态机单测，禁写 tracked 生产目录）
- R3/R4/R5 → fixture 项目副本上 G4 CLI 级检查
- 全部纳入 `just check`；评分场景（若有）走 G3.4 独立子 agent，dispatcher 自评无效
