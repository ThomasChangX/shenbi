# Novel Pipeline 设计 spec

> 日期: 2026-07-01
> 状态: 已批准 (brainstorming) + code review R2 (target 9+)
> 目的: 设计 `pipeline` -- 从小说构思种子到完整小说的全自动生成流水线,以生成质量为最高优先级

## 1. 背景与动机

### 1.1 问题

框架有完整的逐章设计(13步循环、审计/评分/修正闭环、分层记忆、gate链),但**没有自动化执行器**。Round test 001 暴露的核心问题:所有步骤需要人工编排器手动调用,导致大量治理步骤被跳过。

### 1.2 目标

1. **完整端到端**: 从种子文件到完整小说
2. **充分利用所有 skill/gate/helper**: 全部 69 个 skill 被编排或明确标记 out-of-scope
3. **质量优先**: gate链100%执行、独立agent评分(G3强制)、审计闭环、人工审核checkpoint
4. **人工可介入**: 分层审核checkpoint
5. **可扩展**: 支持超长篇(1000+章)
6. **未来 web UI 就绪**: 命令式API、无状态进程、多用户并发

### 1.3 非目标

- 不实现 web UI 本身
- 不替换现有 gate/scoring/dispatcher 基础设施

### 1.4 Skill 覆盖声明 (58 编排 + 11 out-of-scope = 69)

**Pipeline 编排的 skill (58 unique)**:

创世层 (16): worldbuilding, genre-config, character-design, faction-builder, story-architecture, volume-outlining, pacing-design, plot-thread-weaver, foreshadowing-plant, power-system, location-builder, relationship-map, book-spine-init, intent-management, style-learning, anchor-curate

逐章循环 (16): intent-management, chapter-planning, foreshadowing-plant, context-composing, chapter-drafting, state-settling, foreshadowing-track, foreshadowing-recall, foreshadowing-resolve, drift-guidance, snapshot-manage, escalation-review, anti-detect, length-normalizing, style-polishing, chapter-revision

审计层 (20): review-anti-ai, review-continuity, review-character, review-pacing, review-foreshadowing, review-memo-compliance, review-pov, review-era, review-fanfic, review-world-rules, review-sensitivity, review-dialogue, review-motivation, review-texture, review-reader-pull, review-highpoint, review-long-span, review-arc-payoff, review-spinoff, chapter-pattern

评分层 (5): review-resonance, score-arc, score-stratum, score-volume, foundation-review

封印层 (5): memory-distill, volume-consolidation, foreshadowing-resolve(final), style-learning(final), foundation-review(final)

辅助 (1): truth-sync (post-edit/post-rollback)

注: intent-management, foreshadowing-plant, foreshadowing-resolve, style-learning, foundation-review, memory-distill 在多个阶段出现,计为 1 个 unique skill。

**明确 out-of-scope (11)**:

| Skill | 排除原因 |
|-------|---------|
| short-outline | 短篇流水线 |
| short-drafting | 短篇流水线 |
| short-packaging | 短篇流水线 |
| sequel-writing | 续写,在 book closure 之后单独触发 |
| import-analysis | 导入已有作品,本 pipeline 从 seed 创建新小说 |
| character-extraction | 反向提取,本 pipeline 正向创建 |
| world-extraction | 反向提取,本 pipeline 正向创建 |
| canon-import | 同人原作导入,如 seed 指定同人题材则作为可选 genesis 前置 |
| market-radar | 市场趋势分析,非生成环节 |
| writing-skills | 元技能,skill 管理用 |
| using-shenbi | 元技能,skill 发现用 |

## 2. 架构

### 2.1 三层分离

```
+---------------------------------------------+
|           调用层 (Driver)                     |
|   Codex agent (现在) / Web UI (未来)          |
+------------------+--------------------------+
                   | 命令式调用
                   v
+---------------------------------------------+
|         编排层 (Orchestrator)                 |
|   pipeline (Python 状态机)                    |
|   职责: 流程控制、gate 强制、checkpoint 暂停  |
|         状态序列化、重试/升级逻辑             |
|         memory-distill 触发                   |
|         truth-index/embed 维护               |
|         context assembly                     |
+------------------+--------------------------+
                   | dispatch / validate / score
                   v
+---------------------------------------------+
|         执行层 (Skills + Gates + Helpers)    |
|   69 个 skill / G0-G7 / scoring / progress   |
+---------------------------------------------+
```

### 2.2 命令接口

```
pipeline init <seed-file> [--project-dir <dir>]
    # 解析种子文件, 创建项目骨架, 初始化 pipeline-state.json + novel.json
    # 跑 G0 环境检查
    # 幂等: 如 pipeline-state.json 已存在则报错

pipeline next <project-dir>
    # 执行到下一个 checkpoint 并暂停

pipeline status <project-dir>
    # 查询当前状态 (只读, 不需要写锁)

pipeline review <project-dir> approve
pipeline review <project-dir> reject --feedback <file>
pipeline review <project-dir> modify --feedback <file>

pipeline resume <project-dir>
    # 审核通过后继续执行到下一个 checkpoint

pipeline chapters <project-dir>
    # 查看章节进度概览 (只读)

pipeline rollback <project-dir> --chapter <N>
    # 回滚到某章快照 (破坏性操作, 需确认)
```

### 2.3 生命周期

**Phase 1: Genesis** -- 一次性执行
**Phase 2: Per-Chapter Loop** -- 重复执行直到全书完成
**Phase 3: Book Closure** -- 一次性执行

### 2.4 并发约束 (多用户)

