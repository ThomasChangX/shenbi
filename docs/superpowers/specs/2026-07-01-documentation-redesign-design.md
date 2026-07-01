# Documentation Redesign — Wave 1

**Date**: 2026-07-01
**Status**: Approved (design phase)
**Scope**: Wave 1 only (user-facing + architecture overview); Wave 2 (developer reference) deferred.

## Problem

Shenbi's documentation does not match the substance of the project. The actual project contains 69 novel-writing skills, a 7-gate quality system (G0-G7), a three-tier testing framework (T1/T2/T3), truth-file state management, and a detailed execution protocol. But the documentation surface is almost entirely stubs:

- README: two lines ("Novel-writing AI skill framework")
- docs/index.md: four lines
- Getting-started guides: 3-8 sentences each, no actual walkthrough
- Framework docs: one-liners that don't explain concepts
- No skill catalog, no architecture overview, no "why does this exist"

There is a massive gap between the richness of the project and what the docs communicate. The internal protocol docs (`command-to-give.md`, `goal-prompt.md`) are dense and detailed but are in Chinese, oriented toward execution, and not structured for onboarding.

## Goals

- Serve two audiences: novel writers using AI (user guide) and framework developers/contributors (architecture reference).
- Language: bilingual, Chinese-primary, with English translations for key pages.
- Core framing: Shenbi's contribution is (1) orchestration of many specialized skills and (2) a rigorous testing/scoring framework that measures whether those skills work.
- Ship Wave 1 as a complete, credible documentation surface. Wave 2 (developer deep-dive) comes later.

## Non-Goals (Wave 2)

- Individual skill detail pages (auto-generated from SKILL.md metadata).
- Gate internals deep-dive (how each G0-G7 check works internally).
- Scoring mechanics deep-dive (rubric structure, dimension weights, conservative merge).
- API reference pages (already exist as stubs, remain stubs until Wave 2).
- "How to add a new skill" contributor guide.
- ADR reorganization.

## Approach

Phased rollout (Approach C modified). Wave 1 delivers everything a user needs plus a concise architecture overview so readers immediately understand what makes Shenbi different. The deep-dive developer reference is deferred to Wave 2.

## Information Architecture

```
docs/
  index.md                      # Landing: what is Shenbi, why it exists, key links
  getting-started/
    installation.md             # Real setup guide (uv, just, Python 3.11+)
    concepts.md                 # Core vocabulary: skills, gates, truth files, rounds
    first-novel.md              # End-to-end workflow walkthrough by pipeline phase
  skills/
    index.md                    # Full skill catalog: 69 skills grouped by phase
  architecture/
    overview.md                 # How it fits together: pipeline, gates, scoring, truth files
  (existing framework/, api/, adr/ remain untouched until Wave 2)
```

Root README gets a full rewrite (bilingual, elevator pitch, quick start, badge row).

mkdocs nav (Wave 1):

```yaml
nav:
  - 首页 / Home: index.md
  - 快速开始 / Getting Started:
      - 安装 / Installation: getting-started/installation.md
      - 核心概念 / Concepts: getting-started/concepts.md
      - 第一本小说 / Your First Novel: getting-started/first-novel.md
  - 技能目录 / Skills: skills/index.md
  - 架构概览 / Architecture: architecture/overview.md
```

Audience separation: getting-started is for someone who wants to *use* Shenbi (workflow-oriented). Architecture is for someone who wants to *understand* it (gate chain, scoring tiers, truth-file lifecycle). Both audiences hit the landing page, then diverge.

## Page Specifications

### README.md (root)

The single most important page. Must work for a GitHub visitor who has never heard of Shenbi and someone who cloned the repo.

Structure:
1. **Title + bilingual one-liner**: `# Shenbi (神笔)` + bilingual tagline
2. **Badges**: CI, License, Python version
3. **What is Shenbi / 什么是 Shenbi**: ~150 words. Core problem (writing a full novel with AI agents means orchestrating dozens of specialized tasks while keeping consistency across hundreds of pages). What Shenbi provides (69 skills, 7-gate quality system, three-tier testing framework, truth files). Chinese version follows English, same content.
4. **Why Shenbi / 为什么选择 Shenbi**: three bullet points:
   - Skill orchestration: 69 specialized skills cover worldbuilding through anti-AI-detection, organized by pipeline phase
   - Quality gates: 7 validation gates (G0-G7) enforce integrity at every stage — no stage can be skipped
   - Measurable quality: T1/T2/T3 scoring against rubrics, 0-100, with convergence targets
