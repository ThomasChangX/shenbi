# Novel Pipeline 设计 spec

> 日期: 2026-07-01
> 状态: 已批准 (brainstorming)
> 目的: 设计 `shenbi-pipeline` — 一个从小说构思种子到完整小说的全自动生成流水线,以生成质量为最高优先级

## 1. 背景与动机

### 1.1 问题

框架有完整的逐章设计(13步循环、审计/评分/修正闭环、分层记忆、gate链),但**没有自动化执行器**。Round test 001 暴露的核心问题:所有步骤需要人工编排器手动调用,导致大量治理步骤被跳过。

[2026-06-29-pipeline-runner-design-notes.md](2026-06-29-pipeline-runner-design-notes.md) 已列出12条设计约束(串行生成、逐章循环、分层记忆触发、gate不可跳过等),本 spec 将其实现为完整设计。

### 1.2 目标

1. **完整端到端**: 从种子文件(格式同 `outline-example.md`)到完整小说
2. **充分利用所有 skill/gate/helper**: 67个skill + G0-G7 gates + scoring/progress/dispatcher 全部被编排
3. **质量优先**: gate链100%执行、独立agent评分、审计闭环、人工审核checkpoint
4. **人工可介入**: 分层审核checkpoint,允许审核/修正/否决/重新生成
5. **可扩展**: 支持超长篇(1000+章)的渐进式创建和有界context
6. **未来 web UI 就绪**: 命令式API、无状态进程、多用户并发

### 1.3 非目标

- 不修改现有 skill 的 SKILL.md 行为(除了 character-design 增加 expand mode)
- 不实现 web UI 本身(只保证 API 兼容性)
- 不替换现有 gate/scoring/dispatcher 基础设施

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
|   67 个 skill (各自读 SKILL.md 执行)         |
|   G0-G7 gates (结构验证)                     |
|   scoring.py / progress.py / phase_runner    |
+---------------------------------------------+
```

**核心原则**: 编排层不创作、不判断,只负责"按正确顺序、在正确条件下、调用正确的 skill,然后在正确的地方暂停等人工"。所有创意决策发生在执行层。

### 2.2 命令接口

所有命令 project-scoped,进程无状态,状态全部序列化在 `pipeline-state.json`。

```
shenbi-pipeline init <seed-file> [--project-dir <dir>]
    # 解析种子文件, 创建项目骨架, 初始化 pipeline-state.json
    # 跑 G0 环境检查

shenbi-pipeline next <project-dir>
    # 执行到下一个 checkpoint 并暂停
    # 输出当前 checkpoint 类型和 artifact 路径

shenbi-pipeline status <project-dir>
    # 查询当前状态 + pending checkpoint
    # 返回 JSON: phase, current_chapter, current_step, pending_checkpoint

shenbi-pipeline review <project-dir> approve
shenbi-pipeline review <project-dir> reject --feedback <file>
shenbi-pipeline review <project-dir> modify --feedback <file>
    # 提交审核结果, 写入 pipeline-state.json

shenbi-pipeline resume <project-dir>
    # 审核通过后继续执行到下一个 checkpoint

shenbi-pipeline chapters <project-dir>
    # 查看章节进度概览 (章号/状态/评分)

shenbi-pipeline rollback <project-dir> --chapter <N>
    # 回滚到某章快照 (破坏性操作, 需确认)
