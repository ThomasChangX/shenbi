# Documentation Redesign — Wave 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rewrite Shenbi's entire user-facing documentation surface (README + 6 docs pages) into substantive bilingual content, replacing current stubs.

**Architecture:** Nine tasks building from infrastructure (Mermaid config, dependency) through individual page writes, ending with nav update and full build verification. Each task produces a committable, build-verifiable deliverable. All factual claims sourced from `tests/tiers/deps.json`.

**Tech Stack:** mkdocs-material, pymdown-extensions (Mermaid), Markdown, Python (uv for dep management).

## Global Constraints

- Bilingual: Chinese-primary, English below it, consistently across all pages
- Phase data source of truth: `tests/tiers/deps.json` (`t2-phases`, `t3-pipelines`, `_out_of_pipeline`)
- Scoring thresholds: `tests/tiers/acceptance.json` (`{"t1":94,"t2":94,"t3":94}`)
- Skill descriptions pulled verbatim from SKILL.md frontmatter `description` field
- Nav policy: additive (preserve existing Framework/API/ADR nav entries)
- Python: `>=3.11`, uv: `>=0.5` (recommended), just: required
- Docs build verification: `uv run mkdocs build --strict` (CI uses this; strict = warnings are errors)
- 69 skills total: 67 writing + 2 meta
- 9 T2 phases: genesis, architecture, planning, drafting, audit, foundation, management, import, short-story
- 3 T3 pipelines: long-form, short-form, import-form
- GitHub repo: `ThomasChangX/shenbi`

---

## File Structure

| File | Action | Responsibility |
|------|--------|----------------|
| `pyproject.toml` | Modify | Add `pymdown-extensions` to `[dependency-groups] docs` |
| `mkdocs.yml` | Modify | Add `markdown_extensions` (Mermaid) + update `nav` (additive) |
| `README.md` | Rewrite | Repo landing: pitch, quick start, skill overview, links |
| `docs/index.md` | Rewrite | Docs landing: problem, feature cards, dual audience paths |
| `docs/getting-started/installation.md` | Rewrite | Setup guide: prerequisites, install, verify |
| `docs/getting-started/concepts.md` | Rewrite | Core vocabulary: skills, truth files, gates, rounds, scoring |
| `docs/getting-started/first-novel.md` | Rewrite | End-to-end long-form workflow walkthrough |
| `docs/skills/index.md` | Rewrite | Full 69-skill catalog grouped by 9 phases + out-of-pipeline |
| `docs/architecture/overview.md` | Create | Pipeline + gates + scoring + truth files with Mermaid diagrams |

---

### Task 1: Infrastructure — pymdown-extensions + Mermaid config

**Files:**
- Modify: `pyproject.toml` (add dependency)
- Modify: `mkdocs.yml` (add markdown_extensions)

**Interfaces:**
- Produces: Mermaid rendering capability for all subsequent pages

- [ ] **Step 1: Add pymdown-extensions to docs dependency group**

In `pyproject.toml`, find the `[dependency-groups] docs` section and add `pymdown-extensions`:

    docs = [
        "mkdocs>=1.5.3",
        "mkdocs-material[imaging]>=9.5.4",
        "mkdocstrings[python]>=0.24.0",
        "pymdown-extensions>=10.0",
    ]

- [ ] **Step 2: Sync dependencies**

Run: `uv sync --group docs`
Expected: `pymdown-extensions` installed successfully.

- [ ] **Step 3: Add markdown_extensions to mkdocs.yml**

In `mkdocs.yml`, add a `markdown_extensions` section after the `theme` block (before `plugins`):

    markdown_extensions:
      - admonition
      - attr_list
      - pymdownx.superfences:
          custom_fences:
            - name: mermaid
              class: mermaid
              format: !!python/name:pymdownx.superfences.fence_code_format

- [ ] **Step 4: Create architecture directory**

Run: `mkdir -p docs/architecture`

- [ ] **Step 5: Verify existing build still passes**

Run: `uv run mkdocs build --strict`
Expected: Build succeeds with no errors.

