# Clean Test: shenbi-review-foreshadowing

## Skill Under Test
`skills/shenbi-review-foreshadowing/SKILL.md`

## Test Setup
A novel project exists with drafted chapters 5-6 at `drafts/chapter-5.md` and `drafts/chapter-6.md`. The foreshadowing pool at `truth/foreshadowing_pool.md` tracks all hooks. Every hook state transition has proper text evidence citing chapter and specific prose passage.

## Scenario
No defects. All hook lifecycle transitions have complete text evidence with chapter citations and prose passage references.

## Agent Task
Run shenbi-review-foreshadowing audit on chapters 5-6. Expected: report zero issues.
