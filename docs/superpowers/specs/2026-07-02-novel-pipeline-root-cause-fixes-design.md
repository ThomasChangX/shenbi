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

- **Spec 引用:** §3.4, §15 item 18
- **当前状态:** `cmd_resume` 直接重入 orchestration loop，无专门完整性扫描。
- **影响:** 缺失的 truth 文件在下一次 step 的 G1 中才被发现，而非 resume 时立即报错。
- **验收标准:** resume 时对下一步的 contract reads 做轻量 G1 扫描，快速失败并给出明确消息。

#### B3. truth-sync 自动传播 after modify

- **Spec 引用:** §9.2
- **当前状态:** Staging commit 工作，但 derived truth 文件不会自动级联更新。
- **影响:** 人工修改的 truth 变更可能不会传播到派生文件，直到后续 gate 捕获到不一致。
- **验收标准:** define 派生 truth 文件集合，modify 时 queue 对应 producing skill 的 re-dispatch。

#### B4. requires_independent 改为 fail-closed

- **Spec 引用:** §2.6
- **当前状态:** `requires_independent` 在任何异常时返回 `False` (fail-open)，跳过 G3。
- **影响:** 对于 `requires_independent_agent: true` 的 skill，G3 独立性检查可能被意外跳过。
- **验收标准:** 对于已知的 scoring skill (review-resonance 等)，异常时返回 `True` (fail-closed)；对于其他 skill 保持 fail-open。

#### B5. reject 后 step_index 重置

- **Spec 引用:** §9.1
- **当前状态:** Rejected checkpoint 清空 staging 但 advance 到下一步，而非重新执行被 reject 的 step。
- **影响:** Reject 语义不对——应该重做该步骤，而非跳过。
- **验收标准:** Reject 时重置 `step_index` 到 checkpoint 对应的 step，使 resume 时重新执行。

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

### 2.4 Category D: 代码清理

#### D1. _gate_passed 提取为共享工具

- **当前状态:** `_gate_passed` 在 `chapter_loop.py`、`audit_layer.py`、`closure.py` 中各有一份副本。
- **验收标准:** 提取到 `dispatch_helper.py` 或 `shenbi.status` 作为单一实现。

#### D2. MAX_DISPATCH_RETRIES / MAX_AUDIT_RETRIES 常量连接

- **当前状态:** 这两个常量存在于 `error_handler.py` 但不被逻辑读取 (逻辑读 `state.config` 的值)。常量仅被测试断言。
- **验收标准:** 要么从 config 默认值派生常量 (`PipelineConfig` 使用这些常量作为 default)，要么删除常量改用注释。

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
3. 如果 BLOCKING: 调用 `handle_audit_blocking` -> 进入 revision 闭环 (最多 `max_audit_retries` 次)
4. revision 闭环: re-dispatch chapter-revision -> re-run audit -> 如果仍 BLOCKING 且未超限 -> 再 revision; 超限 -> escalation

**修改文件:** `src/shenbi/pipeline/chapter_loop.py`, `tests/unit/pipeline/test_chapter_loop.py`

#### A5: error_handler 三函数接线

**方案:**
1. `handle_audit_blocking`: 在 chapter_loop 的审计 BLOCKING 路径调用 (依赖 A8)
2. `handle_scoring_failure`: 在 review-resonance dispatch 后检查 exit code:
   - exit code 2 -> re-dispatch (G3 重验)
   - exit code 3 -> 先跑 G4 再 re-dispatch
   - 其他 -> 标准失败处理
3. `handle_state_settle_failure`: 在 state-settling dispatch 失败时调用 -> 标记 `settling_failed`, 设 checkpoint 暂停

**修改文件:** `src/shenbi/pipeline/chapter_loop.py`, `src/shenbi/pipeline/error_handler.py`

#### A4: escalation-review dispatch 接线

**方案:** 在 `_handle_failure` (genesis + chapter_loop + closure) 中，当 `handle_dispatch_failure` 返回 `False` 时:
1. 先 `dispatch_escalation(state, project_dir, chapter)` 生成 `audits/escalation-N-report.md`
2. 然后 `set_checkpoint(state, CheckpointType.ESCALATION, ...)` 展示该报告

**修改文件:** `src/shenbi/pipeline/genesis.py`, `src/shenbi/pipeline/chapter_loop.py`, `src/shenbi/pipeline/closure.py`

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

**方案:** `cmd_review` 的 `MODIFY` 分支:
1. **不** commit staging (与 approve 不同)
2. 将 feedback 写入 state 的待处理字段
3. 重置 `step_index` 到 checkpoint 对应的 step
4. resume 时 orchestrator 看到 modify_pending 标记，将 feedback 加入 dispatch prompt 并重新执行该 step

**修改文件:** `src/shenbi/pipeline/cli.py`, `src/shenbi/pipeline/state.py`

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
