# Generative Test: shenbi-truth-sync

## Skill Under Test
`skills/shenbi-truth-sync/SKILL.md`

## Test Setup
A novel project has chapters 1-25 completed. The truth sync scope is set to chapters 20-25. These chapters contain several state changes: a character alliance formed, a location discovered, a magical artifact obtained, a political faction dissolved. Truth files exist at `truth/` including character profiles, location registry, item tracker, faction records, and relationship map.

## Agent Task
Run shenbi-truth-sync to synchronize chapters 20-25 with the truth files. The agent must:
1. Extract all facts from chapters 20-25 that affect truth files
2. Detect every inconsistency between chapter text and existing truth file entries
3. Update only the changed portions incrementally
4. Preserve before/after diffs for auditability
5. Stay within the scope of chapters 20-25 only

## Seed Input
Chapter drafts from `drafts/chapter-20.md` through `drafts/chapter-25.md`, truth files from `truth/`