- [ ] **Step 6: Commit**

    git add pyproject.toml uv.lock mkdocs.yml
    git commit -m "docs: add pymdown-extensions and Mermaid config for documentation redesign"

---

### Task 2: Skill catalog — docs/skills/index.md

**Files:**
- Rewrite: `docs/skills/index.md`

**Interfaces:**
- Consumes: skill descriptions from SKILL.md frontmatter; phase groupings from `tests/tiers/deps.json`
- Produces: the authoritative skill catalog referenced by README, architecture, and first-novel pages

- [ ] **Step 1: Write the complete skill catalog page**

Write the following content to `docs/skills/index.md`. Phase groupings and skill lists come from `tests/tiers/deps.json` `t2-phases[].prerequisites`. Descriptions are pulled from each skill's `SKILL.md` frontmatter `description` field (truncated to ~100 chars where needed). Chinese phase headers; English descriptions as-is from frontmatter.

The page structure is:

    # 技能目录 / Skill Catalog

    Shenbi 包含 67 个写作技能和 2 个元技能，按 9 个 T2 阶段组织。以下数据源自 tests/tiers/deps.json。

    Shenbi includes 67 writing skills and 2 meta-skills, organized by 9 T2 phases. All groupings below are sourced from tests/tiers/deps.json.

Then for each of the 9 phases, a section with bilingual header, a 1-2 sentence description, and a table of skills. The exact phase content:

**Genesis / 创世** (11 skills): worldbuilding, power-system, faction-builder, location-builder, character-design, relationship-map, story-architecture, volume-outlining, genre-config, pacing-design, book-spine-init

**Architecture / 架构** (5 skills): story-architecture, volume-outlining, pacing-design, plot-thread-weaver, genre-config. Note: some overlap with Genesis.

**Planning / 规划** (3 skills): chapter-planning, foreshadowing-plant, context-composing

**Drafting / 起草** (9 skills): chapter-drafting, state-settling, foreshadowing-track, style-polishing, review-resonance, anti-detect, length-normalizing, foreshadowing-recall, score-arc

**Audit / 审计** (18 skills): review-character, review-continuity, review-dialogue, review-pacing, review-anti-ai, review-foreshadowing, review-world-rules, review-sensitivity, review-memo-compliance, review-motivation, review-pov, review-reader-pull, review-highpoint, review-texture, review-long-span, review-era, review-fanfic, review-spinoff

**Foundation / 基设** (4 skills): foundation-review, chapter-revision, truth-sync, style-learning

**Management / 管理** (9 skills): snapshot-manage, drift-guidance, intent-management, chapter-pattern, volume-consolidation, review-arc-payoff, memory-distill, score-volume, score-stratum

**Import / 导入** (4 skills): import-analysis, character-extraction, world-extraction, canon-import

**Short Story / 短篇** (3 skills): short-outline, short-drafting, short-packaging

Then an **Out-of-Pipeline** section with three subsections:
- Auxiliary (4): market-radar, sequel-writing, anchor-curate, escalation-review
- Meta (2): using-shenbi, shenbi-writing-skills
- Drafting Helper (1): foreshadowing-resolve

Each table row: `| shenbi-<name> | <description from SKILL.md frontmatter> |`

End with a note: some skills appear in multiple phases (e.g., genre-config in both Genesis and Architecture). This reflects deps.json, not an error. Total unique: 69 (67 writing + 2 meta).

- [ ] **Step 2: Verify docs build**

Run: `uv run mkdocs build --strict`
Expected: Build succeeds.

- [ ] **Step 3: Verify skill count**

Skills appear in multiple phases (e.g., genre-config in both Genesis and Architecture), so total rows will exceed unique count. Verify both row count and unique count:

Run: `rg "^\\| shenbi-" docs/skills/index.md | wc -l`
Expected: 72 (total rows including cross-phase duplicates: 66 in phase tables + 4 auxiliary + 1 writing-skills + 1 foreshadowing-resolve)

Run: `rg "^\\| shenbi-" docs/skills/index.md | sed 's/| shenbi-//' | sed 's/ |.*//' | sort -u | wc -l`
Expected: 68 (unique shenbi-* skills: 67 functional + 1 meta writing-skills; using-shenbi is excluded by the regex)

