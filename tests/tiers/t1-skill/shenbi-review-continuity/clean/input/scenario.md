# Clean Test: shenbi-review-continuity

## Skill Under Test
`skills/shenbi-review-continuity/SKILL.md`

## Test Setup
A novel project exists with drafted chapters 4-6 at `drafts/chapter-4.md` through `drafts/chapter-6.md`. Chapter summaries at `truth/chapter_summaries.md`. All time markers are consistent across chapters. Character states, locations, and objects are consistent.

## Scenario
No defects. All timeline markers, character continuity, setting continuity, and object continuity are correct and consistent.

## Agent Task
Run shenbi-review-continuity audit on chapters 4-6. Expected: report zero issues.
