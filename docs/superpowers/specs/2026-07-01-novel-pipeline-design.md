# Novel Pipeline 设计 spec

> 日期: 2026-07-01
> 状态: 已批准 (brainstorming) + code review 修正
> 目的: 设计 `shenbi-pipeline` -- 从小说构思种子到完整小说的全自动生成流水线,以生成质量为最高优先级

## 1. 背景与动机

### 1.1 问题

框架有完整的逐章设计(13步循环、审计/评分/修正闭环、分层记忆、gate链),但**没有自动化执行器**。Round test 001 暴露的核心问题:所有步骤需要人工编排器手动调用,导致大量治理步骤被跳过。

[2026-06-29-pipeline-runner-design-notes.md](2026-06-29-pipeline-runner-design-notes.md) 已列出12条设计约束,本 spec 将其实现为完整设计。

### 1.2 目标

1. **完整端到端**: 从种子文件(格式同 `outline-example.md`)到完整小说
2. **充分利用所有 skill/gate/helper**: 全部 69 个 skill + G0-G7 gates + scoring/progress/dispatcher 被编排或明确标记 out-of-scope
3. **质量优先**: gate链100%执行、独立agent评分(G3强制)、审计闭环、人工审核checkpoint
4. **人工可介入**: 分层审核checkpoint,允许审核/修正/否决/重新生成
5. **可扩展**: 支持超长篇(1000+章)的渐进式创建和有界context
6. **未来 web UI 就绪**: 命令式API、无状态进程、多用户并发

### 1.3 非目标

- 不实现 web UI 本身(只保证 API 兼容性)
- 不替换现有 gate/scoring/dispatcher 基础设施

### 1.4 Skill 覆盖声明

**Pipeline 编排的 skill (54)**:

创世层: worldbuilding, genre-config, character-design, faction-builder, story-architecture, volume-outlining, pacing-design, plot-thread-weaver, foreshadowing-plant, power-system, relationship-map, book-spine-init, intent-management, foundation-review, style-learning, anchor-curate

逐章循环: intent-management, chapter-planning, context-composing, chapter-drafting, state-settling, foreshadowing-track, foreshadowing-recall, foreshadowing-resolve, drift-guidance, snapshot-manage, escalation-review, anti-detect, length-normalizing, style-polishing, chapter-revision, style-learning(periodic)

审计层 (20): review-anti-ai, review-continuity, review-character, review-pacing, review-foreshadowing, review-memo-compliance, review-pov, review-era, review-fanfic, review-world-rules, review-sensitivity, review-dialogue, review-motivation, review-texture, review-reader-pull, review-highpoint, review-long-span, review-arc-payoff, review-spinoff, chapter-pattern

评分层: review-resonance, score-arc, score-stratum, score-volume

封印层: memory-distill, volume-consolidation, foundation-review, foreshadowing-resolve(final)

辅助: truth-sync (post-edit)

**明确 out-of-scope (15)**:

| Skill | 排除原因 |
|-------|---------|
| short-outline, short-drafting, short-packaging | 短篇流水线,非长篇小说生成 |
| sequel-writing | 续写,在 book closure 之后单独触发 |
| import-analysis | 导入已有作品分析,本 pipeline 从 seed 创建新小说 |
| character-extraction, world-extraction | 从已有手稿反向提取,本 pipeline 正向创建 |
| canon-import | 同人原作导入,如 seed 指定同人题材则作为可选 genesis 前置 |
| market-radar | 市场趋势分析,非生成环节 |
| writing-skills, using-shenbi | 元技能,skill 管理用 |

## 2. 架构

### 2.1 三层分离

```
+---------------------------------------------+
|           调用层 (Driver)                     |
|   Codex agent (现在) / Web UI (未来)          |
|   职责: 调用命令、展示 checkpoint、收集审核    |
+------------------+--------------------------+
                   | 命令式调用
                   v
+---------------------------------------------+
|         编排层 (Orchestrator)                 |
|   shenbi-pipeline -- Python 状态机            |
|   职责: 流程控制、gate 强制、checkpoint 暂停  |
|         状态序列化、重试/升级逻辑             |
|         memory-distill 触发、progress 更新   |
|         truth-index/embed 维护               |
|         context assembly                     |
+------------------+--------------------------+
                   | dispatch / validate / score
                   v
+---------------------------------------------+
|         执行层 (Skills + Gates + Helpers)    |
|   69 个 skill (各自读 SKILL.md 执行)         |
|   G0-G7 gates (结构验证)                     |
|   scoring.py / progress.py / phase_runner    |
+---------------------------------------------+
```

