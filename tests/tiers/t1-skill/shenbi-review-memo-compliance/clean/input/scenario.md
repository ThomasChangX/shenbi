# Clean Test: shenbi-review-memo-compliance

## Skill Under Test
`skills/shenbi-review-memo-compliance/SKILL.md`

## Test Setup
A novel project exists with chapter memo at `plans/chapter-5-plan.md` and drafted chapter 5 at `drafts/chapter-5.md`. The memo has 8 sections. All 8 sections are fully fulfilled in the drafted chapter. Every required scene, plot point, and element specified in the memo is present.

## Scenario
No defects. All 8 memo sections are correctly fulfilled. The chapter fully complies with its memo.

## Agent Task
Run shenbi-review-memo-compliance audit on chapter 5. Expected: report zero issues, all sections "fulfill".
