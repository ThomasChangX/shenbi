# 第一本小说 / Your First Novel

本指南带你走完 Shenbi 长篇小说的完整创作流程，按 7 个阶段顺序：创世 -> 架构 -> 规划 -> 起草 -> 审计 -> 基设 -> 管理。

This guide walks you through the complete Shenbi long-form novel creation pipeline, in 7 phases: Genesis -> Architecture -> Planning -> Drafting -> Audit -> Foundation -> Management.

> Shenbi 还支持短篇流水线（短篇小说）和导入流水线（已有作品导入）。见页面底部。
>
> Shenbi also supports a short-form pipeline (short stories) and an import pipeline (importing existing works). See the bottom of this page.

---

## 前提条件 / Prerequisites

- Shenbi 已安装（见 [安装指南 / Installation](installation.md)）
- 一个种子文件（`seed.md`），包含目标字数和类型 / A seed file (`seed.md`) with target word count and genre

---

> **术语提示 / Terminology note:** Shenbi 通过"分派（dispatch）"执行技能——每个技能接收输入并产出文件。"轮次（round）"是一次完整的执行周期，其目录结构确保可复现性。命令中的 `T1` 指单技能测试层级，`generative` 是三种测试类型之一。 / Shenbi executes skills via "dispatch" — each skill receives input and produces output files. A "round" is a complete execution cycle whose directory structure ensures reproducibility. The `T1` in commands refers to the per-skill test tier; `generative` is one of three test types.

## 第 1 步：创世 / Step 1: Genesis

**做什么 / What it does:** 构建小说的基础世界——世界观、力量体系、阵营、地点、角色设计、关系图、故事架构、分卷大纲、类型配置、节奏设计、书脊初始化。这是所有后续阶段的根基。

Build the novel's foundational world — worldbuilding, power system, factions, locations, character design, relationship map, story architecture, volume outlining, genre config, pacing design, book spine init. This is the root of all subsequent phases.

**技能 / Skills** (11):

shenbi-worldbuilding, shenbi-power-system, shenbi-faction-builder, shenbi-location-builder, shenbi-character-design, shenbi-relationship-map, shenbi-story-architecture, shenbi-volume-outlining, shenbi-genre-config, shenbi-pacing-design, shenbi-book-spine-init

**真相文件 / Truth Files:**
- 读取 / Reads: `novel.json`
- 写入 / Writes: `world/story_bible.md`, `world/rules.md`, `world/locations.md`, `world/power_system.md`, `world/factions.md`, `characters/protagonist.md`, `characters/relationships.md`, `outline/story_frame.md`, `outline/volume_map.md`

```bash
# 创建轮次 / Create round
bash tests/round-exec.sh <agent> T1

# 分派创世技能 / Dispatch genesis skill
uv run shenbi-dispatch shenbi-worldbuilding generative <round_dir> "<prompt>"
```

---

## 第 2 步：架构 / Step 2: Architecture

**做什么 / What it does:** 细化故事架构、分卷结构和节奏设计。部分技能（story-architecture、volume-outlining、genre-config、pacing-design）与创世阶段重叠——这是设计意图，不是重复。

Refine story architecture, volume structure, and pacing. Some skills (story-architecture, volume-outlining, genre-config, pacing-design) overlap with Genesis — this is intentional, not repetition.

**技能 / Skills** (5):

shenbi-story-architecture, shenbi-volume-outlining, shenbi-pacing-design, shenbi-plot-thread-weaver, shenbi-genre-config

**真相文件 / Truth Files:**
- 读取 / Reads: `outline/story_frame.md`, `outline/volume_map.md`
- 写入 / Writes: `outline/rhythm_principles.md`, `outline/thread_map.md`

```bash
uv run shenbi-dispatch shenbi-plot-thread-weaver generative <round_dir> "<prompt>"
```

---

## 第 3 步：规划 / Step 3: Planning

**做什么 / What it does:** 为每一章生成章节备忘（chapter memo），种植伏笔，组装写作上下文。

Generate chapter memos, plant foreshadowing, and compose writing context for each chapter.

**技能 / Skills** (3):

shenbi-chapter-planning, shenbi-foreshadowing-plant, shenbi-context-composing

**真相文件 / Truth Files:**
- 读取 / Reads: `outline/` files, `truth/current_state.md`
- 写入 / Writes: `plans/chapter-N-plan.md`, `truth/pending_hooks.md`

```bash
uv run shenbi-dispatch shenbi-chapter-planning generative <round_dir> "<prompt>"
```

---

## 第 4 步：起草 / Step 4: Drafting

**做什么 / What it does:** 起草章节正文，结算状态变化，追踪伏笔生命周期，打磨文风，执行反 AI 检测和字数调整。

Draft chapter prose, settle state changes, track foreshadowing lifecycle, polish style, run anti-AI detection, and adjust word count.

**技能 / Skills** (9):

shenbi-chapter-drafting, shenbi-state-settling, shenbi-foreshadowing-track, shenbi-style-polishing, shenbi-review-resonance, shenbi-anti-detect, shenbi-length-normalizing, shenbi-foreshadowing-recall, shenbi-score-arc

**真相文件 / Truth Files:**
- 读取 / Reads: `plans/chapter-N-plan.md`, `truth/current_state.md`, `truth/pending_hooks.md`
- 写入 / Writes: `chapters/chapter-N.md`, `truth/current_state.md` (updated), `truth/chapter_summaries.md`

```bash
uv run shenbi-dispatch shenbi-chapter-drafting generative <round_dir> "<prompt>"
```

---

## 第 5 步：审计 / Step 5: Audit

