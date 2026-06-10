# Clean Test: shenbi-truth-sync

## Skill Under Test
`skills/shenbi-truth-sync/SKILL.md`

## Test Setup
A novel project has chapters 1-18 completed. The truth sync scope is set to chapters 15-18. All chapter content in this scope is consistent with the existing truth files. The sync output at `sync/truth-sync-15-18.md` is fully correct:
- All extracted facts faithfully represent chapter text
- All conflicts between chapter text and truth files detected and flagged
- Only changed portions updated (incremental)
- Before/after diffs preserved for all updates
- Only chapters 15-18 processed (scope respected)

## Scenario
All truth-sync output is correct and follows all skill rules. No defects present.

## Agent Task
Run shenbi-truth-sync quality check on the sync output. Expected result: report zero issues.
