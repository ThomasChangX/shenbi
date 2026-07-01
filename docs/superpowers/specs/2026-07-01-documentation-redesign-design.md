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
3. **What is Shenbi / 什么是 Shenbi**: ~150 words. Core problem (writing a full novel with AI agents means orchestrating dozens of specialized tasks while keeping consistency across hundreds of pages). What Shenbi provides (67 writing skills + 2 meta-skills, 7-gate quality system, three-tier testing framework across 3 pipelines, truth files). Chinese version follows English, same content.
4. **Why Shenbi / 为什么选择 Shenbi**: three bullet points:
   - Skill orchestration: 67 writing skills + 2 meta-skills cover worldbuilding through anti-AI-detection, organized by pipeline phase
   - Quality gates: 7 validation gates (G0-G7) enforce integrity at every stage — no stage can be skipped
   - Measurable quality: T1/T2/T3 scoring against rubrics, 0-100, with convergence targets
5. **Quick start / 快速开始**: clone, uv sync, just check
6. **Documentation / 文档**: links to published docs site with one-line descriptions
7. **Skills at a glance / 技能一览**: compact table of 9 pipeline phases + out-of-pipeline group, with one-line description per phase. Per-phase skill counts sourced from `tests/tiers/deps.json`. No full catalog (that's the skills/ page).
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

Walks through the long-form T3 pipeline (genesis -> architecture -> planning -> drafting -> audit -> foundation -> management) as a narrative. This follows the actual `t3-pipelines.long-form.prerequisites` order from `tests/tiers/deps.json`. The walkthrough also briefly mentions the short-form and import-form pipelines so readers know those exist.

1. Genesis (创世) — worldbuilding, power system, factions, locations, character design, relationship map, story architecture, volume outlining, genre config, pacing, book spine init
2. Architecture (架构) — story architecture, volume outlining, pacing, plot thread weaver, genre config (note: some skills overlap with genesis)
3. Planning (规划) — chapter planning, foreshadowing plant, context composing
4. Drafting (起草) — chapter drafting, state settling, foreshadowing track/recall, style polishing, anti-detect, length normalizing, score arc
5. Audit (审计) — 18 review skills (review-character, review-continuity, review-dialogue, review-pacing, review-anti-ai, etc.)
6. Foundation (基设) — foundation review, chapter revision, truth sync, style learning
7. Management (管理) — snapshot manage, drift guidance, intent management, chapter pattern, volume consolidation, review arc payoff, memory distill, score volume, score stratum

Each phase: what it does, which skills are involved (from deps.json prerequisites), what truth files it reads/writes, and a command example. Goal: someone reads this and understands the shape of writing a novel with Shenbi.

### docs/skills/index.md — Full skill catalog

Single comprehensive page listing all 69 skills grouped by T2 phase, sourced from `tests/tiers/deps.json` → `t2-phases`. For each phase, a table:

```
## Genesis / 创世

| Skill | Description |
|-------|-------------|
| shenbi-worldbuilding | 世界观构建 — Build the world... |
| shenbi-power-system | 力量体系 — Design the magic/power system... |
```

Table pulls `name` and `description` from each SKILL.md frontmatter directly — no manual summarizing. Bilingual headers per phase.

**9 T2 phases** (from `deps.json` `t2-phases[].prerequisites`):
1. Genesis (创世) — worldbuilding, power-system, faction-builder, location-builder, character-design, relationship-map, story-architecture, volume-outlining, genre-config, pacing-design, book-spine-init (11 skills)
2. Architecture (架构) — story-architecture, volume-outlining, pacing-design, plot-thread-weaver, genre-config (5 skills; some overlap with genesis)
3. Planning (规划) — chapter-planning, foreshadowing-plant, context-composing (3 skills)
4. Drafting (起草) — chapter-drafting, state-settling, foreshadowing-track, style-polishing, review-resonance, anti-detect, length-normalizing, foreshadowing-recall, score-arc (9 skills)
5. Audit (审计) — 18 review skills (review-character through review-spinoff)
6. Foundation (基设) — foundation-review, chapter-revision, truth-sync, style-learning (4 skills)
7. Management (管理) — snapshot-manage, drift-guidance, intent-management, chapter-pattern, volume-consolidation, review-arc-payoff, memory-distill, score-volume, score-stratum (9 skills)
8. Import (导入) — import-analysis, character-extraction, world-extraction, canon-import (4 skills)
9. Short Story (短篇) — short-outline, short-drafting, short-packaging (3 skills)

**Out-of-pipeline skills** (from `deps.json` `_out_of_pipeline`):
- Auxiliary: market-radar, sequel-writing, anchor-curate, escalation-review (4 skills)
- Meta: using-shenbi, shenbi-writing-skills (2 skills)
- Drafting helper: foreshadowing-resolve (1 skill)

Note: skills can appear in multiple phases (e.g., genre-config is in both genesis and architecture). Phase assignments come exclusively from `deps.json`, NOT from SKILL.md frontmatter (which has no phase field). The implementer must source all phase groupings from `deps.json` `t2-phases` and `_out_of_pipeline`.

### docs/architecture/overview.md — How it fits together

Four sections, each a few paragraphs with Mermaid diagrams:

1. **The pipeline** — visual showing the 9 T2 phases flowing left to right (genesis -> architecture -> planning -> drafting -> audit -> foundation -> management, with import and short-story as parallel tracks), truth files passed between them. Also shows the 3 T3 pipelines: long-form (the main 7-phase sequence), short-form (short-story phase only), and import-form (import phase only). Mental model for the orchestration contribution.
2. **The gate chain** — G0 through G7, what boundary each guards, the rule that no gate can be skipped. Table or sequence diagram.
3. **The scoring tiers** — T1 (per-skill), T2 (per-phase, 9 phases), T3 (end-to-end, 3 pipelines: long-form, short-form, import-form). The 0-100 rubric system, 94 threshold for advancement, convergence toward 100.
4. **Truth files** — state management backbone. How truth files flow through the pipeline, how skills read and update them, why this keeps a 200,000-word novel from contradicting itself.

Bilingual throughout. Mermaid diagrams require configuration beyond mkdocs-material defaults — see Implementation Notes.

## Implementation Notes

- All new pages are bilingual (Chinese-primary, English secondary). Each section presents Chinese first, then the English translation below it. This is consistent across all Wave 1 pages.
- Skill descriptions in the catalog are pulled from SKILL.md frontmatter, not hand-written.
- **Mermaid rendering is not configured.** `mkdocs.yml` has no `markdown_extensions` section. mkdocs-material does NOT render ` ```mermaid ` blocks out of the box — it requires `pymdownx.superfences` with a mermaid custom fence, or the `mkdocs-mermaid2-plugin`. The implementer must add this configuration to `mkdocs.yml` as a prerequisite task before the architecture page can use diagrams. Example config:
  ```yaml
  markdown_extensions:
    - pymdownx.superfences:
        custom_fences:
          - name: mermaid
            class: mermaid
            format: !!python/name:pymdownx.superfences.fence_code_format
  ```
- **Nav policy: additive, not replacement.** The proposed nav entries (Home, Getting Started, Skills, Architecture) are INSERTED into the existing nav. The existing Framework, API, and Architecture Decisions sections remain. The implementer should preserve all existing nav entries and add the new ones. The bilingual label convention ("首页 / Home") is an intentional style change applied to the new entries only; existing entries keep their current labels until Wave 2.
- **Phase data source of truth.** All phase groupings, skill-to-phase assignments, and pipeline definitions come from `tests/tiers/deps.json`. Do NOT derive phases from SKILL.md content or from prose descriptions. `deps.json` is the single authoritative source.
- **Factual claims data sources.** For auditability:
  - Skill count, phase groupings, pipeline definitions: `tests/tiers/deps.json`
  - Scoring thresholds: `tests/tiers/acceptance.json`
  - Gate definitions: `docs/framework/gates.md`, `src/shenbi/gates/`
  - Truth file structure: `docs/framework/truth-files.yaml`, `docs/framework/truth-files.index.json`
  - Python version: `pyproject.toml` `requires-python`
- `docs/roadmap.md` exists and should be linked from the README or landing page.
- README badge URLs need to be constructed from the actual CI workflow file names.
- The existing `docs/framework/` pages (gates.md, scoring.md, dispatcher.md, logging.md) remain as-is until Wave 2. They are linked from the existing nav entries but not cross-linked from new Wave 1 pages.

## Wave 2 (Deferred)

After Wave 1 ships:
- Individual skill detail pages
- Gate internals deep-dive (expand framework/gates.md)
- Scoring mechanics deep-dive (expand framework/scoring.md)
- API reference pages
- "How to add a new skill" contributor guide
- ADR index cleanup
