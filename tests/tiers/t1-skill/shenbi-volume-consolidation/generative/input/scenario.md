# Generative Test: shenbi-volume-consolidation

## Skill Under Test
`skills/shenbi-volume-consolidation/SKILL.md`

## Test Setup
A novel project has completed Volume 2 (chapters 11-22). Chapter drafts exist at `drafts/chapter-11.md` through `drafts/chapter-22.md`. Per-chapter summaries exist at `truth/chapter_summaries.md`. The pending hooks file is at `truth/pending_hooks.md` with hooks planted across chapters 11-22 in various states (some RESOLVED, some ACTIVE).

## Agent Task
Run shenbi-volume-consolidation to consolidate Volume 2. The agent must:
1. Produce a volume summary ≤500 words
2. List every unresolved hook (status ≠ RESOLVED) from pending_hooks.md
3. Archive per-chapter summaries at expected paths
4. Ensure every major event in the summary is traceable to a specific chapter
5. Include only events affecting character arcs, plot threads, or world state

## Seed Input
Chapter drafts from `drafts/chapter-11.md` through `drafts/chapter-22.md`, chapter summaries from `truth/chapter_summaries.md`, pending hooks from `truth/pending_hooks.md`