- **进程无状态**: 每个命令是独立进程。
- **读写锁分离**: `status` 和 `chapters` 使用只读锁 (共享,不阻塞其他读)。`next`/`review`/`resume`/`rollback`/`init` 使用排他写锁。
- **文件锁**: `pipeline-state.json.lock` (排他写, timeout 300s 因 next 可能长时间运行), `pipeline-state.json.readlock` (共享读)。
- **Init 幂等**: 如 `pipeline-state.json` 已存在则报错,防止重复 init 同一 project_dir。
- **项目隔离**: 每本小说独立 project_dir。
- **dispatch agent 隔离**: agent_id 含 project_dir.name。
- **路径隔离**: 所有产出路径基于 project_dir。

### 2.5 Gate 使用策略

**结构验证 gate**:
- **G0**: init 时环境检查
- **G1**: 每次 dispatch 时由 dispatcher executor 自动调用 (输入验证)
- **G2**: 每次 dispatch 后由 dispatcher executor 自动调用 (输出验证)。Pipeline **不重复运行 G2** (依赖 dispatcher 已执行),仅在特殊场景追加验证。
- **G3**: 每次评分/review dispatch 前独立性检查 (见 2.6)
- **G4**: 每次 dispatch 后 pipeline 追加运行 (skill-specific 结构验证)

Pipeline 依赖 dispatcher executor 内置的 G1+G2,自身只追加 G4。

**测试框架 gate (不使用)**: G5/G6/G7 属于 phase_runner.py 的 T2/T3 流程,pipeline 不使用。

### 2.6 G3 独立性强制

`g3_independence.py` 是 fail-closed。Pipeline dispatch `requires_independent_agent: true` skill 前:
1. 确保 dispatch 使用全新 agent_id
2. 在 pipeline-state.json 中记录 scorer agent 信息
3. 运行 G3 验证
4. G3 FAIL -> 评分无效,重新 dispatch

### 2.7 嵌入式人工交互与延迟写入

多个 skill 内部有"人工批准后才写入"步骤。但 dispatch 是单次无状态调用,skill 在调用内部直接写入文件。Pipeline 通过**延迟写入 staging 机制**解决:

**Staging area**: `staging/` 目录在 project_dir 下。

**工作方式**:
1. Pipeline dispatch 需要人工审核的 skill (chapter-planning, state-settling) 时,dispatch prompt 指示 skill 将产出写入 `staging/` 而非 truth/ 目录
2. Skill 执行完成,产出在 staging/ 中
3. Pipeline 暂停为 checkpoint,展示 staging/ 内容供人工审核
4. `review approve`: Pipeline 将 staging/ 内容 commit 到正式路径 (truth/, plans/, chapters/)
5. `review modify`: feedback 传给 skill,skill 重新写入 staging/,重新审核
6. `review reject`: 清空 staging/,按 reject 语义重做

**映射关系**:

| Skill 内部步骤 | Pipeline checkpoint | Staging 路径 | Commit 目标 |
|--------------|---------------------|-------------|-------------|
| chapter-planning: "Human reviews" | chapter-memo (step 2) | staging/plans/chapter-N-plan.md | plans/chapter-N-plan.md |
| state-settling: "审批门禁" | state-settle (step 5) | staging/truth/*.md (变更部分) | truth/*.md |

其他 skill (intent-management 等) 无内置审批,pipeline 直接让 skill 写入正式路径。

## 3. 状态机

### 3.1 状态转换表

| 当前状态 | 事件 | 新状态 | 动作 |
|---------|------|--------|------|
| (none) | init | genesis:in-progress | 创建项目,解析seed,跑G0,开始genesis step 1 |
| genesis:in-progress | next (step完成) | genesis:in-progress | 执行下一步 |
| genesis:in-progress | next (step 16完成) | genesis:checkpoint-pending | 暂停,设置genesis-complete checkpoint |
| genesis:checkpoint-pending | review approve | chapter-loop:in-progress | commit staging,genesis snapshot,开始ch1 step1 |
| genesis:checkpoint-pending | review modify | genesis:in-progress | 依赖重算 |
| genesis:checkpoint-pending | review reject | genesis:in-progress | 清空genesis产出,从头重来 |
| chapter-loop:in-progress | next (step完成,非checkpoint) | chapter-loop:in-progress | 执行下一步 |
| chapter-loop:in-progress | next (step 2完成) | chapter-loop:checkpoint-pending | 暂停,设置chapter-memo checkpoint |
| chapter-loop:in-progress | next (step 5完成) | chapter-loop:checkpoint-pending | 暂停,设置state-settle checkpoint |
| chapter-loop:in-progress | next (step 13完成,per_chapter on) | chapter-loop:checkpoint-pending | 暂停,设置per-chapter checkpoint |
| chapter-loop:in-progress | next (step 13完成,per_chapter off) | chapter-loop:in-progress | 继续触发检查+下一章step1 |
| chapter-loop:in-progress | next (volume boundary) | chapter-loop:checkpoint-pending | 暂停,设置volume-boundary checkpoint |
| chapter-loop:checkpoint-pending | review approve | chapter-loop:in-progress | commit staging,继续 |
| chapter-loop:checkpoint-pending | review modify | chapter-loop:in-progress | feedback传入,重做相关step |
| chapter-loop:checkpoint-pending | review reject (chapter-memo) | chapter-loop:in-progress | 清staging,重做step2 |
| chapter-loop:checkpoint-pending | review reject (state-settle) | chapter-loop:in-progress | 清staging,回退到step4重写章节 |
| chapter-loop:checkpoint-pending | review reject (per-chapter) | chapter-loop:in-progress | 回滚到上一章snapshot,从step1重做 |
| chapter-loop:checkpoint-pending | review reject (volume) | chapter-loop:in-progress | 回滚整卷 |
| chapter-loop:in-progress | escalation triggered | chapter-loop:checkpoint-pending | 暂停,设置escalation checkpoint |
| chapter-loop:in-progress | N==total_chapters | closure:in-progress | 开始closure step1 |
| chapter-loop:in-progress | unrecoverable error | failed | 记录错误,等待人工 |
| closure:in-progress | next (step 8完成) | closure:checkpoint-pending | 暂停,设置book-closure checkpoint |
| closure:checkpoint-pending | review approve | closure:completed | final snapshot,pipeline status: completed |
| closure:checkpoint-pending | review reject | chapter-loop:in-progress | 标记问题章/卷,回滚重做 |
| (any) | resume (crash recovery) | 原状态 | 验证truth完整性(见3.4),从当前step重做 |
| (any) | rollback --chapter N | chapter-loop:in-progress | 恢复snapshot,运行truth-sync |
| failed | resume (after manual fix) | 原状态 | 人工修复后恢复 |

### 3.2 每步完成后的统一动作

每个 skill dispatch + gate 检查完成后,pipeline 执行:

1. (G1+G2 已由 dispatcher executor 自动运行)
2. `shenbi-validate G4 <skill> <files>` -- pipeline 追加的 skill-specific 验证
3. 验证 contract reads 是否存在 (确保下一步输入完整)
4. **条件性 truth-index/embed 更新**: 仅当该 skill 的 contract `writes`/`updates` 包含 truth/chapter/style/outline/characters/world 文件时,才运行 `pipeline-truth-index update` 和 `pipeline-truth-embed update`。ephemeral skill (如 context-composing) 跳过。
5. **pipeline-state.json 原生进度跟踪**: 更新 `genesis.skills_done` 或 `chapter_states[N].steps_done`。不使用 `shenbi-progress mark-done` (该命令是 T1 测试框架专用,签名为 `<round_dir> <skill> <test_type> <score>`,不适用于 novel 生成)。

对于 `requires_independent_agent: true` skill,额外:
6. 运行 G3 独立性检查

### 3.3 pipeline-state.json

```json
{
  "version": 1,
  "project_dir": "/path/to/novel-project",
  "phase": "genesis | chapter-loop | closure | completed | failed",
  "genesis": {
    "state": "in-progress | checkpoint-pending | completed",
    "current_step": 5,
    "skills_done": ["shenbi-worldbuilding"],
    "retry_counts": {}
  },
  "chapter_loop": {
    "current_chapter": 5,
    "current_step": "chapter-planning",
    "step_index": 2,
    "chapter_states": {
      "5": {"steps_done": ["intent-management"], "status": "in-progress", "resonance_score": null, "audit_results": {}, "revision_count": 0}
    },
    "per_chapter_review_enabled": true,
    "retry_counts": {}
  },
  "closure": {"state": "pending | in-progress | checkpoint-pending | completed"},
  "pending_checkpoint": {"type": "null"},
  "checkpoint_history": [],
  "last_snapshot": {"type": "chapter-004", "created_at": "...", "checksum": "..."},
  "config": {
    "genesis_review_required": true,
    "chapter_memo_review_required": true,
    "state_settle_review_required": true,
    "per_chapter_review_enabled": true,
    "volume_boundary_review_required": true,
    "max_revision_retries": 3,
    "max_audit_retries": 3,
    "context_budget_override": null,
    "style_learning_interval": 12,
    "genre_config_update_on_drift": true,
    "resonance_global_floor": 50,
    "snapshot_retention_chapters": 50
  }
}
```

### 3.4 中断与恢复

- **Resume 时 truth 完整性验证**: `resume` 时,pipeline 对比当前 truth files 与 `last_snapshot` 的 checksum:
  - 如一致 -> 正常恢复
  - 如不一致 (可能 dispatch 中途崩溃导致部分写入) -> 强制运行 `truth-sync` 从最近完整章节重新提取,然后恢复
- **checkpoint 等待中进程终止**: 无影响,状态已持久化。
- **web UI 场景**: 关闭浏览器 -> 重开 -> `status` -> `review` -> `resume`。

## 4. Seed 文件解析

### 4.1 解析映射

```
seed sections -> 目标:
  基本信息       -> novel.json (含 total_chapters, 见 4.2)
  主角设定       -> genesis context
  世界观设定     -> genesis context
  势力/组织      -> genesis context
  核心冲突       -> genesis context
  情节线         -> genesis context
  章节大纲       -> genesis context
  三幕结构       -> genesis context
  叙事技巧       -> genre-config.json
```

### 4.2 total_chapters 定义与更新 [I3]

`total_chapters` 是 Phase 3 closure 的触发条件,必须有明确来源。

- **初始设定**: 由 `volume-outlining` (genesis step 6) 计算并写入 `novel.json.total_chapters`。计算方式: volume_map 中所有卷的章节数之和。如 seed 提供了章数,以 seed 为准。
- **动态更新**: 卷边界扩展 (§6.5) 时,如新卷改变了总章数,更新 `novel.json.total_chapters`。
- **Closure 检查**: `chapter-loop` 每章完成后读取 `novel.json.total_chapters` 动态比对,不硬编码。

### 4.3 可选 seed 增强

风格参考文件路径、参考作品路径、关键配角草图、卷数偏好、题材疲劳词列表、每章目标字数。

## 5. Phase 1: Genesis (创世层)

### 5.1 执行序列

严格串行,每步 dispatch 独立 agent + gate 检查:

| 步骤 | Skill | 追加 Gate | 产出 |
|------|-------|----------|------|
| G0 | -- | G0 | 环境检查 |
| 1 | worldbuilding | G4 | novel.json, world/, truth/*.md |
| 2 | genre-config | G4 | genre-config.json |
| 3 | character-design (genesis) | G4 | characters/*.md |
| 4 | story-architecture | G4 | outline/story_frame.md, volume_map.md, rhythm_principles.md |
| 5 | faction-builder | G4 | world/factions.md |
| 6 | volume-outlining | G4 | outline/volume_map.md (含 total_chapters -> novel.json) |
| 7 | pacing-design | G4 | outline/rhythm_principles.md |
| 8 | plot-thread-weaver | G4 | outline/thread_map.md |
| 9 | foreshadowing-plant (genesis mode) | G4 | truth/pending_hooks.md |
| 10 | power-system | G4 | world/power_system.md |
| 11 | location-builder | G4 | world/locations.md |
| 12 | relationship-map | G4 | characters/relationships.md, truth/character_matrix.md |
| 13 | book-spine-init | G4 | truth/book_spine.md |
| 14 | intent-management | G4 | truth/author_intent.md, truth/current_focus.md |
| 15 | style-learning (bootstrap) | G4 | style/style_profile.md |
| 16 | anchor-curate (optional) | G4 | benchmarks/anchors/AC-*.md |
| 17 | foundation-review | G3+G4 | foundation/review_report.md |

步骤 17 完成后: **[CHECKPOINT: genesis-complete]**

**注**: `foundation-review` 的 contract writes 为 `foundation/review_report.md` (非 `audits/`)。Pipeline 使用此路径。

### 5.2 Genesis Checkpoint

- **approve** -> commit staging, genesis snapshot, 进入逐章循环
- **modify + feedback** -> 依赖重算 (基于 contract writes -> reads 图)
- **reject + feedback** -> 创世层重来

### 5.3 渐进式创建

Genesis 只创建核心阵容。后续角色在卷边界扩展时引入。character-design 增加 `--mode expand`。

### 5.4 风格 Bootstrap (步骤 15)

- **有参考文件**: style-learning 从 `import/source/*.txt` 提取
- **无参考文件**: 从 seed 叙事技巧 + genre-config 生成种子指纹 (标 `bootstrap: true`)
- **首次正式提取**: 前3章完成后重新提取
- **定期更新**: 每 `config.style_learning_interval` 章 (默认12) 或卷边界

### 5.5 锚点策展 (步骤 16, 可选)

- **有参考作品**: anchor-curate 生成 AC-NNN.md
- **无参考作品**: 跳过。resonance 降级运行
- **前章补采**: 前3章完成后可选从前3章高分段落生成初始锚点

## 6. Phase 2: Per-Chapter Loop (逐章循环)

### 6.1 完整步骤流程

```
Step 1:  intent-management        -> 更新 truth/current_focus.md
Step 2:  chapter-planning         -> 产出 plans/chapter-N-plan.md (staging)
         [CHECKPOINT: chapter-memo] (必审)
Step 2b: foreshadowing-plant      -> 根据 step 2 的 hook 账 OPEN 项种植新伏笔
Step 3:  context-composing        -> 组装上下文包 (见 Section 7)
Step 4:  chapter-drafting         -> 读上下文包产出 chapters/chapter-N.md
Step 5:  state-settling           -> 提取 9 类变化, 写入 staging/truth/
         [CHECKPOINT: state-settle] (标准审)
Step 6:  foreshadowing-track      -> 更新 pending_hooks.md 生命周期
Step 7:  foreshadowing-recall     -> 检查超期伏笔
Step 7b: foreshadowing-resolve    -> 如 track 检测到 TRIGGERED hooks, 运行 resolve
Step 8:  审计层 (gate-driven)     -> 三圈审计 (见 6.2)
Step 9:  review-resonance         -> 独立 agent 评分 (G3 强制)
Step 10: revision_routing         -> 诊断分类 -> 路由修订 (见 6.3)
Step 11: 修订执行 (条件触发)      -> 分流到 polishing/anti-detect/length/revision
Step 12: snapshot-manage          -> 增量快照 (见 10.1)
Step 13: drift-guidance           -> 纠偏传导到下一章
         escalation_check         -> 如触发, dispatch escalation-review
         [CHECKPOINT: per-chapter] (可选)
         定期触发检查 -> 见 6.4-6.6
```

### 6.2 审计层设计 (Step 8)

**核心圈 (每章必跑,串行)**:

| 审计 Skill | 严重度 |
|-----------|--------|
| review-anti-ai | BLOCKING |
| review-continuity | BLOCKING |
| review-character | BLOCKING |
| review-pacing | CRITICAL |
| review-foreshadowing | CRITICAL |
| review-memo-compliance | CRITICAL |
| review-pov | BLOCKING |

BLOCKING -> 立即停止,进入 revision。

**题材圈 (gate-driven 激活,核心圈全PASS后并行)**:

审计维度激活矩阵 (`genre-config.json` 的 `audit_dimensions` -> review skill 映射):

| genre-config dimension 值 | 激活的 review skill | 激活条件 |
|--------------------------|-------------------|---------|
| `era: true` | review-era | 题材含历史/年代标签 |
| `fanfic: true` | review-fanfic | novel.json is_fanfic = true |
| `world_rules: true` | review-world-rules | world/rules.md 存在且 > 3 条规则 |
| `sensitivity: true` | review-sensitivity | genre 标签含争议性题材 |
| `dialogue_focus: true` | review-dialogue | genre-config 声明 |
| `motivation_focus: true` | review-motivation | genre-config 声明 |
| `texture_focus: true` | review-texture | genre-config 声明 |
| `reader_pull_focus: true` | review-reader-pull | genre-config 声明 |
| `highpoint_focus: true` | review-highpoint | genre-config 声明 |

Pipeline 的 `triggers.py` 读取此矩阵,确定性激活。

**边界圈 (确定性触发,评分前)**:

| 审计 Skill | 触发条件 |
|-----------|---------|
| review-long-span | chapter % 24 == 0 或卷边界 |
| review-arc-payoff | 卷边界 |
| review-spinoff | pipeline-state 标记章节为衍生 |
| chapter-pattern | chapter % 6 == 0 |

### 6.3 修订闭环 (Step 10-11)

```
审计完成
  +-- 无 BLOCKING + resonance >= max(校准阈值, config.resonance_global_floor) -> 通过
  +-- 无 BLOCKING + resonance 边界/不确定 -> [CHECKPOINT: escalation]
  +-- 无 BLOCKING + resonance < 阈值 -> revision_routing 分流
  +-- 有 BLOCKING -> revision -> 重跑审计 (最多 3 次)
        +-- 3 次失败 -> dispatch escalation-review -> [CHECKPOINT: escalation]
```

**resonance 全局地板**: `config.resonance_global_floor` (默认 50)。即使 chapter_role 校准阈值低于此值,全局地板仍然适用。如 escalation checkpoint 被关闭 (auto-approve) 且章节低于全局地板 -> pipeline 输出警告日志。

**revision_routing 分流**:

| 诊断结果 | 委派 skill |
|---------|-----------|
| 表达层质感 | style-polishing |
| AI 可检测性 | anti-detect |
| 字数越界 | length-normalizing |
| 结构/情节 | chapter-revision |
| 混合 | 先专项后通用 |

**escalation-review dispatch**: 读 contract 实际 reads: `truth/resonance_trend.md`, `audits/volume-N-score.md`, `audits/arc-N-score.md`, `audits/stratum-N-score.md`, `audits/chapter-N-sensitivity.md`。编译升级上下文 + 决策选项 -> `audits/escalation-N-report.md`。

### 6.4 分层记忆与评分触发 (每章完成后)

**写顺序约束 [I14]**: 当 `chapter % 36 == is_volume_boundary(N)` 同时触发 memory-distill L4 和 score-stratum 时,执行顺序固定: **memory-distill 先写数据字段 -> score-stratum 后写诊断字段**。book_spine.md 的字段分区: memory-distill 写数据值 (进度/状态),score-stratum 写诊断值 (漂移/达成),不冲突。

```
if N % 12 == 0:
  -> memory-distill L2 (弧段蒸馏)
  -> score-arc (弧段级评分, G3)
  -> style-learning (定期更新)

if N % 36 == 0:
  -> memory-distill L4 (大弧蒸馏) -- 先执行
  -> score-stratum (大弧评分, G3) -- 后执行

if is_volume_boundary(N):
  -> foreshadowing-resolve (卷尾伏笔盘点 + CP 债务)
  -> volume-consolidation L3 (卷摘要)
  -> review-arc-payoff (体验质量门)
  -> score-volume (目标达成门, G3)
  -> memory-distill L5 (书脊滚动复核)
  -> style-learning (卷级更新)
  -> drift-guidance 卷级
  -> 卷边界扩展 (见 6.5)
  -> [CHECKPOINT: volume-boundary] (必审)
  -> snapshot-manage (volume-boundary 全量快照)
```

### 6.5 卷边界扩展 (渐进式创建)

在 drift-guidance 卷级之后 (所有当前卷评分和审核完成后):

```
1. 读下一卷 volume_map -> 识别需求
2. character-design --mode expand (G2+G4 验证)
3. faction-builder (G2+G4 验证)
4. location-builder (G2+G4 验证)
5. relationship-map (G2+G4 验证)
6. foreshadowing-plant (G2+G4 验证)
7. plot-thread-weaver (G2+G4 验证)
8. pipeline-truth-index rebuild + pipeline-truth-embed rebuild
9. 更新 novel.json.total_chapters (如卷数变化)
```

### 6.6 Genre-Config 运行时更新

drift-guidance 检测到反复疲劳词 (同一 warning 传导 >= 3 次) 且 config.genre_config_update_on_drift: dispatch genre-config -> 审批 -> 后续章节使用新配置。

### 6.7 audit_drift.md 有界化 [I10]

drift-guidance 作为 `audit_drift.md` 的合并器/最终写者,维护**滚动窗口**:
- 保留最近 12 章的纠偏条目 (YAML frontmatter 格式)
- 超过 12 章的历史条目归档到 `truth/audit_drift_archive.md`
- Route C 加载时只加载当前 `audit_drift.md` (<= 12 章 * 5 条 = <= 60 条),有界

## 7. Context Architecture

### 7.1 三路检索 + 确定性重排

```
P1 章节备忘 (语义查询)
  |
  +-> Route A: 实体索引 (确定性, pipeline-truth-index)
  +-> Route B: 向量检索 (bge-large-zh, pipeline-truth-embed)
  +-> Route C: 规则路由 (确定性固定加载)
  |
  v
候选上下文池 (~20-30K tokens)
  |
  v
确定性重排 (Python, 非 LLM):
  - Route A 结果优先级 = P1 直接涉及 (权重 1.0)
  - Route B 结果优先级 = cosine_similarity * 0.8
  - Route C 结果优先级 = 0.6 (固定上下文)
  - 同一片段多路命中 -> 取最高权重, 合并
  |
  v
LLM 策展层 (context-composing agent):
  - 去重 (确定性重排后残留的重复)
  - 冲突检测
  - 按裁剪到 budget
  |
  v
context/chapter-N-context.md (物化文件)
```

**Context package 物化 [I1]**: `pipeline-context-assemble` 将策展后的上下文写入 `context/chapter-N-context.md`。此文件路径需加入 `chapter-drafting` 的 contract reads。context-composing 的 contract 保持 ephemeral (它不产出持久文件,只做策展决策;持久化由 orchestrator 完成)。

### 7.2 自适应 Token Budget (统一 token 单位) [I13]

所有 budget 以 **token** 为单位。中文字符到 token 的转换因子: 1 中文字符 ≈ 1.5 token (基于常见中文 tokenizer 如 cl100k_base)。§7.4 的效果对比也以 token 为单位。

| chapter_role | budget (tokens) | 约等于中文字符 |
|-------------|----------------|-------------|
| 高潮/兑现 | 18,000 | ~12,000 字 |
| 推进/转折 | 12,000 | ~8,000 字 |
| 过渡/铺垫 | 8,000 | ~5,300 字 |

### 7.3 Route B 降级路径 [I11]

如 embedding 模型不可用 (加载失败/API 超时):
1. 跳过 Route B
2. 在 pipeline-state.json 标记 `route_b_degraded: true`
3. 日志输出降级警告 (减少召回率)
4. Routes A+C 继续工作 (精确实体 + 固定规则)
5. 下次 dispatch 时自动重试 Route B

### 7.4 Route B 分块策略

Embedding 分块规则:
- **chapter_summary**: 每章摘要独立 1 chunk (~200-400 字)
- **arc_synthesis**: 每弧段合成独立 1 chunk (~800 字)
- **character_arc**: 每角色弧线描述独立 1 chunk
- **hook**: 每个 hook 的 content + keywords 独立 1 chunk
- **rule**: 每条世界规则独立 1 chunk
- **volume_summary**: 每卷摘要独立 1 chunk

### 7.5 自适应压缩 (memory-distill)

密度驱动触发: 累计变更>60条 / hook新增>15条 / 角色变更>20处 (保底chapter%12)。

### 7.6 效果对比 (第500章, token 单位)

| 维度 | 原始(整文件) | 优化后(三路) |
|------|------------|------------|
| character_matrix | ~15,000 tokens | ~800 tokens |
| pending_hooks | ~6,000 tokens | ~600 tokens |
| chapter_summaries | ~4,000 tokens | ~1,500 tokens |
| 总 context | ~32,000 tokens | ~9,000-12,000 tokens |

## 8. Phase 3: Book Closure

| 步骤 | Skill | 产出路径 | 说明 |
|------|-------|---------|------|
| 1 | foreshadowing-resolve (final) | truth/pending_hooks.md | 全书伏笔盘点: 所有 hooks 必须 RESOLVED |
| 2 | memory-distill L4+L5 | truth/book_strata.md, book_spine.md | 最终合成+复核(complete) |
| 3 | volume-consolidation L3 | truth/volume_summaries.md | 末卷卷摘要 |
| 4 | score-volume (G3) | audits/volume-N-score.md | 末卷评分 |
| 5 | review-arc-payoff | audits/volume-N-payoff.md | 全书体验质量门 |
| 6 | review-long-span | audits/chapter-N-long-span.md | 跨卷长程一致性 |
| 7 | chapter-pattern | outline/chapter_patterns.md | 全书模式分布 |
| 8 | foundation-review (G3+G4) | foundation/review_report.md | 终态基础设定审核 |
| 9 | style-learning (final) | style/style_profile.md | 最终风格指纹 |
| -- | **[CHECKPOINT: book-closure]** | -- | 必审 |
| 10 | snapshot-manage | final-snapshot/ | 全量快照 |

终审检查项: master hooks全RESOLVED / core_hook全RESOLVED / 主角弧线到终点 / 三层冲突全收束 / 主题全探索 / 模式熵>=阈值 / 无UNVERIFIED章节。

## 9. Checkpoint 设计

### 9.1 类型清单

| 类型 | 触发 | 必审/可选 | 审核选项 |
|------|------|----------|---------|
| genesis-complete | 创世层完成 | 必审 | approve / modify / reject |
| chapter-memo | 每章step2 | 必审 | approve / modify / reject |
| state-settle | 每章step5 | 标准审 | approve / modify / reject |
| escalation | 重试上限 | 必审 | accept / rollback / modify-upstream |
| per-chapter | 每章step13 | 可选 | approve / modify / reject |
| volume-boundary | 卷边界 | 必审 | approve / modify / reject |
| book-closure | Phase3 | 必审 | approve / modify |

### 9.2 Review modify 后的 truth-sync

modify feedback 导致章节内容修改时 (per-chapter, state-settle modify 后 chapter-revision 执行了):
- 修改后**必须运行 truth-sync**: 从修改后的章节正文重新反推 truth files,确保一致
- truth-sync 的冲突必须经人工仲裁 (skill 铁律)

### 9.3 审核配置

pipeline-state.json 的 config 可调整。关闭时自动 approve。如 escalation 被关闭且章节低于 `resonance_global_floor` -> 输出警告。

## 10. Snapshot 改进

### 10.1 增量 + 全量混合快照 [I9]

**章节快照 (每章,增量)**:
- truth/*.md (全部 truth 文件,含 foreshadowing_recall_result.md [M4])
- chapters/chapter-NNN.md (仅当前章)
- plans/chapter-NNN-plan.md (仅当前章备忘)
- style/style_profile.md
- characters/*.md (仅当本章有角色变更时)
- manifest (含 checksum)
- 大小: ~50-100KB/章

**全量快照 (仅卷边界 + genesis + closure)**:
- 完整项目状态 (truth/ + characters/ + world/ + outline/ + plans/ + chapters/ + style/)
- 大小: 随章节数增长,但只在卷边界创建 (~20-50个全量快照)

**保留策略 [I9]**: `config.snapshot_retention_chapters` (默认 50)。超过此数量的旧章节快照可清理 (保留全量快照)。

### 10.2 Checksum 强制验证

每次快照: Python hashlib 计算 SHA256 -> 随机重验 1 个文件 -> 不一致则中止。

### 10.3 快照清单更新 [M4]

truth 文件清单 (all truth files via glob, includes foreshadowing_recall_result.md):

### 10.4 回滚完整性

恢复快照覆盖项目 -> 标记后续章节 UNVERIFIED -> **必须运行 truth-sync**。

## 11. 错误处理与恢复

- dispatch/gate失败: 重试最多2次,3次失败->dispatch escalation-review->escalation checkpoint
- 审计BLOCKING: revision闭环最多3次,3次失败->回退最佳版本->escalation checkpoint
- 评分失败: scoring exit code 2->重dispatch(G3重验),exit code 3->先跑G4
- state-settling失败: 标记 settling_failed,暂停 (状态: chapter-loop:in-progress,等待人工)
- 中断规则: 同类失败>=3次->暂停修根因
- 不可恢复错误 -> 状态: `failed`,等待人工修复后 `resume`

## 12. 现有 skill 改动

| Skill | 改动 | 原因 |
|-------|------|------|
| character-design | 增加 `--mode expand` | 渐进式创建 |
| foreshadowing-plant | 增加 `--mode genesis` | Genesis 无 chapter plan,需从 volume_map 提取 master hooks |
| snapshot-manage | 全量快照清单 (truth glob) + foreshadowing_recall_result.md | 回滚完整性 |
| context-composing | 接收预检索包做策展 | 三路检索架构 |
| chapter-drafting | contract reads 增加 `context/chapter-N-context.md` | context package 物化 [I1] |
| memory-distill | 支持密度驱动触发 | 自适应压缩 |
| style-learning | 支持从 seed 叙事技巧生成 bootstrap 指纹 | 风格 bootstrap |
| drift-guidance | audit_drift.md 滚动窗口 (12章) | 有界化 [I10] |

## 13. 新增编排器模块

注: 编排器模块使用 `pipeline-` 前缀 (非 `shenbi-` skill 前缀),避免与 69 个 skill 混淆 [M1]。

| 模块 | 职责 |
|------|------|
| pipeline (CLI) | 命令式入口 (init/next/status/review/resume/rollback) |
| pipeline.state | 状态机管理 + 转换表 |
| pipeline.seed_parser | 种子文件解析 |
| pipeline.genesis | 创世层编排 |
| pipeline.chapter_loop | 逐章循环编排 |
| pipeline.closure | 全书封印编排 |
| pipeline.triggers | 确定性触发器 (memory/volume/expansion/style/genre-config) |
| pipeline.checkpoint | checkpoint 处理 + staging commit |
| pipeline.retry | 重试/升级逻辑 |
| pipeline.dependency_graph | genesis modify 依赖重算 |
| pipeline.revision_router | revision_routing 分流 |
| pipeline-truth-index | 实体索引 (Route A) |
| pipeline-truth-embed | 向量检索 (Route B) |
| pipeline-context-assemble | 三路检索组装 + 物化 |

## 14. 设计决策记录

1. **混合编排**: Python控制流 + skill创意执行
2. **命令式API**: 无状态,水平扩展,web UI就绪
3. **三路检索 + 确定性重排**: Route A精确 + Route B语义 + Route C规则,Python重排优先于LLM策展
4. **渐进式创建**: 超长篇分卷引入角色/地点/势力
5. **增量+全量混合快照**: 章节快照增量,卷边界全量,有保留策略
6. **G3强制**: 评分必须独立agent (fail-closed)
7. **Staging 延迟写入**: checkpoint-gated skill 产出先入 staging/,approve 后 commit
8. **foreshadowing 完整生命周期**: plant(每章+创世+卷边界) -> track(每章) -> recall(每章) -> resolve(条件+卷尾+封印)
9. **style-learning bootstrap**: 种子 -> 前3章正式 -> 定期更新
10. **revision 分流**: 专项问题委派专项 skill
11. **pipeline-state.json 原生进度**: 不复用 shenbi-progress (T1专用)
12. **读写锁分离**: status 只读不阻塞,next 排他写
13. **resume truth 完整性验证**: 对比 snapshot checksum,不一致则 truth-sync

## 15. 验收标准

1. init 解析种子,创建项目,跑通 G0,幂等
2. Genesis 17 步全部 dispatch+gate,到 checkpoint 暂停
3. 逐章循环完整步骤 (含 foreshadowing-plant step 2b) 执行
4. 审计层三圈正确编排,激活矩阵确定性
5. foreshadowing 完整生命周期闭环
6. revision_routing 正确分流
7. memory/volume/style/genre-config 触发器正确触发
8. 卷边界扩展 (G2+G4 验证) + total_chapters 更新
9. 三路检索组装 + 确定性重排 + context 物化文件
10. 所有 checkpoint 正确暂停/review/resume + staging commit
11. modify 后 truth-sync 同步
12. snapshot 增量+全量混合 + checksum + 回滚 + truth-sync
13. G3 独立性在所有评分前强制
14. escalation-review 在升级时被 dispatch
15. 进度跟踪在 pipeline-state.json 中 (不用 shenbi-progress)
16. 状态转换表完整,含 failed 终态
17. 并发安全 (读写锁分离,init 幂等)
18. resume 时 truth 完整性验证
19. audit_drift.md 有界 (12章滚动)
20. Route B 降级路径

## 16. Genesis 依赖验证表

每个 genesis 步骤的 contract reads 必须在执行前存在 (G1 检查)。以下为完整验证:

| 步骤 | Skill | Contract reads | 产出来源 | 验证 |
|------|-------|---------------|---------|------|
| 1 | worldbuilding | novel.json | init | OK |
| 2 | genre-config | novel.json, genre-config.json | step 1 | OK |
| 3 | character-design | world/story_bible.md, world/rules.md | step 1 | OK |
| 4 | story-architecture | world/story_bible.md, characters/**/*.md | step 1, step 3 | OK |
| 5 | faction-builder | novel.json, world/story_bible.md, world/rules.md, characters/**/*.md, outline/story_frame.md | steps 1-4 | OK |
| 6 | volume-outlining | outline/story_frame.md, outline/volume_map.md, truth/author_intent.md | steps 4-5, step 1 (empty template) | OK |
| 7 | pacing-design | novel.json, outline/story_frame.md, outline/volume_map.md, genre-config.json | steps 1-4 | OK |
| 8 | plot-thread-weaver | outline/story_frame.md, outline/volume_map.md, outline/rhythm_principles.md, truth/pending_hooks.md | steps 4-7, step 1 (empty template) | OK |
| 9 | foreshadowing-plant (genesis) | outline/story_frame.md, outline/volume_map.md, truth/pending_hooks.md, genre-config.json | steps 4-8, step 2 | OK (--mode genesis) |
| 10 | power-system | novel.json, world/story_bible.md, world/rules.md, outline/story_frame.md | steps 1-4 | OK |
| 11 | location-builder | novel.json, world/story_bible.md, world/rules.md, world/locations.md, outline/story_frame.md | steps 1-4 | OK |
| 12 | relationship-map | characters/**/*.md, characters/relationships.md, truth/character_matrix.md, world/factions.md | steps 3, 1, 5 | OK |
| 13 | book-spine-init | outline/story_frame.md, outline/volume_map.md, novel.json | steps 4-5, 1 | OK |
| 14 | intent-management | truth/author_intent.md, truth/audit_drift.md | step 1 (empty templates) | OK |
| 15 | style-learning | import/source/*.txt 或 chapters/*.md | seed 或 bootstrap | OK (bootstrap) |
| 16 | anchor-curate (optional) | import/source/*.txt | seed (optional) | OK (optional) |
| 17 | foundation-review | world/*.md, characters/**/*.md, outline/*.md, truth/current_state.md, truth/chapter_summaries.md | steps 1-14, 1 (templates) | OK |

**注**: worldbuilding (step 1) 写 `truth/*.md` 创建所有 truth 文件的空模板。G1 检查文件存在性,不检查内容。因此 `truth/author_intent.md`、`truth/pending_hooks.md` 等在 step 1 后即存在 (空模板),后续 skill 读取不会 G1 失败。

## 17. Ramp-Up 读取覆盖

某些 skill 的 contract reads 包含在小说早期不存在的文件。Pipeline 在 dispatch 这些 skill 时,对 G1 输入进行预处理 (跳过不存在的可选读取):

| Skill | 不存在的 reads | 首次产出时机 | Pipeline 处理 |
|-------|-------------|------------|-------------|
| drift-guidance | truth/volume_score_trend.md, truth/arc_payoff_trend.md | 首个卷边界 | Ramp-up 章节跳过这两个 reads,仅加载 truth/resonance_trend.md + audits/ |
| context-composing | truth/arcs/arc-N.md, truth/book_strata.md, truth/volume_summaries.md | ch12/ch36/卷边界 | Skill SKILL.md 已有爬坡期处理 (缺失层跳过)。Pipeline 在 dispatch 时对 G1 跳过这些可选 reads |
| drift-guidance | truth/resonance_trend.md | ch1 step 9 (首次 review-resonance) | ch1 step 13 时已由 step 9 产出。OK |
| escalation-review | audits/chapter-N-sensitivity.md | 仅 genre-config sensitivity=true 时产出 | 如 sensitivity 维度未激活,跳过此 read (§17 条件性 read) |

**实现**: Pipeline 在 dispatch 前解析 contract reads。对于标记为 `optional` 或在 ramp-up 阶段可能不存在的 reads,pipeline 从 G1 输入列表中移除。G1 只验证必须存在的 reads。

可选 reads 判定规则: 文件路径含 `N` 模板变量 (如 `arc-N.md`) 或文件首次产出在运行时后期 (如 trend files)。

## 18. G4 Staging 验证目标 [R2-4]

对于 checkpoint-gated skill (chapter-planning, state-settling),dispatch 将产出写入 `staging/`。G4 验证目标:

1. **G4 在 staging 内容上运行**: dispatch 完成后,pipeline 运行 G4 验证 staging 路径下的产出 (如 `staging/plans/chapter-N-plan.md`)
2. **G4 通过 -> checkpoint 暂停**: staging 内容验证合格,呈交人工审核
3. **review approve -> commit**: pipeline 将 staging 内容复制到正式路径,然后**不再重复 G4** (已验证)
4. **G4 失败**: 按 §11 重试逻辑,重新 dispatch 该 skill

## 19. foreshadowing-plant --mode genesis [R2-2]

现有 foreshadowing-plant 的 contract reads `plans/chapter-N-plan.md`。Genesis 阶段无章节备忘,需要 genesis 模式:

- `--mode genesis`: reads `outline/story_frame.md` + `outline/volume_map.md` (跨卷 master hooks 从 volume_map 提取),而非 chapter plan。产出仍 updates `truth/pending_hooks.md`
- `--mode per-chapter` (默认): 现有行为,reads `plans/chapter-N-plan.md`

Pipeline 通过 dispatch prompt 传递 mode。SKILL.md 需增加 genesis mode 流程说明 (见 §12)。