```

### 2.3 生命周期

pipeline 分为三个阶段:

**Phase 1: Genesis (创世层)** -- 一次性执行,完成后不可重入(除非人工否决重做)

**Phase 2: Per-Chapter Loop (逐章循环)** -- 重复执行直到全书完成

**Phase 3: Book Closure (全书封印)** -- 一次性执行

### 2.4 并发约束 (多用户)

- **进程无状态**: pipeline 进程不持有任何跨命令的内存状态。每个命令调用是独立的进程。
- **文件锁**: `pipeline-state.json` 读写使用 `filelock` (timeout 30s),防止同一项目的并发命令竞态。
- **项目隔离**: 每个用户/每本小说是独立 project_dir,不共享 truth files。不同项目完全并行。
- **dispatch agent 隔离**: 每次 dispatch 生成唯一 agent_id (含 project_dir.name)。
- **路径隔离**: 所有 gate marker、score report、audit output 路径基于 project_dir,不用全局临时目录。
- **web UI 水平扩展**: 多个 worker 进程可服务不同用户,同一项目的命令通过文件锁串行化。

## 3. 状态机

### 3.1 pipeline-state.json

唯一状态源 (single source of truth):

```json
{
  "version": 1,
  "project_dir": "/path/to/novel-project",
  "phase": "genesis | chapter-loop | closure | completed",
  "genesis": {
    "state": "pending | in-progress | checkpoint-pending | completed",
    "current_skill": "shenbi-story-architecture",
    "skills_done": ["shenbi-worldbuilding", "shenbi-character-design"],
    "retry_counts": {}
  },
  "chapter_loop": {
    "current_chapter": 5,
    "current_step": "chapter-planning",
    "step_index": 2,
    "chapter_states": {
      "5": {
        "steps_done": ["intent-management"],
        "status": "in-progress",
        "resonance_score": null,
        "audit_results": {},
        "revision_count": 0
      }
    },
    "per_chapter_review_enabled": true,
    "retry_counts": {}
  },
  "closure": {
    "state": "pending"
  },
  "pending_checkpoint": {
    "type": "chapter-memo | genesis-complete | volume-boundary | escalation | per-chapter | state-settle | book-closure | null",
    "chapter": 5,
    "artifact": "plans/chapter-5-plan.md",
    "context": "审核理由/失败上下文",
    "options": ["approve", "modify", "reject"],
    "created_at": "2026-07-01T12:00:00Z"
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
    "context_budget_override": null
  }
}
```

### 3.2 状态转换

`next` 命令的核心语义: **执行到下一个 checkpoint 就暂停,写状态,退出进程**。

- genesis in-progress -> 执行下一步 skill dispatch + gate -> 继续 / 到 checkpoint 暂停
- chapter-loop in-progress -> 执行下一步 -> 继续 / 到 checkpoint 暂停
- checkpoint-pending -> 拒绝执行 next,返回"等待 review"
- review approve -> checkpoint 清除 -> resume 执行下一步
- review modify -> 写 feedback -> resume 时按 modify 语义执行
- review reject -> 按 reject 语义执行(重做/回滚)

### 3.3 中断与恢复

- **执行中进程终止**: `resume` 读 `pipeline-state.json`,定位当前 step,从该 step 重做。dispatch 幂等。snapshot 保证 truth files 状态完整性。
- **checkpoint 等待中进程终止**: 无影响,状态已持久化。
- **web UI 场景**: 用户关闭浏览器 -> 进程已退出 -> 重新打开 -> `status` 看到 pending checkpoint -> `review` -> `resume`。

## 4. Seed 文件解析

### 4.1 输入格式

种子文件格式同 `outline-example.md`。pipeline 入口: `shenbi-pipeline init <seed-file>`。

### 4.2 解析映射

```
seed 文件 sections:
  基本信息 (类型/时代/核心概念/目标字数/结局方向)
    -> novel.json

  主角设定 -> genesis context (传给 character-design)
  世界观设定 -> genesis context (传给 worldbuilding)
  势力/组织 -> genesis context (传给 faction-builder)
  核心冲突 -> genesis context (传给 story-architecture)
  情节线 -> genesis context (传给 plot-thread-weaver)
  章节大纲 -> genesis context (传给 volume-outlining)
  三幕结构 -> genesis context (传给 story-architecture)
  叙事技巧 -> genre-config.json (show_tell_ratio, deep_themes)
```

### 4.3 目标章数推导

如果 seed 没给章数: 目标字数 / 每章平均字数(genre-config 定义)。写入 `novel.json.total_chapters` 和 `novel.json.golden_opening_chapters`(默认3)。

### 4.4 Seed 可选增强

缺失时 skill 自行推导: 关键配角草图、明确卷数偏好、题材疲劳词列表、每章目标字数。

## 5. Phase 1: Genesis (创世层)

### 5.1 执行序列

严格串行,每步 dispatch 独立 agent + gate 检查:

| 步骤 | Skill | Gate | 产出 |
|------|-------|------|------|
| G0 | -- | G0 | 环境检查 + seed 解析合法性 |
| 1 | shenbi-worldbuilding | G2+G4 | novel.json, world/, truth/*.md(空模板) |
| 2 | shenbi-genre-config | G2 | genre-config.json |
| 3 | shenbi-character-design (genesis mode) | G2+G4 | characters/*.md, relationships.md |
| 4 | shenbi-faction-builder | G2 | world/factions.md |
| 5 | shenbi-story-architecture | G2+G4 | outline/story_frame.md, volume_map.md(骨架), rhythm_principles.md |
| 6 | shenbi-volume-outlining | G2+G4 | outline/volume_map.md(细化) |
| 7 | shenbi-pacing-design | G2 | outline/rhythm_principles.md(详化) |
| 8 | shenbi-plot-thread-weaver | G2 | outline/thread_map.md |
| 9 | shenbi-foreshadowing-plant | G2+G4 | truth/pending_hooks.md |
| 10 | shenbi-power-system | G2 | world/power_system.md |
| 11 | shenbi-relationship-map | G2 | characters/relationships.md, truth/character_matrix.md |
| 12 | shenbi-book-spine-init | G2+G4 | truth/book_spine.md |
| 13 | shenbi-intent-management | G2 | truth/author_intent.md, truth/current_focus.md |
| 14 | shenbi-foundation-review | -- | audits/foundation-review.md |

步骤 14 完成后: **[CHECKPOINT: genesis-complete]**

### 5.2 每步检查

每步 dispatch 完成后: G2 + G4 验证 -> contract reads 存在性 -> truth-index/embed 增量更新。G2/G4 失败重试最多2次,3次失败升级为 escalation。

### 5.3 Genesis Checkpoint

- **approve** -- 进入逐章循环
- **modify + feedback** -- 依赖重算(改了 story_bible -> 重跑下游)
- **reject + feedback** -- 整个创世层重来

### 5.4 渐进式创建 (超长篇支持)

Genesis 层只创建核心阵容(主角 + golden opening 角色 + 第一卷主要角色 + master hooks 涉及人物)。后续角色在卷边界扩展时引入。

character-design 需增加 `--mode expand`: 只追加新角色,读已有角色卡避免重复。

## 6. Phase 2: Per-Chapter Loop (逐章循环)

### 6.1 13 步流程

```
Step 1:  intent-management        -> 更新 truth/current_focus.md
Step 2:  chapter-planning         -> 产出 plans/chapter-N-plan.md (8段备忘)
         [CHECKPOINT: chapter-memo] (必审)
