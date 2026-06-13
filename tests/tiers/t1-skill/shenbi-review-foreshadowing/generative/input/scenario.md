# Generative Test: shenbi-review-foreshadowing

## Skill Under Test
`skills/shenbi-review-foreshadowing/SKILL.md`

## Test Setup
A novel project exists with drafted chapters 9-11 at `tests/fixtures/chapter-draft-example.md` (representing the full chapter range). The foreshadowing pool at `tests/fixtures/pending-hooks-example.md` tracks all hooks.

## Agent Task
Run shenbi-review-foreshadowing audit on chapters 9-11. Produce a complete foreshadowing audit report including:
1. Hook lifecycle tracking table with all state transitions
2. Text evidence for each transition (chapter + prose passage)
3. Consistency check against foreshadowing pool
4. Abandonment detection for unresolved hooks

## Seed Input
Drafted chapters from `tests/fixtures/chapter-draft-example.md` (representing the full chapter range), foreshadowing pool from `tests/fixtures/pending-hooks-example.md`