5. **Quick start / 快速开始**: clone, uv sync, just check
6. **Documentation / 文档**: links to published docs site with one-line descriptions
7. **Skills at a glance / 技能一览**: compact table of 7 pipeline phases, skill count per phase, one-line description. No full catalog (that's the skills/ page).
8. **Contributing / 贡献**: link to CONTRIBUTING.md
9. **License**: MIT

Bilingual sections are stacked (English then Chinese), not side-by-side.

### docs/index.md — Landing page

Not a stub. Opens with the same bilingual one-liner as the README, then a short "what problem does this solve" paragraph, then three feature cards (skill orchestration, quality gates, measurable quality) each linking to the relevant page. Ends with two clear paths: "I want to write a novel / 我想写小说" -> getting-started, and "I want to understand the framework / 我想理解框架" -> architecture.

### docs/getting-started/installation.md — Setup guide

Expand from current 4 lines. Cover:
- Prerequisites: Python 3.11+, uv 0.5+, just
- Clone and sync commands
- Verifying the install (`just check` passes)
- Note about test fixtures and round directories
- Bilingual

### docs/getting-started/concepts.md — Core vocabulary

Five concepts a user needs before anything makes sense:
1. **Skill (技能)** — what a SKILL.md is, how skills are organized by phase, how an agent discovers and loads them
2. **Truth files (真相文件)** — project state files that persist between skills; backbone of consistency
3. **Gates (门控)** — G0-G7, what each guards, the "no gate skipped" principle
4. **Rounds (轮次)** — what a round directory is, why it matters for reproducibility
5. **Scoring tiers (评分层级)** — T1/T2/T3, what each measures, the 94 threshold

Each concept: 3-5 sentences, bilingual. Enough to orient, not a deep dive (architecture page handles that).

### docs/getting-started/first-novel.md — End-to-end workflow

Walks through the actual pipeline phases as a narrative:
1. Genesis (创世) — worldbuilding, power system, factions, locations
2. Foundation (基设) — character design, relationship map
3. Architecture (架构) — story frame, volume map, pacing
4. Planning (规划) — chapter planning, context composing
5. Drafting (起草) — chapter drafting, foreshadowing plant/track
6. Audit (审计) — style polishing, anti-detect, length normalizing, review skills
7. Revision (修正) — chapter revision, state settling, drift guidance

Each phase: what it does, which skills are involved, what truth files it reads/writes, and a command example. Goal: someone reads this and understands the shape of writing a novel with Shenbi.

### docs/skills/index.md — Full skill catalog

Single comprehensive page listing all 69 skills grouped by pipeline phase. For each phase, a table:

```
## Genesis / 创世

| Skill | Description |
|-------|-------------|
| shenbi-worldbuilding | 世界观构建 — Build the world... |
| shenbi-power-system | 力量体系 — Design the magic/power system... |
```

Table pulls `name` and `description` from each SKILL.md frontmatter directly — no manual summarizing. Bilingual headers per phase.

7 phases:
1. Genesis (创世) — worldbuilding, power system, factions, locations, genre config
2. Foundation (基设) — character design, relationship map, state settling
3. Architecture (架构) — story frame, volume map, pacing, plot thread weaver
4. Planning (规划) — chapter planning, context composing, foreshadowing plant
5. Drafting (起草) — chapter drafting, foreshadowing track/resolve, short drafting
6. Audit (审计) — style polishing, anti-detect, length normalizing, review skills
7. Management (管理) — truth sync, snapshot, drift guidance, sequels, imports

Meta-skills (using-shenbi, shenbi-writing-skills) get their own section at the bottom.

Note: the current `docs/skills/index.md` lists a different phase grouping. The rewrite uses the corrected phase mapping above. Skill-to-phase assignments will be verified against actual SKILL.md content during implementation.

### docs/architecture/overview.md — How it fits together

Four sections, each a few paragraphs with Mermaid diagrams:

1. **The pipeline** — visual showing 7 phases flowing left to right, truth files passed between them. Mental model for the orchestration contribution.
2. **The gate chain** — G0 through G7, what boundary each guards, the rule that no gate can be skipped. Table or sequence diagram.
3. **The scoring tiers** — T1 (per-skill), T2 (per-phase), T3 (end-to-end). The 0-100 rubric system, 94 threshold for advancement, convergence toward 100.
4. **Truth files** — state management backbone. How truth files flow through the pipeline, how skills read and update them, why this keeps a 200,000-word novel from contradicting itself.

Bilingual throughout. Mermaid diagrams (mkdocs-material supports them natively).

## Implementation Notes

- All new pages are bilingual (Chinese-primary, English secondary). Each section presents Chinese first, then the English translation below it. This is consistent across all Wave 1 pages.
- Skill descriptions in the catalog are pulled from SKILL.md frontmatter, not hand-written.
- Mermaid diagrams need `charset="utf-8"` consideration if they contain CJK text (per CLAUDE.md note about DOT/rendering).
- mkdocs.yml nav must be updated to reflect the new structure.
- The existing `docs/framework/` pages (gates.md, scoring.md, dispatcher.md, logging.md) remain as-is until Wave 2. They are not linked from the new Wave 1 pages to avoid confusion.
- README badge URLs need to be constructed from the actual CI workflow file names.

## Wave 2 (Deferred)

After Wave 1 ships:
- Individual skill detail pages
- Gate internals deep-dive (expand framework/gates.md)
- Scoring mechanics deep-dive (expand framework/scoring.md)
- API reference pages
- "How to add a new skill" contributor guide
- ADR index cleanup