Step 3:  context-composing        -> 组装上下文包 (三路检索, 见 Section 7)
Step 4:  chapter-drafting         -> 读上下文包产出 chapters/chapter-N.md
Step 5:  state-settling           -> 提取 9 类变化, 更新 7 个 truth 文件
         [CHECKPOINT: state-settle] (标准审)
Step 6:  foreshadowing-track      -> 更新 pending_hooks.md 生命周期
Step 7:  foreshadowing-recall     -> 检查超期伏笔
Step 8:  审计层 (gate-driven)     -> 按 genre-config 激活的维度运行审计
Step 9:  review-resonance         -> 独立 agent 评分 (4维度 /100)
Step 10: revision_routing         -> 诊断分类 -> spot-fix / regenerate / constrained
Step 11: chapter-revision         -> 修订/重生 (如需) + 重跑审计 + state-settling
Step 12: snapshot-manage          -> 全量项目快照
Step 13: drift-guidance           -> 纠偏传导到下一章
         escalation_check
         [CHECKPOINT: per-chapter] (可选, 可开关)
         memory/volume 触发检查
```

### 6.2 审计层设计 (Step 8)

**核心圈 (每章必跑)**:

| 审计 Skill | 检查什么 | 严重度 |
|-----------|---------|--------|
| review-anti-ai | AI 可检测性标记 | BLOCKING |
| review-continuity | 前后矛盾 | BLOCKING |
| review-character | 角色 OOC / 动机偏移 | BLOCKING |
| review-pacing | 节奏 (太拖/太赶) | CRITICAL |
| review-foreshadowing | 伏笔逻辑 | CRITICAL |
| review-memo-compliance | 章节备忘执行度 | CRITICAL |
| review-pov | 视角一致性 | BLOCKING |

**题材圈 (gate-driven 激活)**: review-era, review-fanfic, review-world-rules, review-sensitivity, review-dialogue, review-motivation, review-texture, review-reader-pull, review-highpoint -- 根据 `genre-config.json` 的 `audit_dimensions` 激活。

**边界圈 (确定性触发)**: review-long-span (chapter % 24 == 0), review-arc-payoff (卷边界), review-spinoff (标记章节), chapter-pattern (chapter % 6 == 0)。

执行规则: 核心圈串行,BLOCKING 则停止。题材圈核心圈全PASS后并行。边界圈在评分前。

### 6.3 修订闭环 (Step 10-11)

无 BLOCKING + resonance >= 阈值 -> 通过。否则进入 revision_routing -> spot-fix/regenerate/constrained -> 重跑审计 (最多3次)。3次失败 -> escalation checkpoint。

### 6.4 确定性触发器

```
if N % 12 == 0:
  -> memory-distill L2 + score-arc
if N % 36 == 0:
  -> memory-distill L4 + score-stratum
if is_volume_boundary(N):
  -> volume-consolidation L3
  -> review-arc-payoff
  -> score-volume
  -> memory-distill L5
  -> 卷边界扩展 (见 6.5)
  -> [CHECKPOINT: volume-boundary] (必审)
  -> snapshot-manage (volume-boundary)
if N == total_chapters:
  -> Phase 3: Book Closure