**做什么 / What it does:** 18 个专项审核技能从不同维度检查已完成章节：角色一致性、连贯性、对话风格、节奏、AI 痕迹、伏笔、世界规则、敏感词、章节备忘合规性等。

18 specialized review skills audit finished chapters from different dimensions: character consistency, continuity, dialogue style, pacing, AI traces, foreshadowing, world rules, sensitivity, memo compliance, and more.

**技能 / Skills** (18):

shenbi-review-character, shenbi-review-continuity, shenbi-review-dialogue, shenbi-review-pacing, shenbi-review-anti-ai, shenbi-review-foreshadowing, shenbi-review-world-rules, shenbi-review-sensitivity, shenbi-review-memo-compliance, shenbi-review-motivation, shenbi-review-pov, shenbi-review-reader-pull, shenbi-review-highpoint, shenbi-review-texture, shenbi-review-long-span, shenbi-review-era, shenbi-review-fanfic, shenbi-review-spinoff

**真相文件 / Truth Files:**
- 读取 / Reads: all truth files + `chapters/chapter-N.md`
- 写入 / Writes: `audits/` directory reports

```bash
# 审核默认从 review-anti-ai 开始 / Default audit starts with review-anti-ai
uv run shenbi-dispatch shenbi-review-anti-ai generative <round_dir> "<prompt>"
```

---

## 第 6 步：基设 / Step 6: Foundation

**做什么 / What it does:** 审查完整的基础设定，修复审计发现的问题，同步真相文件，学习文风指纹。

Review the complete foundation, fix audit-found issues, synchronize truth files, and learn style fingerprints.

**技能 / Skills** (4):

shenbi-foundation-review, shenbi-chapter-revision, shenbi-truth-sync, shenbi-style-learning

**真相文件 / Truth Files:**
- 读取 / Reads: `world/`, `characters/`, `outline/`, `truth/` (all)
- 写入 / Writes: revised chapters, `truth/` (updated via truth-sync)

```bash
uv run shenbi-dispatch shenbi-chapter-revision generative <round_dir> "<prompt>"
```

---

## 第 7 步：管理 / Step 7: Management

**做什么 / What it does:** 管理快照、引导漂移、管理创作意图、分类章节模式、卷总结、分层评分。这些技能维护项目长期健康。

Manage snapshots, guide drift, manage creative intent, classify chapter patterns, consolidate volumes, and score hierarchically. These skills maintain long-term project health.

**技能 / Skills** (9):

shenbi-snapshot-manage, shenbi-drift-guidance, shenbi-intent-management, shenbi-chapter-pattern, shenbi-volume-consolidation, shenbi-review-arc-payoff, shenbi-memory-distill, shenbi-score-volume, shenbi-score-stratum

**真相文件 / Truth Files:**
- 读取 / Reads: `truth/` (all), `audits/`
- 写入 / Writes: `truth/drift_guidance.md`, `truth/volume_summaries.md`, `audits/` scoring reports

```bash
uv run shenbi-dispatch shenbi-volume-consolidation generative <round_dir> "<prompt>"
```

---

## 其他流水线 / Other Pipelines

Shenbi 除了长篇流水线外，还支持两条专用流水线：

In addition to the long-form pipeline, Shenbi supports two specialized pipelines:

### 短篇流水线 / Short-Form Pipeline

专为 30 章以下的短篇小说设计。精简了创世和大纲流程，一次性批量生成全部章节。

Designed for short novels under 30 chapters. Streamlines genesis and outlining, batch-generates all chapters at once.

技能 / Skills: `shenbi-short-outline` -> `shenbi-short-drafting` -> `shenbi-short-packaging`

### 导入流水线 / Import Pipeline

将已有作品导入 Shenbi 进行分析、续写或同人创作。

Import existing works into Shenbi for analysis, continuation, or fanfic creation.

技能 / Skills: `shenbi-import-analysis` -> `shenbi-character-extraction` / `shenbi-world-extraction` -> `shenbi-canon-import`

---

## 完成后 / After Completion

每轮结束后，运行总结和审计：

After each round, run summary and audit:

```bash
uv run shenbi-validate G7 <round_dir>
```

> 完整执行协议见 `command-to-give.md`。
>
> Full execution protocol in `command-to-give.md`.

---

## 流水线命令行 / Pipeline CLI

除了手动分派技能外，Shenbi 还提供 `pipeline` CLI 用于自动化编排。使用 `just` 脚本更方便：

In addition to manually dispatching skills, Shenbi provides a `pipeline` CLI for automated orchestration. The `just` recipes are more convenient:

```bash
# 1. 从种子文件初始化项目 / Initialize project from seed
just pipeline-init seed.md

# 2. 查看当前状态 / Check current status
just pipeline-status ./novel

# 3. 提交检查点审查 / Submit checkpoint review (approve|reject|modify)
just pipeline-review ./novel approve

# 4. 恢复执行 / Resume execution
just pipeline-resume ./novel
```

初始化会创建 `pipeline-state.json`、`novel.json`、`genre-config.json` 和 `genesis-context/` 目录。审查命令在检查点处清除阻塞并记录决定。

Initialization creates `pipeline-state.json`, `novel.json`, `genre-config.json`, and the `genesis-context/` directory. The review command clears the checkpoint block and records the decision.

> **注意：** 自动编排（`next`/`resume`）目前为占位实现，完整生成逻辑将在后续版本落地。状态机、检查点、种子解析等基础层已就绪。
>
> **Note:** Automated orchestration (`next`/`resume`) is currently a placeholder; full generation logic arrives in a later wave. The state machine, checkpoint, and seed parsing foundation layers are ready.
