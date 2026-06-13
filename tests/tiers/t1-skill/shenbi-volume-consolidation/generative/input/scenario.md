# Generative Test: shenbi-volume-consolidation

## Skill Under Test
`skills/shenbi-volume-consolidation/SKILL.md`

## Test Setup
A novel project has completed Volume 2 (chapters 11-22). Chapter drafts exist at `tests/fixtures/chapter-draft-example.md` (representing the full chapter range). Per-chapter summaries exist at `tests/fixtures/chapter-summaries-example.md`. The pending hooks file is at `tests/fixtures/pending-hooks-example.md` with hooks planted across chapters 11-22 in various states (some RESOLVED, some ACTIVE).

## Agent Task
Run shenbi-volume-consolidation to consolidate Volume 2. The agent must:
1. Produce a volume summary ≤500 words
2. List every unresolved hook (status ≠ RESOLVED) from pending_hooks.md
3. Archive per-chapter summaries at expected paths
4. Ensure every major event in the summary is traceable to a specific chapter
5. Include only events affecting character arcs, plot threads, or world state

## Seed Input
Chapter drafts from `tests/fixtures/chapter-draft-example.md` (representing the full chapter range), chapter summaries from `tests/fixtures/chapter-summaries-example.md`, pending hooks from `tests/fixtures/pending-hooks-example.md`