Run: `rg "^\\| using-shenbi" docs/skills/index.md | wc -l`
Expected: 1

- [ ] **Step 4: Commit**

    git add docs/skills/index.md
    git commit -m "docs: rewrite skill catalog with all 69 skills grouped by 9 T2 phases"

---

### Task 3: Architecture overview — docs/architecture/overview.md

**Files:**
- Create: `docs/architecture/overview.md`

- [ ] **Step 1: Write the complete architecture overview page**

Write a page with 4 sections, each a few paragraphs with Mermaid diagrams. Bilingual (Chinese first, English below).

**Section 1: 流水线 / The Pipeline**

Mermaid diagram (use this exact code):

    ```mermaid
    graph LR
        subgraph Long-Form["长篇 / Long-Form"]
            G["创世<br/>Genesis"] --> A["架构<br/>Architecture"]
            A --> P["规划<br/>Planning"]
            P --> D["起草<br/>Drafting"]
            D --> AU["审计<br/>Audit"]
            AU --> F["基设<br/>Foundation"]
            F --> M["管理<br/>Management"]
        end
        subgraph Short["短篇 / Short-Form"]
            S["短篇<br/>Short Story"]
        end
        subgraph Import["导入 / Import-Form"]
            I["导入<br/>Import"]
        end
    ```

Table of 3 T3 pipelines (from deps.json `t3-pipelines`):

| Pipeline | Phase Sequence |
|----------|---------------|
| Long-form | genesis -> architecture -> planning -> drafting -> audit -> foundation -> management |
| Short-form | short-story |
| Import-form | import |

Note: data flows between phases via truth files.

**Section 2: 门控链 / The Gate Chain**

Table of G0-G7 (8 gates) with checkpoint and purpose:

| Gate | Checkpoint | Purpose |
|------|-----------|---------|
| G0 | Round creation | Environment integrity: tool hashes, fixture purity, progress.json consistency |
| G1 | Pre-dispatch | Input file validation |
| G2 | Output validation | Output file structure and content validation |
| G3 | Scoring readiness | Scoring precondition check |
| G4 | Skill quality | Skill-specific structural check + gate marker generation |
| G5 | Phase boundary | T2 phase transition validation |
| G6 | Pipeline integrity | T3 end-to-end validation |
| G7 | Post-round audit | Round closure audit: tool tamper, gate mismatch |

Mermaid gate chain flow (use this exact code):

    ```mermaid
    graph LR
        S["开始 / Start"] --> G0{"G0<br/>环境?"}
        G0 -->|Pass| G1{"G1<br/>输入?"}
        G0 -->|Fail| FIX["修复 / Fix"]
        FIX --> G0
        G1 -->|Pass| DISP["分派技能 / Dispatch"]
        G1 -->|Fail| FIX
        DISP --> G2{"G2<br/>输出?"}
        G2 -->|Pass| G4{"G4<br/>质量?"}
        G2 -->|Fail| DISP
        G4 -->|Pass| G3{"G3<br/>评分就绪?"}
        G4 -->|Fail| DISP
        G3 -->|Pass| SCORE["独立评分 / Score"]
        SCORE --> G7{"G7<br/>审计?"}
        G7 -->|Pass| DONE["完成 / Done"]
    ```

Caption below the diagram: "Note: This diagram shows the per-dispatch quality loop. G5 (phase boundary) and G6 (pipeline integrity) fire at T2 phase transitions and T3 pipeline boundaries respectively, outside this per-skill loop."

Gate rules: G0 block = fix and re-pass; G2/G4 fail = not scored; scoring must use independent subagent (G3.4).

**Section 3: 评分层级 / The Scoring Tiers**

Table of T1/T2/T3 with scope and threshold (94 for all, from acceptance.json):

| Tier | Scope | Threshold |
|------|-------|-----------|
| T1 | Per-skill | >= 94 |
| T2 | Per-phase (9 phases) | >= 94 |
| T3 | End-to-end (3 pipelines) | >= 94 |

