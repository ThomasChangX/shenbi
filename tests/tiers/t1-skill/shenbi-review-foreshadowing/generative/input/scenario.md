# Generative Test: shenbi-review-foreshadowing

## Skill Under Test
`skills/shenbi-review-foreshadowing/SKILL.md`

## Test Setup
A novel project exists with drafted chapters 9-11 at `drafts/chapter-9.md` through `drafts/chapter-11.md`. The foreshadowing pool at `truth/foreshadowing_pool.md` tracks all hooks.

## Agent Task
Run shenbi-review-foreshadowing audit on chapters 9-11. Produce a complete foreshadowing audit report including:
1. Hook lifecycle tracking table with all state transitions
2. Text evidence for each transition (chapter + prose passage)
3. Consistency check against foreshadowing pool
4. Abandonment detection for unresolved hooks

## Seed Input
Drafted chapters from `drafts/chapter-9.md` through `drafts/chapter-11.md`, foreshadowing pool from `truth/foreshadowing_pool.md`