```

### 6.5 卷边界扩展 (渐进式创建)

```
1. 读下一卷 volume_map -> 识别新角色/势力/地点需求
2. character-design --mode expand -> faction-builder -> location-builder
3. relationship-map -> foreshadowing-plant -> plot-thread-weaver
4. truth-index rebuild + truth-embed rebuild
```

## 7. Context Architecture (上下文架构)

### 7.1 三路检索架构 (Hybrid Retrieval)

借鉴 CodeGraph 的"建索引 + 查询驱动 + 跟依赖链"模式。

**Route A: 实体索引 (确定性)** -- truth-index.json,解析P1提取实体信号(角色/hook/地点/线索),查索引返回相关切片。

**Route B: 向量语义检索 (embedding-based)** -- SQLite + sqlite-vec,bge-large-zh embedding。用P1语义查询做相似度检索,返回top-K相关远章片段。

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
| 1 | memory-distill L4+L5 | 最终大弧合成+书脊复核(complete) |
| 2 | volume-consolidation L3 | 末卷卷摘要 |
| 3 | score-volume | 末卷目标达成评分 |
| 4 | review-arc-payoff | 全书体验质量门 |
| 5 | review-long-span | 跨卷长程一致性 |
| 6 | chapter-pattern | 全书模式分布终检 |
| 7 | foundation-review | 终态基础设定审核 |
| -- | **[CHECKPOINT: book-closure]** | 必审 |
| 8 | snapshot-manage | final-snapshot 全量快照 |

终审检查项: master hooks全RESOLVED / core_hook全RESOLVED / 主角弧线到终点 / 三层冲突全收束 / 主题全探索 / 模式熵>=阈值 / 无UNVERIFIED章节。

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

### 9.2 审核配置

pipeline-state.json 的 config 可调整各 checkpoint 是否需要人工审核。关闭时自动 approve。

## 10. Snapshot 改进

### 10.1 全量项目快照

快照清单: truth/*.md + characters/*.md + world/*.md + outline/*.md + plans/ + style/ + chapters/

### 10.2 多触发点

genesis-snapshot / volume-boundary-snapshot / chapter-snapshot / pre-revision-snapshot

### 10.3 回滚完整性

恢复全部快照文件覆盖项目,不只 truth/。N+1到当前章节标记UNVERIFIED。

## 11. 错误处理与恢复

- dispatch/gate失败: 重试最多2次,3次失败->escalation
- 审计BLOCKING: revision闭环最多3次,3次失败->回退最佳版本->escalation
- 评分失败: scoring exit code 2->重dispatch(最多2次),exit code 3->先跑gate
- state-settling失败: 标记settling_failed,暂停
- 中断规则: 同类失败>=3次->暂停修根因

## 12. 现有 skill 改动

1. **character-design**: 增加 `--mode expand` (增量追加角色)
2. **snapshot-manage**: 全量项目快照清单
3. **context-composing**: 接收预检索包做策展
4. **memory-distill**: 支持密度驱动触发

## 13. 新增编排器模块

| 模块 | 职责 |
|------|------|
| shenbi-pipeline (CLI) | 命令式入口 |
| pipeline/state.py | 状态机管理 |
| pipeline/seed_parser.py | 种子文件解析 |
| pipeline/genesis.py | 创世层编排 |
| pipeline/chapter_loop.py | 逐章循环编排 |
| pipeline/closure.py | 全书封印编排 |
| pipeline/triggers.py | 确定性触发器 |
| pipeline/checkpoint.py | checkpoint处理 |
| pipeline/retry.py | 重试/升级逻辑 |
| pipeline/dependency_graph.py | genesis modify依赖重算 |
| shenbi-truth-index | 实体索引(Route A) |
| shenbi-truth-embed | 向量检索(Route B) |
| shenbi-context-assemble | 三路检索组装 |

## 14. 设计决策记录

1. **混合编排**: Python控制流+Meta-Skill创意执行,兼顾可靠性和人工交互
2. **命令式API**: 未来web UI需要,进程无状态,水平扩展
3. **三路检索**: Route A精确召回+Route B语义相关+Route C规则上下文
4. **渐进式创建**: 超长篇角色/地点/势力分卷引入,不是一次性全量生成
5. **全量快照**: 保证回滚完整性,卷边界扩展会修改非truth文件

## 15. 验收标准

1. init解析种子文件,创建项目骨架,跑通G0
2. Genesis 14步全部dispatch+gate检查,到checkpoint暂停
3. 逐章循环13步全部执行,审计层三圈正确编排
4. memory/volume触发器正确触发
5. 卷边界扩展能渐进创建新实体
6. 三路检索组装正确context package
7. 所有checkpoint类型正确暂停/review/resume
8. snapshot全量覆盖,回滚完整恢复
9. 并发安全(文件锁,多项目隔离)
10. 状态机中断恢复正确