Three test types: generative (generate output and score), bug-hunt (detect injected defects), clean (review clean input; hallucinated defect = score 0).

Convergence target: 100. Repair loop for <94: read scoring report, identify root cause (missing template / rubric conflict / output defect), fix and re-run.

**Section 4: 真相文件 / Truth Files**

Explanation: truth files persist project state between skills.

Table of 5 core categories (from truth-files.yaml, which defines 15 `kind` values total):

| Category | Example Files |
|----------|--------------|
| Config | `novel.json`, `genre-config.json` |
| World | `world/story_bible.md`, `world/rules.md`, `world/locations.md`, `world/power_system.md`, `world/factions.md` |
| Character | `characters/protagonist.md`, `characters/relationships.md` |
| Outline | `outline/story_frame.md`, `outline/volume_map.md`, `outline/rhythm_principles.md`, `outline/thread_map.md` |
| Truth | `truth/current_state.md`, `truth/pending_hooks.md`, `truth/chapter_summaries.md`, `truth/character_matrix.md`, `truth/emotional_arcs.md` |

Note: full 15 categories in `docs/framework/truth-files.yaml`.

Workflow: Read (skill reads truth files for current state) -> Execute (skill performs task) -> Update (state-settling extracts changes and updates truth files).

Mermaid truth file cycle (use this exact code):

    ```mermaid
    graph LR
        TF["真相文件<br/>Truth Files"] -->|读取 / Read| SK["技能执行<br/>Skill"]
        SK -->|产出 / Output| SS["状态结算<br/>State Settling"]
        SS -->|更新 / Update| TF
    ```

Reference: full vocabulary in `docs/framework/truth-files.yaml`.


- [ ] **Step 2: Verify docs build**

Run: `uv run mkdocs build --strict`
Expected: Build succeeds.

- [ ] **Step 3: Commit**

    git add docs/architecture/overview.md
    git commit -m "docs: add architecture overview with Mermaid pipeline and gate diagrams"

---

### Task 4: Landing page — docs/index.md

**Files:**
- Rewrite: `docs/index.md`

- [ ] **Step 1: Write the complete landing page**

Structure:

    # Shenbi (神笔)

Bilingual tagline (same as README). Then:

**解决什么问题 / The Problem** — 2-3 sentence paragraph explaining the problem (coordinating dozens of specialized tasks while maintaining consistency across hundreds of thousands of words).

**核心能力 / Core Capabilities** — Three subsections, each with a short bilingual paragraph and a link:
- 技能编排 / Skill Orchestration -> links to skills/index.md
- 质量门控 / Quality Gates -> links to architecture/overview.md
- 可测量的质量 / Measurable Quality -> links to architecture/overview.md

**从这里开始 / Get Started** — Two paths:
- 我想写小说 / I Want to Write a Novel -> links to getting-started/installation.md
- 我想理解框架 / I Want to Understand the Framework -> links to architecture/overview.md

- [ ] **Step 2: Verify docs build**

Run: `uv run mkdocs build --strict`
Expected: Build succeeds.

- [ ] **Step 3: Commit**

    git add docs/index.md
    git commit -m "docs: rewrite landing page with feature cards and dual audience paths"

---

### Task 5: Installation guide — docs/getting-started/installation.md

**Files:**
- Rewrite: `docs/getting-started/installation.md`

- [ ] **Step 1: Write the complete installation page**

Structure:

1. **前提条件 / Prerequisites** — Table: Python 3.11+, uv 0.5+ (recommended), just (latest). With install links.
2. **安装步骤 / Installation Steps** — Four numbered steps:
   - Clone: `git clone https://github.com/ThomasChangX/shenbi.git && cd shenbi`
   - Install: `uv sync --group dev`
   - Install docs (optional): `uv sync --group docs`
   - Pre-commit: `uv run pre-commit install`
3. **验证安装 / Verify Installation** — `just check`, `just test`, `just docs`
4. **常用命令 / Common Commands** — Table: just check, just test, just fix, just docs, just --list
5. **测试数据说明 / Test Data Note** — Brief callout: `tests/fixtures/` contains real skill outputs (not hand-crafted mocks, per G0.9). Round directories live under `tests/rounds/`. These are used by the testing framework, not required for normal novel writing.

