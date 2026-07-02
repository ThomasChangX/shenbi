# Novel Pipeline 根因修复 Spec

> **日期:** 2026-07-02
> **状态:** 设计中
> **前置:** `docs/superpowers/specs/2026-07-01-novel-pipeline-design.md` (原始 spec), 2026-07-02-novel-pipeline-wave{1..5} (已完成实施), commit `beea410`
> **目的:** 对 Pipeline 首次完整实施中发现的所有正确性缺陷、健壮性缺口、测试覆盖盲点和代码债务进行根因修复

## 1. 背景

Pipeline 首次实施 (Wave 1-5) 已完成：32 个 SDD 任务 + 最终全分支审查 + 7 个审查修复提交。当前状态：

- **19 个 pipeline 模块**, 510 个 pipeline 单元测试, 2013+ 完整测试套件通过
- 所有 pre-commit 钩子绿色 (ruff, mypy, basedpyright strict, purity lint, contract checks)
- Spec §15 验收标准: 17/20 通过, 3 个 Partial

本 spec 覆盖剩余的所有已发现问题，按根因分类组织，确保修复后的 Pipeline 能正确执行端到端流程。

## 2. 问题清单

### 2.1 Category A: 正确性缺陷 (阻塞性)

Pipeline 在当前状态下无法可靠完成多卷长篇小说的端到端生成。以下 8 个缺陷是根因。

#### A1. total_chapters 动态重算缺失

- **Spec 引用:** §4.2 [I3], §6.5, §15 item 8
- **当前状态:** `total_chapters` 由 genesis step 6 (volume-outlining) 一次性写入 `novel.json`。卷边界扩展 (§6.5) 运行了 character-design expand / faction-builder / location-builder / foreshadowing-plant / plot-thread-weaver，但**没有任何步骤重新计算并更新 `total_chapters`**。
- **根因:** `triggers.py` 的 `run_triggered_skills` 完成卷边界扩展后，没有后处理步骤读取更新后的 `volume_map.md` 并重算总章节数。
- **影响:** 如果 volume-outlining 的初始估算与实际扩展后的章节数不同，chapter-loop 的终止条件 (`N == total_chapters`) 会出错——少则提前终止导致 closure 缺失内容，多则无限循环。
- **验收标准:** 卷边界扩展完成后，`novel.json.total_chapters` 被重新计算为 `volume_map.md` 中所有卷的章节数之和。

#### A2. resonance 评分解析器缺失

- **Spec 引用:** §6.3, §6.4
- **当前状态:** `check_resonance` 函数已接入 chapter_loop (`_route_revision_after_resonance`)，但 `cs.resonance_score` 始终为 `None`。没有任何代码从 review-resonance 的产出 (`audits/chapter-N-resonance.md`) 中提取分数。
- **根因:** 缺少一个解析器函数从 resonance 审计报告中提取分数并写入 `ChapterState.resonance_score`。
- **影响:** 共振阈值检查空转——无论实际评分如何，`check_resonance(None, floor)` 永远返回 `True`，低于全局地板的章节不会被标记。
- **验收标准:** review-resonance dispatch 后，resonance 分数被提取并写入 `ChapterState.resonance_score`；`check_resonance` 使用真实分数进行判断。

#### A3. genre-config 审计维度键名不匹配

- **Spec 引用:** §6.2
- **当前状态:** `audit_layer.py` 的 `GENRE_ACTIVATION_MATRIX` 使用 snake_case 键 (`era`, `world_rules`, `sensitivity`, `dialogue_focus` 等)，读取 `genre_config["audit_dimensions"]`。但实际的 `genre-config.json` (由 shenbi-genre-config 产出) 使用 camelCase 键名 `auditDimensions`，且键名集不同。
- **不匹配详情:**
  - 仅有 2/9 个矩阵键能匹配 fixture: `sensitivity` 和 `worldRules` (需大小写归一)
  - 7/9 个矩阵键在 fixture 中无对应: `era`, `fanfic`, `dialogue_focus`, `motivation_focus`, `texture_focus`, `reader_pull_focus`, `highpoint_focus`
  - 8 个 fixture 键在矩阵中无对应: `antiAi`, `character`, `motivation`, `pacing`, `continuity`, `foreshadowing`, `dialogue`, `texture`
- **根因:** spec §6.2 设计的审计矩阵与实际 genre-config skill 产出的字段结构完全不同。这不是命名风格差异，而是语义集合差异。
- **影响:** 题材审计圈在任何真实运行中激活 0 个审计维度 (因为顶层键名 `auditDimensions` 不等于 `audit_dimensions` 也会导致 `.get()` 返回空 dict)。
- **验收标准:** 审计矩阵能正确读取 genre-config.json 的 `auditDimensions` 字段，并基于真实 fixture 的键名激活正确的审计 skill。

#### A4. escalation-review dispatch 未接线

- **Spec 引用:** §6.3, §11, §15 item 14
- **当前状态:** `dispatch_escalation` 函数在 `revision_router.py` 中已实现且有单元测试，但 orchestrator 在重试耗尽时直接设 `ESCALATION` checkpoint，**跳过了 dispatch escalation-review 这一步**。
- **根因:** `_handle_failure` (genesis) 和 `_handle_failure` (chapter_loop) 在 `handle_dispatch_failure` 返回 `False` 后，直接 `set_checkpoint(state, CheckpointType.ESCALATION, ...)`，没有先调用 `dispatch_escalation`。
- **影响:** 升级决策没有 escalation-review 的分析报告支撑，人工审核者只能看到 "dispatch failed 3 times" 而无上下文。
- **验收标准:** 重试耗尽后，先 dispatch `shenbi-escalation-review` 生成 `audits/escalation-N-report.md`，然后设 checkpoint 展示该报告。

#### A5. error_handler 三个函数未接线