**核心原则**: 编排层不创作、不判断,只负责"按正确顺序、在正确条件下、调用正确的 skill,然后在正确的地方暂停等人工"。

### 2.2 命令接口

所有命令 project-scoped,进程无状态,状态全部序列化在 `pipeline-state.json`。

```
shenbi-pipeline init <seed-file> [--project-dir <dir>]
    # 解析种子文件, 创建项目骨架, 初始化 pipeline-state.json
    # 跑 G0 环境检查

shenbi-pipeline next <project-dir>
    # 执行到下一个 checkpoint 并暂停

shenbi-pipeline status <project-dir>
    # 查询当前状态 + pending checkpoint

shenbi-pipeline review <project-dir> approve
shenbi-pipeline review <project-dir> reject --feedback <file>
shenbi-pipeline review <project-dir> modify --feedback <file>

shenbi-pipeline resume <project-dir>
    # 审核通过后继续执行到下一个 checkpoint

shenbi-pipeline chapters <project-dir>
    # 查看章节进度概览

shenbi-pipeline rollback <project-dir> --chapter <N>
    # 回滚到某章快照 (破坏性操作, 需确认)
```

### 2.3 生命周期

**Phase 1: Genesis (创世层)** -- 一次性执行

**Phase 2: Per-Chapter Loop (逐章循环)** -- 重复执行直到全书完成

**Phase 3: Book Closure (全书封印)** -- 一次性执行

### 2.4 并发约束 (多用户)

- **进程无状态**: 每个命令调用是独立的进程,不持有跨命令内存状态。
- **文件锁**: `pipeline-state.json` 读写使用 `filelock` (timeout 30s)。
- **项目隔离**: 每本小说是独立 project_dir。不同项目完全并行。
- **dispatch agent 隔离**: 每次 dispatch 生成唯一 agent_id (含 project_dir.name)。
- **路径隔离**: 所有 gate marker、score report、audit output 路径基于 project_dir。

### 2.5 Gate 使用策略

Pipeline 复用现有 gate 系统,但明确区分两类用途:

**结构验证 gate (每次 skill dispatch 后)**:
- **G0**: init 时环境检查 + seed 解析合法性
- **G1**: 每次 dispatch 时输入验证 (由 dispatcher executor 自动调用)
- **G2**: 每次 dispatch 后输出结构验证
- **G3**: 每次评分/review dispatch 前独立性检查 (见 2.6)
- **G4**: 每次 dispatch 后 skill-specific 结构验证

**测试框架 gate (本 pipeline 不使用)**:
- G5 (T2 phase start), G6 (T3 pipeline), G7 (round close) 是测试框架专用 gate。Pipeline 不使用 phase_runner.py 的 T2/T3 流程,因此不调用 G5/G6/G7。

### 2.6 G3 独立性强制

`g3_independence.py` 是 fail-closed: 无独立评分证据 -> FAIL。

Pipeline 在 dispatch 任何 `requires_independent_agent: true` 的 skill (所有 review-* 和 score-* skill) 前必须:
1. 确保 dispatch 使用全新的 agent_id (不复用生成 agent)
2. 在 progress.json 中记录 `current_scorer_agent`
3. 运行 G3 gate 验证独立性
4. G3 FAIL -> 该评分无效,重新 dispatch 独立 agent

### 2.7 嵌入式人工交互映射

多个 skill 的 SKILL.md 内部包含人工审批步骤。Pipeline 将这些映射为 checkpoint,不额外添加重复审核:

| Skill 内部步骤 | Pipeline checkpoint 映射 |
|--------------|------------------------|
| chapter-drafting: "Human approves PRE_WRITE_CHECK" | 不设独立 checkpoint。PRE_WRITE_CHECK 在 dispatch 内部完成(自动批准模式)。如需人工审 PRE_WRITE_CHECK,通过 per_chapter_review_enabled 在 step 4 后捕获 |
| intent-management: "Ask human: changes to long-term intent?" | 不设独立 checkpoint。Intent 更新在 dispatch 内自动完成。人工可通过 modify checkpoint 的 feedback 调整 intent |
| state-settling: "审批门禁 + 跨文件一致性验证" | **映射为 state-settle checkpoint** (step 5)。Pipeline 展示 skill 的审批门禁输出,人工 approve/modify/reject |
| chapter-planning: "Human reviews" | **映射为 chapter-memo checkpoint** (step 2) |

## 3. 状态机

### 3.1 pipeline-state.json

唯一状态源:

```json
{
  "version": 1,
  "project_dir": "/path/to/novel-project",
  "phase": "genesis | chapter-loop | closure | completed",
  "genesis": {
    "state": "pending | in-progress | checkpoint-pending | completed",
    "current_skill": "shenbi-story-architecture",
    "skills_done": [],
    "retry_counts": {}
  },
  "chapter_loop": {
    "current_chapter": 5,
    "current_step": "chapter-planning",
    "step_index": 2,
    "chapter_states": {},
    "per_chapter_review_enabled": true,
    "retry_counts": {}
  },
  "closure": {"state": "pending"},
  "pending_checkpoint": {
    "type": "null",
    "chapter": null,
    "artifact": null,
    "context": null,
    "options": [],
    "created_at": null
  },
  "checkpoint_history": [],
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
    "genre_config_update_on_drift": true
  }
}
```

### 3.2 每步完成后的统一动作

每个 skill dispatch + gate 检查完成后,pipeline 执行:

1. `shenbi-validate G2 <files> <type>` -- 输出结构验证
2. `shenbi-validate G4 <skill> <files>` -- skill-specific 结构验证
3. 验证 contract reads 是否存在 (确保下一步输入完整)
4. `shenbi-truth-index update` -- 增量更新实体索引
5. `shenbi-truth-embed update` -- 增量更新 embedding
6. `shenbi-progress mark-done <round_dir> <skill> <test_type> <score>` -- 记录进度

对于 `requires_independent_agent: true` 的 skill,额外:
7. 运行 G3 独立性检查

## 4. Seed 文件解析

### 4.1 输入格式

种子文件格式同 `outline-example.md`。

### 4.2 解析映射

```
seed sections:
  基本信息       -> novel.json
  主角设定       -> genesis context (character-design)
  世界观设定     -> genesis context (worldbuilding)
  势力/组织      -> genesis context (faction-builder)
  核心冲突       -> genesis context (story-architecture)
  情节线         -> genesis context (plot-thread-weaver)
  章节大纲       -> genesis context (volume-outlining)
  三幕结构       -> genesis context (story-architecture)
  叙事技巧       -> genre-config.json (show_tell_ratio, deep_themes)
```

### 4.3 可选 seed 增强

- 风格参考文件路径 (`import/source/*.txt`) -- 如有,style-learning 从参考作品提取初始风格指纹
- 参考作品路径 -- 如有,anchor-curate 从参考作品生成评分锚点
- 关键配角草图、卷数偏好、题材疲劳词列表、每章目标字数

## 5. Phase 1: Genesis (创世层)

### 5.1 执行序列

严格串行,每步 dispatch 独立 agent + gate 检查:

| 步骤 | Skill | Gate | 产出 | 说明 |
|------|-------|------|------|------|
| G0 | -- | G0 | -- | 环境检查 + seed 解析合法性 |
| 1 | shenbi-worldbuilding | G2+G4 | novel.json, world/, truth/*.md | seed 世界规则作为推导输入 |
| 2 | shenbi-genre-config | G2 | genre-config.json | seed 叙事技巧 + 疲劳词 |
| 3 | shenbi-character-design (genesis) | G2+G4 | characters/*.md, relationships.md | seed 主角设定作为输入 |
| 4 | shenbi-faction-builder | G2 | world/factions.md | seed 势力作为输入 |
| 5 | shenbi-story-architecture | G2+G4 | outline/story_frame.md, volume_map.md(骨架), rhythm_principles.md | seed 三幕+冲突 |
| 6 | shenbi-volume-outlining | G2+G4 | outline/volume_map.md(细化) | 逐卷 OKR + 章级目标 |
| 7 | shenbi-pacing-design | G2 | outline/rhythm_principles.md(详化) | 节奏规则 |
| 8 | shenbi-plot-thread-weaver | G2 | outline/thread_map.md | 线索编织 |
| 9 | shenbi-foreshadowing-plant | G2+G4 | truth/pending_hooks.md | 初始 master hooks |
| 10 | shenbi-power-system | G2 | world/power_system.md | 力量体系 |
| 11 | shenbi-relationship-map | G2 | characters/relationships.md, truth/character_matrix.md | 关系图谱 |
| 12 | shenbi-book-spine-init | G2+G4 | truth/book_spine.md | 初始化 L5 书脊 |
| 13 | shenbi-intent-management | G2 | truth/author_intent.md, truth/current_focus.md | 初始化作者意图 |
| 14 | shenbi-style-learning (bootstrap) | G2 | style/style_profile.md | 见 5.5 风格 bootstrap |
| 15 | shenbi-anchor-curate (optional) | G2 | benchmarks/anchors/AC-*.md | 见 5.6 锚点策展 |
| 16 | shenbi-foundation-review | -- | audits/foundation-review.md | 基础设定审核(创世层自检) |

步骤 16 完成后: **[CHECKPOINT: genesis-complete]**

### 5.2 Genesis Checkpoint

- **approve** -- 进入逐章循环
- **modify + feedback** -- 依赖重算 (改了 story_bible -> 重跑下游)
- **reject + feedback** -- 整个创世层重来

**modify 依赖重算**: pipeline 维护 genesis 步骤依赖图 (基于 contract writes -> reads)。人工修改某文件 -> 追溯 writes 的 skill -> 重跑该 skill 及所有下游。

### 5.3 渐进式创建

Genesis 只创建核心阵容: 主角 + golden opening 角色 + 第一卷主要角色 + master hooks 涉及人物。后续角色在卷边界扩展时引入。

character-design 增加 `--mode expand`: 只追加新角色,读已有角色卡避免重复。

### 5.4 每步检查

每步 dispatch 后: G2+G4 验证 -> contract reads 存在性 -> truth-index/embed 增量 -> shenbi-progress mark-done。G2/G4 失败重试最多2次,3次失败升级为 escalation。

### 5.5 风格 Bootstrap (步骤 14)

`style-learning` reads `chapters/*.md` 或 `import/source/*.txt`。Genesis 阶段无章节,存在 bootstrap 问题。

策略:
- **如有 seed 提供的风格参考文件** (`import/source/*.txt`): style-learning 从参考作品提取初始风格指纹
- **如无参考文件**: style-learning 从 seed 的"叙事技巧"(show/tell比, 深层主题) + genre-config 的题材惯例生成**种子风格指纹** (标 `bootstrap: true`, 置信度低)
- **首次正式 style-learning**: 前3章完成后 (chapter_loop step 13 后),从实际章节重新提取,覆盖 bootstrap 指纹
- **定期更新**: 每 `config.style_learning_interval` 章 (默认12) 或卷边界,重新运行 style-learning 更新风格指纹

### 5.6 锚点策展 (步骤 15, 可选)

`review-resonance` 需要 `benchmarks/anchors/` 做校准。无锚点时降级为"无锚点参照"模式 (flag `anchor_calibration: unavailable`)。

- **如有参考作品** (`import/source/*.txt`): anchor-curate 从参考作品提取工艺分析,生成 AC-NNN.md
- **如无参考作品**: 跳过此步。resonance 评分降级运行,在 chapter loop 前几章产出后,可选择从前3章中选取高分段落生成初始锚点
- **质量影响**: 有锚点时 resonance 评分置信度更高 (high vs mid)。无锚点时锚点命中率无法计算,置信度强制降级为 mid

## 6. Phase 2: Per-Chapter Loop (逐章循环)

### 6.1 完整步骤流程

每章执行完整序列,不可跳过:

```
Step 1:  intent-management        -> 更新 truth/current_focus.md
Step 2:  chapter-planning         -> 产出 plans/chapter-N-plan.md (8段备忘)
         [CHECKPOINT: chapter-memo] (必审) -- 映射 skill 的 "Human reviews"
Step 3:  context-composing        -> 组装上下文包 (三路检索, 见 Section 7)
Step 4:  chapter-drafting         -> 读上下文包, PRE_WRITE_CHECK + 产出 chapters/chapter-N.md
Step 5:  state-settling           -> 提取 9 类变化, 更新 7 个 truth 文件
         [CHECKPOINT: state-settle] (标准审) -- 映射 skill 的 "审批门禁"
Step 6:  foreshadowing-track      -> 更新 pending_hooks.md 生命周期
Step 7:  foreshadowing-recall     -> 检查超期伏笔
Step 7b: foreshadowing-resolve    -> 如 track 检测到 TRIGGERED hooks, 立即运行 resolve
                                    (条件触发: track 输出含 TRIGGERED 状态 hook)
Step 8:  审计层 (gate-driven)     -> 三圈审计 (见 6.2)
Step 9:  review-resonance         -> 独立 agent 评分 (4维度 /100, G3 强制)
Step 10: revision_routing         -> 诊断分类 -> 路由修订 (见 6.3)
Step 11: 修订执行 (条件触发)      -> 按 revision_routing 结果分发:
         - spot-fix: chapter-revision (PATCHES)
         - 表达层问题: style-polishing (疲劳词/句长/修辞)
         - AI检测问题: anti-detect (structural tells)
         - 字数越界: length-normalizing
         - 结构问题: chapter-revision (rewrite/regenerate)
         修订后重跑受影响审计 + state-settling
Step 12: snapshot-manage          -> 全量项目快照 (含 checksum 验证)
Step 13: drift-guidance           -> 纠偏传导到下一章
         escalation_check         -> 如触发, dispatch escalation-review
         [CHECKPOINT: per-chapter] (可选, 可开关)
         定期触发检查 -> 见 6.4-6.6
```

### 6.2 审计层设计 (Step 8)

**核心圈 (每章必跑,串行)**:

| 审计 Skill | 检查什么 | 严重度 |
|-----------|---------|--------|
| review-anti-ai | AI 可检测性标记 | BLOCKING |
| review-continuity | 前后矛盾 | BLOCKING |
| review-character | 角色 OOC / 动机偏移 | BLOCKING |
| review-pacing | 节奏 (太拖/太赶) | CRITICAL |
| review-foreshadowing | 伏笔逻辑 | CRITICAL |
| review-memo-compliance | 章节备忘执行度 | CRITICAL |
| review-pov | 视角一致性 | BLOCKING |

BLOCKING -> 立即停止后续审计,进入 revision。

**题材圈 (gate-driven 激活,核心圈全PASS后并行)**:

review-era, review-fanfic, review-world-rules, review-sensitivity, review-dialogue, review-motivation, review-texture, review-reader-pull, review-highpoint -- 根据 `genre-config.json` 的 `audit_dimensions` 激活。

**边界圈 (确定性触发,评分前)**:

| 审计 Skill | 触发条件 |
|-----------|---------|
| review-long-span | chapter % 24 == 0 或卷边界 |
| review-arc-payoff | 卷边界 |
| review-spinoff | 用户标记衍生/番外章节 |
| chapter-pattern | chapter % 6 == 0 |

所有审计 skill 均 `requires_independent_agent: true`。Pipeline 通过独立 dispatch + G3 检查强制保证。

### 6.3 修订闭环 (Step 10-11)

```
审计完成
  +-- 无 BLOCKING + resonance >= 校准阈值 -> 通过, 继续 step 12
  +-- 无 BLOCKING + resonance 边界/不确定 -> [CHECKPOINT: escalation]
  +-- 无 BLOCKING + resonance < 阈值 -> revision_routing 分流
  +-- 有 BLOCKING -> revision -> 重跑审计 (最多 3 次)
        +-- 3 次失败 -> dispatch escalation-review -> [CHECKPOINT: escalation]
```

**revision_routing 分流规则** (chapter-revision SKILL.md 委派边界):

| 诊断结果 | 委派 skill | 触发判定 |
|---------|-----------|---------|
| 表达层质感 (疲劳词/句长/修辞) | style-polishing | 审计为表达层,无情节/角色影响 |
| AI 可检测性 (structural tells) | anti-detect | anti-ai 审计 critical/blocking |
| 字数越界 (< 3000 或 > 10000) | length-normalizing | 字数 hard-gate 未过 |
| 结构/情节问题 (blocking) | chapter-revision | 需改写叙事内容 |
| 混合问题 | 先专项后通用 | 先 polishing/anti-detect/length, 再 chapter-revision |

修订后:重跑受影响审计 skill + state-settling (如章节内容变更)。

**escalation-review dispatch**: escalation 触发时,pipeline dispatch `shenbi-escalation-review` (独立 agent)。该 skill 读取 audits/ + truth/resonance_trend.md + truth/volume_score_trend.md,编译升级上下文 + 决策选项,写入 audits/escalation-N-report.md。然后 pipeline 呈交该报告给人工 (escalation checkpoint)。

### 6.4 分层记忆触发 (每章完成后)

```
if N % 12 == 0:
  -> memory-distill L2 (弧段蒸馏 -> truth/arcs/arc-(N//12).md)
  -> score-arc (弧段级评分, G3 强制)
  -> style-learning (定期风格指纹更新)

if N % 36 == 0:
  -> memory-distill L4 (大弧蒸馏 -> truth/book_strata.md)
  -> score-stratum (大弧/书级评分, G3 强制)

if is_volume_boundary(N):
  -> foreshadowing-resolve (卷尾伏笔盘点 + Chase Power 债务计算)
  -> volume-consolidation L3 (卷摘要)
  -> review-arc-payoff (体验质量门)
  -> score-volume (目标达成门, G3 强制)
  -> memory-distill L5 (书脊滚动复核)
  -> style-learning (卷级风格指纹更新)
  -> drift-guidance 卷级
  -> 卷边界扩展 (见 6.5)
  -> [CHECKPOINT: volume-boundary] (必审)
  -> snapshot-manage (volume-boundary 全量快照)

if N == total_chapters:
  -> Phase 3: Book Closure
```

### 6.5 卷边界扩展 (渐进式创建)

在 volume-consolidation 之后、review-arc-payoff 之前:

```
1. 读下一卷 volume_map -> 识别新角色/势力/地点需求
2. character-design --mode expand (追加新角色卡)
3. faction-builder (如有新势力)
4. location-builder (如有新地点)
5. relationship-map (更新关系矩阵)
6. foreshadowing-plant (新角色/新卷的伏笔)
7. plot-thread-weaver (下一卷线索规划)
8. truth-index rebuild + truth-embed rebuild
```

### 6.6 Genre-Config 运行时更新

当 drift-guidance 检测到反复出现的疲劳词模式 (同一类 warning 传导 >= 3 次),且 `config.genre_config_update_on_drift` 为 true:
1. dispatch shenbi-genre-config (更新疲劳词列表)
2. 人工审核 (通过 genre-config skill 的审批门禁)
3. 更新后后续章节的审计使用新配置

## 7. Context Architecture (上下文架构)

### 7.1 三路检索架构 (Hybrid Retrieval)

借鉴 CodeGraph 的"建索引 + 查询驱动 + 跟依赖链"模式。

**Route A: 实体索引 (确定性)** -- truth-index.json,解析P1提取实体信号(角色/hook/地点/线索),查索引返回相关切片。

**Route B: 向量语义检索 (embedding-based)** -- SQLite + sqlite-vec,bge-large-zh embedding。用P1语义查询做相似度检索,返回top-K相关远章片段。覆盖:
- 章节摘要 (时间线事件)
- 弧段合成 (事件链)
- 角色弧线描述
- 伏笔内容
- 规则

**Route C: 规则路由 (确定性)** -- 固定加载: book_spine/audit_drift/style_profile/超期hook/当前弧段/近章结尾轨迹。

**LLM 策展层**: 三路产出候选池 -> 去重 -> 优先级排序 -> 冲突检测 -> 裁剪到budget。

### 7.2 自适应 Token Budget

| chapter_role | budget (tokens) |
|-------------|----------------|
| 高潮/兑现 | 18,000 |
| 推进/转折 | 12,000 |
| 过渡/铺垫 | 8,000 |

### 7.3 自适应压缩 (memory-distill 优化)

密度驱动触发: 累计变更>60条 / hook新增>15条 / 角色变更>20处 (保底chapter%12)。

压缩粒度自适应: 高密度600字 / 标准800字 / 低密度1200字。

### 7.4 效果对比 (第500章)

| 维度 | 原始(整文件) | 优化后(三路) |
|------|------------|------------|
| character_matrix | ~500行全加载 | ~5-8行本章角色 |
| pending_hooks | ~200条全加载 | ~8+3条相关+超期 |
| chapter_summaries | 近8章 | 近3章+5章语义相关 |
| 总 context | ~10,700字 | ~6,000-8,000字 |

## 8. Phase 3: Book Closure (全书封印)

| 步骤 | Skill | 说明 |
|------|-------|------|
| 1 | foreshadowing-resolve (final) | 全书伏笔盘点: 所有 hooks 必须 RESOLVED 或显式 ABANDON (需人工批准) |
| 2 | memory-distill L4+L5 | 最终大弧合成+书脊复核(status: complete) |
| 3 | volume-consolidation L3 | 末卷卷摘要 |
| 4 | score-volume | 末卷目标达成评分 (G3 强制) |
| 5 | review-arc-payoff | 全书体验质量门 |
| 6 | review-long-span | 跨卷长程一致性 |
| 7 | chapter-pattern | 全书模式分布终检 |
| 8 | foundation-review | 终态基础设定审核 |
| 9 | style-learning (final) | 最终风格指纹 |
| -- | **[CHECKPOINT: book-closure]** | 必审 |
| 10 | snapshot-manage | final-snapshot 全量快照 |

终审检查项: master hooks全RESOLVED / core_hook全RESOLVED / 主角弧线到终点 / 三层冲突全收束 / 主题全探索 / 模式熵>=阈值 / 无UNVERIFIED章节。

### 8.1 Final Snapshot

`final-snapshot/`: 全部 truth files + chapters/ + characters/ + world/ + outline/ + plans/ + audits/ + style/ + truth-index.json + truth-embeddings.db + pipeline-state.json (status: completed)。

## 9. Checkpoint 设计

### 9.1 类型清单

| 类型 | 触发 | 必审/可选 | 审核选项 |
|------|------|----------|---------|
| genesis-complete | 创世层完成 | 必审 | approve / modify(依赖重算) / reject |
| chapter-memo | 每章step2 | 必审 | approve / modify / reject(重做) |
| state-settle | 每章step5 | 标准审 | approve / modify / reject(重写章节) |
| escalation | 重试上限 | 必审 | accept / rollback / modify-upstream |
| per-chapter | 每章step13 | 可选 | approve / modify / reject |
| volume-boundary | 卷边界 | 必审 | approve / modify / reject(回滚整卷) |
| book-closure | Phase3 | 必审 | approve / modify |

### 9.2 Review modify 语义

modify feedback 的处理:
- **chapter-memo**: feedback 传给 chapter-planning dispatch,重做 step 2
- **state-settle**: feedback 传给 state-settling,修正提取
- **per-chapter**: feedback 传给 chapter-revision 进入修订。修订后 **必须运行 truth-sync** 重新同步 truth files
- **volume-boundary**: feedback 传给下一卷 volume-outlining
- **genesis-complete**: 触发 modify 依赖重算

### 9.3 审核配置

pipeline-state.json 的 config 可调整各 checkpoint。关闭时自动 approve (不暂停)。

## 10. Snapshot 改进

### 10.1 全量项目快照

快照清单: truth/*.md + characters/*.md + world/*.md + outline/*.md + plans/ + style/ + chapters/

### 10.2 多触发点

genesis-snapshot / volume-boundary-snapshot / chapter-snapshot / pre-revision-snapshot

### 10.3 Checksum 强制验证

每次创建快照时,pipeline 必须执行 snapshot-manage SKILL.md 要求的 checksum 流程:
1. 对每个 truth 文件计算 SHA256 (Python `hashlib`,禁止 LLM 生成)
2. 随机选取 1 个文件重新计算,确认一致
3. 不一致 -> 报告差异,中止快照

### 10.4 回滚完整性

恢复全部快照文件覆盖项目。N+1到当前章节标记UNVERIFIED。

回滚后 **必须运行 truth-sync**: 从回滚恢复的章节正文重新提取 truth,确保与快照中的 truth files 一致。

## 11. 错误处理与恢复

- dispatch/gate失败: 重试最多2次,3次失败->dispatch escalation-review->escalation checkpoint
- 审计BLOCKING: revision闭环最多3次,3次失败->回退最佳版本->escalation checkpoint
- 评分失败: scoring exit code 2->重dispatch(最多2次,G3重新验证),exit code 3->先跑gate
- state-settling失败: 标记settling_failed,暂停
- 中断规则: 同类失败>=3次->暂停修根因

## 12. 现有 skill 改动

1. **character-design**: 增加 `--mode expand` (增量追加角色)
2. **snapshot-manage**: 全量项目快照清单
3. **context-composing**: 接收预检索包做策展
4. **memory-distill**: 支持密度驱动触发
5. **style-learning**: 支持从 seed 叙事技巧生成 bootstrap 指纹 (当无章节/无参考文件时)

## 13. 新增编排器模块

| 模块 | 职责 |
|------|------|
| shenbi-pipeline (CLI) | 命令式入口 |
| pipeline/state.py | 状态机管理 |
| pipeline/seed_parser.py | 种子文件解析 |
| pipeline/genesis.py | 创世层编排 |
| pipeline/chapter_loop.py | 逐章循环编排 |
| pipeline/closure.py | 全书封印编排 |
| pipeline/triggers.py | 确定性触发器 (memory/volume/expansion/style/genre-config) |
| pipeline/checkpoint.py | checkpoint处理 |
| pipeline/retry.py | 重试/升级逻辑 |
| pipeline/dependency_graph.py | genesis modify依赖重算 |
| pipeline/revision_router.py | revision_routing 分流 (委派 polishing/anti-detect/length/revision) |
| shenbi-truth-index | 实体索引(Route A) |
| shenbi-truth-embed | 向量检索(Route B) |
| shenbi-context-assemble | 三路检索组装 |

## 14. 设计决策记录

1. **混合编排**: Python控制流+Meta-Skill创意执行
2. **命令式API**: 无状态,水平扩展,web UI就绪
3. **三路检索**: Route A精确召回+Route B语义相关+Route C规则上下文
4. **渐进式创建**: 超长篇分卷引入角色/地点/势力
5. **全量快照**: 保证回滚完整性
6. **G3强制**: 所有评分/审计必须独立agent (fail-closed)
7. **嵌入式交互映射**: skill 内部的人工审批映射为 pipeline checkpoint,不重复审核
8. **foreshadowing 完整生命周期**: plant(创世) -> track(每章) -> recall(每章) -> resolve(条件触发+卷尾+封印)
9. **style-learning bootstrap**: 种子风格 -> 前3章后首次正式提取 -> 定期更新
10. **revision 分流**: 专项问题委派专项 skill (polishing/anti-detect/length),通用问题走 chapter-revision

## 15. 验收标准

1. init解析种子文件,创建项目骨架,跑通G0
2. Genesis 16步全部dispatch+gate检查,到checkpoint暂停
3. 逐章循环完整步骤执行,审计层三圈正确编排
4. foreshadowing 完整生命周期 (plant->track->recall->resolve) 在 pipeline 中闭环
5. revision_routing 正确分流到 polishing/anti-detect/length/revision
6. memory/volume/style/genre-config 触发器正确触发
7. 卷边界扩展能渐进创建新实体
8. 三路检索组装正确context package
9. 所有checkpoint类型正确暂停/review/resume
10. modify 后 truth-sync 正确同步
11. snapshot全量覆盖+checksum验证,回滚完整恢复+truth-sync
12. G3独立性检查在所有评分前强制执行
13. escalation-review 在升级触发时被dispatch
14. shenbi-progress mark-done 在每步后调用
15. 并发安全(文件锁,多项目隔离)
16. 状态机中断恢复正确