- [ ] **Step 2: Verify docs build**

Run: `uv run mkdocs build --strict`
Expected: Build succeeds.

- [ ] **Step 3: Commit**

    git add docs/getting-started/installation.md
    git commit -m "docs: rewrite installation guide with prerequisites, steps, and verification"

---

### Task 6: Core concepts — docs/getting-started/concepts.md

**Files:**
- Rewrite: `docs/getting-started/concepts.md`

- [ ] **Step 1: Write the complete concepts page**

Five concepts, each 3-5 sentences bilingual (Chinese first, English below):

1. **技能 / Skill** — what a SKILL.md is, 9 pipeline phases, how agents discover skills via using-shenbi trigger map. Link to skills/index.md.
2. **真相文件 / Truth Files** — persistent project state. truth-files.yaml defines 15 `kind` values; the 5 core categories are config, world, character, outline, truth. State-settling updates them. Reference to truth-files.yaml for the full vocabulary. Core mechanism for consistency.
3. **门控 / Gates** — G0-G7, what each guards, "no gate skipped" principle, gate failure = rejected. Link to architecture overview.
4. **轮次 / Rounds** — what a round directory is, reproducibility property, command to create.
5. **评分层级 / Scoring Tiers** — T1/T2/T3 table with scope, 94 threshold, 100 convergence target, three test types. Link to architecture overview.

- [ ] **Step 2: Verify docs build**

Run: `uv run mkdocs build --strict`
Expected: Build succeeds.

- [ ] **Step 3: Commit**

    git add docs/getting-started/concepts.md
    git commit -m "docs: rewrite core concepts with 5 concepts (skills, truth files, gates, rounds, scoring)"

---

### Task 7: First novel walkthrough — docs/getting-started/first-novel.md

**Files:**
- Rewrite: `docs/getting-started/first-novel.md`

**Interfaces:**
- Consumes: long-form T3 pipeline order from `deps.json` `t3-pipelines.long-form.prerequisites`

- [ ] **Step 1: Write the complete first-novel walkthrough**

Follow the actual long-form T3 pipeline order: genesis -> architecture -> planning -> drafting -> audit -> foundation -> management. For each phase, provide:

- Bilingual heading
- 1-2 sentence description of what it does
- Skill list (from deps.json, exact skill names)
- Truth files read/written (specific file paths, see mapping below)
- Example dispatch command

Prerequisites section at top: Shenbi installed + seed file.

**Phase-to-truth-file mapping** (use these exact file references per phase):

- **Genesis**: Reads: `novel.json` (config). Writes: `world/story_bible.md`, `world/rules.md`, `world/locations.md`, `world/power_system.md`, `world/factions.md`, `characters/protagonist.md`, `characters/relationships.md`, `outline/story_frame.md`, `outline/volume_map.md`
- **Architecture**: Reads: `outline/story_frame.md`, `outline/volume_map.md`. Writes: `outline/rhythm_principles.md`, `outline/thread_map.md`
- **Planning**: Reads: `outline/` files, `truth/current_state.md`. Writes: `plans/chapter-N-plan.md` (kind: plan), `truth/pending_hooks.md`
- **Drafting**: Reads: `plans/chapter-N-plan.md`, `truth/current_state.md`, `truth/pending_hooks.md`. Writes: `chapters/chapter-N.md` (kind: chapter), `truth/current_state.md` (updated), `truth/chapter_summaries.md`
- **Audit**: Reads: all truth files + `chapters/chapter-N.md`. Writes: `audits/` directory reports (kind: report)
- **Foundation**: Reads: `world/`, `characters/`, `outline/`, `truth/` (all). Writes: revised chapters, `truth/` (updated via truth-sync)
- **Management**: Reads: `truth/` (all), `audits/`. Writes: `truth/drift_guidance.md`, `truth/volume_summaries.md` (kind: truth), `audits/` scoring reports