- **Spec 引用:** §11
- **当前状态:** `handle_audit_blocking`、`handle_scoring_failure`、`handle_state_settle_failure` 已实现且有测试，但从未从 orchestrator 调用。
- **根因:** chapter_loop 没有审计 BLOCKING 的重试循环 (§6.3 "审计BLOCKING: revision闭环最多3次")；scoring 失败没有按 exit code 分流 (§11 "exit code 2: 重新 dispatch, exit code 3: 先跑 G4")；state-settling 失败没有标记 `settling_failed` 并暂停。
- **影响:** 审计 BLOCKING 不触发 revision 闭环 (直接跳过)；scoring exit code 不被检查；state-settling 失败被当作普通 dispatch 失败处理。
- **验收标准:** 三个函数被正确接入 orchestrator 的失败处理路径，实现 §11 描述的完整重试/升级/暂停逻辑。

#### A6. modify 决策与 approve 行为完全相同

- **Spec 引用:** §2.7, §9.1
- **当前状态:** `cmd_review` 对 `MODIFY` 和 `APPROVE` 执行完全相同的 staging commit。Feedback 被记录在 `checkpoint_history` 但从未被使用。
- **根因:** Spec 说 modify 应该 "feedback 传给 skill, skill 重新写入 staging/, 重新审核"。但当前实现把 modify 当作 approve + 附带 feedback 记录。
- **影响:** 人工修改反馈被静默丢弃，skill 不会被重新 dispatch 来整合修改。
- **验收标准:** `modify` 将 feedback 传入，设置状态使下一步重新 dispatch 对应 skill (不 commit staging)；或至少标记 "modify_pending" 使 orchestrator 在 resume 时知道需要重新执行。

#### A7. state-settling G4 验证为空操作

- **Spec 引用:** §6.1 step 5, §18
- **当前状态:** state-settling step 的 `output_path` 为空字符串，G4 收到空文件列表，直接返回 PASS/SKIP。
- **根因:** state-settling 写入 `staging/truth/*.md` (动态多个文件)，orchestrator 无法预知文件列表。
- **影响:** state-settling 产出没有结构验证，格式错误的 truth 文件变更不会被 G4 拦截。
- **验收标准:** state-settling step 的 G4 验证 staging 目录下的 truth 文件 (glob `staging/truth/*.md`)，而非空列表。

#### A8. 审计 BLOCKING 即时停止 + genre 圈接线

- **Spec 引用:** §6.2
- **当前状态:** chapter_loop 的 audit step (`TODO(W3T4)`) 从未调用 `run_audit_layer`。BLOCKING 审计发现不触发即时停止。
- **根因:** W3T4 实现了 `audit_layer.py` 模块但 W3T3 的 chapter_loop 中的 `TODO(W3T4)` 标记从未被替换为实际调用。
- **影响:** 题材审计圈和边界审计圈完全不运行；BLOCKING 发现不停止 chapter。
- **验收标准:** chapter_loop step 8 后调用 `run_audit_layer`；BLOCKING 发现时停止当前 chapter 并进入 revision 闭环。

### 2.2 Category B: 健壮性增强

#### B1. Ramp-up G1 可选读取过滤

- **Spec 引用:** §17
- **当前状态:** `dispatch_helper.py` 没有 ramp-up skip 逻辑。Skills 在自己的 SKILL.md 中声明容忍缺失文件。
- **影响:** 严格 G1 在 ramp-up 章节可能报假阳性失败。
- **验收标准:** dispatch 前解析 contract reads，移除标记为 optional 或含 `N` 模板变量且在当前阶段尚不存在的路径。

#### B2. Resume truth 完整性校验

- **Spec 引用:** §3.4, 设计决策 #13, §15 item 18
- **当前状态:** `cmd_resume` 直接重入 orchestration loop，无专门完整性扫描。
- **影响:** 缺失的 truth 文件在下一次 step 的 G1 中才被发现。更严重的是，如果 dispatch 中途崩溃导致部分写入 (文件存在但内容损坏)，G1 不会发现内容损坏。
- **方案:**
  1. **存在性检查**: resume 时对下一步的 contract reads 做 G1 扫描
  2. **Checksum 对比** (设计决策 #13): 读取 `state.last_snapshot` 中的 `checksums` 字段 (一个 `dict[str, str]` 映射 truth file 相对路径到 SHA256)。对比当前 truth files 的实际 SHA256:
     - 一致: 正常恢复
     - 不一致: 标记 `needs_truth_sync = True`，暂停等待人工 truth-sync
  3. **首次 resume 跳过路径:** 如果 `state.last_snapshot` 为空 dict 或不含 `checksums` 键 (首次 resume，genesis 后无快照)，跳过 checksum 检查，仅做存在性检查
  4. **checksum manifest 写入:** `snapshot-manage` skill 在创建快照时写入 checksum manifest 到 `state.last_snapshot["checksums"]`。pipeline 的 snapshot 步骤 dispatch 后，读取 `snapshot-manifest.json` 并更新 state。如果 snapshot-manifest.json 不存在 (skill 未产出)，日志 warning 并跳过 checksum 更新。
- **验收标准:** resume 时对比 truth files checksum；不一致时触发 truth-sync 而非静默继续。

#### B3. truth-sync 传播标记 after modify

- **Spec 引用:** §9.2 ("truth-sync 的冲突必须经人工仲裁")
- **当前状态:** Staging commit 工作，但 derived truth 文件不会级联更新。人工修改反馈被静默丢弃。
- **影响:** 人工修改的 truth 变更可能不会传播到派生文件。
- **方案:** 遵循 §9.2 的"人工仲裁"原则，**不自动 re-dispatch**:
  1. modify 时在 `PipelineState` 中标记 `needs_truth_sync: true` 和受影响的 truth 文件列表
  2. 下次 `cmd_status` 输出中显示 "truth_sync_needed" 警告
  3. 人工决定是否运行 truth-sync (spec 说"冲突必须经人工仲裁")
  4. truth-sync 完成后人工清除标记
- **验收标准:** modify 后 state 标记 needs_truth_sync；status 命令显示警告；不自动 re-dispatch。

#### B4. requires_independent 改为 fail-closed

- **Spec 引用:** §2.6
- **当前状态:** `requires_independent` 在任何异常时返回 `False` (fail-open)，跳过 G3。
- **影响:** 对于 `requires_independent_agent: true` 的 skill，G3 独立性检查可能被意外跳过。
- **方案:** 不使用硬编码的 skill 列表。`requires_independent()` 已读取 contract 的 `requires_independent_agent` 标志。修复方式：try 块中调用 requires_independent_agent(skill)；如果抛异常，except 块直接返回 True (fail-closed) — 不重新读取 contract。无法确定独立性时假设需要独立，符合 §14 设计决策 #6。
- **验收标准:** 任何 contract 声明 `requires_independent_agent: true` 的 skill 在异常时返回 `True` (fail-closed)。

#### B5. reject 后 step_index 重置

- **Spec 引用:** §9.1
- **当前状态:** Rejected checkpoint 清空 staging 但 advance 到下一步，而非重新执行被 reject 的 step。
- **影响:** Reject 语义不对——应该重做该步骤，而非跳过。
- **方案:** Reject 时根据当前 phase 重置对应的状态游标:
  - Genesis phase: 重置 `genesis.current_step = 0` 并清空 `genesis.skills_done` (全阶段重启)
  - Chapter-loop phase: 重置 `chapter_loop.step_index` 到 checkpoint 对应的 step index (精确回退)
  - Closure phase: 重置 `closure_step = 0` 并清空 `closure_skills_done` (全阶段重启)
- **设计说明:** Genesis/closure reject 是全阶段重启 (设计决定 — reject 语义是"从头重做")；chapter-loop reject 使用 `_checkpoint_to_step_index(cp)` 精确回退到 checkpoint 对应步骤。
- **验收标准:** Reject 时根据 phase 正确重置状态游标，使 resume 时重新执行。

### 2.3 Category C: 测试覆盖补全

#### C1. Route B 三个 CLI main() 冒烟测试

- **当前状态:** `pipeline-truth-index`、`pipeline-truth-embed`、`pipeline-context-assemble` 的 main() 函数零测试覆盖。
- **验收标准:** 每个 CLI main() 至少一个冒烟测试：invoke `main([...])`, assert exit code 0 和 JSON 输出。

#### C2. dispatch chain 端到端集成测试

- **当前状态:** 所有 dispatch 测试 mock 了 `subprocess.run`，没有验证 `dispatch_skill` 到 dispatcher CLI 到 `dispatch_with_write_audit` 的完整路径。
- **验收标准:** 一个集成测试运行 `dispatch_skill` 对一个最小 fixture skill，验证 returncode == 0。

#### C3. Route B 向量维度修复

- **当前状态:** `test_route_b_search_works_with_stored_embeddings` 存储了 3-float 向量，但 `bge-large-zh` 产出 1024 维。`search_cosine` 静默跳过维度不匹配的 chunk，测试不实际验证 cosine 排序。
- **验收标准:** 测试使用与模型一致维度的向量，或重命名测试以准确描述其验证内容。

#### C4. Closure post-approval 完整路径测试

- **当前状态:** Closure 测试覆盖了 pre-checkpoint 暂停，但 post-approval (step 10 snapshot 到 completed) 路径仅在单元测试中覆盖。
- **验收标准:** 一个集成测试验证 book-closure approve 后 resume 到 snapshot-manage dispatch 再到 closure:completed 完整路径。

#### C5. cmd_next vs cmd_resume checkpoint 后行为测试

- **当前状态:** 用户在 checkpoint approve 后调用 `cmd_next` 而非 `cmd_resume` 的行为未测试。
- **验收标准:** 测试验证 `cmd_next` 在 checkpoint pending 时返回 `BLOCKED`，在 checkpoint cleared 后正确推进。

#### C6. 审计 BLOCKING revision 闭环端到端测试

- **当前状态:** 无测试覆盖 BLOCKING -> revision -> re-audit -> pass/fail/escalation 的完整循环。
- **验收标准:** 集成测试验证:
  1. 审计发现 BLOCKING -> step_index 回退到 revision -> chapter-revision 重新 dispatch
  2. Re-audit 后 BLOCKING 消失 -> 正常推进
  3. Re-audit 后仍 BLOCKING 且未超限 -> 再次 revision
  4. 超过 max_audit_retries -> escalation checkpoint
  5. Escalation checkpoint 展示 escalation-report

### 2.4 Category D: 代码清理

#### D1. _gate_passed 提取为共享工具

- **当前状态:** `_gate_passed` 在 **5 个文件**中各有一份副本: `chapter_loop.py`、`audit_layer.py`、`closure.py`、`genesis.py`、`triggers.py`。注意 `triggers.py` 的变体接受 `PASS` 和 `SKIP` (使用 `status in (GateStatus.PASS, GateStatus.SKIP)`)，其他四个仅接受 `PASS`。提取时必须处理这个语义差异。
- **方案:** 提取为 `dispatch_helper.py` 中的 `gate_passed(result, allow_skip=False)`，默认 `allow_skip=False`。`triggers.py` 调用时传 `allow_skip=True`。
- **修改文件:** `dispatch_helper.py` (新增), `chapter_loop.py`, `audit_layer.py`, `closure.py`, `genesis.py`, `triggers.py` (全部替换为 import)
- **验收标准:** 5 个文件统一使用共享实现；triggers.py 的 SKIP 语义通过参数保留。

#### D2. MAX_DISPATCH_RETRIES / MAX_AUDIT_RETRIES 常量连接

- **当前状态:** 这两个常量存在于 `error_handler.py` 但不被逻辑读取 (逻辑读 `state.config` 的值)。常量仅被测试断言。
- **方案:** 将常量移到 `state.py` 的 `PipelineConfig` 模块级别作为 `DEFAULT_MAX_DISPATCH_RETRIES = 3` 和 `DEFAULT_MAX_AUDIT_RETRIES = 3`。`PipelineConfig` 的 `max_revision_retries` 和 `max_audit_retries` 字段使用这些常量作为默认值。`error_handler.py` 从 `state.py` 导入。消除循环依赖，保持 spec §11 的值文档化。
- **验收标准:** 常量从 PipelineConfig 默认值派生；error_handler 导入而非重复定义。

#### D3. arc-payoff / spinoff 死条目注释

- **当前状态:** `BOUNDARY_TRIGGERS` 中这两个条目的 lambda 永远返回 `False`，读者可能期望它们工作。
- **验收标准:** 添加行内注释说明 "由 chapter_loop 在卷边界/衍生标记时激活"。

#### D4. dispatch prompt 上下文增强

- **当前状态:** Genesis/chapter_loop 的 dispatch prompt 仅包含 `f"Execute {step.skill}. Project dir: {project_dir}"`。
- **验收标准:** 添加注释说明上下文注入是 dispatcher 的职责；或在 dispatch_helper 中增强 prompt 构建逻辑 (传递 mode、chapter number 等)。

## 3. 修复方案

### 3.1 架构原则

所有修复遵循现有 Pipeline 的设计模式：
- Python 3.11+, `from __future__ import annotations`
- `pathlib.Path` for I/O, `json` for structured output
- `safe_write` for all state writes
- structlog for logging (no `print()`)
- `StrEnum` for typed enums
- Tests in `tests/unit/pipeline/`
- Conventional Commits

### 3.2 修复优先级与依赖

```
Phase 1 (正确性阻塞): A3 -> A8 -> A5 -> A4 -> A1 -> A2 -> A6 -> A7
Phase 2 (健壮性):     B1, B2, B3, B4, B5 (相互独立)
Phase 3 (测试补全):   C1, C2, C3, C4, C5 (相互独立)
Phase 4 (代码清理):   D1, D2, D3, D4 (相互独立)
```

Phase 1 内的依赖链:
- A3 (genre-config 对齐) 必须先于 A8 (审计接线)，因为 A8 需要 genre 圈能正确激活
- A8 (审计接线) 必须先于 A5 (error_handler 接线)，因为 A5 的 `handle_audit_blocking` 依赖审计结果
- A5 必须先于 A4 (escalation 接线)，因为 escalation 是 audit blocking 重试耗尽后的路径
- A1 (total_chapters) 和 A2 (resonance parser) 相互独立，可与 A8/A5/A4 并行
- A6 (modify) 和 A7 (state-settle G4) 相互独立

### 3.3 各修复的技术方案

#### A3: genre-config 审计维度对齐

**方案:** 重写 `GENRE_ACTIVATION_MATRIX` 以匹配真实 genre-config.json 的字段结构。

真实 genre-config.json 使用:
- 顶层键: `auditDimensions` (camelCase)
- 维度键: `antiAi`, `character`, `motivation`, `pacing`, `continuity`, `foreshadowing`, `sensitivity`, `worldRules`, `dialogue`, `texture`

映射关系 (fixture键 到 review skill):
- `antiAi` -> 已在 core circle (review-anti-ai)，**不在 genre circle**
- `character` -> 已在 core circle，**不在 genre circle**
- `motivation` -> `shenbi-review-motivation`
- `pacing` -> 已在 core circle，**不在 genre circle**
- `continuity` -> 已在 core circle，**不在 genre circle**
- `foreshadowing` -> 已在 core circle，**不在 genre circle**
- `sensitivity` -> `shenbi-review-sensitivity`
- `worldRules` -> `shenbi-review-world-rules`
- `dialogue` -> `shenbi-review-dialogue`
- `texture` -> `shenbi-review-texture`

额外需要新增的 genre-config 维度 (spec §6.2 提到但 fixture 尚未产出):
- `era` -> `shenbi-review-era` (条件: 题材含历史/年代标签)
- `fanfic` -> `shenbi-review-fanfic` (条件: novel.json is_fanfic = true)
- `readerPull` -> `shenbi-review-reader-pull`
- `highpoint` -> `shenbi-review-highpoint`

**修改文件:** `src/shenbi/pipeline/audit_layer.py`, `tests/unit/pipeline/test_audit_layer.py`

#### A8: 审计 BLOCKING 即时停止 + genre 圈接线

**方案:**
1. 在 `chapter_loop.py` 中替换 `TODO(W3T4)` 为实际调用 `run_audit_layer`
2. 审计完成后检查 `audit_result.blocking_found`
3. 如果 BLOCKING: 进入 **inline revision 闭环** (不使用 step_index 回退):

   **Inline revision loop (在 `run_chapter_step` 内部):**
   ```python
   if audit_result.blocking_found:
       while cs.audit_retry_count < state.config.max_audit_retries:
           cs.audit_retry_count += 1
           log.info("audit_blocking_revision", chapter=chapter,
                    retry=cs.audit_retry_count)
           # Dispatch chapter-revision
           result = dispatch_skill("shenbi-chapter-revision", project_dir, prompt)
           if not result.success:
               break
           # Re-run audit layer inline
           audit_result = run_audit_layer(project_dir, chapter, gc)
           if not audit_result.blocking_found:
               break  # Fixed!
       if audit_result.blocking_found:
           # Max retries exhausted -> escalation (A4)
           from shenbi.pipeline.revision_router import dispatch_escalation
           dispatch_escalation(project_dir, chapter)
           set_checkpoint(state, CheckpointType.ESCALATION, chapter=chapter,
                          artifact=f"audits/escalation-{chapter}-report.md")
           return True  # checkpoint raised
   ```
   This approach calls `run_audit_layer` directly after revision, avoiding the
   linear step ordering paradox (audit steps 10-16 are behind revision step 18).

4. 如果无 BLOCKING: 正常推进到 review-resonance (step 9)

**为什么不用 step_index 回退:** CHAPTER_STEPS 中审计圈 (steps 10-16, indices 9-15)
在 revision step (step 18, index 17) 之前。step_index 回退到 revision 后，
无法重新到达审计步骤——审计在 revision 前面。inline loop 直接在 step 处理函数内
调用 `run_audit_layer`，绕过线性游标问题。

**修改文件:** `src/shenbi/pipeline/chapter_loop.py`, `src/shenbi/pipeline/state.py` (audit_retry_count), `tests/unit/pipeline/test_chapter_loop.py`

#### A5: error_handler 三函数接线

**方案:**
1. `handle_audit_blocking`: 在 chapter_loop 的审计 BLOCKING 路径调用 (依赖 A8)
2. `handle_scoring_failure`: 在 review-resonance dispatch 后，从 `dispatch_result.returncode` 获取 exit code，调用 `handle_scoring_failure(state, dispatch_result.returncode)`:
   - exit code 2 -> re-dispatch (G3 重验)
   - exit code 3 -> 先跑 G4 再 re-dispatch
   - 其他 -> 标准失败处理 (`_handle_failure`)
3. `handle_state_settle_failure`: 在 state-settling dispatch 失败时调用 -> 标记 `settling_failed`, 设 checkpoint 暂停

**注意 (审查修复):** `handle_audit_blocking` 的实际签名是 `(state, chapter, revision_count)` (三个参数)。A8 的 inline loop 不直接调用它，而是内联了等价的重试逻辑。如果需要调用它，使用 `handle_audit_blocking(state, chapter, cs.audit_retry_count)`。

**修改文件:** `src/shenbi/pipeline/chapter_loop.py`, `src/shenbi/pipeline/error_handler.py`, `tests/unit/pipeline/test_chapter_loop.py`, `tests/unit/pipeline/test_error_handler.py`

**修改文件:** `src/shenbi/pipeline/chapter_loop.py`, `src/shenbi/pipeline/error_handler.py`

#### A4: escalation-review dispatch 接线

**方案:** 在 `_handle_failure` (genesis + chapter_loop + closure) 中，当 `handle_dispatch_failure` 返回 `False` 时:
1. 先调用 `dispatch_escalation(project_dir, chapter)` 生成 `audits/escalation-N-report.md`
   - **注意签名:** `dispatch_escalation(project_dir: Path | str, chapter: int, context: str = "")` — 不接受 state 参数
2. 然后 `set_checkpoint(state, CheckpointType.ESCALATION, ...)` 展示该报告

**修改文件:** `src/shenbi/pipeline/genesis.py`, `src/shenbi/pipeline/chapter_loop.py`, `src/shenbi/pipeline/closure.py`, `tests/unit/pipeline/test_genesis.py`, `tests/unit/pipeline/test_chapter_loop.py`, `tests/unit/pipeline/test_closure.py`

#### A1: total_chapters 动态重算

**方案:** 在 `triggers.py` 的 `run_triggered_skills` 中，卷边界扩展步骤完成后:
1. 读取 `outline/volume_map.md`
2. 计算所有卷的章节数之和
3. 如果与当前 `novel.json.total_chapters` 不同，更新 `novel.json`
4. 日志记录更新

**修改文件:** `src/shenbi/pipeline/triggers.py`, `tests/unit/pipeline/test_triggers.py`

#### A2: resonance 评分解析器

**方案:** 在 `chapter_loop.py` 的 review-resonance step 完成后:
1. 读取 `audits/chapter-N-resonance.md`
2. 用正则提取分数 (匹配 `resonance_score: NN` 或 `共振分数: NN` 或 JSON frontmatter)
3. 写入 `ChapterState.resonance_score`
4. `check_resonance` 使用真实分数

**修改文件:** `src/shenbi/pipeline/chapter_loop.py`, `src/shenbi/pipeline/revision_router.py`

#### A6: modify 决策行为修正

**方案:** `cmd_review` 的 `MODIFY` 分支遵循 spec §2.7 的完整 modify 语义:

1. **不** commit staging (与 approve 不同)
2. **清除当前 staging 内容** (skill 将重新生成)
2b. 设置 `state.needs_truth_sync = True` 和 `state.needs_truth_sync_files` (B3 集成)
3. 在 `PipelineState` 中新增 `modify_feedback: str | None` 字段和 `modify_pending_step: int | None` 字段
4. 将 feedback 文件内容写入 `state.modify_feedback`
5. 设置 `state.modify_pending_step` 为 checkpoint 对应的 step number
6. 重置 `step_index` 到该 step (使 resume 时从该 step 重新执行)
7. `cmd_resume` / `_orchestrate_to_checkpoint` 检测到 `modify_pending_step is not None` 时:
   - 将 `state.modify_feedback` 注入到该 step 的 dispatch prompt 中 (追加到 prompt 末尾)
   - dispatch 完成后清除 `modify_feedback` 和 `modify_pending_step`
8. skill 重新执行，将新产出写入 staging，重新暂停为 checkpoint

**修改文件:** `src/shenbi/pipeline/cli.py`, `src/shenbi/pipeline/state.py`, `src/shenbi/pipeline/chapter_loop.py` (dispatch prompt 构建), `src/shenbi/pipeline/genesis.py` (同上)

#### A7: state-settling G4 目录验证

**方案:** 修改 `chapter_loop.py` 中 state-settling step 的 G4 调用:
1. 不传 `output_path` (空)
2. 改为在 dispatch 后 glob `staging/truth/*.md` 获取文件列表
3. 将实际文件列表传给 `run_gate_g4`

**修改文件:** `src/shenbi/pipeline/chapter_loop.py`

#### B1-B5, C1-C5, D1-D4

各方案已在 §2.2-§2.4 中描述，实现时遵循标准 TDD 流程。

## 4. 验收标准

修复完成后必须满足:

1. **§15 全部 20 条验收标准 Pass** (当前 3 个 Partial 全部消除)
2. **端到端集成测试**覆盖以下完整路径:
   - init -> genesis (17 steps) -> checkpoint -> approve -> chapter-loop (ch1-ch3) -> closure -> book-closure checkpoint
   - BLOCKING 审计 -> revision 闭环 -> re-audit -> pass
   - Volume boundary -> expansion -> total_chapters update -> checkpoint -> snapshot
   - Resonance below floor -> revision routing -> escalation
3. **批判性审核通过**: 全分支审查关注流程正确性和一致性，无 Critical/Important 发现
4. **所有 pre-commit 钩子绿色**
5. **Pipeline 测试数 >= 600** (当前 510)

## 5. 批判性审核要求

修复完成后，执行一次高精度批判性全分支审核，重点关注:

1. **状态一致性**: 所有可能的状态转换路径是否都保持 pipeline-state.json 的完整性？是否存在中间状态丢失或状态不一致的场景？
2. **流程正确性**: genesis -> chapter-loop -> closure 的完整流程是否能正确执行？每个 phase 的 entry/exit 条件是否完备？
3. **错误恢复完整性**: 所有失败路径 (dispatch fail, gate fail, audit BLOCKING, scoring fail, state-settle fail) 是否都有明确的恢复策略 (retry/escalate/pause)？
4. **并发安全**: WriteLock/ReadLock 的使用是否覆盖了所有状态读写路径？
5. **跨模块接口一致性**: 模块间的函数签名、返回类型、数据格式是否一致？是否有隐式假设？

审核由独立 subagent 执行，使用最 capable 的模型，生成 review package 覆盖全分支 diff。

## 6. 非目标

- 不实现 web UI
- 不修改 69 个 skill 的核心逻辑 (仅修改 pipeline 编排层)
- 不优化性能 (Route B O(n) cosine search 等)
- 不实现 rollback 的完整 truth-sync (仅标记 UNVERIFIED)
- 不实现 genesis modify 的依赖重算 (§3.1 "依赖重算 基于 contract writes→reads 图") — `pipeline.dependency_graph` 模块 (§13) 从未实现，独立子系统，不在本 spec 范围

## 7. 补充：逐任务审查遗漏项

以下 22 个发现来自 Wave 1-5 的 per-task 审查，在初版 spec 中遗漏，现补入。

### 7.1 Category E: 补充正确性缺陷

#### E1. _route_b 错误路径 SQLite 连接泄漏

- **来源:** W2T3 最终审查
- **当前状态:** `context_assemble.py:153-155` 中 `store.close()` 在 try 块内，但 broad `except Exception` (line 169) 不关闭 store。如果 `search_cosine` 在 `EmbeddingStore(db_path)` 之后、`store.close()` 之前抛异常，SQLite 连接泄漏。
- **根因:** 缺少 try/finally 或 with-context 包裹 store 生命周期。
- **影响:** 每次查询时的异常路径泄漏一个 SQLite 连接，长期运行后耗尽连接池。
- **修改文件:** `src/shenbi/pipeline/context_assemble.py`
- **验收标准:** `store.close()` 在任何异常路径中都被调用 (try/finally 或 context manager)。

#### E2. clear_checkpoint 不幂等

- **来源:** W1T2 审查
- **当前状态:** `machine.py:69` 的 `clear_checkpoint` 在 checkpoint 已为 NONE 时调用，仍追加 `{"type": "none"}` 记录到 history。
- **根因:** 缺少 guard `if cp.type == CheckpointType.NONE: return`。
- **影响:** checkpoint_history 被伪记录污染，下游消费者 (如 audit) 可能误判。
- **修改文件:** `src/shenbi/pipeline/machine.py`
- **验收标准:** checkpoint 已为 NONE 时 clear_checkpoint 是 no-op，不追加 history。

#### E3. --feedback 文件不存在时未捕获 FileNotFoundError

- **来源:** W1T6 审查 (finding #5)
- **当前状态:** `cli.py:348` 的 `Path(args.feedback).read_text(encoding="utf-8")` 不在 try/except 内。错误的 feedback 文件路径产生 traceback 而非 `{"status": "error"}` envelope。
- **根因:** 缺少 try/except 包裹。
- **影响:** 用户看到误导性的 "project not found" 错误消息 (被外层 `except FileNotFoundError` 捕获)，而非明确的 "feedback file not found" 消息。
- **修改文件:** `src/shenbi/pipeline/cli.py`
- **验收标准:** feedback 文件不存在时返回 `{"status": "error", "message": "feedback file not found: ..."}` 和 exit code 1。

#### E4. cmd_rollback 是非功能 stub

- **来源:** W1T6 (设计阶段即知)
- **当前状态:** `cli.py:519` 返回 `"not_implemented"` + exit code 0。无项目验证、无快照恢复、无 truth-sync。
- **根因:** 整个回滚功能未实现。snapshot 基础设施 (W4T3) 已就绪，但 rollback 命令未接线。
- **影响:** spec §2.2 定义了 `pipeline rollback <project-dir> --chapter <N>` 作为破坏性操作命令，用户无法回滚。
- **决策:** 标记为**非目标** (本 spec 不实现完整回滚)，但修复以下三点：
  1. exit code 改为非零 (1 而非 0)
  2. 添加项目验证 (load_state，不存在则报错)
  3. 更新 stub 消息 (移除过期的 "Wave 3/4" 引用)
- **修改文件:** `src/shenbi/pipeline/cli.py`

#### E5. extract_entities_from_plan 返回顺序不确定

- **来源:** W2T1 审查 (finding #3)
- **当前状态:** `truth_index.py` 的 `extract_entities_from_plan` 中 characters/rules 从 set 转为 list，跨 Python 运行顺序不确定。
- **根因:** 缺少 `sorted()` 排序。
- **影响:** 下游消费者和测试断言可能不稳定。
- **修改文件:** `src/shenbi/pipeline/truth_index.py`
- **验收标准:** 返回的 characters/rules 列表是 `sorted()` 的。

#### E6. 审计 BLOCKING 重试耗尽后缺少版本回退

- **来源:** §6.3 spec
- **当前状态:** spec §6.3 说 "3 次失败 → 回退最佳版本 → escalation checkpoint"。回退未实现。
- **根因:** 缺少 "最佳版本" 的选择逻辑和快照恢复调用。
- **影响:** escalation 时没有回退到之前通过审计的版本，章节停留在最后一次失败的状态。
- **决策:** 标记为**非目标** (完整 rollback 是 E4 的范畴)。在 A5 的 escalation 路径中添加日志标记 "version_rollback_not_implemented"。

### 7.2 Category F: 补充测试缺口

#### F1. ChapterState 序列化往返未测试

- **来源:** W1T1 审查
- **当前状态:** `chapter_states` 是 `to_dict`/`from_dict` 中最复杂的嵌套 dict 分支，但测试从不填充它。
- **验收标准:** 添加测试：构造包含多个 chapter_states 的 PipelineState，往返后验证完整性。

#### F2. Checkpoint options/context 往返未断言

- **来源:** W1T1 审查
- **当前状态:** 测试构造了 `CheckpointData(context="Review memo", options=["approve","modify","reject"])` 但仅断言 type/chapter/artifact。
- **验收标准:** 往返后断言 `context` 和 `options` 字段。

#### F3. PipelineConfig 完整往返未测试

- **来源:** W1T1 审查
- **当前状态:** 12 个 config 字段中仅 2 个 (max_revision_retries, resonance_global_floor) 被往返测试。
- **验收标准:** 往返后断言全部 12 个 config 字段。

#### F4. test_save_is_atomic docstring 承诺过度

- **来源:** W1T2 审查
- **当前状态:** docstring 说 "no partial writes on crash" 但仅检查 `json.loads(content)` 成功。
- **验收标准:** 重命名为 `test_save_writes_valid_json` 或添加真正的原子性断言 (如检查无 .tmp 文件残留)。

#### F5. embed_and_store 成功路径零覆盖

- **来源:** W2T2 审查
- **当前状态:** `embed_and_store` 中调用 `model.encode()` 的代码路径从未被测试 (因为 model 是可选依赖)。
- **验收标准:** 使用 mock model 注入测试 encode → store → search 的完整路径。

#### F6. G4 调用参数未验证

- **来源:** W3T2 审查 (finding #5)
- **当前状态:** `test_runs_step_g4_and_advances` 使用 `mock_g4.assert_called_once()` 但不检查参数。
- **验收标准:** 使用 `assert_called_with(skill, [output_path], project_dir)` 验证 G4 接收正确的文件路径。

#### F7. genesis phase transition 后 save_state 缺失

- **来源:** 最终审查 (finding M4)
- **当前状态:** `cli.py` 中 `transition_genesis_to_chapter_loop(state)` 后不调用 `save_state` 就进入 `_orchestrate_to_checkpoint`。如果 orchestration 抛异常，phase transition 丢失。
- **验收标准:** phase transition 后立即 `save_state`，与 book_closure 分支保持一致。

### 7.3 Category G: 补充代码质量

#### G1. gate 返回 dict status 类型不一致

- **来源:** W3T1 审查 (finding #3)
- **当前状态:** 成功路径的 status 来自 `json.loads` (plain `str`)；失败路径使用 `GateStatus.FAIL` (StrEnum)。`== "FAIL"` 因 StrEnum 而工作，但类型不一致。
- **修改文件:** `src/shenbi/pipeline/dispatch_helper.py`
- **验收标准:** 失败路径使用 `GateStatus.FAIL.value` 统一为 plain `str`。

#### G2. _check_conditional_resolve 跳过 G4

- **来源:** W3T3 审查 (finding #1)
- **当前状态:** `chapter_loop.py` 的 `_check_conditional_resolve` dispatch foreshadowing-resolve 但不运行 G4 验证且不检查 `result.success`。
- **修改文件:** `src/shenbi/pipeline/chapter_loop.py`
- **验收标准:** conditional resolve 后运行 G4，检查 result.success，失败时 log warning。

#### G3. _resolve_g4_path 不使用 staging_path() API

- **来源:** W3T3 审查 (finding #2)
- **当前状态:** 手动拼接 `f"{STAGING_DIR}/{resolved}"` 而非调用 `checkpoint.staging_path()`。
- **修改文件:** `src/shenbi/pipeline/chapter_loop.py`
- **验收标准:** 使用 `staging_path()` 统一 staging 路径构造。

#### G4. truth_embed.main() rebuild 是空操作

- **来源:** W2T3 审查 (finding #3)
- **当前状态:** `rebuild` 命令打开 DB、创建表、关闭。不做任何 embedding。
- **修改文件:** `src/shenbi/pipeline/truth_embed.py`
- **验收标准:** 要么实现 rebuild (遍历 truth files 重新 embed)，要么添加明确日志 "rebuild not yet implemented, use update with --text"。

#### G5. truth_index.main() 丢弃 update 命令

- **来源:** W2T3 审查 (finding #4)
- **当前状态:** brief 指定 `choices=["update", "rebuild", "query"]`，实现使用 `["rebuild", "query"]`。
- **修改文件:** `src/shenbi/pipeline/truth_index.py`
- **验收标准:** 添加 `update` 作为 `rebuild` 的别名 (两者行为相同)，或在 help 中说明 "use rebuild"。

#### G6. book_closure trigger 分支冗余 save_state

- **来源:** 最终审查 (finding M3)
- **当前状态:** `cli.py:111` 在 trigger 分支中显式调用 `save_state`，但 caller 在循环返回后也会调用。
- **修改文件:** `src/shenbi/pipeline/cli.py`
- **验收标准:** 移除冗余 `save_state`，或添加注释说明为何需要提前保存。

#### G7. ClosureStateData 在 "Produces" 中列出但未定义

- **来源:** W1T1 审查
- **当前状态:** Wave 1 brief 的 "Produces" 接口列表包含 `ClosureStateData`，但实际代码使用 `closure: ClosureState` + `closure_step: int` 扁平化设计。
- **修改文件:** 无代码修改 (文档对齐)，但需先 grep 确认无代码引用
- **验收标准:** grep 确认 `ClosureStateData` 不被任何 `src/shenbi/` 或 `tests/` 代码引用；在 spec 或代码注释中说明 closure 状态扁平化到 `PipelineState`。

### 7.4 Category H: 补充文档修复

#### H1. Spec coverage matrix 需要更新

- **来源:** W5T3 产出
- **当前状态:** `docs/superpowers/plans/2026-07-02-pipeline-coverage-matrix.md` 记录 17/20 pass, 3 partial。修复后应为 20/20。
- **修改文件:** `docs/superpowers/plans/2026-07-02-pipeline-coverage-matrix.md`
- **验收标准:** 所有修复完成后更新 matrix 为 20/20 pass，移除 G1-G4 gap 描述。

#### H2. cmd_rollback stub 消息过期

- **来源:** W1T6
- **当前状态:** 消息说 "Rollback requires snapshot integration (Wave 3/4)"，但 Wave 3/4 已完成。
- **修改文件:** `src/shenbi/pipeline/cli.py`
- **验收标准:** 更新为 "Rollback not yet implemented" (不引用已完成的 wave)。

## 8. 更新后的完整修复优先级

```
Phase 1 (正确性阻塞): A3 → A8 → A5 → A4 → A1 → A2 → A6 → A7
Phase 2 (补充正确性): E1, E2, E3, E5 (相互独立), E4 (stub 修复)
Phase 3 (健壮性):     B1, B2, B3, B4, B5 (相互独立)
Phase 4 (测试补全):   C1-C5, F1-F7 (相互独立)
Phase 5 (代码清理):   D1-D4, G1-G7, H1-H2, I1-I3 (相互独立)
```

Phase 2 可与 Phase 1 的独立项 (A1, A2, A6, A7) 并行。

## 9. 更新后的验收标准

修复完成后必须满足:

1. **§15 全部 20 条验收标准 Pass**
2. **端到端集成测试**覆盖完整路径 (init → genesis → chapter-loop → closure)
3. **批判性审核通过**: 无 Critical/Important 发现
4. **所有 pre-commit 钩子绿色**
5. **Pipeline 测试数 >= 650** (当前 510 + 预估 140+ 新测试，含 C6 审计闭环端到端)
6. **Spec coverage matrix 更新为 20/20**
7. **无 broad `except Exception`** 不带 try/finally 的资源泄漏 (E1)
8. **所有 CLI 命令在错误输入时返回 error envelope** 而非 traceback (E3)

### 7.5 Category I: 流程与文档根因修复

以下 3 个发现来自审查 M1-M3，根因不在代码缺陷本身，而在导致缺陷残留或被掩盖的流程/文档问题。

#### I1. Progress ledger TODO 残留误导 (M1 根因)

- **来源:** 审查 M1
- **表面问题:** progress ledger (`.superpowers/sdd/novel-pipeline/progress.md`) 中仍有 `TODO W3T5: chapter-revision runs unconditionally`，但代码在 commit `e3c2ffb` 已修复 (`if step.skill == "shenbi-chapter-revision" and _is_revision_skipped(state, chapter)`)。
- **根因:** SDD 流程缺少"修复后清理 ledger TODO 标记"的步骤。progress ledger 是手工维护的追踪文档，代码修复后没有同步更新。残留的 TODO 标记会误导后续工作——有人读 ledger 后认为问题未修复而重新工作，或在批判性审核中误报为未修复项。
- **影响:** 文档与代码状态不一致；后续 SDD 执行或审核可能重复劳动或产生误报。
- **方案:**
  1. 逐行审查 progress ledger 中的所有 `TODO`、`Follow-up`、`CONCERN` 标记
  2. 对每个标记，grep 对应代码确认是否已修复
  3. 已修复的标记：标注 "(resolved in commit XXXX)" 或删除
  4. 未修复的标记：确认在本次 fixes spec 中有对应修复项
- **修改文件:** `.superpowers/sdd/novel-pipeline/progress.md` (gitignored, 本地文件)
- **验收标准:** progress ledger 中无残留的已修复 TODO 标记；每个未修复标记都能追溯到 fixes spec 中的对应项。

#### I2. ClosureStateData 设计决策未文档化 (M3/G7 根因深化)

- **来源:** 审查 M3 + G7
- **表面问题:** Wave 1 Task 1 的 brief 在 "Produces" 接口列表中列出了 `ClosureStateData`，但实际实现使用 `closure: ClosureState` + `closure_step: int` 扁平化到 `PipelineState`。grep 确认无代码引用 `ClosureStateData`。
- **根因:** brief 是一次性文档，代码迭代后 brief 不更新。代码实现选择了更简单的扁平化设计（合理——closure 只有 state + step 两个字段，不值得单独 dataclass），但这个设计决策从未在代码注释、模块文档字符串或任何 spec 中记录。后续开发者如果按 brief 的 "Produces" 列表查找 `ClosureStateData`，会发现它不存在且无解释。
- **影响:** 接口预期与实际实现不一致；新开发者困惑。
- **方案:**
  1. 在 `src/shenbi/pipeline/state.py` 的 `PipelineState` 类文档字符串中添加说明：closure 状态为何扁平化到顶层字段而非独立 dataclass
  2. 明确列出 closure 相关字段：`closure: ClosureState`、`closure_step: int`、`closure_retry_counts: dict`
  3. 不修改任何代码逻辑——纯文档对齐
- **修改文件:** `src/shenbi/pipeline/state.py` (文档字符串)
- **验收标准:** `PipelineState` 文档字符串明确说明 closure 字段结构和设计决策；无代码引用 `ClosureStateData`。

#### I3. D2 常量循环依赖根因 (M2 根因深化)

- **来源:** 审查 M2 + D2
- **表面问题:** `MAX_DISPATCH_RETRIES` 和 `MAX_AUDIT_RETRIES` 常量在 `error_handler.py` 中定义但不被逻辑读取（逻辑读 `state.config` 的值），仅被测试断言。
- **根因:** 常量最初从 spec §11 的值直接定义在 `error_handler.py`。后来 `PipelineConfig` 添加了 `max_revision_retries` 和 `max_audit_retries` 字段（也默认为 3），但 `error_handler.py` 的常量没有同步删除或连接到 config。这导致同一值在两处定义（DRY 违规），且如果 config 默认值改变，常量会静默偏移。
- **注意:** D2 方案已在本次 spec 更新中修订为"将常量移到 `state.py` 作为 `DEFAULT_MAX_DISPATCH_RETRIES`，`PipelineConfig` 引用它作为默认值"。此处补充根因记录：这是 SDD 分阶段实施导致的增量 DRY 违规——W3T1 创建常量，W3T8 添加 config 字段，两个阶段没有交叉清理。
- **影响:** 如果 `PipelineConfig.max_revision_retries` 默认值从 3 改为 4，`error_handler.py` 的常量仍为 3，测试断言会失败或误导。
- **方案:** 已在 D2 中定义（常量移到 `state.py`）。此处仅记录根因。
- **验收标准:** 见 D2。