Bottom section: Other Pipelines — brief mention of short-form (short-outline -> short-drafting -> short-packaging) and import-form (import-analysis -> character-extraction/world-extraction -> canon-import).

> Note: the skill lists per phase are the same as in Task 2 (sourced from deps.json). Truth file categories come from `docs/framework/truth-files.yaml`.

Closing: after completion, run `uv run shenbi-summarize <round_dir>` and `uv run shenbi-validate G7 <round_dir>`. Reference command-to-give.md for full protocol.

- [ ] **Step 2: Verify docs build**

Run: `uv run mkdocs build --strict`
Expected: Build succeeds.

- [ ] **Step 3: Commit**

    git add docs/getting-started/first-novel.md
    git commit -m "docs: rewrite first-novel walkthrough following actual long-form pipeline order"

---

### Task 8: README — README.md (root)

**Files:**
- Rewrite: `README.md`

- [ ] **Step 1: Write the complete README**

Structure:
1. Title + bilingual tagline
2. Badges: CI (ci.yml), Docs (docs.yml), Python 3.11+, MIT
3. **什么是 Shenbi / What is Shenbi** — ~150 words bilingual. Problem + solution (67 skills + 2 meta, 8 gates (G0-G7), T1/T2/T3, truth files)
4. **为什么选择 Shenbi / Why Shenbi** — 3 bilingual bullets: skill orchestration, quality gates, measurable quality
5. **快速开始 / Quick Start** — clone, uv sync, just check
6. **文档 / Documentation** — links to docs site (thomaschangx.github.io/shenbi/) with descriptions
7. **技能一览 / Skills at a Glance** — table of 9 phases + out-of-pipeline with skill counts and descriptions
8. **贡献 / Contributing** — link to CONTRIBUTING.md + roadmap.md
9. **License** — MIT

Badge URLs: `https://github.com/ThomasChangX/shenbi/actions/workflows/ci.yml/badge.svg`

- [ ] **Step 2: Commit**

    git add README.md
    git commit -m "docs: rewrite README with bilingual pitch, badges, skill overview, and doc links"

---

### Task 9: Update mkdocs.yml nav + final verification

**Files:**
- Modify: `mkdocs.yml`

- [ ] **Step 1: Update the nav section in mkdocs.yml**

Replace the existing `nav` with an additive nav. New entries use bilingual labels; existing entries keep their current labels.

Note: the existing nav has `Skills` as a nested section (`Skills: - Index: skills/index.md`). The new nav flattens this to a direct page (`技能目录 / Skills: skills/index.md`). This is an intentional structural change consistent with the spec, not a pure addition. All other existing entries (Framework, API, Architecture Decisions) are preserved exactly.

The proposed nav:

    nav:
      - 首页 / Home: index.md
      - 快速开始 / Getting Started:
          - 安装 / Installation: getting-started/installation.md
          - 核心概念 / Concepts: getting-started/concepts.md
          - 第一本小说 / Your First Novel: getting-started/first-novel.md
      - 技能目录 / Skills: skills/index.md
      - 架构概览 / Architecture: architecture/overview.md
      - Framework:
          - Gates: framework/gates.md
          - Scoring: framework/scoring.md
          - Dispatcher: framework/dispatcher.md
          - Logging: framework/logging.md
      - API:
          - Exceptions: api/exceptions.md
          - Logging: api/logging.md
      - Architecture Decisions: adr/index.md

- [ ] **Step 2: Build docs site in strict mode**

Run: `uv run mkdocs build --strict`
Expected: Build succeeds with zero warnings or errors.

- [ ] **Step 3: Run full CI checks**

Run: `just check`
Expected: All checks pass.

- [ ] **Step 4: Commit**

    git add mkdocs.yml
    git commit -m "docs: update nav with bilingual labels for Wave 1 pages, preserve existing entries"

This completes Wave 1 of the documentation redesign.

> **Note for Wave 2:** The existing `docs/framework/gates.md` says "7 validation gates" but lists G0-G7 (8 gates). This pre-existing typo should be fixed when the framework docs are expanded in Wave 2. Wave 1 correctly uses "8 gates (G0-G7)" throughout.
